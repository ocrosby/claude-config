# Plan Grilling

Use this skill when an existing plan, decision, or design is on the table and the user wants its weak points surfaced through a relentless one-question-at-a-time interview before committing to implementation.

Sourced from [mattpocock/skills — productivity/grill-me](https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me) (MIT). The one-at-a-time question rule and the "recommend before asking" rule are Matt's; the structure is adapted to this repo's numbered-step convention.

## When to use / When NOT to use

**Use when:** a plan, decision, or design is already on the table and the user wants its weak points surfaced before committing to implementation.

**Do not use when:**

- The user wants a *new* plan built from scratch — use `/architect interview` instead.
- The user asks for adversarial *code* review of already-written code — use `/code grill` instead.
- The user said "just do it" / "skip the grill" / "no interview" — proceed straight to the requested action.

## Workflow

### 1. Restate the target in one sentence

Name the plan, decision, or design under grill in one sentence, before any question. If the user's request is vague ("grill me on this"), restate what "this" refers to so the user can correct scope before questioning starts. **If the target is not clear after restating: stop and ask which plan, decision, or design.**

### 2. Look up every fact before asking

For every dimension of the target, discover facts from the environment first: read referenced files, run `git log`, check tool output, grep the codebase. Ask the user only about **decisions** — anything that requires judgment or context the environment does not carry. **If a question could have been answered by a Read, Bash, or Grep call: do not ask it — look it up.**

### 3. Ask exactly one question per turn

Every turn must end with exactly one question. Never batch questions. Every question must include:

- The specific decision under grill
- The recommended answer, in one sentence, with the reason
- The failure mode if the recommendation is wrong

Wait for the user's answer before the next turn. Do not queue follow-up questions in the same message — resolve each answer before deriving the next question.

### 4. Walk the decision tree, resolving dependencies

Order questions so dependencies resolve first. When an answer closes a branch, prune the dependent questions and name which ones went away — do not carry dead questions. When an answer invalidates the recommended answer of a later question, restate the recommendation before asking. **If an answer contradicts the target's premise: stop and restart from step 1 with the revised premise.**

### 5. Draft the outcome summary

When every open question is answered, draft a three-to-five bullet summary in this shape:

```
### What stood
- <element of the target that survived, unchanged>

### What changed
- <element of the target with the specific revision from this session>

### What got dropped
- <element abandoned; the answer that killed it>
```

### 6. Verify the summary, then wait for user confirmation

Before delivering the step 5 summary, run every check below. **If any check fails: fix the summary before delivering it.**

- Every `What stood / What changed / What got dropped` heading has at least one bullet, or is followed by `_(none)_` explicitly — no heading is left silently empty.
- Every question answered during the session is reflected in exactly one of the three sections. No answered question is silently omitted.
- If any question went unanswered (because the user said "skip to the summary" or reframed scope mid-session), the summary ends with an `### Unresolved` section listing them by decision name, so the user knows the summary is partial.
- No section contains a recommendation that was invalidated during grilling.

After delivering the summary, wait for the user's explicit confirmation. **If the user does not confirm: adjust the summary and re-run this step; do not begin implementation, editing, or follow-up planning in the same turn as confirmation.** Grilling ends at confirmation — action is a separate step the user starts.

## Exceptions

- **"I don't know — what do you recommend?"** — not a dead end. Present two options with the tradeoff and let the user pick.
- **"Just give me the summary" / "Stop grilling, summarize what you have"** — stop questioning immediately and jump to step 5 with what has been answered so far. Include the `### Unresolved` section required by step 6 so the user knows the summary is partial.
- **"Actually, let's grill the revised approach where ..." / "Reframe: the plan is now X"** — restart from step 1 with the new scope. Do not patch the tree in place.
