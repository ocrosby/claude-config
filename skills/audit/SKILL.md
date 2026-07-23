---
description: Use when the user asks to audit the Claude workflow system (rules, agents, hooks, skills, commands, settings), a git repository's history (churn, ownership, hotspots, momentum), individual SKILL.md files against authoring conventions, or GitHub Actions Node-version deprecation. Invoke as /audit <system|repo|skill|actions>.
argument-hint: "<subcommand> [arguments]"
aliases: codebase-audit, workflow-audit
allowed-tools: Read, Grep, Glob, Bash
---

# Audit: Audit Dispatcher

Use this skill for any "audit X" workflow. The dispatcher routes between four disjoint scopes:

- `system` — the Claude workflow system in `~/.claude/` (rules, agents, hooks, skills, commands, settings)
- `repo` — the git history of any repository (churn, ownership, bug hotspots, momentum, firefighting)
- `skill` — individual `SKILL.md` files against the skill-authoring conventions
- `actions` — third-party `uses:` actions in `.github/workflows/*.yml` against the GitHub Node-20 runner deprecation

## Usage

```
/audit                  # show this help
/audit system           # audit the Claude workflow components
/audit repo             # audit the current git repository's history
/audit skill [name]     # audit every SKILL.md (or one by name) via skill-reviewer
/audit actions          # check workflow actions for Node-version deprecation
```

## Workflow

### 1. Parse the subcommand

Split `$ARGUMENTS` on the first space. The first word is the subcommand.

- Empty or `help` → print **Usage** and stop.
- Not one of `system`, `repo`, `skill`, `actions` → print **Usage** and stop.
- Dispatch to the matching step.

### 2. Dispatch — `system`

Use this when auditing the Claude workflow components (`~/.claude/rules/`, `agents/`, `hooks/`, `skills/`, `commands/`, `settings.json`).

Read `~/.claude/skills/audit/system.md` and apply its workflow. **If the file cannot be read: stop and do not proceed. Report the missing dispatch file.**

**If the user has not confirmed before any change is applied: stop and do not proceed.**

### 3. Dispatch — `repo`

Use this when auditing the git history of the current repository (orientation, repo health assessment).

Read `~/.claude/skills/audit/repo.md` and apply its workflow. **If the file cannot be read: stop and do not proceed. Report the missing dispatch file.**

The audit is read-only — never modify the repository being audited.

### 4. Dispatch — `skill`

Use this when auditing individual `SKILL.md` files for structural quality.

Read `~/.claude/skills/audit/skills.md` and apply its workflow. **If the file cannot be read: stop and do not proceed. Report the missing dispatch file.**

**If the user has not confirmed before any fix-in-place is applied: stop and do not proceed.**

### 5. Dispatch — `actions`

Use this when checking third-party GitHub Actions referenced via `uses:` for the Node-20 runner deprecation.

Read `~/.claude/skills/audit/actions.md` and apply its workflow. **If the file cannot be read: stop and do not proceed. Report the missing dispatch file.**

**If the user has not confirmed before any version-pin bump is applied: stop and do not proceed.**

### 6. Final verification step

Each dispatch step ends with its own verification gate inside the referenced Level 3 file. After the dispatch step returns, confirm its verification step produced observable output — a report, a diff, or an explicit "no findings" message. **If no such output was produced: stop and do not report success.**

## Rules (apply across all subcommands)

- Never report issues that were already fixed in the current session.
- Never manufacture findings — if the system looks well-optimized, say so.
