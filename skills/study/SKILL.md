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

Using the Vault and Repo root values from the Environment section above.

If Vault is **not** `not-configured`, skip this section entirely and proceed to Step 1.

If Vault is `not-configured`, ask the user:

> No shared vault is configured for this repo (`.claude-vault` not found). Do you want to
> publish this report to a shared Obsidian vault repo? If yes, give me the git URL to use
> (new or existing) — I'll remember it in `.claude-vault` for next time.

**If the user declines or has no vault to use:** skip vault publishing for this session
and go directly to Step 1 — Step 4's local report is unaffected either way.

**If the user provides a URL:** continue to PF1.

### PF1 — Create `.claude-vault`

Write the vault URL the user provided to `<repo_root>/.claude-vault`.

### PF2 — Check whether the file would be gitignored

```bash
git -C "$repo_root" check-ignore -q .claude-vault 2>/dev/null && echo "ignored" || echo "tracked"
```

- If the output is `ignored`: the project has intentionally excluded `.claude-vault` from version
  control. Use the file silently for this session — do not attempt to commit it. Skip to Step 1.
- If the output is `tracked`: continue to PF3.

### PF3 — Attempt to commit and push on the current branch

```bash
cd "$repo_root"
git add .claude-vault
git commit -m "chore: add .claude-vault for study skill vault integration"
git push 2>&1
```

- If the push succeeds: inform the user quietly:
  > `.claude-vault` was missing — created and pushed to `<branch>`.

  Then skip to Step 1.

- If the push fails (non-zero exit, or output contains `rejected` / `protected` / `permission`):
  proceed to PF4.

### PF4 — PR fallback

The direct push failed. Reset the commit and create a dedicated branch + PR instead:

```bash
cd "$repo_root"
git reset HEAD~1                        # undo the commit, keep the file staged
git stash                               # stash .claude-vault changes
git fetch origin main
git checkout -b chore/add-claude-vault origin/main
git stash pop
git add .claude-vault
git commit -m "chore: add .claude-vault for study skill vault integration"
git push -u origin chore/add-claude-vault 2>&1
```

Then open a PR:

```bash
gh pr create \
  --title "chore: add .claude-vault for study skill vault integration" \
  --body "$(cat <<'EOF'
## Summary

- Adds `.claude-vault` pointing at the shared research vault so the `/study` skill can publish findings to the team Obsidian vault.

## Why

The `/study` skill pre-flight detected that `.claude-vault` was missing. This PR adds it so future sessions can publish directly without prompting.

## Vault

`<vault_url>`
EOF
)" \
  --base main 2>&1
```

Inform the user:
> Could not push `.claude-vault` directly to `<branch>`. Opened a PR instead: `<pr_url>`
>
> Proceeding with vault publishing for this session using the local file.

Then continue to Step 1 — the local `.claude-vault` file is present and will be picked up
by Step 5 even if the PR has not yet merged.

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

Create a team with **3 researchers** (one per source type) plus yourself as lead.

### Researcher 1: Codebase Explorer

```
You are researching a question by exploring the local codebase. Your job is to find relevant code, patterns, implementations, and architecture decisions.

RESEARCH QUESTION: [primary question]

SCOPE: [scope and depth from Step 1]

Your job:
1. Search the codebase thoroughly:
   - Find files, modules, and functions relevant to the question
   - Read implementations to understand how things currently work
   - Look for patterns, conventions, and architectural decisions
   - Check tests for behavioral documentation
   - Look at git history for context on why things are the way they are

2. Document your findings:
   - Reference specific files and line numbers
   - Note patterns and conventions you observe
   - Identify gaps — what's missing or unclear from code alone
   - Flag anything that contradicts other researchers' findings

3. Report your findings:
   - RELEVANT CODE: Key files and what they reveal (with file:line references)
   - PATTERNS: Conventions and architectural decisions observed
   - GAPS: What the codebase doesn't answer about the research question
   - KEY INSIGHT: The most important thing you learned

When done, send your findings to the lead and the other researchers.
```

