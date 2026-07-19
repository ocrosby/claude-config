---
description: Enforces structural and language conventions when editing Claude skill files
paths:
  - "skills/*/SKILL.md"
---

# Skill File Conventions

When writing or editing a `skills/*/SKILL.md` file, the following conventions are mandatory. A skill that violates these will drift, contradict other configuration, or fail to enforce the behavior it describes.

## Frontmatter

Every field is optional. Only `description` is recommended so Claude knows when to invoke the skill.

- `description` — one sentence, specific enough to distinguish this skill from similar ones
- `paths` — glob patterns, if the skill fires automatically based on file context
- `aliases` — prior name(s) this skill was renamed from, single value or comma-separated
- `argument-hint` — autocomplete hint shown after the slash command
- `disable-model-invocation: true` — block Claude/sub-agents from auto-invoking; the user can still type the slash command
- `user-invocable: false` — hide from the `/` menu so the user does not invoke manually; Claude can still invoke programmatically
- `allowed-tools` — pre-approve tools while the skill is active

**The directory name provides the slash command.** `skills/git/` automatically registers as `/git`. **Never** add a `triggers:` field — it is not a real frontmatter field and will be silently ignored.

The full field reference and `disable-model-invocation` vs `user-invocable` decision matrix live in `skills/CLAUDE.md` — read it before adding a new field.

## Language

- Use **mandatory** language: "must", "always", "never", "do not", "required"
- Do **not** use advisory language: "should", "consider", "suggest", "prefer", "when appropriate"
- Advisory language is interpreted as optional and skipped inconsistently across sessions
- Exception: use "consider" only in a clearly labeled optional/suggestion section, never in workflow steps

## Workflow structure

- Number every step: `### 1. Step Name`
- Each step must describe a concrete action, not a general principle
- Hard-stop conditions must be explicit: "**If X: stop and do not proceed.**"
- The final step must be a verification step — confirm the output is correct before the skill exits

## Scope

- Every skill must have a "When to use" section (or an equivalent opening paragraph) that states what triggers it
- Every skill that has exceptions must define them with literal examples, not category names
- If the skill delegates to an agent, name the agent explicitly

## Scope buckets

Every skill must fit cleanly into exactly **one** of four scope buckets. A skill that straddles two or more confuses invocation — split it or trim its scope until it fits one.

- **Utility** — does one small reusable thing, every time.
- **Verification** — checks final output quality against an objective bar.
- **Data Enrichment** — pulls external data in.
- **Orchestration** — chains other skills into a multi-step playbook.

Orchestration that coordinates other skills is **not** straddling — a playbook is allowed to touch every bucket through the skills it calls, as long as it does not itself do their work inline.

A **Verification** skill must produce an objective output — a Pass/Fail or a grade out of 10, never a vague verdict ("looks good", "seems fine") — and check one of:

- **Correctness** — does the output run/compile/pass tests, match a schema or API contract, or satisfy a lint/style rule?
- **Fidelity** — are facts, config values, version numbers, and referenced docs real and accurate — not hallucinated flags, deprecated APIs, or wrong paths?
- **Quality** — does it meet a bar the user cares about (idiomatic code, consistent commit-message format, a PR body that explains the "why", docs that match the current CLI surface)?

## Conflict check

- Before finalizing a skill, verify it does not duplicate what an existing rule already enforces
- If a rule covers the same ground, the skill must reference the rule rather than repeat it
- Contradictions between a skill and a rule create cycles — one will be ignored; resolve before committing

## Skills as orchestrators, commands as building blocks

**This is an intentional design decision — do not simplify it away.**

A skill orchestrates a workflow. A command performs one focused action. When the same concrete mechanic appears in two or more skills, it must be extracted so it lives in exactly one place.

### Mandatory behavior

- When 2+ skills share the same concrete mechanic (e.g. constructing a Conventional Commits message, opening a PR with `gh pr create`, creating a feature branch from `main`), extract that mechanic. Do not inline it twice.
- The extracted unit must be either a **command** (`commands/<name>.md`) or a **script** (`scripts/<name>.py`). Choose by the rule below.
- A skill that uses an extracted command must invoke it explicitly: `Invoke /<command-name>` as a numbered step. Do not paraphrase the command's contents — the skill names the command and trusts it.
- The extracted command must remain user-invocable in isolation. If `/foo` only makes sense as a sub-step of `/bar`, it is not a real command — keep it inlined in `/bar`.

### Command vs. script — choose by the mechanic's nature

| The mechanic is... | Extract to a... | Examples |
|---|---|---|
| Prompted reasoning — Claude composes text, decides a name, drafts a message, picks an approach | **Command** (`commands/*.md`) | Compose a Conventional Commits message from staged diff; write a PR body; decide a branch name from the change type |
| Deterministic logic — parsing, scanning, classification, file inspection that always returns the same answer for the same input | **Script** (`scripts/*.py`) | Group mixed-concern changes into per-type buckets; parse `CODEOWNERS` and `pyproject.toml`; tally invocations from session history |

Existing examples to follow: `scripts/migrate_scan.py` (called by `/code migrate`), `scripts/analyze_history.py` (called by `/skill gaps`), `scripts/tally_invocations.py` (called by `/skill usage`). Skill orchestrates → script returns structured data → skill acts on the result.

### When extraction is NOT required

- The mechanic appears in exactly one skill and has no obvious second consumer. Inline it.
- The "shared" surface is just a one-line shell command (`git fetch origin main`). Inlining is clearer than referencing.
- The mechanic is a single sentence of prose that two skills phrase the same way. That's not shared mechanics — that's coincidence.

### Why this exists

Without this convention, skills grow to 200+ lines, the same git pipeline appears in three places, and any change has to be made N times. The `migrate` / `skill-gaps` / `skill-usage` pattern already proved that skill = orchestrator and helper = focused tool is the durable shape. This section codifies it so it does not regress.
