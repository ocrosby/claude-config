#!/usr/bin/env bash
# Emit today's work-journal contents to stdout so Claude sees them as
# SessionStart additionalContext. Path convention mirrors bootstrap.sh:
# ~/work/YYYY/M/D.md with no zero-padding.
set -euo pipefail

Y=$(date +%Y)
M=$(date +%-m)
D=$(date +%-d)
FILE="$HOME/work/$Y/$M/$D.md"

if [ -f "$FILE" ]; then
  echo "Today's work journal ($FILE):"
  echo
  cat "$FILE"
else
  echo "No work journal exists yet for today ($Y-$M-$D). Run /work to initialize."
fi
