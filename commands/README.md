# Commands

Commands are Markdown files loaded as a prompt when the user types `/command-name` in a Claude Code session. They are the simplest invocation mechanism — no required frontmatter, no step enforcement, just a document Claude reads and acts on.

## File format

A command file is plain Markdown named after the slash command it responds to:

```
commands/
  workflow.md  →  /workflow
  bdd.md       →  /bdd
  audit.md     →  /audit
```

Frontmatter is optional. The filename (without `.md`) becomes the command name. Two frontmatter fields matter here:

- `description` — shown in autocomplete; describe the command in one specific sentence.
- `user-invocable: false` — hides the command from the `/` menu so it is reachable only by other skills/commands that explicitly invoke it. Use this for building blocks.

## Commands vs. skills

Both are invoked with a `/command`. The distinction is where the file lives and what structure it has:

| | Commands (`commands/`) | Skills (`skills/*/SKILL.md`) |
|---|---|---|
| Location | Flat file in `commands/` | Subdirectory with `SKILL.md` |
| Frontmatter | Optional | `description`, `paths`, etc. recommended |
| Auto-activation | Never — always invoked by user or by a skill | Can activate via `paths` globs |
| Best for | Reference docs, building-block actions, single-shot dispatchers | Repeatable multi-step workflows with enforced structure |

Use a command when the content is primarily a reference document or a focused atomic action that a skill needs to share. Use a skill when the workflow has numbered steps that must be followed in order with hard-stop conditions.

## Two kinds of commands

Commands in this directory fall into two roles.

### Building blocks (hidden from the `/` menu — `user-invocable: false`)

These exist so 2+ skills can share the same focused action without duplicating it. Skills invoke them as numbered steps.

| Command | Used by | Purpose |
|---|---|---|
| `/branch-from-main` | `/git ship`, `/git cpr`, `/git sync`, `/git worktree` | Create a clean feature/hotfix branch from the latest `main`, stashing and re-applying uncommitted work. |
| `/conventional-commit-msg` | `/git ship`, `/git cpr` | Compose a Conventional Commits message from the staged diff and commit. No staging, no push, no branch. |
| `/open-pr` | `/git ship`, `/git cpr` | Push the current branch upstream and open (or update) a PR with a structured body. |
| `/test-and-fix` | `/feature`, `/code`, `/debug` workflows | Run the test suite, diagnose failures, fix them in place, re-run until green. |

See `rules/skill-conventions.md` → "Skills as orchestrators, commands as building blocks" for the extraction rule.

### Standalone reference commands

Commands that exist as their own entry point — references, dispatchers, or single-action prompts.

### `/audit`

Audits the entire `.claude/` directory — agents, hooks, skills, commands, rules, and `settings.json` — and reports what's suboptimal grouped by category and ordered by impact. Checks for correctness, redundancy, missing connections, coverage gaps, and discoverability issues. Asks which findings to implement before making any changes. (Also reachable as the `/audit` skill — the command is a thin alias of the workflow.)

### `/bdd`

Runs a BDD feature file's pytest stub against a target environment and region. Parses arguments in the form `<feature_name> [--env|-e <env>] [--region|-r <region>] [--serial|-s]`, locates the feature file and corresponding test stub, runs pytest with the correct environment variables, and produces a structured results summary with per-failure detail blocks.

```
/bdd site_based_observations
/bdd time_series --env prod
/bdd historical_postal -e prod -r use1 --serial
```

### `/workflow`

Development workflow reference. Documents the full feature workflow (`/architect design` → `/feature` → `/code review` → `/git ship` → `/git main`), branch management, maintenance commands, debugging paths, automated quality gates, and rules that fire automatically. Use this when orienting to the workflow or deciding which tool to reach for.
