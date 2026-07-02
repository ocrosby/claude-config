---
description: Scan skills across both repos + recent conversation history for gotchas to add
allowed-tools: Bash, Read, Glob, Grep
---

Analyze my Claude skills and recent conversation/session history, and
suggest any "gotchas" (edge cases, mistakes, or missing clarifications)
that should be added to each skill.

Skills live across two repos, symlinked into ~/.claude:
- ~/src/github/ocrosby/claude-config
- ~/src/github/TheWeatherCompany/sun-claude-marketplace

Steps:
1. Find all SKILL.md files under both repos (use Glob).
2. For each one, resolve whether it's linked into ~/.claude and confirm
   the real repo path (not the symlink) — that's where edits will land.
3. Review recent session transcripts / conversation history available to
   you for moments where a skill's instructions were ambiguous, wrong,
   or missing a case that caused friction or a redo.
4. For each gotcha found, note:
   - repo + real file path
   - a short quote/summary of the moment that surfaced it
   - the exact proposed text, and where in the skill file it belongs

Output a single markdown file at ~/gotcha-review.md, grouped by repo then
skill file, like:

## <repo>/<skill filename>
- [ ] **Gotcha:** <short description>
      **Evidence:** <what happened in conversation>
      **Proposed addition:** <exact text to insert>

Do not modify any skill files directly. Only write ~/gotcha-review.md.
If ~/gotcha-review.md already exists with checked boxes from a previous
run, treat checked items as approved — apply those edits to the real
skill files first, then regenerate the file with the remaining
unchecked/new gotchas.

$ARGUMENTS
