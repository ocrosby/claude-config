---
description: Authoritative conventions for authoring Claude skill files — frontmatter, progressive disclosure, structure, language, scope buckets, invocation control, and script extraction
paths:
  - "skills/*/SKILL.md"
---

# Skill File Conventions

Single source of truth for authoring a Claude skill. `skills/CLAUDE.md` intentionally points here and does not restate content — do not add authoring guidance to that file. A skill that violates the conventions below will drift, contradict other configuration, or fail to enforce the behavior it describes.

## Two mandates (apply to every skill)

### 1. Composable and focused

Each skill does **one** thing well. If the description needs the word "and", the skill is two skills wearing one hat — split it. A workflow that could be re-described as two independent jobs is two skills. Also enforced under **Design qualities → Composable** below.

### 2. Extract scripts over inline logic

Whenever a workflow step does parsing, scanning, validating, or transforming data, extract it into a script alongside `SKILL.md`. Inline code is allowed only when the logic is **under 20 lines** AND will not be regenerated across invocations. The canonical exemplar is `scripts/tally_invocations.py` — copy its shape (standard library only, argparse CLI, Markdown or JSON to stdout, exit 0/1). Detailed economics are under **Reusable scripts beat regenerated code** below.

---

## Progressive disclosure — the three levels

A skill is organized in three levels so only relevant content occupies the context window at any given time. When authoring, decide which level each piece of content belongs to. Misplaced content is expensive: reference material in Level 2 inflates every invocation; workflow steps in Level 3 are invisible to Claude until something happens to fetch them.

### Level 1 — Metadata (always loaded)

- **What:** the skill's name (from directory) and `description` (plus optional `when_to_use`) from frontmatter
- **When loaded:** at session start and after compaction, for every skill in the registry — present in context for the entire session
- **Token cost:** skill names are always present; descriptions share a budget of ~1% of the model's context window (configurable via `skillListingBudgetFraction`). Each entry's combined description + `when_to_use` is capped at 1,536 characters. When the budget overflows, descriptions for least-used skills are dropped first
- **What belongs here:** a single specific sentence that lets Claude decide whether the skill is relevant — and, if needed, `when_to_use` trigger phrases. Put the key use case first; long descriptions get truncated under budget pressure

### Level 2 — Instructions (loaded on invocation)

- **What:** the rendered body of `SKILL.md` — workflow, usage, exceptions, hard-stop conditions
- **When loaded:** when the skill is invoked, and persists in context for the remainder of the **session**, not just the task. Claude Code does not re-read the file on later turns
- **Token cost:** typically 500–3,000 tokens; paid on every invocation and held for the rest of the session. After auto-compaction, the most recent invocation of each skill is re-attached, capped at 5,000 tokens per skill and 25,000 tokens total across all re-attached skills
- **What belongs here:** numbered workflow steps, invocation syntax, exceptions with literal examples, agents the skill delegates to. Every padding sentence is paid for every invocation and every turn after — keep it tight (target under 500 lines)

### Level 3 — Resources (loaded on demand)

- **What:** supporting files alongside `SKILL.md` — templates, scripts, reference docs, fixture data, long examples
- **When loaded:** only when the workflow explicitly reads or executes them via Read/Bash
- **Token cost:** zero until referenced; can be arbitrarily large because the cost is opt-in
- **What belongs here:** anything voluminous, conditional, or reference-only — language-specific cheatsheets, prompt templates, helper scripts, sample fixtures. Link from Level 2; Claude reads only when the workflow requires

### Optimizing across levels

- If a sentence does not help Claude decide *whether* to invoke the skill, it does not belong in Level 1
- If a paragraph is reference material Claude consults rather than executes, move it to Level 3 and link from Level 2
- If content is procedural and runs every invocation, it belongs in Level 2
- The cheapest token is the one in Level 3 that never gets read

---

## Reusable scripts beat regenerated code

If a workflow needs the same Python (or shell, or other) logic on every invocation, save it once as a script in the skill folder and execute it via Bash. Regenerating logic in chat costs tokens twice — once to write it, once to read it back — and drifts between runs.

**Recognition signals — extract a script when any of these are true:**

- Multi-line shell pipeline with state, grouping, or conditionals (sed/awk/jq chains)
- The same parsing happens on every invocation (history files, git output, OpenAPI specs, frontmatter)
- The skill emits format-stable structured output (JSON or a fixed Markdown shape)
- Validation against a fixed ruleset (frontmatter checks, doc-review rules, deprecation patterns)
- Aggregation across many files (counting, classifying, summarizing)

