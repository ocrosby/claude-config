---
description: Use whenever the user mentions "the vault", "my notes", "Obsidian", a daily note, an inbox capture, or asks to look up or jot down anything that sounds like personal knowledge management — even if they do not say the word "Obsidian". Reads, writes, and navigates Omar's PARA-organized vault at ~/src/github.com/ocrosby/obsidian (git-tracked, not iCloud).
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

First-run only: create the PARA folders, add `.gitignore` noise rules, and commit `.gitkeep` files. Read `~/.claude/skills/obsidian/setup.md` and run it. Skip if the vault is already bootstrapped.

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

Operative rules: filenames are `snake_case.md` (daily notes `Daily/YYYY-MM-DD.md`, no date prefixes elsewhere); cross-references use path-style-relative Obsidian wikilinks (`[[../readme]]`), preserved exactly as written — never normalized to short form or markdown links; most notes have **no** frontmatter, so don't add it when editing a note that lacks it. Full conventions with examples and the frontmatter-by-operation table live in `~/.claude/skills/obsidian/conventions.md` — read it before creating or editing a note.

## Daily notes workflow

Daily notes live at `Daily/YYYY-MM-DD.md` — the catch-all for a single day's thoughts. The create-or-open, append-a-thought, and open-a-past-date shell recipes live in `~/.claude/skills/obsidian/daily-notes.md`; read it and apply. Invariants: when today's note already exists, append under `## Notes` rather than overwrite; never backfill a past date without confirming first.

## Templates (when you start using them)

`Templates/` is empty for now; this skill works without it. When you're ready to adopt reusable note formats, read `~/.claude/skills/obsidian/templates.md` for the starter template files, the `{{date}}`/`{{title}}` substitution rules, and the optional Obsidian core-plugin setup.

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

2. **Apply a template if one exists** at `Templates/<type>.md` (see `~/.claude/skills/obsidian/templates.md` for the `{{date}}`/`{{title}}` substitution rules). Otherwise create the note without frontmatter (to match the vault's current convention).

3. **Use snake_case** for the filename. Don't add a date prefix.

4. **Use wikilinks** for cross-references, in the relative-path style already common in the vault.

## Editing notes

- Preserve existing frontmatter exactly. Only add fields that are missing **if** the note already has a frontmatter block.
- Don't rewrite `id` if present — it may be a deliberate alias.
- Keep the wikilink style as written. Don't convert `[[../readme]]` to `[[readme]]` or to a markdown link.
- Don't reformat surrounding content unless asked.

## Finding things

Search recipes — by filename, full-text, tag, backlinks, and recent-mentions (mtime-sorted) — live in `~/.claude/skills/obsidian/finding.md`; read it and apply. Always exclude `.obsidian/` and `.trash/`; prefer `rg`/`fd`, falling back to `grep`/`find`. For broad questions ("what notes do I have about Postgres?"), search both filenames and content.

## Git discipline

The vault is git-tracked with remote `github.com/ocrosby/obsidian`. This skill does **not** commit on your behalf. After a session of edits, surface the change set and let your normal `/git ship` flow handle the commit — that keeps note edits auditable in the same way as code changes.

If a session creates multiple notes, group them into one logical commit (e.g. `docs(daily): 2026-06-03 + linked project updates`) rather than one commit per file.

## Verify

Before the skill exits, confirm the outcome of what was actually done:

- **Read** requests — the surfaced content is from the vault at `~/src/github.com/ocrosby/obsidian` (not the other registered vaults, unless the user named one explicitly). Cite each hit as `path:line`.
- **Write/edit** requests — the file exists and contains the intended change. Re-`cat` the modified section (or the whole file if short) so the user can visually confirm.
- **Directory or search** requests — the result set is scoped to the vault (excluded `.obsidian/`, `.trash/`), and count/summary is shown.

If any check fails, name the failure — do not exit as if the request succeeded.
