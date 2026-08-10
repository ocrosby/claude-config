---
description: Multi-source research — a parallel team of codebase, web, and GitHub researchers converges on a synthesized report, optionally published to a shared vault.
argument-hint: "[question, topic, or area to research]"
allowed-tools: Agent, Bash, Read, Write, Glob, Grep, WebSearch, WebFetch, AskUserQuestion
# Spawns a multi-agent research team and can push to an external vault repo — human-gated so a model never kicks off a multi-minute team run or an external commit on its own initiative.
disable-model-invocation: true
---

# /study — Multi-Source Research Team

Coordinate an agent team where parallel researchers investigate a question from different angles — codebase, web, and GitHub — then synthesize findings into a structured report.

**Why this works:** A single research pass tends to anchor on the first relevant result and miss important context. Parallel researchers covering different source types cast a wider net, cross-reference findings, and produce a more complete picture.

## Examples

```
/study what caching strategies does this service use?
/study how should we handle rate limiting for external API calls?
/study best practices for structured logging in Go
/study 42  (GitHub issue number — fetches the issue and derives the question)
/study how does authentication work end-to-end in this repo?
```

## Prerequisites

REQUIRED: Verify agent teams are enabled before spawning any teammates. If not enabled, show the user these instructions and STOP — do not proceed without agent teams:

> Agent teams are experimental. Enable them by adding to your settings.json:
> ```json
> { "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" } }
> ```

## When NOT to Use

- Questions answerable by reading one file — just read it.
- Simple code lookups (use Grep/Glob).
- Debugging (use `/debug`).

## Environment

- Branch: !`git branch --show-current 2>/dev/null || echo "(not a git repo)"`
- Repo root: !`git rev-parse --show-toplevel 2>/dev/null || echo "(not a git repo)"`
- Recent commits: !`git log --oneline -10 2>/dev/null || echo "(not a git repo)"`
- Vault: !`cat "$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.claude-vault" 2>/dev/null || echo "not-configured"`

## Pre-flight: Ensure vault is configured

- If **Vault is a real URL** (not `not-configured`), skip this section and proceed to Step 1.
- If **Vault is `not-configured`**, read `~/.claude/skills/study/vault-preflight.md` and follow the steps there. That file handles asking the user, creating `.claude-vault`, and pushing via direct commit or PR fallback. When it returns, proceed to Step 1.

## Step 1: Frame the Research Question

From `$ARGUMENTS`, establish the research context:

| Input | Action |
|-------|--------|
| Clear question or topic | Use directly |
| GitHub issue number | Fetch with `gh issue view <number>` and extract the research question |
| Vague or empty | Ask the user to clarify what they want to learn |

Refine the question into:
- **Primary question** — the specific thing to answer
- **Scope** — what's in and out of bounds (codebase-only? web-only? everything?)
- **Depth** — quick survey vs. deep dive
- **Output focus** — decision support, learning, comparison, or implementation guidance

Present the framing to the user and ask if they want to adjust before spawning researchers.

## Step 2: Spawn the Research Team

Create a team with **3 researchers** (one per source type) plus yourself as lead:

- **Researcher 1: Codebase Explorer** — finds relevant code, patterns, implementations, and architecture decisions
- **Researcher 2: Web Researcher** — finds documentation, articles, best practices, and community knowledge
- **Researcher 3: GitHub & Ecosystem Analyst** — finds relevant issues, PRs, discussions, and related projects

Read `~/.claude/skills/study/researcher-prompts.md` and use the verbatim prompt for each researcher, substituting `[primary question]` and `[scope and depth from Step 1]` before spawning that teammate.

When spawning teammates, use `model: sonnet` and `maxTurns: 30` in the Agent tool parameters.

Do NOT require plan approval — researchers should start exploring immediately.

## Step 3: Cross-Reference