**Conventions:**

- **Save it when:** any recognition signal applies, OR the logic exceeds ~20 lines
- **Where it lives:** `skills/<skill-name>/<verb_noun>.py` (or `.sh`, `.js`) alongside `SKILL.md` — a Level 3 resource
- **How the workflow invokes it:** Level 2 describes only the command (`python3 ~/.claude/skills/<skill-name>/extract_frontmatter.py <args>`); the implementation stays out of context
- **Token math:** a 200-line helper inlined in Level 2 costs ~1,500 tokens on every invocation. The same helper saved as a script costs zero tokens to invoke — only its output enters context
- **Naming:** scripts describe the action they perform (`validate_links.sh`, `extract_frontmatter.py`), not the skill they belong to
- **Inline allowed only when:** the logic is a single bash call (`git status`, `find . -name "*.go"`), a 3-line range derivation, or another genuinely one-off transformation that will not be regenerated on the next invocation. "Small enough to ignore" is not an exception — measure against the recognition signals above

**Exemplar:** `scripts/tally_invocations.py` — standard library only, argparse CLI, Markdown to stdout, exits 0/1. Copy its shape for new scripts.

Before writing inline code in a workflow step, ask: "Would I regenerate this on the next invocation?" If yes, save it as a script.

---

## Layout

- One folder per skill: `skills/<skill-name>/SKILL.md`
- The directory name **is** the invocation command — `skills/git/` automatically provides `/git`. There is no separate `triggers` field
- Supporting files (templates, scripts, reference docs) live alongside `SKILL.md` in the same folder

## Frontmatter

Every field is optional. Only `description` is recommended so Claude knows when to invoke the skill.

```yaml
---
description: <one sentence — specific, not generic; key use case first>
when_to_use: <optional trigger phrases or example requests>
aliases: <old-name>                  # prior names this skill was renamed from (comma-separated for multiple)
disable-model-invocation: true       # block Claude/sub-agents from auto-invoking
user-invocable: false                # hide from the / menu
allowed-tools: Bash(git *) Read Grep # pre-approve tools while the skill is active
argument-hint: "[issue-number]"      # autocomplete hint
arguments: [issue, branch]           # named positional args for $issue / $branch substitution
paths:                               # auto-load only when working on matching files
  - "**/*.go"
context: fork                        # run in an isolated subagent context
agent: Explore                       # which subagent type when context: fork
---
```

Reference (full field list): https://code.claude.com/docs/en/skills#frontmatter-reference

Notable fields beyond identity:

- **`allowed-tools`** — pre-approves the listed tools while the skill is active, suppressing per-use permission prompts. Does **not** restrict other tools; permission settings still apply. Use to make a skill feel native (e.g. a commit skill pre-approving `Bash(git add *)`, `Bash(git commit *)`)
- **`paths`** — glob patterns that limit when Claude auto-loads the skill. The skill remains user-invocable even if no paths match
- **`aliases`** — prior name(s) this skill was renamed from. Used by `/skill usage` to attribute historical invocations to the current canonical name. Single value or comma-separated. Example: `aliases: git-ship, ship` on the consolidated `git` skill means past `/git-ship` and `/ship` invocations count toward `/git` in usage reports
- **`context: fork`** + **`agent`** — runs the skill body as a prompt to a subagent (e.g. `Explore`, `Plan`, a custom agent). Use for read-heavy or context-isolated work that should not pollute the main session

**Never** add a `triggers:` field — it is not a real frontmatter field and will be silently ignored. The directory name already provides the slash command.

## Invocation control

By default both the user and Claude (including sub-agents) can invoke any skill. Two frontmatter fields restrict this, and they are **independent controls with different mechanisms** — they are not symmetric:

- **`disable-model-invocation: true`** — removes the skill's description from Claude's context, so Claude cannot auto-invoke it. The user can still type `/skill-name` to run it. Use this as a **human gate** on any skill whose side effects you do not want a model to take on its own initiative: deploys, releases, production migrations, sending external messages, charging money, granting access, force-pushes, anything that touches infrastructure outside the local repo, or anything that costs real money or is hard to reverse
- **`user-invocable: false`** — hides the skill from the `/` menu so the user is unlikely to invoke it manually. Claude can still invoke it programmatically based on the description. Use for background-knowledge skills that are not meaningful actions to type (e.g. `legacy-system-context` — Claude consults it when relevant, but `/legacy-system-context` is not a command users would run)

