---
description: Audits the Claude workflow system — reads every component (rules, agents, hooks, skills, commands, settings) and reports what's suboptimal with specific fixes, grouped by category and ordered by impact. For per-skill structural quality only, use /skill audit instead.
aliases: workflow-audit
---

# Workflow Audit

## Workflow

### 1. Read Everything

**Use two parallel batches — do not read files sequentially.**

**Batch 1 — discover file paths** (run these Glob calls in a single parallel message):
- `Glob("agents/*.md")`
- `Glob("hooks/*.sh")`
- `Glob("skills/*/SKILL.md")`
- `Glob("commands/*.md")`
- `Glob("rules/*.md")`

**Batch 2 — read all discovered files plus settings** (issue every Read call in a single parallel message):
- `skills/*/SKILL.md` — read with `limit: 50` (frontmatter + purpose section is sufficient; full workflow steps are not needed for structural analysis)
- `agents/*.md` — read in full (they're short and the full content is needed)
- `hooks/*.sh` — read in full (enforcement logic must be understood completely)
- `rules/*.md` — read in full (they're short and the full path/content is needed)
- `commands/*.md` — read in full
- `settings.json` and `CLAUDE.md` — read in full

Do not read files one at a time. Issue all Read calls together so they execute concurrently. If a skill's first 50 lines reveal an issue that requires deeper inspection, read that specific file in full as a follow-up. The audit is only as good as its coverage — do not skip any file.

### 2. Analyze Against Five Categories

#### Correctness
- Rules or skills that fire in the wrong context (e.g., a mandatory rule that activates during tasks it doesn't apply to)
- Semantic mismatches between a stated intent and actual behavior
- Skills whose workflow steps contradict their own rules or each other

#### Redundancy
- Duplicate sources of truth (e.g., a rule that restates what `settings.json` already enforces)
- Skills that duplicate agent logic instead of delegating to it
- Rules that repeat guidance already covered by another rule on the same paths

#### Missing Connections
- Skills that should delegate to specialist agents but do their own inline analysis instead
- Agents that have no user-invocable skill entry point
- Rules that state "never do X" with no hook to enforce it
- Skills that reference related skills/agents without linking to them

#### Coverage Gaps
- Language families with inconsistent coverage (one language has a security rule, others don't; one has a debugger agent, others don't)
- Hooks that cover some file types but not others in the same family
- Automation that would close a gap between a stated rule and its enforcement

#### Discoverability
- Workflows that exist but aren't surfaced via autocomplete, rules, or skill cross-references
- Skills or agents that solve the same problem without knowing about each other
- The `commands/` directory underused when key workflows aren't reachable via `/`

### 3. Verify Coverage

Before assembling the report, confirm every file path discovered in Batch 1 of step 1 was actually read in Batch 2. **If any file was skipped: read it now and re-run the analysis in step 2. Do not proceed to step 4 until coverage is complete.** A report built on partial coverage is worse than no report — it gives false confidence that the system is sound.

### 4. Report Findings

For each finding:

```
**[Category] Title**
What: one sentence describing the issue
Why: why it matters — what breaks or degrades without a fix
Fix: the specific change needed (file, section, what to add/remove/change)
```

Group by category. Within each group, order by impact — correctness and safety issues first, symmetry and polish last.

If no issues are found in a category, omit it from the report.

Apply these constraints to every report:

- Never report issues that were already fixed in the current session.
- Always distinguish "this is broken" (correctness) from "this could be better" (polish).
- If the system looks genuinely well-optimized, say so — never manufacture findings.

### 5. Confirm Before Implementing

**After presenting all findings: stop and do not proceed with any changes.** Ask the user:

> Which of these should I implement? (say "all" or list specific items)

**Do not make any changes until the user explicitly confirms.**

## Related

For auditing individual `SKILL.md` files against structural conventions, use `/skill audit` instead — it runs `skill-reviewer` on each skill file and is scoped to skill quality, not system-wide integration.
