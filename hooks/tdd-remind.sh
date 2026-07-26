#!/usr/bin/env bash
# PreToolUse TDD reminder hook — fires before Edit/Write on code files
# Outputs a reminder for Claude to follow TDD; Claude sees this as a hook warning.
# Exit 0: allow the tool call to proceed (reminder only, not a block)
#
# Fast path: bash-only extraction and filename gate before any decision work.
# Skips the jq subprocess for the ~80% of Edit/Write calls that hit non-code
# files (YAML, JSON, Markdown, shell, config).
set -uo pipefail

INPUT=$(cat)

# Extract file_path via bash regex; skip if absent (no jq subprocess cost).
if [[ "$INPUT" =~ \"file_path\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]]; then
  FILE="${BASH_REMATCH[1]}"
else
  exit 0
fi

# Only trigger on implementation code files
case "${FILE##*.}" in
  lua|go|py) ;;
  *) exit 0 ;;
esac

# Skip if this IS a test file — TDD in progress, not a violation
BASENAME=${FILE##*/}
case "$BASENAME" in
  *_spec.lua|*_test.lua|test_*.py|*_test.py|*_test.go) exit 0 ;;
esac
case "$FILE" in
  */tests/*|*/test/*) exit 0 ;;
esac

# Skip Neovim config files — pure configuration, no testable behavior
case "$FILE" in
  */lua/config/*.lua|*/lua/plugins/*.lua|*/lsp/*.lua|*/after/ftplugin/*.lua) exit 0 ;;
esac

echo "[hook: tdd-remind] TDD REQUIRED: Write a failing test, run it, show failure output — THEN edit ${FILE}. Exceptions: /migrate, /refactor, or purely mechanical renames only."
