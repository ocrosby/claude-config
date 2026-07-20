# Skills

Skills are named workflows invoked by typing `/command` in a Claude Code session. Each skill is a Markdown file that defines a multi-step process Claude must follow — they enforce consistent, repeatable behavior for recurring tasks.

## Workflow stage map

The full development loop runs across five stages. Each stage has one skill.

| Stage | Skill | Purpose |
|---|---|---|
| 1. Design | `/architect` | Plan structure, pick patterns, draft an OpenAPI spec |
| 2. Implement | `/feature` | TDD a new feature, routed by language |
| 3. Triage | `/debug` | Reproduce, isolate, fix when something breaks |
| 4. Review | `/code` | Structured review, refactor, simplify, migrate |
| 5. Ship | `/git` | Branch / commit / push / PR / rebase / merge |

`/workflow` prints the same map with the rules, agents, and hooks that fire at each stage.

## What is a dispatcher?

A **dispatcher** is a top-level skill whose first argument selects a subcommand or whose language is auto-detected from the working directory. One slash command (`/git`, `/code`, `/feature`, …) gives access to many related operations without expanding the `/` menu with every variant.

Two routing styles:

- **Subcommand dispatch** — `/git ship`, `/git sync`, `/git worktree`. The dispatcher reads the first word of `$ARGUMENTS` and runs the matching workflow.
- **Language auto-detect** — `/feature`, `/debug`, `/bench` look at the current working directory and route to the matching language workflow (Go, Python, Lua/Neovim, Gherkin, REST). Override explicitly with `/feature go`, `/debug py`, etc.

Reference-only content for a subcommand lives alongside `SKILL.md` (e.g. `skills/nvim/config.md`) and is loaded only when that subcommand runs.

## The 11 dispatchers

Ordered by how often you reach for them, most-used first.

### Daily — inside every working session

| Skill | Subcommands / Routes by | Description |
|---|---|---|
| `/git` | `ship`, `sync`, `main`, `worktree`, `release-notes`, `cli` | Branch / commit / push / PR / rebase / merge cleanup / parallel worktrees / changelog generation. `cli` is a quick reference for `gh` operations the workflow subcommands don't already wrap (CI debugging, inline PR reviews, GraphQL, issue triage). |
| `/code` | `review` (`--rest` / `-f` / `-fc`), `grill`, `refactor`, `migrate`, `techdebt`, `simplify` | Structured review (delegates to language-reviewer agents), adversarial verdict (`grill`), structural refactor (Go/Python/Neovim), deprecated-pattern migration, dead-code sweep (`techdebt`), `simplify` delegates to the external `/simplify` skill. |
| `/feature` | language auto-detect (or `go / py / nvim / gherkin / rest <op>`) | Layered feature dev with TDD per language. For `rest`, implements a handler against an existing OpenAPI spec. |
| `/debug` | language auto-detect (or `go / py / nvim / gherkin`) | Reproduce → isolate → emit a minimal-repro artifact → escalate to the matching language debugger agent → verify the fix. |

### Bookend — before and after the feature

| Skill | Subcommands / Routes by | Description |
|---|---|---|
| `/architect` | `design` (lang auto-detect), `patterns`, `spec`, `catalog`, `interview`, `grill` | Language-architect agents for design proposals, GoF pattern recognition, OpenAPI design-first authoring, first-time Backstage catalog registration, the standalone plan-mode interview (questions + outline before a detailed plan), and adversarial one-question-at-a-time stress-testing of an existing plan or decision. |
| `/docs` | `write` (lang auto-detect), `review` (`-f`/`-fc`), `research <topic>` | Generate per-language API docs (godoc, Google-style docstrings, vimdoc, Gherkin living-docs), audit any documentation against Write-the-Docs principles, or research a topic and publish to here.now. |

### Periodic — maintenance cadence, not per-task

| Skill | Subcommands / Routes by | Description |
|---|---|---|
| `/audit` | `system`, `repo`, `skill` | `system` — Claude workflow components (rules, agents, hooks, skills, commands, settings) for inter-component correctness. `repo` — any git repository's history (churn, ownership / bus factor, hotspots, momentum, firefighting). `skill` — per-SKILL.md structural quality via `skill-reviewer`. |
| `/bench` | language auto-detect (or `go / py / nvim`) | Write, run, and analyze benchmarks. Go: `testing.B` + `benchstat` + `pprof`. Python: `pytest-benchmark` + `cProfile` + `py-spy`. Neovim: `vim.loop.hrtime` + `--startuptime`. |
| `/skill` | `author`, `gaps`, `usage` | Interactive new-skill workflow, gaps (repeating tasks lacking skills) from session history, invocation counts with retirement recommendations. For per-SKILL.md structural quality, use `/audit skill`. |

