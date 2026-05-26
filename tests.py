"""
Vrext v1.1 Test Suite
"""

import time
import sys
sys.path.insert(0, "/home/claude/vrext")

from vrext import parse, serialize, to_dict

PASS = 0
FAIL = 0

def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"  ✓ {name}")
        PASS += 1
    else:
        print(f"  ✗ {name}{' — ' + detail if detail else ''}")
        FAIL += 1


# ---------------------------------------------------------------------------
print("\n[ Basic field parsing ]")

msg = parse("T:find_crm_system")
test("single value", msg.first("T").value == "find_crm_system")

msg = parse("Q:0.9")
test("confidence field", msg.first("Q").value == 0.9)

msg = parse("#:10_person_startup")
test("hash field", msg.first("#").value == "10_person_startup")

msg = parse("$:~50")
test("approximate value", msg.first("$").approximate is True)
test("approximate value content", msg.first("$").value == "50")


# ---------------------------------------------------------------------------
print("\n[ Arrays ]")

msg = parse("C:[search_complete,pricing_complete,exclusions_complete]")
test("plain array", msg.first("C").value == ["search_complete", "pricing_complete", "exclusions_complete"])

msg = parse("V:candidates=[notion,linear,asana]")
test("array in value", isinstance(msg.first("V").value, str))  # value contains raw before =

msg = parse("$:[notion=10pp,linear=8pp,asana=13pp]")
test("kv array", msg.first("$").value == {"notion": "10pp", "linear": "8pp", "asana": "13pp"})


# ---------------------------------------------------------------------------
print("\n[ Symbols ]")

msg = parse("X:jira ∵complexity_10person")
test("exclusion with reason", msg.first("X").value == "jira")
test("exclusion reason", msg.first("X").reason == "complexity_10person")

msg = parse("N:eval_integrations→rank_candidates")
test("leads_to", msg.first("N").leads_to == "rank_candidates")
test("leads_to base value", msg.first("N").value == "eval_integrations")

msg = parse("S:identified×5")
test("count multiplier", msg.first("S").count == 5)
test("count base value", msg.first("S").value == "identified")

msg = parse("N:?")
test("unknown value", msg.first("N").unknown is True)

msg = parse("!T:critical_task")
test("critical flag", msg.first("T").critical is True)

msg = parse("T:do_thing Q:0.85")
test("inline confidence", msg.first("T").confidence == 0.85)


# ---------------------------------------------------------------------------
print("\n[ Inline field separators ]")

msg = parse("T:find_crm|#:10_startup")
test("inline separator field 1", msg.first("T").value == "find_crm")
test("inline separator field 2", msg.first("#").value == "10_startup")

msg = parse("VER:1.1|TS:1716000000|TTL:3600")
test("three inline fields", msg.first("VER").value == "1.1")
test("three inline fields TS", msg.first("TS").value == "1716000000")
test("three inline fields TTL", msg.first("TTL").value == "3600")


# ---------------------------------------------------------------------------
print("\n[ Multi-value fields (X:) ]")

text = "X:jira ∵complexity\nX:monday ∵cost"
msg = parse(text)
exclusions = msg.get("X")
test("multi X fields count", len(exclusions) == 2)
test("first exclusion", exclusions[0].value == "jira")
test("second exclusion", exclusions[1].value == "monday")
test("second exclusion reason", exclusions[1].reason == "cost")


# ---------------------------------------------------------------------------
print("\n[ Error handling ]")

msg = parse("UNKNOWN_FIELD:value")
test("unknown field skipped", len(msg.fields) == 0)
test("unknown field error logged", len(msg.errors) == 1)

msg = parse("Q:not_a_number")
test("invalid Q defaults to 0.5", msg.first("Q").value == 0.5)
test("invalid Q logs error", any("invalid Q" in e for e in msg.errors))

msg = parse("Q:1.5")
test("Q clamped to 1.0", msg.first("Q").value == 1.0)

msg = parse("Q:-0.1")
test("Q clamped to 0.0", msg.first("Q").value == 0.0)


# ---------------------------------------------------------------------------
print("\n[ TTL expiry ]")

past_ts = int(time.time()) - 7200
msg = parse(f"TS:{past_ts}\nTTL:3600")
test("expired TTL detected", msg.is_expired() is True)
test("expired TTL in errors", "TTL_EXPIRED" in msg.errors)

future_ts = int(time.time())
msg = parse(f"TS:{future_ts}\nTTL:3600")
test("valid TTL not expired", msg.is_expired() is False)


# ---------------------------------------------------------------------------
print("\n[ Full example ]")

FULL = """VER:1.1
TS:1716000000
TTL:999999999
T:research_pm_tools
#:10_person_startup
S:identified×5|pricing_analyzed|exclusions×2_complete Q:0.95
V:candidates=[notion,linear,asana]|$:[notion=10pp,linear=8pp,asana=13pp]
X:jira ∵complexity_10person
X:monday ∵cost_at_scale
C:[search_complete,pricing_complete,exclusions_complete]
N:eval[slack_integration,github_integration]→rank_candidates
SEQ:[search_complete,pricing_complete,rank_candidates]
Q:0.95"""

msg = parse(FULL)
test("VER parsed", msg.first("VER").value == "1.1")
test("T parsed", msg.first("T").value == "research_pm_tools")
test("two X fields", len(msg.get("X")) == 2)
test("C is array", isinstance(msg.first("C").value, list))
test("SEQ is array", isinstance(msg.first("SEQ").value, list))
test("Q is float", msg.confidence() == 0.95)
test("not expired (far future TTL)", msg.is_expired() is False)
test("no critical errors", not any("TTL_EXPIRED" in e for e in msg.errors))


# ---------------------------------------------------------------------------
print("\n[ Serialization round-trip ]")

msg = parse(FULL)
reserialised = serialize(msg)
msg2 = parse(reserialised)

test("round-trip T", msg2.first("T").value == msg.first("T").value)
test("round-trip Q", msg2.confidence() == msg.confidence())
test("round-trip X count", len(msg2.get("X")) == len(msg.get("X")))
test("round-trip C array", msg2.first("C").value == msg.first("C").value)


# ---------------------------------------------------------------------------
print("\n[ to_dict ]")

msg = parse("T:find_crm\nQ:0.9\nX:jira ∵cost\nX:monday ∵complexity")
d = to_dict(msg)
test("dict T", d["T"] == "find_crm")
test("dict Q", d["Q"] == 0.9)
test("dict X is list", isinstance(d["X"], list))
test("dict X[0] has reason", d["X"][0]["reason"] == "cost")


# ---------------------------------------------------------------------------
print(f"\n{'='*40}")
print(f"  Results: {PASS} passed, {FAIL} failed")
print(f"{'='*40}\n")

sys.exit(0 if FAIL == 0 else 1)
