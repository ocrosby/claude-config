---
description: Audit dispatcher — system (Claude workflow components), repo (git history of any repository), skill (per-SKILL.md structural quality). The first word of $ARGUMENTS selects the subcommand.
argument-hint: "<subcommand> [arguments]"
aliases: codebase-audit, workflow-audit
allowed-tools: Read, Grep, Glob, Bash
---

# Audit: Audit Dispatcher

Use this skill for any "audit X" workflow. The dispatcher routes between three disjoint scopes:

- `system` — the Claude workflow system in `~/.claude/` (rules, agents, hooks, skills, commands, settings)
- `repo` — the git history of any repository (churn, ownership, bug hotspots, momentum, firefighting)
- `skill` — individual `SKILL.md` files against the skill-authoring conventions

## Usage

```
/audit                  # show this help
/audit system           # audit the Claude workflow components
/audit repo             # audit the current git repository's history
/audit skill [name]     # audit every SKILL.md (or one by name) via skill-reviewer
```

## Workflow

### 1. Parse the subcommand

Split `$ARGUMENTS` on the first space. The first word is the subcommand.

- Empty or `help` → print **Usage** and stop.
- Not one of `system`, `repo`, `skill` → print **Usage** and stop.
- Dispatch to the matching step.

### 2. Dispatch — `system`

Use this when auditing the Claude workflow components (`~/.claude/rules/`, `agents/`, `hooks/`, `skills/`, `commands/`, `settings.json`).

Read `~/.claude/skills/audit/system.md` and apply its workflow:

- Two parallel batches — discover file paths, then read every file
- Analyze against five categories (correctness, redundancy, missing connections, coverage gaps, discoverability)
- Verify coverage before reporting
- Report findings grouped by category and ordered by impact
- Confirm with the user before implementing any fix

### 3. Dispatch — `repo`

Use this when auditing the git history of the current repository (orientation, repo health assessment).

Read `~/.claude/skills/audit/repo.md` and apply its workflow:

- Detect GitHub availability (`gh repo view --json nameWithOwner`)
- Five parallel analyses: high-churn files, ownership / bus factor, bug hotspots, project momentum, firefighting patterns
- Synthesize into a structured markdown report with key takeaways

### 4. Dispatch — `skill`

Use this when auditing individual `SKILL.md` files for structural quality.

Read `~/.claude/skills/audit/skills.md` and apply its workflow:

- Discover every `SKILL.md` under `~/.claude/skills/`
- Run the `skill-reviewer` agent on each
- Compile findings into Must Fix / Should Fix / Consider buckets per `rules/findings-format.md`
- Surface the top 3 to fix now
- Optionally fix in place, one skill at a time, with per-skill commits

### 5. Final verification step

Each dispatch step ends with its own verification gate inside the referenced Level 3 file. Confirm the gate fired before exiting.

## Rules (apply across all subcommands)

- Never report issues that were already fixed in the current session.
- Never manufacture findings — if the system looks well-optimized, say so.
- For `system` and `skill`: do not make changes without explicit user confirmation.
- For `repo`: the audit is read-only; never modify the repository being audited.