Effects per the official docs:

| Frontmatter                       | You can invoke | Claude can invoke | When loaded into context                                       |
|-----------------------------------|----------------|-------------------|---------------------------------------------------------------|
| (default)                         | Yes            | Yes               | Description always in context; body loads when invoked         |
| `disable-model-invocation: true`  | Yes            | No                | Description **not** in context; body loads when you invoke     |
| `user-invocable: false`           | No (hidden)    | Yes               | Description always in context; body loads when invoked         |

Note: `user-invocable` only controls menu visibility. To block programmatic invocation by Claude, use `disable-model-invocation: true`. Combining both leaves the skill reachable only through deliberate slash-command invocation by a user who already knows the name.

Leave both unset unless there is a concrete reason to restrict. When set, state the reason in a one-line comment above the field so a future reader does not relax the control by accident.

---

## Structure

1. `# Skill Name` heading
2. Opening line: `Use this skill when <specific trigger condition>.`
3. `## Usage` block with concrete invocation forms (only if the skill is user-invocable)
4. `## Workflow` with numbered steps (`### 1.`, `### 2.`, …); every step is a concrete action
5. Final workflow step is a verification step — confirm the output is correct before the skill exits
6. `## Exceptions` (only if real exceptions exist) — define each with a literal example, not a category name

## Language

- Mandatory only: **must**, **always**, **never**, **do not**, **required**
- No advisory phrasing: ~~should~~, ~~consider~~, ~~suggest~~, ~~prefer~~, ~~when appropriate~~
- Hard stops are explicit: `**If <condition>: stop and do not proceed.**`
- `consider` is allowed only inside an explicitly labeled optional/suggestion block

## Scope

- Every skill must have a "When to use" section (or an equivalent opening paragraph) that states what triggers it
- Every skill that has exceptions must define them with literal examples, not category names
- If the skill delegates to an agent, name the agent explicitly

## Scope buckets

Every skill must fit cleanly into exactly **one** of four scope buckets. A skill that straddles two or more confuses invocation — split it or trim its scope until it fits one.

- **Utility** — does one small reusable thing, every time
- **Verification** — checks final output quality against an objective bar
- **Data Enrichment** — pulls external data in
- **Orchestration** — chains other skills into a multi-step playbook

Orchestration that coordinates other skills is **not** straddling — a playbook is allowed to touch every bucket through the skills it calls, as long as it does not itself do their work inline.

A **Verification** skill must produce an objective output — a Pass/Fail or a grade out of 10, never a vague verdict ("looks good", "seems fine") — and check one of:

- **Correctness** — does the output run/compile/pass tests, match a schema or API contract, or satisfy a lint/style rule?
- **Fidelity** — are facts, config values, version numbers, and referenced docs real and accurate — not hallucinated flags, deprecated APIs, or wrong paths?
- **Quality** — does it meet a bar the user cares about (idiomatic code, consistent commit-message format, a PR body that explains the "why", docs that match the current CLI surface)?

---

## Design qualities

Every skill must be composable, portable, efficient, and powerful. Apply these checks before finalizing.

### Composable — does one thing, works with others

- Single, nameable purpose. If the description needs "and", split into two skills. The skill must fit cleanly into one of the four scope buckets above — straddling two is a signal to split
- Delegates to existing skills and agents instead of reimplementing their behavior — name them explicitly (e.g. `Use the skill-reviewer agent`, `Invoke /code review`)
- Outputs are usable by another skill or by the user without post-processing — structured findings, predictable file paths, predictable exit conditions
- No silent overlap with another skill. If two skills cover the same trigger, one must be removed or refactored

### Portable — works anywhere, depends on little

- No hardcoded absolute paths outside `~/.claude/`. Project paths are derived from the current working directory
- No assumption of language, framework, or OS unless the skill is explicitly language-scoped via a subcommand (e.g. `/feature go`, `/bench py`). Top-level dispatchers auto-detect the language from the working directory and route to specialist agents rather than embedding language logic
- Tools used are the standard set (Read, Edit, Write, Bash, Grep, Agent) or the agent-set the skill explicitly declares. No reliance on machine-specific binaries without a version check or install hint
- No assumption of unsaved conversation state — a skill must work on a fresh invocation with only the user's arguments

### Efficient — minimum context, minimum tool calls

