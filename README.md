# Vrext

**Token-efficient communication protocol for AI agents.**

Vrext cuts inter-agent state by ~60% versus JSON. Same information. Fewer tokens. No dependencies.

```
pip install vrext
```

---

## Why not JSON?

JSON was designed for humans and HTTP APIs. It repeats keys, requires quotes, and nests deeply. When agents pass state to each other hundreds of times per task, that overhead compounds into real cost.

Vrext is designed for one thing: agents passing state to agents.

| Format | Tokens | Relative cost |
|--------|--------|---------------|
| Vrext  | ~35    | 1×            |
| YAML   | ~70    | 2×            |
| JSON   | ~85    | 2.4×          |

*Same state expressed in each format. Token counts via cl100k_base.*

---

## Quickstart

```python
from vrext import parse, serialize, to_dict

# Parse a Vrext message
msg = parse("""
VER:1.1
TS:1716000000
TTL:3600
T:find_crm_system
V:candidates=[hubspot,pipedrive]|$:~50
X:salesforce ∵cost
C:[research_complete,pricing_complete]
N:book_demonstrations→compare
Q:0.9
""")

# Read fields
print(msg.first("T").value)        # find_crm_system
print(msg.first("X").reason)       # cost
print(msg.first("N").leads_to)     # compare
print(msg.confidence())            # 0.9
print(msg.is_expired())            # False

# Convert to dict for JSON interop
d = to_dict(msg)

# Serialize back to Vrext
text = serialize(msg)
```

---

## Format

Each field on its own line. No quotes. Underscores instead of spaces.

```
VER:1.1
TS:1716000000
TTL:3600
T:research_pm_tools
#:10_person_startup
V:candidates=[notion,linear,asana]|$:[notion=10pp,linear=8pp,asana=13pp]
X:jira ∵complexity
X:monday ∵cost_at_scale
C:[search_complete,pricing_complete]
N:eval[slack_integration,github_integration]→rank_candidates
SEQ:[search_complete,pricing_complete,rank_candidates]
Q:0.95
```

### Symbols

| Symbol | Meaning |
|--------|---------|
| `:`    | field definition |
| `\|`   | inline field separator |
| `=`    | value assignment |
| `[]`   | array |
| `∵`    | because / reason |
| `∴`    | therefore / conclusion |
| `→`    | leads to / produces |
| `×`    | count multiplier |
| `!`    | critical / high priority |
| `?`    | unknown / unresolved |
| `@`    | agent reference |
| `~`    | approximate value |
| `&`    | combine / and |

### Fields

| Field | Meaning |
|-------|---------|
| `VER` | protocol version |
| `TS`  | unix timestamp |
| `TTL` | expiry in seconds |
| `T`   | task goal |
| `S`   | episodic summary |
| `V`   | variables and facts |
| `N`   | next required action |
| `X`   | exclusion with reason |
| `B`   | blocked by |
| `R`   | requirements |
| `C`   | completed steps |
| `A`   | agent capability needed |
| `$`   | cost or budget |
| `#`   | count or quantity |
| `P`   | priority (1=highest) |
| `Q`   | confidence 0.0–1.0 |
| `SEQ` | sequence dependency |
| `RLY` | relay target |

---

## Grammar

```
Single value       FIELD:value
Array              FIELD:[val1,val2,val3]
Key-value array    FIELD:[a=1,b=2,c=3]
With reason        FIELD:value ∵ reason
With outcome       FIELD:value → outcome
With count         FIELD:value×3
Inline fields      FIELD1:val|FIELD2:val
Critical           !FIELD:value
Unknown            FIELD:?
Approximate        FIELD:~value
Inline confidence  FIELD:value Q:0.9
Agent reference    @agent_id:capability
Conditional        IF condition → THEN action | ELSE fallback
```

---

## Multi-agent example

```
VER:1.1
TS:1716000100
TTL:1800
T:process_and_store_results
B:rank_candidates
RLY:@storage_agent:write
A:@eval_agent:integration_check
SEQ:[eval_complete,rank_complete,store_complete]
N:await_eval_agent→receive_rankings
Q:0.85
```

---

## API

### `parse(text: str) -> VrextMessage`

Parses a Vrext string. Never raises — malformed input is logged to `msg.errors`.

```python
msg = parse(text)
msg.first("T")        # first value for field T
msg.get("X")          # all values for field X (list)
msg.confidence()      # float from Q field, defaults to 0.5
msg.is_expired()      # True if TS + TTL < now
msg.errors            # list of parse warnings
```

### `serialize(msg: VrextMessage) -> str`

Serializes a VrextMessage back to Vrext text in canonical field order.

### `to_dict(msg: VrextMessage) -> dict`

Converts to a plain Python dict for JSON interop.

### `VrextValue`

Every parsed field value is a `VrextValue`:

```python
v.value        # str, list, dict, or float
v.reason       # str or None  (∵)
v.conclusion   # str or None  (∴)
v.leads_to     # str or None  (→)
v.count        # int or None  (×)
v.approximate  # bool         (~)
v.critical     # bool         (!)
v.unknown      # bool         (?)
v.confidence   # float or None (inline Q:)
```

---

## Error handling

Vrext parsers are fault-tolerant by spec:

| Problem | Behavior |
|---------|----------|
| Unknown field | skipped, logged to `msg.errors` |
| Invalid Q value | defaults to 0.5, logged |
| Malformed array | treated as string |
| Expired TTL | `TTL_EXPIRED` in `msg.errors` |
| Unknown symbol | treated as literal |

---

## Roadmap

| Version | Target |
|---------|--------|
| v1.1 | ✅ Core spec, Python parser |
| v1.2 | TypeScript parser |
| v1.3 | Rust parser |
| v2.0 | Multi-agent coordination primitives |

---

## License

MIT. Free to use, implement, and extend.

---

## Contributing

The spec lives in `SPEC.md`. The parser lives in `vrext/vrext.py`. Tests in `tests.py`.

To add a symbol or field, open an issue first — breaking changes increment the major version.
