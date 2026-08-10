# Obsidian Vault: Finding Things

Level-3 resource for the `obsidian` skill (workflow step 3). All recipes assume `VAULT="$HOME/src/github.com/ocrosby/obsidian"`. Exclude `.obsidian/` and `.trash/` to keep results signal-rich. Prefer `rg`/`fd`; fall back to `grep`/`find` if missing.

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
