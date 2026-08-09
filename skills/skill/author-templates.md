# Skill Author — Skeletons

Level-3 resource for `/skill author` (dispatch steps 4–5). Fill-in-the-blank skeletons for a new `SKILL.md`. The normative requirements (mandatory language, verification step, named agents) stay in `SKILL.md` — these are just the shapes to fill.

## Title and scope skeleton (step 4)

```markdown
# Skill Name

Use this skill when <specific trigger condition>.

## When NOT to use
- <exclusion 1 with literal example>
- <exclusion 2 with literal example>
```

Omit "When NOT to use" if there are no meaningful exclusions.

## Workflow skeleton (step 5)

```markdown
## Workflow

### 1. <Action verb> the <thing>

- Concrete substep
- **If <failure condition>: stop and do not proceed.** <What to tell the user.>

### 2. <Next action>
...

### N. Verify

Confirm the output is correct:
- <verification check 1>
- <verification check 2>
```
