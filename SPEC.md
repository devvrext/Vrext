# Vrext v1.1 Specification
**AI-to-AI Communication Language**
Author: Trew Lite
Version: 1.1.0
Status: Draft

---

## What is Vrext?

Vrext is a communication language designed exclusively for AI-to-AI information transfer. It is not intended to be human-readable. It is optimized for two properties equally:

1. Token efficiency — maximum meaning per token
2. Unambiguous parsing — zero interpretive overhead

---

## Core Design Rules

1. No quotes
2. No brackets except for arrays []
3. No whitespace in values — use underscores
4. Every symbol has exactly one meaning
5. Order is meaningful — never repeat information
6. All abbreviations must be inferrable from context
7. Each field on its own line
8. Arrays use [] with comma-separated values

---

## Symbol Vocabulary

```
:     field definition
|     inline field separator within a field
=     value assignment
[]    array or list
∵     because / reason
∴     therefore / conclusion
→     leads to / produces
×     count multiplier
!     critical / high priority
?     unknown / unresolved
@     agent reference (@agent_id:capability)
~     approximate value
&     combine / and
```

---

## Field Codes

```
VER:  protocol version
TS:   unix timestamp
TTL:  expiry in seconds
T:    task goal
S:    episodic summary
V:    variables and facts
N:    next required action
X:    exclusions (item ∵ reason)
B:    blocked by
R:    requirements and constraints
C:    completed steps
A:    agent capability needed
$:    cost or budget
#:    count or quantity
P:    priority (1=highest)
Q:    confidence score 0.0-1.0
SEQ:  sequence dependency
RLY:  relay target
```

---

## Grammar Rules

```
Single value        FIELD:value
Multiple values     FIELD:[val1,val2,val3]
With reason         FIELD:value ∵ reason
With result         FIELD:value → outcome
With count          FIELD:value×3
Inline multi        FIELD1:val|FIELD2:val
Priority flag       !FIELD:value
Unknown             FIELD:?
Approximate         FIELD:~value
Confidence suffix   FIELD:value Q:0.9
Agent reference     @agent_id:capability
```

---

## Conditional Syntax

```
IF condition → THEN action
IF condition → THEN action | ELSE fallback
```

---

## Temporal Markers

```
TTL:seconds         expires after N seconds
SEQ:[a,b,c]         a must complete before b before c
TS:unix_timestamp   when this message was created
```

---

## Confidence and Uncertainty

```
Q:1.0    certain
Q:0.9    highly confident
Q:0.7    probable
Q:0.5    uncertain
Q:0.0    unknown
```

---

## Error Handling

Parsers encountering malformed input must follow these rules:

- Unknown field code → skip and continue, do not abort
- Missing required field → set field value to ?
- Malformed array → treat entire value as single string
- Invalid Q value → default to Q:0.5
- Expired TTL → halt processing, return TTL_EXPIRED status
- Unknown symbol → treat as literal character

---

## Token Efficiency Benchmark

Equivalent state expressed in three formats:

**Vrext**
```
T:find_pm_tool|#:10_person_startup
V:candidates=[notion,linear]|$:[notion=10pp,linear=8pp]
X:jira ∵complexity|monday ∵cost
N:eval_integrations→rank
Q:0.9
```
~35 tokens

**JSON**
```json
{
  "task": "find_pm_tool",
  "team_size": "10_person_startup",
  "candidates": ["notion", "linear"],
  "pricing": {"notion": "10pp", "linear": "8pp"},
  "exclusions": [
    {"tool": "jira", "reason": "complexity"},
    {"tool": "monday", "reason": "cost"}
  ],
  "next_action": "eval_integrations",
  "next_outcome": "rank",
  "confidence": 0.9
}
```
~85 tokens

**YAML**
```yaml
task: find_pm_tool
team_size: 10_person_startup
candidates: [notion, linear]
pricing:
  notion: 10pp
  linear: 8pp
exclusions:
  - tool: jira
    reason: complexity
  - tool: monday
    reason: cost
next_action: eval_integrations → rank
confidence: 0.9
```
~70 tokens

**Vrext saves ~60% tokens versus JSON and ~50% versus YAML for equivalent state.**

---

## Full Example

```
VER:1.1
TS:1716000000
TTL:3600
T:research_pm_tools
#:10_person_startup
S:identified×5|pricing_analyzed|exclusions×2_complete Q:0.95
V:candidates=[notion,linear,asana]|$:[notion=10pp,linear=8pp,asana=13pp]
X:jira ∵complexity_10person
X:monday ∵cost_at_scale
C:[search_complete,pricing_complete,exclusions_complete]
N:eval[slack_integration,github_integration]→rank_candidates
SEQ:[search_complete,pricing_complete,rank_candidates]
Q:0.95
```

---

## Multi-Agent Example

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

## What Vrext Does Not Handle Yet

```
Emotional or tone context        → planned v0.2
Complex nested relationships     → planned v0.2
Native model fine-tuning         → planned v1.0
```

---

## Versioning

Vrext follows semantic versioning.
Breaking changes increment the major version.
New symbols increment the minor version.
Bug fixes increment the patch version.

---

## License

Open standard. Free to implement. Free to extend.
