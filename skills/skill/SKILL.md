---
description: Use when creating a new skill (author), finding recurring tasks that no existing skill covers (gaps), or reporting skill invocation counts and retirement candidates (usage). Invoke as /skill <author|gaps|usage>. For per-SKILL.md structural quality, use /audit skill.
argument-hint: "<subcommand> [arguments]"
aliases: skill-author, skill-audit, skill-gaps, skill-usage
---

# Skill: Skill-System Maintenance Dispatcher

Use this skill to manage the skill catalog itself: create new skills, find gaps where repeated tasks lack skill coverage, or report invocation counts and retirement candidates.

For per-SKILL.md structural quality, use `/audit skill` — it runs `skill-reviewer` on each file. For a system-wide audit of how all components (hooks, rules, agents, skills, settings) integrate, use `/audit system`.

## Usage

```
/skill                              # show this help
/skill author [skill-name]          # create skills/<name>/SKILL.md interactively
/skill gaps [--since 30d|90d]       # find repeating tasks with no skill coverage
/skill usage [--since 30d|90d]      # invocation counts and retirement recommendations
```

If you typed `/skill audit`, use `/audit skill` instead — the per-skill structural audit moved to the `/audit` dispatcher to co-locate the three audit surfaces (`system`, `repo`, `skill`).

## Workflow

### 1. Parse the subcommand

Split `$ARGUMENTS` on the first space. The first word is the subcommand.

- Empty or `help` → print **Usage** and stop.
- `audit` → print: "`/skill audit` moved to `/audit skill`. Re-run as `/audit skill [name]`." Then stop.
- Not one of `author`, `gaps`, `usage` → print **Usage** and stop.
- Dispatch.

### 2. Dispatch — `author`

Guides creation of a new skill with frontmatter, workflow, language audit, conflict check, and review.

1. **Define purpose and scope.**
   - What does this skill do? One sentence, specific enough to distinguish from existing skills.
   - What triggers it? A user command (`/name`), a file pattern (`**/*.go`), or both?
   - What does it NOT do? Identify the boundary so it doesn't expand into adjacent skills.
   - Does anything like this already exist? Run `grep -rl "<keyword>" ~/.claude/skills/` and check.

   **If an existing skill already covers this purpose: stop and recommend extending the existing skill instead.**

2. **Check for rule conflicts.**
   ```bash
   grep -rl "<topic>" ~/.claude/rules/
   ```
   If a rule already enforces the behavior, the skill must reference the rule, not repeat it. Repeating creates drift.

3. **Write the frontmatter.** Read `~/.claude/skills/CLAUDE.md` (Frontmatter section) before adding any field. That file is authoritative — do not duplicate the field reference here. Only `description` is recommended for Claude to know when to invoke the skill.

4. **Write the title and scope section.**
   ```markdown
   # Skill Name

   Use this skill when <specific trigger condition>.

   ## When NOT to use
   - <exclusion 1 with literal example>
   - <exclusion 2 with literal example>
   ```
   Omit "When NOT to use" if there are no meaningful exclusions.

5. **Write the workflow.** Number every step. Each step must describe a concrete action, not a general principle.
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

   Requirements: every blocking condition says "**stop and do not proceed**" (not "pause"); every step that produces output specifies what the output looks like; the final step is a verification step; agents the skill delegates to are named explicitly.

6. **Write exceptions (if any)** with literal examples, not category names.

   Never write: "except for mechanical changes". Always write: "except for renaming an identifier, moving a file, or updating an import path with no logic change".

7. **Audit the language.** Apply the advisory-vs-mandatory filter defined in `~/.claude/skills/CLAUDE.md` (Language section). Rewrite every advisory phrase as a mandatory directive, or move it to an explicit "optional" callout. Do not duplicate the filter table here — `skills/CLAUDE.md` is authoritative and any divergence is drift.

8. **Review with the skill-reviewer agent.** Invoke `skill-reviewer` on the finished file. **If any Must Fix or Should Fix finding is reported: stop and do not proceed.** Resolve all Must Fix and Should Fix findings, then re-run `skill-reviewer` to confirm they are cleared. Consider-level findings are optional. See `rules/findings-format.md`.

9. **Commit.**
   ```bash
   git add skills/<skill-name>/SKILL.md
   git commit -m "feat(claude): add /<skill-name> skill — <one-line description>"
   git push
   ```

**Rules for `author`.** Never create a skill that duplicates an existing rule — reference the rule instead. Never use advisory language in workflow steps. Every exception must have a literal example. Always run the `skill-reviewer` agent before committing.

### 3. Dispatch — `gaps`

Scans `~/.claude/history.jsonl` for repeating tasks that no existing skill covers.

