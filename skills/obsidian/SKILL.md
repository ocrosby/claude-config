---
description: Find, navigate, read, and edit notes in Omar's PARA-organized Obsidian vault at ~/src/github.com/ocrosby/obsidian (git-tracked, not iCloud). Use whenever the user mentions "the vault", "my notes", "Obsidian", a daily note, an inbox capture, or asks to look up / jot down anything that sounds like personal knowledge management — even if they don't say the word "Obsidian".
when_to_use: User wants to read, create, or edit a note. Examples — "add a daily note", "what did I write about X", "jot this down in my inbox", "save this to the vault", "open today's note", "find my Postgres notes", "add to my scout-sleuth project", "what's in my vault about Y".
allowed-tools: Bash(rg *) Bash(fd *) Bash(find *) Bash(grep *) Bash(mkdir *) Bash(touch *) Bash(cat *) Bash(date *) Bash(stat *) Bash(wc *) Bash(sort *) Bash(xargs *) Bash(cut *) Read Edit Write
---

## When NOT to use

This skill targets **only** the primary vault at `~/src/github.com/ocrosby/obsidian`. Do not use it for:

- `~/src/github.com/ocrosby/notes` — the larger reference collection (adr/, algorithms/, architecture/). Ask which vault the user means if ambiguous.
- `~/notes/notes` — the second registered vault; targeted only if the user names it explicitly.
- AI-generated indexes over a pile of assets (raw/ + wiki/) → use `/knowledge-base` instead — `wiki/` is regenerable and must not be hand-edited.
- Code-adjacent documentation (README.md, docs/) → use `/docs write` instead.

# Obsidian vault

Omar's vault is a plain markdown directory tree organized with the [PARA method](https://fortelabs.com/blog/para/). Because it's just files, all standard Unix tools work — Obsidian.app is not required to read or write notes.

