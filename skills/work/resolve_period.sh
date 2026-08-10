#!/usr/bin/env bash
# Resolve a `/work list` period to the existing daily-journal files in range,
# oldest first. Used by skills/work/SKILL.md step 4.
#
# Usage: resolve_period.sh [today|yesterday|this-week|last-week]   (default today)
# Emits: one existing file path per line (empty output if none).
#
# Owns the date math (Monday-of-week, previous calendar week) and the journal
# path format ({WORK_ROOT}/{YYYY}/{M}/{D}.md, no zero-padding) so the skill
# does not re-derive them. Uses macOS/BSD `date -v` (matches bootstrap.sh).
set -euo pipefail

WORK="${WORK_ROOT:-$HOME/work}"
PERIOD="${1:-today}"

# start/end are "days ago" from today; start >= end (start is the oldest day).
case "$PERIOD" in
  today) start=0; end=0 ;;
  yesterday) start=1; end=1 ;;
  this-week)
    dow=$(date +%u) # 1=Mon .. 7=Sun
    start=$((dow - 1)) # this Monday, in days ago
    end=0 ;; # through today
  last-week)
    dow=$(date +%u)
    start=$((dow - 1 + 7)) # previous Monday
    end=$((dow - 1 + 1)) ;; # previous Sunday
  *)
    echo "error: unknown period '$PERIOD' (use today|yesterday|this-week|last-week)" >&2
    exit 1 ;;
esac

i=$start
while [ "$i" -ge "$end" ]; do
  path="$WORK/$(date -v-"${i}"d +%Y/%-m/%-d).md"
  if [ -f "$path" ]; then
    echo "$path"
  fi
  i=$((i - 1))
done
