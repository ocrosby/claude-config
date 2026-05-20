---
description: Count how often each skill has been explicitly invoked from session history and recommend which skills to retire.
---

# Skill Usage

Use this skill when you want to identify which skills in `~/.claude/skills/` are unused and candidates for retirement. The report cross-references explicit `/command` invocations in `~/.claude/history.jsonl` against the current skill catalog, then ends with a ranked retirement list.

## Usage

```
/skill-usage              # all-time usage report
/skill-usage --since 30d  # only count invocations in the last 30 days
/skill-usage --since 90d  # last 90 days
```

## Workflow

### 1. Confirm Inputs Exist

```bash
test -f ~/.claude/history.jsonl
test -d ~/.claude/skills
```

**If either is missing: stop and report which input is absent.** Do not attempt to generate the report from partial data.

### 2. Run the Tally Script

Invoke the bundled script with the user's `--since` argument (or no argument for all-time):

```bash
python3 ~/.claude/skills/skill-usage/tally_invocations.py [--since 30d]
```

The script:

- Parses every record in `~/.claude/history.jsonl`
- Extracts the leading `/<command>` from each prompt
- Restricts matches to commands that map to directories under `~/.claude/skills/`
- Resolves renamed skills via the `aliases:` frontmatter field — historical invocations under a previous name (e.g. `/ship` before the `/git-ship` rename) count toward the canonical name
- Tallies invocation counts per skill (canonical name)
- Reads each skill's `SKILL.md` frontmatter to detect `disable-model-invocation: true` (a skill that only fires on explicit user input — zero usage is a stronger retirement signal)
- Uses git first-add time (via `git log --diff-filter=A --follow`) as "age in catalog", with file mtime as the fallback, so newly-added skills with zero counts are held rather than retired
- Produces a ranked retirement recommendation as the final section

### 3. Present the Report

The script prints a Markdown report in this exact shape:

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

Pass the output through to the user verbatim. Do not re-summarize the histogram or the recommendation rationale.

### 4. Interpret the Recommendations

The "Retire" section is the action list. The "Consider" section is a second tier. Note these caveats before the user acts:

- A skill loaded automatically via `paths:` (e.g. a language rule firing on `.go` files) may not produce `/command` invocations even if it fires on every session — check the skill's frontmatter for `paths:` before retiring
- A skill marked `disable-model-invocation: true` only runs on explicit user input — zero usage on that subset is the highest-confidence retirement signal
- A skill modified in the last 30 days is excluded from "Retire" because mtime change suggests active maintenance

### 5. Verify the Report

Confirm the printed output contains:

- A scanned-records count and a matched-invocations count
- A `### Zero invocations` section
- A `### Retire (recommended)` section (with the literal text `None.` if empty)

**If any of those sections are absent, the script failed silently — re-run with the same arguments and inspect stderr.**
