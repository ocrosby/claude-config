#!/usr/bin/env bash
# PreToolUse hook: warns when Claude is about to read a sensitive file.
# Always exits 0 (never blocks reads) — the warning surfaces to Claude so it
# avoids echoing secret values back in explanations or diffs.
#
# Fast path: bash-only regex extract of file_path from JSON input, avoiding
# a jq subprocess spawn on the ~95% of Reads that hit non-sensitive files.
#
# After stowing, make executable: chmod +x ~/.claude/hooks/sensitive-file-warn.sh
set -uo pipefail

INPUT=$(cat)

# Extract file_path from JSON without spawning jq. Bash's regex is enough for
# the well-formed { "tool_input": { "file_path": "..." } } shape the harness
# sends. If the pattern doesn't match, there's no path to warn about.
if [[ "$INPUT" =~ \"file_path\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]]; then
  FILE="${BASH_REMATCH[1]}"
else
  exit 0
fi

# Match on full path — covers .env files, key/cert material, and secrets directories
case "$FILE" in
  */.env | */.env.* | *.env)           ;;  # .env files (any depth)
  *.key | *.pem | *.p12 | *.pfx | *.crt | *.cer) ;;  # key and certificate files
  */credentials.json | */credentials.yml | */credentials.yaml) ;;
  */secrets.json | */secrets.yml | */secrets.yaml) ;;
  */.ssh/* | */.gnupg/*)               ;;  # SSH and GPG key directories
  *) exit 0 ;;
esac

HOOK="[hook: sensitive-file-warn]"
LOG="$HOME/.claude/hooks/hook-debug.log"
echo "$(date -u +%FT%TZ) $HOOK $FILE" >> "$LOG"
echo "$HOOK WARNING: Reading sensitive file: $FILE"
echo "Do not reproduce the contents of this file verbatim in responses, diffs, or code blocks."

exit 0
