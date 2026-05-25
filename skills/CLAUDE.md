# Skill Authoring Conventions

This directory holds Claude skills. Each skill lives in its own folder as `<skill-name>/SKILL.md`. When creating or editing a skill, the full conventions live in `rules/skill-conventions.md` and the guided workflow lives in the `/skill author` subcommand — use those as the source of truth. The summary below is a fast reference.

## Design preferences

Two mandates apply to every skill — read these before authoring.

### 1. Skills must be composable and focused

Each skill does **one** thing well. If the description needs the word "and", the skill is two skills wearing one hat — split it. A workflow that could be re-described as two independent jobs is two skills.

This is also enforced under "Design qualities → Composable" further down; it lives at the top of this file because it shapes every other authoring decision.

### 2. Prefer extracted scripts over inline logic

Whenever a workflow step does parsing, scanning, validating, or transforming data, extract it into a script alongside `SKILL.md`. Inline code is allowed only when the logic is **under 20 lines** AND will not be regenerated across invocations.

The canonical exemplar is `scripts/tally_invocations.py` — copy its shape (standard library only, argparse CLI, Markdown or JSON to stdout, exit 0/1). The detailed economics live under "Reusable scripts beat regenerated code" below.

---

## Progressive disclosure: the three levels

A skill is organized in three levels so that only relevant content occupies the context window at any given time. When authoring, decide which level each piece of content belongs to. Misplaced content is expensive: reference material in Level 2 inflates every invocation; workflow steps in Level 3 are invisible to Claude until something happens to fetch them.

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
- **What belongs here:** anything voluminous, conditional, or reference-only — language-specific cheatsheets, prompt templates, helper scripts, sample fixtures. Link from Level 2; Claude reads only when the workflow requires.

### Optimizing across levels

- If a sentence does not help Claude decide *whether* to invoke the skill, it does not belong in Level 1
- If a paragraph is reference material Claude consults rather than executes, move it to Level 3 and link from Level 2
- If content is procedural and runs every invocation, it belongs in Level 2
- The cheapest token is the one in Level 3 that never gets read

### Reusable scripts beat regenerated code

If a workflow needs the same Python (or shell, or other) logic on every invocation, save it once as a script in the skill folder and execute it via Bash. Regenerating logic in chat costs tokens twice — once to write it, once to read it back — and drifts between runs.

**Recognition signals** — extract a script when any of these are true:

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
- **Inline allowed only when:** the logic is a single bash call (`git status`, `find . -name "*.go"`), a 3-line range derivation, or another genuinely one-off transformation that will not be regenerated on the next invocation. "Small enough to ignore" is not an exception — measure against the recognition signals above.

**Exemplar:** `scripts/tally_invocations.py` — standard library only, argparse CLI, Markdown to stdout, exits 0/1. Copy its shape for new scripts.

When authoring a skill, before writing inline code in a workflow step, ask: "Would I regenerate this on the next invocation?" If yes, save it as a script.

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

## Invocation control

By default both the user and Claude (including sub-agents) can invoke any skill. Two frontmatter fields restrict this, and they are **independent controls with different mechanisms** — they are not symmetric:

- **`disable-model-invocation: true`** — removes the skill's description from Claude's context, so Claude cannot auto-invoke it. The user can still type `/skill-name` to run it. Use this as a **human gate** on any skill whose side effects you do not want a model to take on its own initiative: deploys, releases, production migrations, sending external messages, charging money, granting access, force-pushes, anything that touches infrastructure outside the local repo, or anything that costs real money or is hard to reverse.
- **`user-invocable: false`** — hides the skill from the `/` menu so the user is unlikely to invoke it manually. Claude can still invoke it programmatically based on the description. Use for background-knowledge skills that are not meaningful actions to type (e.g. `legacy-system-context` — Claude consults it when relevant, but `/legacy-system-context` is not a command users would run).

Effects per the official docs:

| Frontmatter                       | You can invoke | Claude can invoke | When loaded into context                                       |
|-----------------------------------|----------------|-------------------|---------------------------------------------------------------|
| (default)                         | Yes            | Yes               | Description always in context; body loads when invoked         |
| `disable-model-invocation: true`  | Yes            | No                | Description **not** in context; body loads when you invoke     |
| `user-invocable: false`           | No (hidden)    | Yes               | Description always in context; body loads when invoked         |

