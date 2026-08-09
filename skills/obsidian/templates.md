# Obsidian Vault: Templates

Level-3 resource for the `obsidian` skill. `Templates/` is empty for now; the note-creation logic checks for `Templates/<type>.md` and falls back to the minimal frontmatter in `SKILL.md` if missing. When you're ready to adopt reusable note formats, create the files below — this skill will start using them automatically.

## How to add templates

1. **Create the template files** under `Templates/` using `{{date}}` and `{{title}}` placeholders. Suggested starters:

   ```markdown
   # Templates/daily.md
   ---
   id: {{date}}
   date: {{date}}
   tags: [daily-notes]
   ---

   # {{date}}

   ## What I worked on

   ## Notes

   ## Tomorrow
   ```

   ```markdown
   # Templates/meeting.md
   ---
   id: {{date}}-{{title}}
   date: {{date}}
   tags: [meeting]
   attendees: []
   ---

   # {{title}} — {{date}}

   ## Agenda

   ## Notes

   ## Action items
   ```

   ```markdown
   # Templates/project.md
   ---
   id: {{title}}
   status: active
   tags: [project]
   ---

   # {{title}}

   ## Goal

   ## Status

   ## Links
   ```

2. **Substitution rules** (this skill follows these when a template is present):
   - `{{date}}` → `YYYY-MM-DD` (today, or the date the user named)
   - `{{title}}` → the snake_case basename of the note (without `.md`)

3. **Optional — install the Obsidian "Templates" core plugin** (Settings → Core plugins → Templates → set Template folder location to `Templates`) so the Obsidian.app UI can insert them too. This skill works either way; the core plugin only matters for in-app usage.

4. **Frontmatter-generator plugin** (community): if you adopt it later, it auto-fills frontmatter on note creation inside Obsidian.app. Notes created from the shell via this skill won't go through it, so the templates above stay the source of truth.
