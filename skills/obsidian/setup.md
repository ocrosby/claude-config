# Obsidian Vault: Setup Checklist (one-time bootstrap)

Level-3 resource for the `obsidian` skill. Run once, on first use, to bring the on-disk structure in line with the vault's `readme.md` so the workflow has somewhere to write.

The vault's own `readme.md` describes a PARA layout, but several folders it lists aren't created yet:

```bash
VAULT="$HOME/src/github.com/ocrosby/obsidian"
mkdir -p "$VAULT"/{Inbox,Daily,Archives,Templates}
```

Optional but recommended:

- **Add a `.gitignore` rule for `.obsidian/workspace*.json`** — these track UI state (open panes, recent files) and create noise in commits. Run from the vault root: `printf '.obsidian/workspace*.json\n.obsidian/cache\n.trash/\n' >> .gitignore && git add .gitignore`.
- **Decide on the daily-notes cadence.** A practical starter: open today's note first thing each morning, capture the day's thoughts, link out to project notes via `[[Projects/scout_sleuth/...]]` when work shifts there. `~/.claude/skills/obsidian/daily-notes.md` has the create-if-missing recipe.
- **Install `obsidian.nvim` only if you want in-editor vault management.** It's not currently in `yoda.nvim/lua/plugins/`; the shell + Obsidian.app combo this skill assumes works without it. If you do add it, prefer `/add-plugin` and re-read this skill afterward to surface obsidian.nvim-specific shortcuts.

After bootstrapping, commit the empty folders intentionally (each needs a `.gitkeep` since git ignores empty dirs):

```bash
for d in Inbox Daily Archives Templates; do touch "$VAULT/$d/.gitkeep"; done
```

Template files are covered in `~/.claude/skills/obsidian/templates.md` — leave `Templates/` empty for now; this skill works fine without it.
