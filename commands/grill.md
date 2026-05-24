---
description: "Adversarial code review — invokes /code-review in skeptical-staff-engineer mode. Use to stress-test changes before shipping."
---

# Grill: Adversarial Code Review

Use this command when you want a **harsher pass** over the current branch than the default `/code-review` produces. The mechanics are the same — only the persona and rating scale differ.

**Relationship to `/code-review`:** this command does not duplicate `/code-review`'s logic. It runs the same review pipeline (diff base detection, language routing, reviewer-agent delegation) but instructs the reviewer to apply the strictest interpretation of every finding and to refuse to clear the changes until each issue is resolved.

## Steps

1. Invoke `/code-review` against the current branch with the explicit instruction: **"Adversarial mode — apply the strictest interpretation. Default to NEEDS WORK unless every issue is conclusively resolved."**
2. After `/code-review` returns, override its summary with a verdict on this scale:
   - **SHIP IT** — no Must Fix, no Should Fix, no Consider items remain
   - **NEEDS WORK** — any Should Fix or Consider items remain
   - **BLOCK** — any Must Fix items remain, or there are tests missing for new/changed behavior, or there is a breaking change to a public API
3. If NEEDS WORK or BLOCK: list every issue with file, line, and the specific fix required. Do not paraphrase the reviewer agent's findings — quote them.
4. After fixes are applied, re-run from step 1. Loop until SHIP IT.
5. Only return SHIP IT when steps 1–4 produced a clean pass with zero remaining items.

## Rules

- Never lower the verdict to accommodate effort already spent on the change.
- Never collapse Must Fix items into Should Fix.
- A breaking change to a public API is always BLOCK until the breakage is justified in the commit message or the API is restored.
- Missing tests for new or changed behavior is always BLOCK.