### Researcher 2: Web Researcher

```
You are researching a question using web sources. Your job is to find documentation, articles, best practices, and community knowledge.

RESEARCH QUESTION: [primary question]

SCOPE: [scope and depth from Step 1]

Your job:
1. Search the web strategically:
   - Official documentation for relevant technologies
   - Technical blog posts and articles
   - Stack Overflow and similar Q&A sites
   - Best practice guides and design pattern references
   - Fetch and read pages that look highly relevant

2. Evaluate sources critically:
   - Prefer official docs and well-known authors
   - Note when sources disagree
   - Check dates — flag outdated information
   - Distinguish opinions from established practices

3. Report your findings:
   - KEY SOURCES: Most relevant URLs with what each covers
   - BEST PRACTICES: Established patterns and recommendations
   - TRADE-OFFS: Where the community disagrees or where context matters
   - KEY INSIGHT: The most important thing you learned

When done, send your findings to the lead and the other researchers.
```

### Researcher 3: GitHub & Ecosystem Analyst

```
You are researching a question by analyzing GitHub activity and the broader ecosystem. Your job is to find relevant issues, PRs, discussions, and related projects.

RESEARCH QUESTION: [primary question]

SCOPE: [scope and depth from Step 1]

Your job:
1. Search GitHub and the ecosystem:
   - Search this repo's issues and PRs for related discussions: `gh search issues`, `gh search prs`
   - Check if related issues exist in upstream/dependency repos
   - Look for similar implementations in other projects: `gh search repos`, `gh search code`
   - Check release notes and changelogs for relevant changes

2. Analyze what you find:
   - What have others tried? What worked, what didn't?
   - Are there open issues or known limitations?
   - What approaches do similar projects take?
   - Is there an emerging consensus or active debate?

3. Report your findings:
   - RELATED ISSUES/PRs: Relevant discussions with links and summaries
   - ECOSYSTEM: How other projects handle this (with repo references)
   - KNOWN ISSUES: Gotchas, limitations, or unresolved problems
   - KEY INSIGHT: The most important thing you learned

When done, send your findings to the lead and the other researchers.
```

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

Write `.claude/study/${CLAUDE_SESSION_ID}/report.md`:

```markdown
# Research: [topic/question]

**Date:** [today's date]
**Question:** [the primary research question]

## Summary

[2-3 paragraph executive summary answering the research question. Lead with the answer, then supporting context.]

## Findings by Source

### Codebase
[What the local code reveals — patterns, implementations, architecture decisions. Include file:line references.]

### Web & Documentation
[What external sources say — best practices, official guidance, community consensus. Include URLs.]

### GitHub & Ecosystem
[What the broader ecosystem shows — related projects, issues, community approaches. Include links.]

## Cross-References

[Where findings from different sources align or conflict. This is often where the most valuable insights emerge.]

## Recommendations

[Actionable conclusions based on the synthesized findings. Numbered list, most important first.]

## Open Questions

[What remains unclear or needs further investigation.]

## Sources

[Numbered list of all referenced URLs, repos, files, and issues.]
```

Clean up the research team.

## Step 5: Publish to Shared Vault

Using the Vault value from the Environment section above:

- If it is `not-configured`, skip this step silently and proceed to Step 6.
- If a vault URL is present, ask the user:

  > Research complete. Publish this report to the shared vault at `<vault_url>`?

  If the user declines, skip to Step 6.

### 5a — Clone the vault

```bash
vault_dir=$(mktemp -d)
git clone --depth 1 "$vault_url" "$vault_dir" 2>&1
```

If the clone fails, warn the user:
> Could not clone vault at `<vault_url>`. Continuing without publishing.
> Check VPN access and repository permissions.

Then skip to Step 6.

### 5b — Bootstrap check

