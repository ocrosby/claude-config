# Findings Format

When a skill or agent produces a structured review report (e.g. `/audit skill`, `/code review`, `/code grill`, `/docs review`, `skill-reviewer`, `go-reviewer`, `py-reviewer`, `nvim-reviewer`, `rest-reviewer`, `gherkin-reviewer`), it must use these three severity buckets and no others.

## The three buckets

| Bucket | When to use | Example trigger |
|---|---|---|
| **Must Fix** | The issue causes correctness failure. The skill will not work; the code will break under realistic input; the document is incorrect (worse than missing); a public API contract is violated; a security or correctness invariant is broken. | Lint failure; missing test for new behavior; broken link; complexity regression on a hot path with unbounded input. |
| **Should Fix** | The issue causes drift over time. Behavior is inconsistent across sessions; terminology drifts across the same surface; a known limit holds today but is likely to be exceeded; a stated convention is not enforced. | Inconsistent terminology in a single doc; bounded-N complexity that will outgrow its bound; a rule that fires but has no hook to enforce it. |
| **Consider** | The issue is an improvement that does not block. An alternative shape would read more clearly; a refactor would reduce drift risk later; additional examples would help readers. | Heading wording; an extra cross-reference; a marginal asymptotic gain at realistic N. |

## The finding shape

Every finding must include:

1. **File and line** — `path/to/file.ext:LINE` (or `path/to/file.ext:LINE-LINE` for a range). Click-to-jump is the point.
2. **What** — one sentence describing the issue.
3. **Why** — one sentence on what breaks or drifts if it is not fixed. The "why" line is what distinguishes the finding from a personal preference.
4. **Fix** (Must Fix and Should Fix only) — one or two sentences naming the change. Optional for Consider items.

## Report shape

Group findings by bucket in this order: **Must Fix → Should Fix → Consider**. Within each bucket, order by impact (most critical first). Omit a bucket entirely when it has no entries — do not print an empty `### Must Fix` header.

```
## <Report title>

### Must Fix
- `path/to/file.ext:42` — <what>. **Why:** <why>. **Fix:** <fix>.

### Should Fix
- `path/to/file.ext:88` — <what>. **Why:** <why>. **Fix:** <fix>.

### Consider
- `path/to/file.ext:120` — <what>. **Why:** <why>.
```

## Forbidden synonyms

Do not use **Critical** / **Warning** / **Suggestion** or **Blocker** / **Major** / **Minor** or **Error** / **Warning** / **Info** as bucket names. The three terms above are canonical. Multiple terms for the same idea cause drift across reports and confuse users who skim output from more than one skill.

A report that uses a forbidden synonym is a **Should Fix** finding when audited.

## Verdict labels (optional summary)

A skill that summarizes the report at the end may use these verdict shorthands. The underlying findings must still use the three buckets.

| Verdict | Condition |
|---|---|
| **SHIP IT** | Zero Must Fix, zero Should Fix, zero Consider items |
| **NEEDS WORK** | Zero Must Fix, but Should Fix or Consider items remain |
| **BLOCK** | One or more Must Fix items, OR new/changed behavior missing tests, OR a breaking change to a public API |

Never lower the verdict to accommodate effort already spent. Never collapse Must Fix into Should Fix.

## Mandatory behaviors

- A skill or agent that produces findings must **link to this rule** in the relevant step of its workflow and must **not restate the bucket definitions** inline. The rule is authoritative; SKILL.md repeats only as much as the workflow needs.
- When the workflow includes an auto-fix pass (e.g. `/code review -f`), apply **Must Fix and Should Fix** changes and leave Consider items for human review.
- When the workflow includes a verdict, emit it after the report — never instead of it.