- Workflow steps are concrete and unpadded. If a step exists only to restate the goal, delete it
- Parallel tool calls are used wherever steps are independent. Sequential calls appear only where one depends on another
- Expensive or wide-scope work (codebase search, multi-file analysis) is delegated to an Agent so the main context stays clean. Name the agent and the thoroughness level
- The skill does not re-read files it already has, and does not re-invoke an agent for information it already received

### Powerful — high leverage per invocation

- Encapsulates a multi-step workflow that a user would otherwise type out manually each time, or enforces conventions easy to forget
- Has a hard-stop condition that prevents a known failure mode (e.g. "If working tree is dirty: stop and do not proceed")
- Produces a verifiable outcome — a PR URL, a passing test run, a written report, a committed change. The final step confirms the outcome
- If the skill could be replaced by a single tool call, it must not exist as a skill

---

## Skills as orchestrators, commands as building blocks

**This is an intentional design decision — do not simplify it away.**

A skill orchestrates a workflow. A command performs one focused action. When the same concrete mechanic appears in two or more skills, it must be extracted so it lives in exactly one place.

### Mandatory behavior

- When 2+ skills share the same concrete mechanic (e.g. constructing a Conventional Commits message, opening a PR with `gh pr create`, creating a feature branch from `main`), extract that mechanic. Do not inline it twice
- The extracted unit must be either a **command** (`commands/<name>.md`) or a **script** (`scripts/<name>.py`). Choose by the rule below
- A skill that uses an extracted command must invoke it explicitly: `Invoke /<command-name>` as a numbered step. Do not paraphrase the command's contents — the skill names the command and trusts it
- The extracted command must remain user-invocable in isolation. If `/foo` only makes sense as a sub-step of `/bar`, it is not a real command — keep it inlined in `/bar`

### Command vs. script — choose by the mechanic's nature

| The mechanic is... | Extract to a... | Examples |
|---|---|---|
| Prompted reasoning — Claude composes text, decides a name, drafts a message, picks an approach | **Command** (`commands/*.md`) | Compose a Conventional Commits message from staged diff; write a PR body; decide a branch name from the change type |
| Deterministic logic — parsing, scanning, classification, file inspection that always returns the same answer for the same input | **Script** (`scripts/*.py`) | Group mixed-concern changes into per-type buckets; parse `CODEOWNERS` and `pyproject.toml`; tally invocations from session history |

Existing examples to follow: `scripts/migrate_scan.py` (called by `/code migrate`), `scripts/analyze_history.py` (called by `/skill gaps`), `scripts/tally_invocations.py` (called by `/skill usage`). Skill orchestrates → script returns structured data → skill acts on the result.

### When extraction is NOT required

- The mechanic appears in exactly one skill and has no obvious second consumer. Inline it
- The "shared" surface is just a one-line shell command (`git fetch origin main`). Inlining is clearer than referencing
- The mechanic is a single sentence of prose that two skills phrase the same way. That's not shared mechanics — that's coincidence

### Why this exists

Without this convention, skills grow to 200+ lines, the same git pipeline appears in three places, and any change has to be made N times. The `migrate` / `skill-gaps` / `skill-usage` pattern already proved that skill = orchestrator and helper = focused tool is the durable shape. This section codifies it so it does not regress.

---

## Conflict check

- Before finalizing a skill, verify it does not duplicate what an existing rule already enforces
- If a rule covers the same ground, the skill must reference the rule rather than repeat it
- Contradictions between a skill and a rule create cycles — one will be ignored; resolve before committing

## Before committing a new skill

- Run `grep -rl "<topic>" ~/.claude/rules/` to confirm no existing rule already covers the behavior — if one does, reference it rather than repeat it
- Run `ls ~/.claude/skills/` and `grep -h "^description:" ~/.claude/skills/*/SKILL.md` to confirm no existing skill already covers the purpose
- Invoke the `skill-reviewer` agent on the finished file and address all **Must Fix** and **Should Fix** findings per `rules/findings-format.md`; **Consider** items are optional

## Do not

- Duplicate a rule's content in a skill — reference the rule
- Use advisory language in workflow steps
- Use a `triggers:` field — it is not a real frontmatter field; the directory name already provides `/skill-name`
- Write exceptions as category names ("mechanical changes") instead of literal examples ("renaming an identifier, moving a file")
- Confuse `disable-model-invocation` (blocks Claude) with `user-invocable` (hides from menu) — they restrict different parties
