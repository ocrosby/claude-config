---
description: Opt-in guidance for reading project markdown (README, CONTRIBUTING, ARCHITECTURE, docs/) at session start. Consultation-only — no paths glob. Referenced from CLAUDE.md under "Skip discovery when not needed".
---

# Session Startup: Project Markdown (opt-in)

**Default: do not read project markdown at session start.** Most turns are narrow — a single-file edit, a config tweak, a targeted question — and do not need broad context. Reading four files unconditionally wastes tokens and slows the first response.

**When to read `README.md`, `CONTRIBUTING.md`, `ARCHITECTURE.md`, and top-level files under `docs/`:**

- The user asks a **substantive** question about the project (how does X work, why is Y designed this way, what are the conventions).
- The task requires knowledge of the codebase's architecture (adding a feature that spans layers, refactor that touches multiple modules, unfamiliar repo you have not read this session).
- The user explicitly asks you to orient before acting.

**Do NOT read them for:**

- Single-file edits or focused bug fixes.
- Answering a factual question that can be resolved by `grep`/`rg`/`git log`.
- Running or fixing tests.
- Formatting, lint, or style-only changes.
- Any task the user has already scoped precisely.

If the working directory is `~/.claude` or a non-project directory, skip regardless.

**How to read them, when you do:** in a single batched message with parallel Read calls — never serialize.
