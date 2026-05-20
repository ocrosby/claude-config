---
description: Analyze Claude Code session history to find repeating tasks with no skill coverage. Run periodically to discover new skill candidates.
---

# Skill Gaps: Identify Missing Skills from History

Scans `~/.claude/history.jsonl` to surface tasks you type repeatedly that are not covered by an existing skill. Run after a few weeks of sessions to find the next batch of skills worth writing.

The JSONL parsing and frequency tally live in the bundled `analyze_history.py` script so this body stays small. The *gap interpretation* (deciding which repeated phrases are real gaps vs already-covered) stays inline because it requires reading the current skill catalog.

## Usage

```
/skill-gaps                  # all-time
/skill-gaps --since 30d      # last 30 days
/skill-gaps --since 90d      # last 90 days
```

## Workflow

### 1. Tally history

```bash
python3 ~/.claude/skills/skill-gaps/analyze_history.py [--since 30d] [--min-count N]
```

The script emits two Markdown sections:

- **Top slash-command invocations** — which skills are getting used (signal that they exist and work)
- **Repeating natural-language phrases** — phrases typed N+ times with no `/command` prefix; candidates for unmet skill gaps

### 2. List existing skills

```bash
ls ~/.claude/skills/
```

### 3. Identify gaps

For each pattern that appears ≥5 times in the natural-language section, check the existing skill catalog. A pattern is a **gap** if:

- No skill's description matches the intent
- The user is typing freeform what a skill could automate
- The pattern is mechanical enough to be a workflow (not a one-off question)

Skip patterns that are:

- Conversational (`thanks`, `ok`, `continue`)
- Already covered by an existing skill (just rare invocation)
- Personal/contextual (not portable to a skill)

### 4. Report

Present a ranked table of candidates:

| Suggested Skill | Count | Example phrase | Gap reason |
|---|---|---|---|
| ... | ... | ... | ... |

Order by frequency descending. For each gap, propose a skill name and a one-line description. Also include the top slash commands by frequency — these confirm which skills are getting used.

### 5. Verify

Confirm the output includes:

- The history-scanned count and in-window count
- Both sections (slash commands AND natural-language phrases)
- A ranked gap table OR a `_No gaps identified_` line

**If any of those are missing, the script failed silently — re-run with the same arguments and inspect stderr.**