1. **Tally history.**
   ```bash
   python3 ~/.claude/scripts/analyze_history.py [--since 30d] [--min-count N]
   ```
   The script emits two Markdown sections:
   - *Top slash-command invocations* — which skills are getting used (signal that they exist and work).
   - *Repeating natural-language phrases* — phrases typed N+ times with no `/command` prefix; candidates for unmet gaps.

2. **List existing skills.**
   ```bash
   ls ~/.claude/skills/
   ```

3. **Identify gaps.** For each pattern that appears ≥5 times in the natural-language section, check the existing catalog. A pattern is a **gap** if: no skill description matches the intent, the user is typing freeform what a skill could automate, and each occurrence could have been completed by a numbered workflow (not a one-off conversational question or an ad-hoc research query).

   Skip patterns that are: conversational (`thanks`, `ok`, `continue`), already covered by an existing skill (just rare invocation), or personal/contextual (not portable to a skill).

4. **Report.** Present a ranked table:
   ```
   | Suggested Skill | Count | Example phrase | Gap reason |
   |---|---|---|---|
   | ... | ... | ... | ... |
   ```
   Order by frequency descending. For each gap, propose a skill name and one-line description. Also include top slash commands by frequency — these confirm which skills are getting used.

5. **Verify** the output includes: the history-scanned count and in-window count; both sections (slash commands AND natural-language phrases); a ranked gap table OR a `_No gaps identified_` line.

   **If any of those are missing, the script failed silently — re-run with the same arguments and inspect stderr.**

### 4. Dispatch — `usage`

Invocation counts and retirement recommendations.

1. **Confirm inputs exist.**
   ```bash
   test -f ~/.claude/history.jsonl
   test -d ~/.claude/skills
   ```
   **If either is missing: stop and report which input is absent.** Do not attempt the report from partial data.

2. **Run the tally script** with the user's `--since` argument (or no argument for all-time):
   ```bash
   python3 ~/.claude/scripts/tally_invocations.py [--since 30d]
   ```
   The script parses every record in `~/.claude/history.jsonl`, extracts the leading `/<command>` from each prompt, restricts matches to commands that map to directories under `~/.claude/skills/`, resolves renamed skills via the `aliases:` frontmatter field (historical invocations under a previous name count toward the canonical name), tallies counts per skill, reads each SKILL.md to detect `disable-model-invocation: true` (zero usage there is a stronger retirement signal), and uses git first-add time as "age in catalog" (file mtime as fallback) so newly-added skills with zero counts are held rather than retired. Produces a ranked retirement recommendation as the final section.

3. **Present the report** in this exact shape:

   ```
   ## Skill usage (last 90 days)

   History records scanned: <N>
   Skill invocations matched: <M>
   Skills in catalog: <K>

   ### Heavily used (>=10)
   - /code-review  45
   - /git-ship     32

   ### Moderately used (3-9)
   - /architect     7

   ### Lightly used (1-2)
   - /here-now      1

   ### Zero invocations
   - /skill-author      [added 92d ago]
   - /rest-spec         [added 5d ago, new]
   - /update-config     [added 180d ago, user-invocable only]

   ### Retire (recommended)

   These skills have zero invocations, have existed for ≥30 days, and are not new additions. Ordered by strongest signal first (longest unused).

   1. /update-config   — 180d in catalog, user-invocable only, never invoked
   2. /skill-author    — 92d in catalog, never invoked

   ### Consider retiring

   Low usage (1–2 invocations all-time) — keep if intentional, drop if accidental:

   - /here-now  (1 invocation)
   ```

   Pass the script output through verbatim. Do not re-summarize the histogram or the recommendation rationale.

4. **Interpret the recommendations.** Note these caveats before the user acts:
   - A skill loaded automatically via `paths:` (e.g. a language rule firing on `.go` files) may not produce `/command` invocations even if it fires every session — check the skill's frontmatter for `paths:` before retiring.
   - A skill marked `disable-model-invocation: true` only runs on explicit user input — zero usage there is the highest-confidence retirement signal.
   - A skill modified in the last 30 days is excluded from "Retire" because mtime change suggests active maintenance.

5. **Verify the report** contains: a scanned-records count and matched-invocations count; a `### Zero invocations` section; a `### Retire (recommended)` section (with literal text `None.` if empty).

   **If any of those sections are absent, the script failed silently — re-run with the same arguments and inspect stderr.**

### 5. Final verification step

Each dispatch above ends with its own verification gate. Confirm the gate fired before exiting.

## Rules (apply across all subcommands)

- For per-skill structural quality, use `/audit skill` (delegates to `skill-reviewer`).
- For the broader inter-component audit (hooks, rules, agents, skills, settings together), use `/audit system`.
- `gaps` reads `~/.claude/history.jsonl`; `usage` reads it too — both are read-only on history.
- `author` always ends in a `skill-reviewer` pass before commit. Do not skip.