### Context-specific — fire only when you're in that mode

| Skill | Subcommands / Routes by | Description |
|---|---|---|
| `/nvim` | `rpc`, `config`, `plugin` | `rpc` — talk to a running Neovim via msgpack-RPC. `config` — native vim.pack config authoring (no plugin manager). `plugin` — authoring redistributable Neovim plugins. For yoda.nvim / lazy.nvim adds, use `/add-plugin`. |
| `/work` | `add`, `list`, `done`, `update`, `note` | Date-structured daily log of engineering activity at `~/work/{YYYY}/{M}/{D}.md`. Already used subcommand dispatch internally; the model for the other dispatchers. |

## Standalone primitives

These skills are single-purpose primitives with unique triggers — they intentionally remain top-level rather than folding under a dispatcher.

| Skill | Purpose |
|---|---|
| `/obsidian` | Read / create / edit notes in the PARA-organized vault at `~/src/github.com/ocrosby/obsidian`. |
| `/proof` | Back up a claim with a verifiable citation (file:line, version-pinned URL, commit SHA, test result), or honestly downgrade the claim. |

## Building-block commands

These live in `commands/` rather than `skills/` because they are single focused actions reused by the dispatchers above. They are hidden from the `/` menu (`user-invocable: false`) but the user can still type them. See `commands/README.md`.

| Command | Used by |
|---|---|
| `/branch-from-main` | `/git ship`, `/git sync`, `/git worktree` |
| `/conventional-commit-msg` | `/git ship` |
| `/open-pr` | `/git ship` |
| `/test-and-fix` | `/feature`, `/code`, `/debug` |

---

## Authoring reference

The rest of this document is for writing or modifying a skill. The full conventions live in `skills/CLAUDE.md`.

### Skills vs. rules vs. commands

- **Rule** (`rules/*.md`) — Always-on behavioral constraint. Loads automatically when matching files are in context; no invocation needed.
- **Skill** (`skills/*/SKILL.md`) — Multi-step workflow invoked on demand (`/git`, `/code`, `/feature`).
- **Command** (`commands/*.md`) — Single focused action, usually a building block that skills invoke.

Use a rule when behavior should be enforced automatically. Use a skill when the user opts in to a workflow. Use a command when 2+ skills share the same atomic mechanic.

### File format

Each skill lives in its own subdirectory and is always named `SKILL.md`:

```
skills/
  git/
    SKILL.md
  code/
    SKILL.md
```

```markdown
---
description: One-line summary of what this skill does.
aliases: prior-name
paths:
  - "**/*.go"
---

# Skill Title

Prose and workflow steps here.
```

### Frontmatter fields

| Field | Required | Description |
|---|---|---|
| `description` | Recommended | Shown in skill listings; used by Claude to decide which skill fits a task |
| `paths` | Optional | Glob patterns — skill fires automatically when matching files are in context |
| `aliases` | Optional | Prior names this skill was renamed from — used by `/skill usage` for historical invocation attribution |
| `disable-model-invocation` | Optional | `true` blocks Claude from auto-invoking; user can still type the slash command |
| `user-invocable` | Optional | `false` hides from the `/` menu while still allowing programmatic invocation |
| `argument-hint` | Optional | Autocomplete hint shown after the slash command |
| `allowed-tools` | Optional | Pre-approves listed tools while the skill is active |

The directory name **is** the slash command — `skills/git/` automatically registers as `/git`. There is no `triggers:` field; do not add one.

The full field reference and the `disable-model-invocation` vs `user-invocable` decision matrix live in `skills/CLAUDE.md`.

### Authoring a new skill

Use `/skill author` to create a new skill interactively — it walks through purpose definition, frontmatter, workflow authoring, and consistency checks. See `skills/CLAUDE.md` for the full conventions.

### Reusable scripts over inline logic

Workflow steps that do parsing, scanning, validating, or transforming data must be extracted into a script under `~/.claude/scripts/`. Inline code is only allowed when the logic is under 20 lines AND will not be regenerated across invocations.

See `skills/CLAUDE.md` for the recognition signals and the full token-economics rationale. The canonical exemplar is `scripts/tally_invocations.py` — standard library only, argparse CLI, structured stdout. `/skill author` walks through this decision when authoring new skills.