As findings come in:
- Encourage researchers to react to each other's findings:
  ```
  [Researcher A] found [X] in the codebase. Does this align with what you're
  seeing in the docs/ecosystem? Any contradictions?
  ```
- If a researcher finishes early, redirect them to dig deeper on gaps identified by others
- If findings conflict, ask the relevant researchers to reconcile

## Step 4: Synthesize Report

After all researchers have reported, synthesize findings into a report.

Write `.claude/study/${CLAUDE_SESSION_ID}/report.md` using the report template in `~/.claude/skills/study/report-format.md` — fill the placeholders, lead the Summary with the answer, and include file:line / URLs / ecosystem links per source.

### 4a. Update the study index

After writing the report, append (or create) an entry in `.claude/study/INDEX.md`. This index is what future Claude sessions read to become aware of prior research in this repo — without it, every future prompt starts from scratch even if we've already researched the topic.

The index header (create `.claude/study/INDEX.md` with it if the file is missing) and the per-study entry (append at the top, below the `---`) are both templated in `~/.claude/skills/study/report-format.md`.

The `Topics:` line matters — future sessions will grep the index for keywords in the current question. Choose keywords a future substantive question is likely to contain (e.g. `caching`, `rate-limiting`, `authentication`, `error-handling`).

**Never overwrite existing entries** — always append at the top. The full history is the value; an index that only holds the latest run is nearly worthless.

Clean up the research team.

## Step 5: Publish to Shared Vault

Using the Vault value from the Environment section:

- If **Vault is `not-configured`**, skip this step silently and proceed to Step 6.
- If **Vault is a real URL**, ask the user:

  > Research complete. Publish this report to the shared vault at `<vault_url>`?

  If the user declines, skip to Step 6.

  If the user confirms, read `~/.claude/skills/study/vault-publish.md` and follow steps 5a through 5h in that file (clone → bootstrap check → derive metadata → write note → update MOC and index → commit and push). When it returns, proceed to Step 6.

## Step 6: Present Findings

Present the user with:

1. **Inline summary** — a concise (5-10 line) answer to their research question, highlighting the most important findings and recommendations
2. **Link to full report** — point them to `.claude/study/${CLAUDE_SESSION_ID}/report.md` for the complete analysis
3. **Vault link** — if the note was published in Step 5, tell the user the vault path: `research/<YYYY-MM>/<note_slug>.md`

Ask if they want to:
1. Dig deeper on any specific finding
2. Start a follow-up research question
3. Move to implementation based on findings

## Step 7: Capture Learnings (optional)

After the user makes their choice above, ask:

> Before ending this session, would you like to capture any lessons learned?
> This helps improve the workflow for future use.

If the user wants to capture lessons:

```bash
mkdir -p .claude/learnings/study/
```

Write a structured entry to `.claude/learnings/study/${CLAUDE_SESSION_ID}.md`:

```markdown
# Session Learning: study
**Date:** [today's date]
**Session:** ${CLAUDE_SESSION_ID}
**Workflow:** /study
**Outcome:** [the verdict or outcome from this session]

## What worked well
- [observation from user]

## What didn't work well
- [observation from user]

## Proposed skill improvement
- [specific, actionable suggestion]
```

If the user declines, end the session without writing anything.

## Step 8: Verify

Before the skill exits, confirm:

1. `.claude/study/${CLAUDE_SESSION_ID}/report.md` exists and is non-empty.
2. `.claude/study/INDEX.md` exists and contains this session's entry (grep for `${CLAUDE_SESSION_ID}`). **If missing: re-run Step 4a — without this, future sessions will not benefit from this research.**
3. If Step 5 published to a vault, the note is present at `research/<YYYY-MM>/<note_slug>.md` in the vault repo — either by checking the commit that landed or by re-cloning and reading the path. **If vault publish was attempted but no note is present: report the failure to the user and offer to retry.**
4. Step 6's inline summary was shown to the user (not just the file path).

If any check fails, report which one and what to do — do not exit silently.
