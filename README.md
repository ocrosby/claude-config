# claude-config

My personal Claude Code configuration — version-controlled, and symlinked into `~/.claude/` with GNU Stow.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Examples](#examples)
- [Configuration](#configuration)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)
- [Tips from the Claude Code team](#tips-from-the-claude-code-team)
- [Power features](#power-features)
- [Related documentation](#related-documentation)
- [References](#references)

## Overview

*Written for: me, on a fresh machine. If you're someone else, read it for ideas — none of it is tuned for your workflow.*

**Claude Code reads its configuration from `~/.claude/`.** `CLAUDE.md` holds standing instructions loaded into every session; `rules/` holds always-on conventions; `skills/`, `agents/`, `commands/`, `hooks/`, and `output-styles/` hold the things you invoke or that fire on events. If you use Claude Code, you already have that directory.

By default it is machine-local and unversioned, so it accumulates by drift. A rule gets tightened after one bad session. A skill gets written mid-task and never looked at again. A line lands in `CLAUDE.md` because Claude did something annoying that Tuesday. Six months later a second machine has none of it, and when a rule says something surprising there is no record of which mistake it was written to prevent.

Version-controlling it is not a matter of running `git init` in `~/.claude/`. Claude Code writes its own runtime state into that same directory — sessions, projects, plans, caches, shell snapshots, telemetry — and creates new such directories as it gains features. So the directory you want to track and the directory the tool owns are the same directory. What you actually need is something that links tracked config *in* while leaving runtime state alone, doesn't fight the tool when it invents a new folder next month, and doesn't need re-running every time you add a skill.

That is what GNU Stow does, with this repo's root as the stow package:

```bash
stow -t ~/.claude -d ~/src/github.com/ocrosby claude-config
```

One command symlinks `CLAUDE.md`, `settings.json`, and every tracked directory into `~/.claude/`, and touches nothing else in there. Git supplies the history, the rollback, and — in `LEARNINGS.md` — a place to record *why* a rule says what it says.

## Features

- **One command to provision a machine** — clone, stow, done. No copying files, no per-machine drift.
- **Coexists with Claude Code's own state** — runtime directories are left untouched because they aren't in the package.
- **Config is reviewable** — every rule change is a diff with a commit message explaining the mistake it prevents.
- **Layered instruction surface** — always-on rules, on-demand skills, isolated agents, single-file commands, event-driven hooks, and session-wide output styles.
- **Deterministic work lives in `scripts/`** — parsing, scanning, and classification run as code rather than being re-derived by the model each session.
- **Machine-local escape hatch** — `settings.local.json` stays gitignored, so per-machine permissions never enter the repo.

## Requirements

- [Claude Code](https://code.claude.com/docs/en/overview)
- [GNU Stow](https://www.gnu.org/software/stow/) — `brew install stow`
- Git
- [uv](https://docs.astral.sh/uv/) — only to run the helper scripts under `scripts/`, which are PEP 723 single-file scripts

## Installation

```bash
mkdir -p ~/src/github.com/ocrosby ~/.claude
git clone https://github.com/ocrosby/claude-config ~/src/github.com/ocrosby/claude-config
stow -t ~/.claude -d ~/src/github.com/ocrosby claude-config
```

Verify the links resolve back into the repo:

```bash
readlink ~/.claude/CLAUDE.md   # → ../src/github.com/ocrosby/claude-config/CLAUDE.md
readlink ~/.claude/rules       # → ../src/github.com/ocrosby/claude-config/rules
```

### What gets linked, and what doesn't

`.stow-local-ignore` controls this. Defining that file **overrides** stow's built-in default ignore list, so the defaults worth keeping are repeated inside it. Currently excluded from the package: `.git`, `.gitignore`, `README.md`, `LICENSE.*`, `LEARNINGS.md`, and `SKILLS.md` — repo-only meta-documents that are not live configuration.

Everything else at the top level is linked, including `scripts/`, `docs/`, and `prompts/`.

### Layout

The repo root *is* the stow package. **Never wrap the contents in a `.claude/` directory** — that wrapper would force stow into a less-direct linking shape. The flat layout is intentional.

```text
claude-config/                ← the stow package; repo root
├── README.md                 ← not linked
├── LEARNINGS.md              ← not linked
├── .stow-local-ignore        ← defines what stays repo-only
├── CLAUDE.md                 ← global instructions, loaded every session
├── settings.json
├── agents/
├── commands/
├── docs/
├── hooks/
├── output-styles/
├── prompts/
├── rules/
├── scripts/
└── skills/
```

### If stow reports conflicts

`~/.claude/` may already hold files from a previous setup. Stow refuses rather than clobbering them:

```bash
# Adopt the existing files into the repo, then review what got pulled in
stow --adopt -t ~/.claude -d ~/src/github.com/ocrosby claude-config
git -C ~/src/github.com/ocrosby/claude-config diff

# Or clear and re-link
rm -rf ~/.claude && mkdir -p ~/.claude
stow -t ~/.claude -d ~/src/github.com/ocrosby claude-config
```

Leave the runtime directories Claude Code created (`projects/`, `sessions/`, `plans/`, `shell-snapshots/`, `telemetry/`, and friends) — they aren't in this repo and won't conflict.

### Folded vs unfolded directories

When `~/.claude/` has no directory of the same name, stow links the whole directory in one symlink:

```bash
readlink ~/.claude/skills   # → ../src/github.com/ocrosby/claude-config/skills
```

While that holds, a newly added skill is visible to Claude immediately — no re-stow needed.

If `~/.claude/skills/` already exists as a real directory (because Claude Code or another tool created entries there), stow *unfolds* it: it links each skill individually instead. In that state a newly added skill has **no symlink until you re-run the stow command**, and Claude will not see it. Check which state you are in with the `readlink` above — if it prints nothing, you are unfolded and must re-stow after every addition.

### Migrating from a dotfiles-managed setup

> Transitional. Remove this section once every machine is over.

On a machine where `~/.claude/` is still wired through `~/dotfiles/claude`:

```bash
cd ~/dotfiles && stow -D claude                                   # free ~/.claude/
mkdir -p ~/.claude
stow -t ~/.claude -d ~/src/github.com/ocrosby claude-config       # link this repo
readlink ~/.claude/CLAUDE.md                                      # confirm
```

Then start a fresh Claude Code session and confirm a global skill (`/audit`, `/git ship`) loads.

Leave `~/dotfiles/claude/` in place — the two trees coexist as long as only one is stowed at a time. Removing it is a separate dotfiles PR once every machine has been flipped. An orphaned `~/dotfiles/.claude/settings.local.json` can stay; it is machine-local and part of neither package.

## Usage

Once stowed, most of this repo works without being invoked. Rules load themselves; hooks fire on tool events; `CLAUDE.md` is in the system prompt of every session. The parts you invoke are skills (`/skill-name`) and commands (`/command-name`).

The five surfaces differ by *when they run* and *what they can reach*:

| I want Claude to... | Use a... | Lives in | Activation |
|---|---|---|---|
| Always follow a convention | Rule | `rules/` | Session start, or lazily when `paths:` matches an opened file |
| Run a workflow when I ask | Skill | `skills/` | `/skill-name`, or by Claude from its `description` |
| Delegate a task with restricted tools or its own context | Agent | `agents/` | `@agent-name`, or by Claude from its `description` |
| Run a simple prompt when I ask | Command | `commands/` | `/command-name` |
| Change response style for a whole session | Output style | `output-styles/` | `outputStyle` in `settings.json` |
| Run deterministic logic at a lifecycle event | Hook | `hooks/` | Configured in `settings.json` |

Two distinctions worth keeping straight, because they are the ones that blur:

- **Rule vs skill.** A rule applies without anyone remembering to ask; a skill is a multi-step workflow with flags and choices that the user opts into. If forgetting to invoke it would be a bug, it's a rule.
- **Command vs script.** A command is a prompt — reasoning you want Claude to do. A script under `scripts/` is code — parsing, scanning, classification that should never be re-derived by a language model. When two or more skills repeat the same focused action, extract it: prompts become a command, logic becomes a script.

Rules use optional frontmatter:

| Field | Required | Effect |
|---|---|---|
| `description` | No | Shown in rule listings; identifies what the rule covers |
| `paths` | No | Glob patterns. The rule activates the first time the Read tool opens a matching file, then stays loaded for the session. Omit to load at session start and apply everywhere |

## Examples

### Write a rule that actually holds

Rules written in advisory language drift — "consider" and "should" get read as optional and quietly dropped under pressure. The fix is mandatory phrasing plus a reason the constraint exists:

| Drifts | Holds |
|---|---|
| "Consider running tests before shipping" | "Always run the test suite before committing. Do not proceed if tests fail." |
| "You should use parameterized queries" | "Never build SQL queries by string interpolation. Always use parameterized queries." |
| "Prefer dependency injection" | "Pass dependencies via constructor — never use globals. **This is an intentional design decision — do not simplify it away.**" |

The bolded anchor matters more than it looks. Without a stated *why*, Claude optimizes the constraint away the moment the code gets complicated enough to make it inconvenient.

Scope exceptions with literal cases, not categories — a category like "mechanical changes" will be read as broadly as it possibly can be:

```markdown
<!-- Too broad — gets overused -->
Exceptions: mechanical changes.

<!-- Scoped — stays stable -->
Exceptions: renaming an identifier, moving a file to a different package,
updating an import path. If there is any change to logic, control flow, or
observable behavior, it is not mechanical.
```

### Add a skill and confirm Claude can see it

```bash
mkdir -p skills/deploy
cat > skills/deploy/SKILL.md <<'EOF'
---
description: Deploy the current service to an environment. Invoke as /deploy <staging|prod>.
---

# Deploy

1. Confirm the branch is clean and rebased on main.
2. Run the test suite; stop on failure.
3. Deploy to the named environment.
EOF

readlink ~/.claude/skills   # non-empty → folded, skill is already live
```

If that `readlink` prints nothing, `~/.claude/skills/` is unfolded and the new skill has no symlink yet:

```bash
stow -R -t ~/.claude -d ~/src/github.com/ocrosby claude-config
readlink ~/.claude/skills/deploy   # → .../claude-config/skills/deploy
```

Commit the skill so the next machine gets it — a skill that only exists in `~/.claude/` is exactly the drift this repo exists to prevent.

### Find the rule that governs something

Rules are the surface most likely to surprise you later, because they apply without being invoked. To see what is currently in force:

```bash
for f in ~/.claude/rules/*.md; do
  echo "=== $(basename "$f") ==="
  awk '/^description:/' "$f"
done
```

Rules with no `description:` print only their filename — that's a gap worth filling, since the description is what makes a rule discoverable.

## Configuration

| File | Tracked | Purpose |
|---|---|---|
| `CLAUDE.md` | Yes | Global instructions loaded into every session |
| `settings.json` | Yes | Permissions, hooks, enabled plugins, TUI options, auto-approve rules |
| `settings.local.json` | No — gitignored | Per-machine permissions and paths. Never commit it |
| `.stow-local-ignore` | Yes | Which top-level entries stay repo-only |

`settings.json` currently defines `includeCoAuthoredBy`, `permissions`, `hooks`, `enabledPlugins`, `tui`, `skipAutoPermissionPrompt`, `voiceEnabled`, and `autoApprove`. Machine-specific overrides belong in `settings.local.json`, which Claude Code merges over the tracked file.

## Development

The helper scripts under `scripts/` are PEP 723 single-file scripts — run them directly and `uv` resolves the interpreter and dependencies:

```bash
./scripts/check_docs.py README.md              # documentation findings
./scripts/check_docs.py . --fail-on=must       # gate on Must Fix across the repo
./scripts/check_stow.py                        # is the package actually linked?
./scripts/tally_invocations.py                 # which skills actually get used
```

Scripts with behavior worth pinning have a sibling test file, run the same way:

```bash
./scripts/test_check_docs.py
./scripts/test_check_stow.py
```

After changing anything that affects linking — a new top-level directory, an edit to `.stow-local-ignore` — re-stow and confirm the package is clean:

```bash
stow -R -t ~/.claude -d ~/src/github.com/ocrosby claude-config
./scripts/check_stow.py
```

`check_stow.py` answers what `git status` cannot: whether everything in the package is actually linked into `~/.claude/`, whether a re-stow would drag in something that isn't config, and whether any link now dangles. A directory added to the repo months ago and never stowed looks perfectly healthy in git.

Conventions for this repo live in `CLAUDE.md`: Conventional Commits, one `type(scope)` pair per PR, and branch-before-touching-files. Insights about how rules and skills behave in practice go in `LEARNINGS.md`, not here.

## Contributing

This is a personal configuration, so outside contributions aren't expected and issues may sit unanswered. Fork it and make it yours instead — the license permits it, and it will serve you better than a patch to mine.

## License

MIT. See [LICENSE](./LICENSE). Copy whatever is useful; nothing here is warranted to work on your machine.

`.stow-local-ignore` excludes `LICENSE.*` from the stow package, so the file stays repo-only and is never linked into `~/.claude/`.

## Tips from the Claude Code team

> From [Boris Cherny's January 2026 thread](https://x.com/bcherny/status/2017742741636321619). Boris created Claude Code at Anthropic.

**Parallelism** — run 3–5 sessions in parallel using git worktrees; use subagents to throw more compute at a problem and to keep the main context clean; route permission requests through a hook to auto-approve safe ones.

**Planning** — start complex tasks in plan mode (shift+tab); re-plan instead of pushing through when things go sideways; use plan mode for verification steps, not just builds.

**Configuration** — invest in `CLAUDE.md` and update it after every mistake; commit reusable skills to git; use `/statusline` to surface context usage and branch; name and color-code one terminal tab per task or worktree.

**Prompting** — "Grill me on these changes"; "Prove to me this works"; "Scrap this, implement the elegant solution"; write detailed specs to cut ambiguity.

**Workflow** — paste a Slack bug thread and say "fix"; say "go fix the failing CI tests" without micromanaging how; point Claude at docker logs to troubleshoot distributed systems; use it for analytics against any database CLI, MCP, or API.

**Learning** — enable the Explanatory output style in `/config` to get the *why*; have Claude generate visual HTML presentations for unfamiliar code and ASCII diagrams of protocols; use voice dictation (fn twice on macOS), since you speak about 3× faster than you type.

**Terminal** — the team recommends Ghostty, for synchronized rendering and unicode support.

## Power features

> From [Boris Cherny's March 2026 thread](https://x.com/bcherny/status/2038454336355999749) on under-used Claude Code features.

**Mobile and cross-device** — there's an iOS/Android app (Claude app → Code tab); `/teleport` or `claude --teleport` continues a cloud session locally; `/remote-control` drives a local session from a phone or browser, and `/config` can enable it for all sessions.

**Automation** — `/loop` runs a skill on an interval (`/loop 5m /babysit` for auto review and rebase); `/schedule` runs Claude on a cron schedule up to a week out. Turn a workflow into a skill first, then loop it.

**Hooks** — deterministic logic at each lifecycle stage: `SessionStart` to load context, `PreToolUse` to log every bash command, `PermissionRequest` to route approvals to another channel, `Stop` to poke Claude to keep going. See the [hooks documentation](https://code.claude.com/docs/en/hooks).

**Desktop and browser** — Cowork Dispatch for secure remote control of Claude Desktop; the Chrome extension for frontend work, where Claude iterates until the result looks right; the desktop app auto-starts web servers and tests them in a built-in browser.

**Session management** — `/branch` forks the current session (or `claude --resume <id> --fork-session`); `/btw` answers a side question without derailing the agent; `/voice` enables voice input.

**Parallel work at scale** — `claude -w` starts a session directly in a git worktree; `/batch` fans a changeset out to many worktree agents; the `WorktreeCreate` hook covers non-git VCS.

**SDK and CLI flags** — `--bare` speeds SDK startup up to 10× by skipping `CLAUDE.md`, settings, and MCP auto-load; `--add-dir` (or `/add-dir`) grants access and permissions in additional repos; `--agent=<name>` runs a custom agent, including non-interactively; `additionalDirectories` in `settings.json` always loads extra folders.

## Related documentation

- `CLAUDE.md` — global instructions loaded into every session
- `LEARNINGS.md` — accumulated notes on what makes rules, skills, hooks, and agents behave reliably
- `docs/OPERATING.md` — plan mode, session management, parallel work, multi-repo setups
- Per-directory `README.md` files under `skills/`, `agents/`, `commands/`, `hooks/`, and `output-styles/`. Each `SKILL.md`'s `description:` frontmatter is the source of truth for what that skill does — there is no separate catalog to keep in sync

## References

- [Claude Code documentation](https://code.claude.com/docs/en/overview) — configuration, skills, rules, agents
- [obra/superpowers](https://github.com/obra/superpowers) — community collection of skills, rules, and agents
- [affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code) — broad harness covering skills, instincts, memory, security, and research-first development
- [shanraisshan/claude-code-best-practice](https://github.com/shanraisshan/claude-code-best-practice) — patterns and conventions for agents, commands, and skills
- [0xquinto/bcherny-claude](https://github.com/0xquinto/bcherny-claude) — Boris Cherny's own configuration; the two sourced sections above draw on this repo and the linked threads
- [GNU Stow](https://www.gnu.org/software/stow/) — the symlink farm manager wiring this package into `~/.claude/`
