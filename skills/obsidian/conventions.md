# Obsidian Vault: Note Conventions

Level-3 resource for the `obsidian` skill. Read before creating or editing a note.

## Filenames

- **Daily notes**: `Daily/YYYY-MM-DD.md` (e.g. `Daily/2026-06-03.md`)
- **All other notes**: `snake_case.md` — matching the existing pattern (`project_planning.md`, `llm_assisted_project_development_framework.md`). Do not introduce Title Case, kebab-case, or date prefixes; the rest of the vault is consistent snake_case.

## Wikilinks

The vault uses **Obsidian wikilinks**, and the observed style is **path-style relative** — not the shortest-form most Obsidian docs show:

```markdown
[[../readme]]
[[../prompt_engineering/readme]]
[[readme]]
```

**Preserve the style as written.** If the user wrote `[[../readme]]`, don't "normalize" it to `[[readme]]`. If creating a new cross-reference and unsure, use the relative-path form already present nearby — it's the dominant convention here.

Standard markdown links (`[text](path.md)`) are not used — use wikilinks.

## Frontmatter

Most existing notes have **no YAML frontmatter**. Behavior:

- **When editing**: preserve what's there. Don't add frontmatter to a note that doesn't have it.
- **When creating a new note** via this skill: add a minimal block only if a template calls for it (see `~/.claude/skills/obsidian/templates.md`). Otherwise leave the file frontmatter-free to match the surrounding vault.
- **When creating a Daily note**: include the canonical daily frontmatter (`date`, `tags: [daily-notes]`) — see `~/.claude/skills/obsidian/daily-notes.md`.