Note: `user-invocable` only controls menu visibility. To block programmatic invocation by Claude, use `disable-model-invocation: true`. Combining both leaves the skill reachable only through deliberate slash-command invocation by a user who already knows the name.

Leave both unset unless there is a concrete reason to restrict. When set, state the reason in a one-line comment above the field so a future reader does not relax the control by accident.

## Structure

1. `# Skill Name` heading
2. Opening line: `Use this skill when <specific trigger condition>.`
3. `## Usage` block with concrete invocation forms (only if the skill is user-invocable)
4. `## Workflow` with numbered steps (`### 1.`, `### 2.`, …); every step is a concrete action
5. Final workflow step is a verification step
6. `## Exceptions` (only if real exceptions exist) — define each with a literal example, not a category name

## Language

- Mandatory only: **must**, **always**, **never**, **do not**, **required**
- No advisory phrasing: ~~should~~, ~~consider~~, ~~suggest~~, ~~prefer~~, ~~when appropriate~~
- Hard stops are explicit: `**If <condition>: stop and do not proceed.**`
- `consider` is allowed only inside an explicitly labeled optional/suggestion block

## Design qualities

Every skill must be composable, portable, efficient, and powerful. Apply these checks before finalizing.

### Composable — does one thing, works with others

- Single, nameable purpose. If the description needs "and", split into two skills.
- Delegates to existing skills and agents instead of reimplementing their behavior — name them explicitly (e.g. `Use the skill-reviewer agent`, `Invoke /code review`).
- Outputs are usable by another skill or by the user without post-processing — structured findings, predictable file paths, predictable exit conditions.
- No silent overlap with another skill. If two skills cover the same trigger, one must be removed or refactored.

### Portable — works anywhere, depends on little

- No hardcoded absolute paths outside `~/.claude/`. Project paths are derived from the current working directory.
- No assumption of language, framework, or OS unless the skill is explicitly language-scoped (e.g. `go-bench`). Language-agnostic skills route to specialists rather than embedding language logic.
- Tools used are the standard set (Read, Edit, Write, Bash, Grep, Agent) or the agent-set the skill explicitly declares. No reliance on machine-specific binaries without a version check or install hint.
- No assumption of unsaved conversation state — a skill must work on a fresh invocation with only the user's arguments.

### Efficient — minimum context, minimum tool calls

- Workflow steps are concrete and unpadded. If a step exists only to restate the goal, delete it.
- Parallel tool calls are used wherever steps are independent. Sequential calls appear only where one depends on another.
- Expensive or wide-scope work (codebase search, multi-file analysis) is delegated to an Agent so the main context stays clean. Name the agent and the thoroughness level.
- The skill does not re-read files it already has, and does not re-invoke an agent for information it already received.

### Powerful — high leverage per invocation

- Encapsulates a multi-step workflow that a user would otherwise type out manually each time, or enforces conventions easy to forget.
- Has a hard-stop condition that prevents a known failure mode (e.g. "If working tree is dirty: stop and do not proceed").
- Produces a verifiable outcome — a PR URL, a passing test run, a written report, a committed change. The final step confirms the outcome.
- If the skill could be replaced by a single tool call, it must not exist as a skill.

## Before committing a new skill

- Run `grep -rl "<topic>" ~/.claude/rules/` to confirm no existing rule already covers the behavior — if one does, reference it rather than repeat it
- Run `ls ~/.claude/skills/` and `grep -h "^description:" ~/.claude/skills/*/SKILL.md` to confirm no existing skill already covers the purpose
- Invoke the `skill-reviewer` agent on the finished file and address all Critical and Warning findings

## Do not

- Duplicate a rule's content in a skill — reference the rule
- Use advisory language in workflow steps
- Use a `triggers:` field — it is not a real frontmatter field; the directory name already provides `/skill-name`
- Write exceptions as category names ("mechanical changes") instead of literal examples ("renaming an identifier, moving a file")
- Confuse `disable-model-invocation` (blocks Claude) with `user-invocable` (hides from menu) — they restrict different parties
