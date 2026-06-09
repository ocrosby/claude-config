# Skill File Audit (Structural Quality)

Health-check individual `SKILL.md` files against the skill-authoring conventions in `skills/CLAUDE.md` and `rules/skill-conventions.md`. Delegates to the `skill-reviewer` agent.

For a system-wide audit of how all components (hooks, rules, agents, skills, settings) integrate, use `/audit system` — it covers inter-component correctness, not individual file quality.

## Workflow

### 1. Discover skill files

```bash
find ~/.claude/skills -name "SKILL.md" | sort
```

If a skill name was provided after `skill` (e.g. `/audit skill git`), filter to that file only.

### 2. Run `skill-reviewer` on each file discovered

Collect all findings.

### 3. Compile the report

Group findings by severity per `rules/findings-format.md` — **Must Fix → Should Fix → Consider**. Within each bucket, order by impact. Omit a bucket that has no entries.

Per-skill section shape:

```
**skills/<name>/SKILL.md**
- `path/to/SKILL.md:LINE` — <what>. **Why:** <why>. **Fix:** <fix>.
```

### 4. Prioritize

After the report, write a **Top 3 to fix now** section: the three skills whose Must Fix or Should Fix findings are most likely to affect current work or cause immediate cycles.

### 5. Optionally fix in place

If the user asks: fix Must Fix findings immediately, one skill at a time. Confirm each fix with `skill-reviewer` before moving to the next. Commit after each:

```
fix(claude): resolve skill-audit findings in /<skill-name>
```

**Do not batch multiple skills into one commit** — it makes reverts harder.

## Rules

- Do not skip any skill file in step 1 — a partial audit is misleading.
- Do not auto-fix without user confirmation.
- Report findings even if the skill is rarely used.
