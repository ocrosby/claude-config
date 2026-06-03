---
description: Before writing a plan for non-trivial work, interview the user — surface open questions and a high-level outline first, iterate, then commit to a plan. Pairs naturally with Claude Code's plan mode (Shift+Tab); use when entering planning without enough context.
when_to_use: User asks for a plan / design / implementation strategy AND key questions are unresolved. Examples — "plan how we'd add X", "design the migration", "what's the approach for Y", or any time you'd otherwise jump to writing a multi-step plan without enough context. Skip when the user has already provided full context or explicitly says "just plan it".
disable-model-invocation: false
---

# Plan Interview

Before writing a plan, work back and forth with the user. Surface the open questions and a high-level outline first; commit to a detailed plan only after the unknowns are resolved.

Source: adapted from [fredrikaverpil/dotfiles](https://github.com/fredrikaverpil/dotfiles/blob/main/stow/shared/.claude/skills/plan-interview/SKILL.md). Upstream is a one-line directive; expanded here with concrete questions and stopping rules.

## Workflow

### 1. List your open questions

Before proposing any structure, write a numbered list of the specific unknowns blocking a good plan. Aim for 3–8 questions. Group them as:

- **Scope** — what's in / out, success criteria, deadline
- **Constraints** — must-have invariants, stability/perf budgets, compatibility requirements
- **Inputs** — data sources, fixtures, environment access, credentials
- **Outputs** — the artifact you produce (PR, doc, script, dashboard) and who consumes it
- **Risks** — known failure modes the user wants you to avoid

If a question's answer is already in `CLAUDE.md`, the working directory's existing files, or recent conversation context, don't ask it — answer it yourself in the next step.

### 2. Sketch a high-level outline

Three to five bullets describing the shape of the plan you'd write *if* your assumptions hold. Not a detailed plan — an outline of the major phases or decision points. Mark each assumption that ties to an open question with `(Q1)`, `(Q3)`, etc. so the user can see what would change if a question's answer flips.

### 3. Ask, iterate, converge

Send the questions + outline to the user. Wait for answers. If the user reframes scope or contradicts an assumption, restart from step 1 — don't try to patch the outline incrementally. Two rounds is normal; three or more is a signal the problem isn't ready for a plan yet.

### 4. Commit to the plan

When the open questions are answered and the outline survives a round, write the detailed plan. Reference the questions and answers inline so the user can see how their input shaped the design.

## Pairs with plan mode

This skill is the *information-gathering* phase that should precede entering Claude Code's plan mode (Shift+Tab). Once questions are resolved, switch to plan mode for the detailed plan itself — the two are complementary, not redundant. Per `CLAUDE.md`'s "Working with Plan Mode" rule: "Pour energy into the plan so Claude can 1-shot the implementation."

## When to skip this skill

- The user said "just plan it" or "skip the interview"
- All context needed is already on the table (the task is mechanical: a bug fix with a clear repro, a refactor with a known target shape)
- You're inside `/architect design` or another dispatcher that already runs its own interview step

## Hard rules

- Do not write a multi-step plan before the open questions are surfaced — partial plans built on wrong assumptions waste both the user's review time and your tokens
- Never stack more than 8 questions in one round. If you have more, ask the most blocking 5 first
- If the user answers a question with "I don't know — what do you recommend?", that's not a dead end — propose two options with the tradeoff and let them pick