Structure adapted from [fredrikaverpil/dotfiles](https://github.com/fredrikaverpil/dotfiles/blob/main/stow/shared/.claude/skills/obsidian/SKILL.md); content tailored to Omar's actual vault layout, conventions, and git-tracked workflow.

## Where it lives

```
~/src/github.com/ocrosby/obsidian
```

This is the **primary** vault — the one marked `"open":true` in `~/Library/Application Support/obsidian/obsidian.json`. It's a git repo (`github.com/ocrosby/obsidian`), not iCloud-synced. The path has no spaces, so quoting is optional but harmless. Shorthand for shell sessions:

```bash
VAULT="$HOME/src/github.com/ocrosby/obsidian"
```

**Two other vaults are registered** with Obsidian.app: `~/notes/notes` and `~/src/github.com/ocrosby/notes`. This skill targets the primary vault above; if a question seems to belong to one of the others (e.g. `~/src/github.com/ocrosby/notes` has a much larger reference collection — `adr/`, `algorithms/`, `architecture/`, etc.), ask before assuming.

If `$VAULT` doesn't exist, stop and tell the user — don't fabricate notes.

## Workflow

### 1. Resolve the vault

```bash
VAULT="$HOME/src/github.com/ocrosby/obsidian"
```

**If `$VAULT` does not exist: stop and do not proceed.** Tell the user which path is missing. Never fabricate notes into a non-existent tree.

**If the user's request seems to belong to the two other registered vaults (`~/notes/notes`, `~/src/github.com/ocrosby/notes`): stop and ask** which vault they mean before reading or writing.

### 2. Identify the intent

Route based on what the user asked for:

| Intent | Go to |
|---|---|
| Read / find an existing note | step 3 |
| Create a new note (non-daily) | step 4 |
| Edit / append to an existing note | step 5 |
| Daily-note operations (today's, yesterday's, or a specific date) | step 6 |
| Quick-capture into `Inbox/` | step 4 (folder = `Inbox/`) |

**If the intent is ambiguous between "find X" and "create X": stop and do not proceed.** Ask the user to clarify.

### 3. Find or read a note

Apply the recipes in the "Finding things" section below. Always exclude `.obsidian/` and `.trash/`.

**If more than one candidate matches the query: stop and list them; ask which one.** Do not pick silently.

### 4. Create a note

Follow the "Creating notes" section below for folder choice, template application, snake_case filename, and wikilink style.

**If the target PARA folder does not exist under `$VAULT`: run the "Setup checklist" first.** Never create ad-hoc top-level folders outside the documented PARA layout.

### 5. Edit a note

Follow the "Editing notes" section below. Preserve existing frontmatter, wikilink style, and surrounding formatting. Do not reformat content the user did not ask about.

### 6. Daily-note operations

Apply the recipes in the "Daily notes workflow" section below. The create-or-open shell block is idempotent — always append under `## Notes` rather than overwrite when the file exists.

**If the user asked to backfill a past daily note: stop and confirm** — backfilling is usually not what they want.

### 7. Verify the outcome

Confirm the resulting path exists and print it so the user can open it in Obsidian.app:

```bash
[ -f "$RESULT" ] && echo "wrote: $RESULT" || { echo "FAILED: $RESULT"; exit 1; }
```

**If the write did not land where expected: stop and do not report success.** Return to the failing step and re-check the folder/filename derivation.

Committing is the user's job — surface the change set per the "Git discipline" section, but do not run `git add`/`git commit` from this skill.

## Setup checklist (one-time bootstrap)

The vault's own `readme.md` describes a PARA layout, but several folders it lists aren't created yet. Run this once to bring the on-disk structure in line with the readme so the workflow below has somewhere to write:

```bash
VAULT="$HOME/src/github.com/ocrosby/obsidian"
mkdir -p "$VAULT"/{Inbox,Daily,Archives,Templates}
```

Optional but recommended:

- **Add a `.gitignore` rule for `.obsidian/workspace*.json`** — these track UI state (open panes, recent files) and create noise in commits. Run from the vault root: `printf '.obsidian/workspace*.json\n.obsidian/cache\n.trash/\n' >> .gitignore && git add .gitignore`.
- **Decide on the daily-notes cadence.** A practical starter: open today's note first thing each morning, capture the day's thoughts, link out to project notes via `[[Projects/scout_sleuth/...]]` when work shifts there. The "Daily notes workflow" section below has the create-if-missing recipe.
- **Install `obsidian.nvim` only if you want in-editor vault management.** It's not currently in `yoda.nvim/lua/plugins/`; the shell + Obsidian.app combo this skill assumes works without it. If you do add it, prefer `/add-plugin` and re-read this skill afterward to surface obsidian.nvim-specific shortcuts.

After bootstrapping, commit the empty folders intentionally (each needs a `.gitkeep` since git ignores empty dirs):

```bash
for d in Inbox Daily Archives Templates; do touch "$VAULT/$d/.gitkeep"; done
```

Templates rollout is covered in its own section below — leave `Templates/` empty for now; this skill works fine without it.

## Folder layout

```
$VAULT/
├── Inbox/                    # Unprocessed quick captures — first stop for new thoughts
├── Daily/                    # Daily notes, one file per day: YYYY-MM-DD.md
├── Projects/                 # Active projects with clear goals
│   ├── scout_sleuth/         # College Recruiting Intelligence Platform
│   └── dotfiles/             # System configuration project
├── Areas/                    # Ongoing responsibilities
│   ├── development/          # Languages, editors, frameworks, tools, architecture
│   └── systems/              # Shell, mac, keyboard, tmux, window-manager
├── Resources/                # Reference materials (cheatsheets, tutorials, docs)
├── Archives/                 # Completed or inactive material
├── Templates/                # (Future) reusable note formats — see Templates section
├── Meta/                     # Vault documentation and structure guides
├── copilot-custom-prompts/   # Omar's reusable AI prompt library — not PARA
├── _excalidraw/              # (If present) Excalidraw drawings as .excalidraw.md files
└── .obsidian/                # App config — skip in searches
```

Skip `.obsidian/` and `.trash/` (if present) when searching unless the user explicitly asks about deleted notes or app config.

## Note conventions

### Filenames

- **Daily notes**: `Daily/YYYY-MM-DD.md` (e.g. `Daily/2026-06-03.md`)
- **All other notes**: `snake_case.md` — matching the existing pattern (`project_planning.md`, `llm_assisted_project_development_framework.md`). Do not introduce Title Case, kebab-case, or date prefixes; the rest of the vault is consistent snake_case.

### Wikilinks

The vault uses **Obsidian wikilinks**, and the observed style is **path-style relative** — not the shortest-form most Obsidian docs show:

```markdown
[[../readme]]
[[../prompt_engineering/readme]]
[[readme]]
```

**Preserve the style as written.** If the user wrote `[[../readme]]`, don't "normalize" it to `[[readme]]`. If creating a new cross-reference and unsure, use the relative-path form already present nearby — it's the dominant convention here.

Standard markdown links (`[text](path.md)`) are not used — use wikilinks.

### Frontmatter

Most existing notes have **no YAML frontmatter**. Behavior:

- **When editing**: preserve what's there. Don't add frontmatter to a note that doesn't have it.
- **When creating a new note** via this skill: add a minimal block only if a template (see below) calls for it. Otherwise leave the file frontmatter-free to match the surrounding vault.
- **When creating a Daily note**: include the canonical daily frontmatter (`date`, `tags: [daily-notes]`) — see the daily-notes section.

## Daily notes workflow

The daily note is the catch-all for a single day's thoughts: standups, what you worked on, things you want to revisit, links to project notes. Daily notes live at `Daily/YYYY-MM-DD.md`.

### Create-or-open today's note

```bash
VAULT="$HOME/src/github.com/ocrosby/obsidian"
TODAY="$VAULT/Daily/$(date +%Y-%m-%d).md"
if [ ! -f "$TODAY" ]; then
  cat > "$TODAY" <<EOF
---
id: $(date +%Y-%m-%d)
date: $(date +%Y-%m-%d)
tags: [daily-notes]
---

# $(date +%Y-%m-%d)

## What I worked on

## Notes

## Tomorrow
EOF
fi
```

When the user says "today's daily note" or "add to today", run this pattern. If `$TODAY` already exists, append rather than overwrite — usually under `## Notes`. Show the resulting path so they can open it in Obsidian.app.

### Append a quick thought to today

```bash
echo -e "\n- $(date +%H:%M) — <thought here>" >> "$TODAY"
```

### Open yesterday's / a specific date's note

```bash
YESTERDAY="$VAULT/Daily/$(date -v-1d +%Y-%m-%d).md"   # macOS date syntax
SPECIFIC="$VAULT/Daily/2026-05-15.md"
```

If the requested date's note doesn't exist, ask before creating — backfilling daily notes is usually not what the user wants.

## Templates (when you start using them)

`Templates/` is empty for now. When you're ready to adopt them, create the files below — this skill will start using them automatically (the note-creation logic checks for `Templates/<type>.md` and falls back to the minimal frontmatter above if missing).

### How to add templates

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

## Creating notes

When the user asks to create a note (not a daily one), follow these rules:

1. **Pick the right folder** by intent:
   - Quick capture, not yet classified → `Inbox/`
   - Active project work → `Projects/<project_name>/`
   - Ongoing responsibility (language, tool, system) → `Areas/<area>/<topic>/`
   - Durable reference (cheatsheet, doc, tutorial) → `Resources/<type>/<topic>/`
   - Half-formed thought → `Inbox/` (and let weekly review move it)
   - Completed / inactive → `Archives/`
   - Vault structure or process docs → `Meta/`

   If unsure between two folders, ask — folder choice is how the user finds things later.

2. **Apply a template if one exists** at `Templates/<type>.md`. Otherwise create the note without frontmatter (to match the vault's current convention).

3. **Use snake_case** for the filename. Don't add a date prefix.

4. **Use wikilinks** for cross-references, in the relative-path style already common in the vault.

## Editing notes

- Preserve existing frontmatter exactly. Only add fields that are missing **if** the note already has a frontmatter block.
- Don't rewrite `id` if present — it may be a deliberate alias.
- Keep the wikilink style as written. Don't convert `[[../readme]]` to `[[readme]]` or to a markdown link.
- Don't reformat surrounding content unless asked.

## Finding things

All recipes assume `VAULT="$HOME/src/github.com/ocrosby/obsidian"`. Exclude `.obsidian/` and `.trash/` to keep results signal-rich. Prefer `rg`/`fd`; fall back to `grep`/`find` if missing.

```bash
# Find notes by filename (case-insensitive, fuzzy on basename)
fd -tf 'pattern' "$VAULT" -E .obsidian -E .trash

# Full-text search across notes
rg --type md -n 'search term' "$VAULT" -g '!.obsidian' -g '!.trash'

# Find notes tagged X (frontmatter list or inline #tag)
rg --type md -n '(^|\s)#X\b|tags:.*\bX\b' "$VAULT" -g '!.obsidian' -g '!.trash'

# Find backlinks to a note titled `project_planning`
rg --type md -n '\[\[(.*/)?project_planning(\||#|\]\])' "$VAULT" -g '!.obsidian' -g '!.trash'

# What did I write about X recently? (combine filename + content; sort by mtime)
{ fd -tf 'X' "$VAULT" -E .obsidian -E .trash; rg --type md -l 'X' "$VAULT" -g '!.obsidian' -g '!.trash'; } | sort -u | xargs -I{} stat -f '%m %N' {} | sort -rn | head -10 | cut -d' ' -f2-
```

For broad questions ("what notes do I have about Postgres?"), search both filenames and content — the vault organizes by both folder and inline references.

## Git discipline

The vault is git-tracked with remote `github.com/ocrosby/obsidian`. This skill does **not** commit on your behalf. After a session of edits, surface the change set and let your normal `/git ship` flow handle the commit — that keeps note edits auditable in the same way as code changes.

If a session creates multiple notes, group them into one logical commit (e.g. `docs(daily): 2026-06-03 + linked project updates`) rather than one commit per file.
