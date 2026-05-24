#!/usr/bin/env bash
# Bootstrap today's work journal entry, carrying over open tasks from the
# most recent prior file. Used by skills/work/SKILL.md.
#
# Emits 4 or 5 lines:
#   {CREATED_ROOT|OK_ROOT}
#   {CREATED_TODAY|OK_TODAY}
#   [CARRYOVER:N]       (only when CREATED_TODAY)
#   <human-readable date>
#   How we're doing so far: D/T (P%) Complete
set -euo pipefail

WORK="${WORK_ROOT:-$HOME/work}"
YEAR=$(date +%Y); MONTH=$(date +%-m); DAY=$(date +%-d)
TODAY_FILE="$WORK/$YEAR/$MONTH/$DAY.md"

if [ ! -d "$WORK" ]; then
  mkdir -p "$WORK"
  cat > "$WORK/README.md" <<'README'
# Work Journal

A date-structured daily log of engineering activity.

Structure: work/YYYY/M/D.md (no zero-padding)

Commands:
  /work                   Show help
  /work add <task>        Add a task to today's journal
  /work list [period]     List tasks (today/yesterday/this-week/last-week)
  /work done [task text]  Mark a task complete
README
  echo "CREATED_ROOT"
else
  echo "OK_ROOT"
fi

if [ ! -f "$TODAY_FILE" ]; then
  mkdir -p "$WORK/$YEAR/$MONTH"

  PREV_FILE=$(find "$WORK" -name "[0-9]*.md" ! -path "$TODAY_FILE" 2>/dev/null \
    | sed 's|.*/\([0-9]*\)/\([0-9]*\)/\([0-9]*\)\.md$|\1 \2 \3 &|' \
    | sort -k1,1n -k2,2n -k3,3n \
    | awk '{print $4}' \
    | tail -1)

  CARRYOVER=""
  CARRYOVER_COUNT=0
  if [ -n "$PREV_FILE" ] && [ -f "$PREV_FILE" ]; then
    CARRYOVER=$(grep '- \[ \]' "$PREV_FILE" 2>/dev/null || true)
    [ -n "$CARRYOVER" ] && CARRYOVER_COUNT=$(echo "$CARRYOVER" | grep -c '- \[ \]')
  fi

  printf "%s\n\n## Tasks\n" "$(date '+%A %b %-d')" > "$TODAY_FILE"

  if [ -n "$CARRYOVER" ]; then
    echo "$CARRYOVER" >> "$TODAY_FILE"
    echo "$CARRYOVER" | grep -q 'Review Jenkins Jobs' || printf "%s\n" "- [ ] Review Jenkins Jobs" >> "$TODAY_FILE"
  else
    printf "%s\n" "- [ ] Review Jenkins Jobs" >> "$TODAY_FILE"
  fi

  printf "\n## Notes\n" >> "$TODAY_FILE"

  echo "CREATED_TODAY"
  echo "CARRYOVER:$CARRYOVER_COUNT"
else
  echo "OK_TODAY"
fi

read -r DONE OPEN <<< "$(awk '/- \[x\]/{d++} /- \[ \]/{o++} END{printf "%d %d",d+0,o+0}' "$TODAY_FILE")"
TOTAL=$((DONE + OPEN))
PCT=$(awk -v d="$DONE" -v t="$TOTAL" 'BEGIN{if(t>0) printf "%d",int(d/t*100+0.5); else print 0}')

date "+%A, %B %-d, %Y — %-I:%M %p"
echo "How we're doing so far: $DONE/$TOTAL (${PCT}%) Complete"