Check whether `$vault_dir/_vault-index.md` exists.

If it is **missing**, the vault has not been initialized. Offer to bootstrap it:

> The vault repository exists but has not been initialized.
> Would you like me to set it up now? This will create the `Home.md`, `_vault-index.md`,
> `maps/`, and `research/` structure and push an initial commit.

If the user confirms, read `vault-init.md` from this skill's directory and follow
steps B2 through B4 in that file. Then continue from 5c.

If the user declines, warn:
> Skipping vault publishing — run `/study` again after initializing the vault.

Then skip to Step 6.

### 5c — Read the vault index

Read `$vault_dir/_vault-index.md`. Use it to:
- Identify existing topic clusters by their `## <cluster>` headings.
- Find specific prior notes that are closely related to this research question (for wikilinks).
- Determine which MOC to update (`maps/<cluster>.md`), or that a new MOC must be created.

### 5d — Derive metadata

From the research question and synthesized findings, determine:

| Field | Rule |
|-------|------|
| `topic_cluster` | kebab-case; match an existing index cluster if one fits; otherwise a new short name |
| `note_slug` | kebab-case summary of the research question (e.g. `token-bucket-vs-leaky-bucket`) |
| `tags` | 3–5 lowercase terms relevant to the topic |
| `related_notes` | up to 5 wikilinks to prior notes from the index with the highest topical overlap |

### 5e — Write the vault note

Write to `$vault_dir/research/$(date +%Y-%m)/<note_slug>.md`:

```markdown
---
date: <YYYY-MM-DD>
question: "<primary research question verbatim>"
tags: [<tag1>, <tag2>, ...]
maps: [[maps/<topic_cluster>]]
source-repo: <git remote URL of originating repo>
branch: <current branch>
session: <CLAUDE_SESSION_ID>
---

# <note title>

> **Question:** <primary research question>

## Summary

<2–3 paragraph executive summary from the synthesis — lead with the answer>

## Key Findings

### Codebase
<3–5 bullet points with file:line references>

### External Sources
<3–5 bullet points with URLs>

### Ecosystem
<3–5 bullet points with repo/issue links>

## Recommendations

<numbered list — top 3–5 actionable conclusions>

## Related Notes

<one [[wikilink]] per entry in related_notes, one per line>

## Open Questions

<bullet list from the research report>

## Sources

<numbered list of all URLs and file references>
```

### 5f — Update or create the MOC

**If `maps/<topic_cluster>.md` does not exist**, create it:

```markdown
# <Topic Cluster — title cased>

Research notes about <topic_cluster>.

## Notes

- [[research/<YYYY-MM>/<note_slug>]] — <one-line summary>
```

Then append a link inside the `<!--MAPS-START-->` / `<!--MAPS-END-->` block in `Home.md`:

```
- [[maps/<topic_cluster>]] — <one-line topic description>
```

**If the MOC already exists**, append to its `## Notes` section:

```
- [[research/<YYYY-MM>/<note_slug>]] — <one-line summary>
```

### 5g — Update `_vault-index.md`

If a `## <topic_cluster>` section already exists in the index, append to it:

```
- `research/<YYYY-MM>/<note_slug>.md` | <note title> | tags: <tag1>, <tag2>, ...
```

If no section exists for this cluster, add one:

```markdown

## <topic_cluster>
- `research/<YYYY-MM>/<note_slug>.md` | <note title> | tags: <tag1>, <tag2>, ...
```

Update the `<!-- Last updated: ... -->` comment at the top to today's date.

### 5h — Commit and push

```bash
cd "$vault_dir"
git add -A
git commit -m "research(<topic_cluster>): <note_slug> [<source_repo_name>]"
git push
rm -rf "$vault_dir"
```

If the push fails (concurrent update from another session), warn the user:
> Vault push failed — a concurrent update may have occurred. The local report is still
> at `.claude/study/<session>/report.md`. Re-run `/study` to retry publishing.

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
