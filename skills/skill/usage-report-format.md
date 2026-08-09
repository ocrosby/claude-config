# Skill Usage — Report Format

Level-3 resource for `/skill usage` (dispatch step 3). Present the report in this exact shape, passing the `tally_invocations.py` output through verbatim — do not re-summarize the histogram or the recommendation rationale.

```
## Skill usage (last 90 days)

History records scanned: <N>
Skill invocations matched: <M>
Skills in catalog: <K>

### Heavily used (>=10)
- /code-review  45
- /git-ship     32

### Moderately used (3-9)
- /architect     7

### Lightly used (1-2)
- /here-now      1

### Zero invocations
- /skill-author      [added 92d ago]
- /rest-spec         [added 5d ago, new]
- /update-config     [added 180d ago, user-invocable only]

### Retire (recommended)

These skills have zero invocations, have existed for ≥30 days, and are not new additions. Ordered by strongest signal first (longest unused).

1. /update-config   — 180d in catalog, user-invocable only, never invoked
2. /skill-author    — 92d in catalog, never invoked

### Consider retiring

Low usage (1–2 invocations all-time) — keep if intentional, drop if accidental:

- /here-now  (1 invocation)
```
