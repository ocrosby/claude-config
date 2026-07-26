# /study — vault publish (Level 3 resource)

Read this file **only when** the Vault value from `SKILL.md` Environment is a real URL (not `not-configured`) AND the user confirmed publishing at the end of synthesis. Publishes the research note to the shared Obsidian vault.

## When to read

Loaded on demand by Step 5 of `SKILL.md`. If Vault is `not-configured` or the user declined, skip this file entirely and jump to Step 6.

## Steps

### 5a — Clone the vault

```bash
vault_dir=$(mktemp -d)
git clone --depth 1 "$vault_url" "$vault_dir" 2>&1
```

If the clone fails, warn the user:
> Could not clone vault at `<vault_url>`. Continuing without publishing.
> Check VPN access and repository permissions.

Then skip to Step 6 in `SKILL.md`.

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

Then skip to Step 6 in `SKILL.md`.

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
