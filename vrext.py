"""
Vrext v1.1 Parser
AI-to-AI Communication Language
"""

import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional, Union


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class VrextValue:
    """A parsed field value with optional modifiers."""
    raw: str
    value: Any                          # str, list, dict, or float (for Q)
    reason: Optional[str] = None        # ∵ because
    conclusion: Optional[str] = None    # ∴ therefore
    leads_to: Optional[str] = None      # → produces
    count: Optional[int] = None         # × multiplier
    approximate: bool = False           # ~ prefix
    critical: bool = False              # ! prefix
    unknown: bool = False               # ?
    confidence: Optional[float] = None  # inline Q:


@dataclass
class VrextMessage:
    """A fully parsed Vrext message."""
    fields: dict[str, list[VrextValue]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    # Convenience accessors
    def get(self, code: str) -> Optional[list[VrextValue]]:
        return self.fields.get(code.upper())

    def first(self, code: str) -> Optional[VrextValue]:
        vals = self.get(code)
        return vals[0] if vals else None

    def is_expired(self) -> bool:
        ts = self.first("TS")
        ttl = self.first("TTL")
        if not ts or not ttl:
            return False
        try:
            created = float(ts.value)
            expiry = float(ttl.value)
            return time.time() > created + expiry
        except (ValueError, TypeError):
            return False

    def confidence(self) -> float:
        q = self.first("Q")
        if q is None:
            return 0.5
        try:
            return float(q.value)
        except (ValueError, TypeError):
            return 0.5


# ---------------------------------------------------------------------------
# Known field codes
# ---------------------------------------------------------------------------

KNOWN_FIELDS = {
    "VER", "TS", "TTL", "T", "S", "V", "N", "X", "B", "R",
    "C", "A", "$", "#", "P", "Q", "SEQ", "RLY",
}


# ---------------------------------------------------------------------------
# Value parser
# ---------------------------------------------------------------------------

def _parse_array(raw: str) -> list[str]:
    """Parse [a,b,c] into ['a','b','c']. Returns None if malformed."""
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1]
        return [item.strip() for item in inner.split(",") if item.strip()]
    return None


def _parse_kv_array(raw: str) -> dict[str, str]:
    """Parse [a=1,b=2] into {'a':'1','b':'2'}."""
    items = _parse_array(raw)
    if items is None:
        return None
    result = {}
    for item in items:
        if "=" in item:
            k, _, v = item.partition("=")
            result[k.strip()] = v.strip()
        else:
            result[item] = None
    return result


def _parse_confidence(raw: str) -> tuple[str, Optional[float]]:
    """Strip trailing Q:0.x from a value string. Returns (cleaned, confidence)."""
    pattern = r"\s+Q:([\d.]+)$"
    m = re.search(pattern, raw)
    if m:
        try:
            q = float(m.group(1))
            q = max(0.0, min(1.0, q))
            return raw[:m.start()], q
        except ValueError:
            return raw, None
    return raw, None


