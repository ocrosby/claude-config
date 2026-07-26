---
description: How to record repo-committed insights about Claude rules, skills, hooks, and agents in LEARNINGS.md
paths:
  - "LEARNINGS.md"
---

# LEARNINGS.md Standard (claude-config repo)

`LEARNINGS.md` is the single home for repo-committed insights about how Claude rules, skills, hooks, and agents behave — drift patterns, tooling gotchas, contradictions that caused Claude to alternate between behaviors. Do **not** put this content in `README.md`, which stays a clean user-facing document (see `rules/readme-standard.md`).

Cross-project behavioral preferences and feedback go to the memory system instead — see `CLAUDE.md` `# Self-Improvement`.

## When to trigger this

A learning has occurred when any of these happen:

- A rule was changed because it was too soft, too vague, or contradicted another rule
- A hook or skill was found to not enforce what it claimed to enforce
- A contradiction between two files caused Claude to alternate between behaviors
- A new pattern was discovered that makes rules more durable (e.g., "always" vs "suggest")
- A specific configuration decision is made that future sessions might undo without context
- A language-specific practice (Go, Python, Lua) is found to work better than the previous approach
- A CI debugging loop required multiple rounds of iteration — the root cause is a candidate lesson
- A tooling version compatibility issue was discovered (e.g., linter built with wrong Go version)
- A build/test failure was caused by a pattern that an existing rule or hook should have caught
- An audit (`/audit`) revealed gaps between stated behavior and actual enforcement

**These are high-priority triggers.** If a session involved 3+ rounds of CI debugging to fix an issue that a rule could have prevented, that is always worth a `LEARNINGS.md` entry.

## What to write

Each entry belongs under the appropriate section heading. Write it as a short, concrete lesson — not a description of what was changed, but what was learned and why it matters for future rule authoring.

Structure:
- **One sentence stating the lesson**
- Optional: a before/after example showing the drift pattern and the fix
- Optional: the specific consequence that prompted the change

Do not pad entries. If the lesson can be stated in one sentence, use one sentence.

## How to update

1. Read the current `LEARNINGS.md`
2. Add the new entry under the appropriate section (or create a new section if none fits)
3. Run `/git ship -m` to commit directly to main and push without a PR — use commit message `docs(claude): add learning — <one-line summary>`
4. Do not batch learnings across sessions — ship immediately after each session that produced a new learning

## Sections in LEARNINGS.md

- **Rule Authoring** — lessons about writing durable, enforceable rules
- **TDD Enforcement** — lessons about test-driven development consistency
- **Go-Specific** — Go tooling, patterns, and reviewer behavior
- **Python-Specific** — Python tooling, patterns, and reviewer behavior
- **Lua/Neovim-Specific** — Lua plugin conventions and reviewer behavior
- **Complexity** — code quality limits and their rationale
- **Concurrency (Go)** — goroutine, channel, and context patterns
- Add new sections when learnings don't fit existing ones
