#!/usr/bin/env bash
# PreToolUse hook: warn Claude when files changed on this branch also changed on
# origin/main since the branch diverged — surfaces potential merge conflicts
# before the push, so a rebase can happen first.
#
# Outputs additionalContext JSON (non-blocking) when overlap is found.
#
# Performance: `git fetch origin main` is a network round-trip. On slow links
# it adds seconds directly to the user's push. We rate-limit fetches to once
# per FETCH_MAX_AGE_SECONDS via a per-repo timestamp file; if the last fetch
# was recent enough, we reuse the current origin/main ref and skip the fetch.
set -uo pipefail

INPUT=$(cat)

# Extract command via bash regex; skip if absent (no jq subprocess cost).
if [[ "$INPUT" =~ \"command\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]]; then
  COMMAND="${BASH_REMATCH[1]}"
else
  exit 0
fi

# Only relevant for git push
[[ "$COMMAND" != *"git push"* ]] && exit 0

# protect-main.sh handles the main/master case; skip here
BRANCH=$(cd "${CLAUDE_PROJECT_DIR:-.}" && git branch --show-current 2>/dev/null)
[[ "$BRANCH" == "main" || "$BRANCH" == "master" ]] && exit 0

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

# Rate-limit fetch: skip if origin/main was updated within the last N seconds.
# 300s (5m) is a reasonable freshness ceiling — long enough to make fetching
# during a burst of pushes free, short enough to catch same-session collisions.
FETCH_MAX_AGE_SECONDS=300
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null) || exit 0
STAMP="$GIT_DIR/.claude-conflict-check-fetch-ts"

should_fetch=1
if [[ -f "$STAMP" ]]; then
  now=$(date +%s)
  last=$(cat "$STAMP" 2>/dev/null || echo 0)
  age=$((now - last))
  if (( age < FETCH_MAX_AGE_SECONDS )); then
    should_fetch=0
  fi
fi

if (( should_fetch )); then
  # Kick fetch off in the background so it does not block the push.
  # Give it a short window; if it doesn't finish, exit without warning —
  # surface only actual conflicts, never false positives from stale refs.
  ( git fetch origin main --quiet 2>/dev/null && date +%s > "$STAMP" ) &
  FETCH_PID=$!
  wait_deadline=$(( $(date +%s) + 2 ))
  while kill -0 "$FETCH_PID" 2>/dev/null; do
    (( $(date +%s) >= wait_deadline )) && exit 0
    sleep 0.1
  done
fi

MERGE_BASE=$(git merge-base HEAD origin/main 2>/dev/null) || exit 0
[[ -z "$MERGE_BASE" ]] && exit 0

# Files this branch changed since it diverged from main
BRANCH_FILES=$(git diff --name-only "$MERGE_BASE" HEAD 2>/dev/null | sort -u)
[[ -z "$BRANCH_FILES" ]] && exit 0

# Files main changed since the branch diverged
MAIN_FILES=$(git diff --name-only "$MERGE_BASE" origin/main 2>/dev/null | sort -u)
[[ -z "$MAIN_FILES" ]] && exit 0

OVERLAP=$(comm -12 <(echo "$BRANCH_FILES") <(echo "$MAIN_FILES") 2>/dev/null)
[[ -z "$OVERLAP" ]] && exit 0

FILES_LIST=$(echo "$OVERLAP" | tr '\n' ' ' | sed 's/[[:space:]]*$//')
printf '{"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": "Conflict warning: the following files were also modified on origin/main since this branch diverged — %s — rebase before opening the PR to avoid merge conflicts: git rebase origin/main"}}\n' "$FILES_LIST"

exit 0