def _parse_value(raw: str) -> VrextValue:
    """Parse a single value string into a VrextValue."""
    original = raw.strip()
    critical = False
    approximate = False
    unknown = False
    reason = None
    conclusion = None
    leads_to = None
    count = None
    confidence = None

    # Strip inline confidence Q:
    raw, confidence = _parse_confidence(original)
    raw = raw.strip()

    # Critical flag !
    if raw.startswith("!"):
        critical = True
        raw = raw[1:].strip()

    # Unknown ?
    if raw == "?":
        return VrextValue(
            raw=original, value=None, unknown=True,
            critical=critical, confidence=confidence
        )

    # Approximate ~
    if raw.startswith("~"):
        approximate = True
        raw = raw[1:].strip()

    # ∵ because / reason
    if "∵" in raw:
        parts = raw.split("∵", 1)
        raw = parts[0].strip()
        reason = parts[1].strip()

    # ∴ therefore / conclusion
    if "∴" in raw:
        parts = raw.split("∴", 1)
        raw = parts[0].strip()
        conclusion = parts[1].strip()

    # → leads to
    if "→" in raw:
        parts = raw.split("→", 1)
        raw = parts[0].strip()
        leads_to = parts[1].strip()

    # × count multiplier
    count_match = re.search(r"×(\d+)$", raw)
    if count_match:
        count = int(count_match.group(1))
        raw = raw[:count_match.start()].strip()

    # Parse the core value: array, kv-array, or string
    if raw.startswith("[") and raw.endswith("]"):
        # Try kv array first, fall back to plain array, then string
        parsed = _parse_kv_array(raw)
        if parsed is None or all(v is None for v in parsed.values()):
            parsed = _parse_array(raw)
        if parsed is None:
            parsed = raw  # malformed — treat as string per spec
        value = parsed
    else:
        value = raw

    return VrextValue(
        raw=original,
        value=value,
        reason=reason,
        conclusion=conclusion,
        leads_to=leads_to,
        count=count,
        approximate=approximate,
        critical=critical,
        unknown=unknown,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Line parser
# ---------------------------------------------------------------------------

def _parse_line(line: str) -> list[tuple[str, str]]:
    """
    Parse one line into [(field_code, raw_value), ...].
    Handles inline | separators between fields.
    Returns empty list for blank/comment lines.
    """
    line = line.strip()
    if not line or line.startswith("//"):
        return []

    # Split on | but only between field:value pairs
    # A pipe is a field separator when it's followed by FIELD: pattern
    field_pattern = re.compile(r"([A-Z$#]+):(.+?)(?=\|[A-Z$#]+:|$)", re.DOTALL)
    
    # Try to find field:value pairs with inline separators
    # First check if line has any field: pattern at all
    if not re.match(r"[A-Z$#!_a-z]+:", line):
        return []

    # Reject lines where field code contains lowercase or underscore — log as unknown
    segments_check = re.split(r"\|(?=[A-Z$#_a-z]+:)", line)
    for seg in segments_check:
        m = re.match(r"^!?([A-Za-z$#_]+):", seg)
        if m and not re.match(r"^[A-Z$#]+$", m.group(1)):
            return [("__UNKNOWN__", m.group(1))]

    # Split on | that precede a field code
    segments = re.split(r"\|(?=[A-Z$#]+:)", line)
    pairs = []
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        # Handle ! prefix on field codes
        m = re.match(r"^(!?)([A-Z$#]+):(.*)$", seg, re.DOTALL)
        if m:
            prefix, code, value = m.group(1), m.group(2), m.group(3)
            raw_value = ("!" + value.strip()) if prefix == "!" else value.strip()
            pairs.append((code.upper(), raw_value))
    return pairs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse(text: str) -> VrextMessage:
    """
    Parse a Vrext message string into a VrextMessage.

    Unknown fields are skipped (not aborted).
    Expired TTL is noted in errors but parsing continues.
    """
    msg = VrextMessage()

    for lineno, line in enumerate(text.splitlines(), 1):
        pairs = _parse_line(line)

        # If line looks like a field but yielded no pairs, log it
        stripped = line.strip()
        if stripped and not pairs and re.match(r"[A-Z$#!]+:", stripped):
            code_candidate = re.match(r"!?([A-Z$#]+):", stripped)
            if code_candidate and code_candidate.group(1) not in KNOWN_FIELDS:
                msg.errors.append(f"line {lineno}: unknown field '{code_candidate.group(1)}' — skipped")

        for code, raw_value in pairs:
            if code == "__UNKNOWN__":
                msg.errors.append(f"line {lineno}: unknown field '{raw_value}' — skipped")
                continue
            if code not in KNOWN_FIELDS:
                msg.errors.append(f"line {lineno}: unknown field '{code}' — skipped")
                continue

            parsed = _parse_value(raw_value)

            # Special validation for Q field
            if code == "Q":
                try:
                    q = float(parsed.value)
                    parsed.value = max(0.0, min(1.0, q))
                except (ValueError, TypeError):
                    msg.errors.append(f"line {lineno}: invalid Q value '{raw_value}' — defaulting to 0.5")
                    parsed.value = 0.5

            if code not in msg.fields:
                msg.fields[code] = []
            msg.fields[code].append(parsed)

    # Check TTL expiry after full parse
    if msg.is_expired():
        msg.errors.append("TTL_EXPIRED")

    return msg


def serialize(msg: VrextMessage) -> str:
    """
    Serialize a VrextMessage back to Vrext text.
    Fields are output in canonical order.
    """
    ORDER = ["VER", "TS", "TTL", "T", "S", "V", "N", "X", "B",
             "R", "C", "A", "$", "#", "P", "Q", "SEQ", "RLY"]

    lines = []
    seen = set()

    def _serialize_value(v: VrextValue) -> str:
        parts = ""
        if v.critical:
            parts += "!"
        if v.unknown:
            return parts + "?"
        if v.approximate:
            parts += "~"
        if isinstance(v.value, list):
            parts += "[" + ",".join(str(i) for i in v.value) + "]"
        elif isinstance(v.value, dict):
            items = ",".join(
                f"{k}={val}" if val is not None else k
                for k, val in v.value.items()
            )
            parts += "[" + items + "]"
        else:
            parts += str(v.value) if v.value is not None else ""
        if v.count is not None:
            parts += f"×{v.count}"
        if v.leads_to:
            parts += f"→{v.leads_to}"
        if v.reason:
            parts += f"∵{v.reason}"
        if v.conclusion:
            parts += f"∴{v.conclusion}"
        if v.confidence is not None:
            parts += f" Q:{v.confidence}"
        return parts

    for code in ORDER:
        if code in msg.fields:
            seen.add(code)
            for v in msg.fields[code]:
                lines.append(f"{code}:{_serialize_value(v)}")

    # Any fields not in canonical order
    for code, values in msg.fields.items():
        if code not in seen:
            for v in values:
                lines.append(f"{code}:{_serialize_value(v)}")

    return "\n".join(lines)


def to_dict(msg: VrextMessage) -> dict:
    """
    Convert a VrextMessage to a plain Python dict for interop with JSON etc.
    Multi-value fields (like X:) become lists.
    """
    def _val(v: VrextValue) -> Any:
        out = {"value": v.value}
        if v.reason:      out["reason"] = v.reason
        if v.conclusion:  out["conclusion"] = v.conclusion
        if v.leads_to:    out["leads_to"] = v.leads_to
        if v.count:       out["count"] = v.count
        if v.approximate: out["approximate"] = True
        if v.critical:    out["critical"] = True
        if v.unknown:     out["unknown"] = True
        if v.confidence:  out["confidence"] = v.confidence
        return out if len(out) > 1 else v.value

    result = {}
    for code, values in msg.fields.items():
        result[code] = [_val(v) for v in values] if len(values) > 1 else _val(values[0])
    return result
