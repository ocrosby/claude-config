# Commands

Commands are Markdown files loaded as a prompt when the user types `/command-name` in a Claude Code session. They are the simplest invocation mechanism — no frontmatter, no step enforcement, just a document Claude reads and acts on.

## File format

A command file is plain Markdown named after the slash command it responds to:

```
commands/
  ship.md      →  /ship
  workflow.md  →  /workflow
  work.md      →  /work
```

No frontmatter is required. The filename (without `.md`) becomes the command name.

## Commands vs. skills

Both are invoked with a `/command`. The distinction is where the file lives and what structure it has:

| | Commands (`commands/`) | Skills (`skills/*/SKILL.md`) |
|---|---|---|
| Location | Flat file in `commands/` | Subdirectory with `SKILL.md` |
| Frontmatter | None required | `description`, `triggers`, `paths` |
| Auto-activation | Never — always user-invoked | Can activate via `paths` globs |
| Best for | Reference docs, complex dispatchers, multi-subcommand tools | Repeatable multi-step workflows with enforced structure |

Use a command when the content is primarily a reference document or a dispatcher that Claude reads top-to-bottom. Use a skill when the workflow has numbered steps that must be followed in order with hard-stop conditions.

## Two kinds of commands

Commands in this directory fall into two roles. Both are user-invocable; the difference is whether they are also called from inside skills.

### Building blocks

Commands that exist so that 2+ skills can share the same focused action without duplicating it. The skill invokes the command as a numbered step, and the user can also invoke it standalone.

| Command | Used by | Purpose |
|---|---|---|
| `/conventional-commit-msg` | `/git-ship`, `/git-cpr` | Compose a Conventional Commits message from staged diff and commit. No staging, no push, no branch. |

See `rules/skill-conventions.md` → "Skills as orchestrators, commands as building blocks" for the extraction rule.

### Standalone commands

Commands that exist as their own entry point — references, dispatchers, or single-action prompts that no skill needs to reuse.

### `/audit`

Audits the entire `.claude/` directory — agents, hooks, skills, commands, rules, and `settings.json` — and reports what's suboptimal with specific fixes grouped by category and ordered by impact. Checks for correctness, redundancy, missing connections, coverage gaps, and discoverability issues. Asks which findings to implement before making any changes.

### `/bdd`

Runs a BDD feature file's pytest stub against a target environment and region. Parses arguments in the form `<feature_name> [--env|-e <env>] [--region|-r <region>] [--serial|-s]`, locates the feature file and corresponding test stub, runs pytest with the correct environment variables, and produces a structured results summary with per-failure detail blocks.

```
/bdd site_based_observations
/bdd time_series --env prod
/bdd historical_postal -e prod -r use1 --serial
```

### `/grill`

Adversarial code review. Invokes `/code-review` in strictest-interpretation mode and refuses to clear changes until every Must Fix, Should Fix, and Consider item is resolved. Use to stress-test changes before shipping. Mechanically identical to `/code-review`; only the persona and rating scale differ.

### `/test-and-fix`

Run the test suite, diagnose failures, fix them in place, re-run until green.

### `/workflow`

Development workflow reference. Documents the full feature workflow (`/architect` → `/*-feat` → `/code-review` → `/git-ship` → `/git-main`), branch management, maintenance commands, debugging paths, automated quality gates, and rules that fire automatically. Use this when orienting to the workflow or deciding which tool to reach for.
