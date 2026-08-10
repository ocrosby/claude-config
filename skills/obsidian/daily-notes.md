# Obsidian Vault: Daily Notes Workflow

Level-3 resource for the `obsidian` skill (workflow step 6). The daily note is the catch-all for a single day's thoughts: standups, what you worked on, things you want to revisit, links to project notes. Daily notes live at `Daily/YYYY-MM-DD.md`.

## Create-or-open today's note

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

## Append a quick thought to today

```bash
echo -e "\n- $(date +%H:%M) — <thought here>" >> "$TODAY"
```

## Open yesterday's / a specific date's note

```bash
YESTERDAY="$VAULT/Daily/$(date -v-1d +%Y-%m-%d).md"   # macOS date syntax
SPECIFIC="$VAULT/Daily/2026-05-15.md"
```

If the requested date's note doesn't exist, ask before creating — backfilling daily notes is usually not what the user wants.
