#!/usr/bin/env bash
# PreToolUse hook: blocks direct commits to main/master and pushes to any
# branch GitHub branch protection covers.
# Exit non-zero aborts the git command before it executes.
#
# After stowing, make executable: chmod +x ~/.claude/hooks/protect-main.sh
set -uo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

# A command commonly looks like `cd <other-repo> && git ...` when the git
# operation targets a repo other than the session's project dir (e.g. this
# session's cwd is ~/.claude but the git commands run against a sibling repo).
# Resolve the actual target dir instead of trusting CLAUDE_PROJECT_DIR blindly
# — otherwise branch checks silently run against the wrong repo and never fire.
TARGET_DIR="${CLAUDE_PROJECT_DIR:-.}"
if [[ "$COMMAND" =~ ^cd[[:space:]]+([^&]+)\&\& ]]; then
  CD_PATH="${BASH_REMATCH[1]}"
  CD_PATH="${CD_PATH%\"}"; CD_PATH="${CD_PATH#\"}"
  CD_PATH="${CD_PATH%\'}"; CD_PATH="${CD_PATH#\'}"
  CD_PATH="$(echo -n "$CD_PATH" | sed -e 's/[[:space:]]*$//')"
  [[ -d "$CD_PATH" ]] && TARGET_DIR="$CD_PATH"
fi

# Check for direct commits to main/master
if [[ "$COMMAND" == *"git commit"* ]]; then
  # ALLOW_MAIN_COMMIT=1 is set by /ship -m and /ship -p for authorized direct-main commits
  [[ -n "${ALLOW_MAIN_COMMIT:-}" ]] && exit 0
  BRANCH=$(git -C "$TARGET_DIR" branch --show-current 2>/dev/null)
  if [[ "$BRANCH" == "main" || "$BRANCH" == "master" ]]; then
    echo "[hook: protect-main] ERROR: Direct commit to '$BRANCH' is not allowed."
    echo ""
    echo "  Use /ship -m to commit directly to main, or create a feature branch:"
    echo "    git checkout -b feature/<name>"
    exit 1
  fi
fi

# Check for force-push to main/master
if [[ "$COMMAND" == *"git push"* ]] && ([[ "$COMMAND" == *"--force"* ]] || [[ "$COMMAND" == *" -f "* ]] || [[ "$COMMAND" == *" -f" ]]); then
  if [[ "$COMMAND" == *"main"* || "$COMMAND" == *"master"* ]]; then
    echo "[hook: protect-main] ERROR: Force-push to a protected branch is not allowed."
    echo ""
    echo "  Force-pushing to main/master can overwrite history and break other contributors."
    echo "  If you need to update the remote, use: git push --force-with-lease"
    exit 1
  fi
fi

# Pre-flight: block a plain push to any branch GitHub protects, on ANY repo —
# not just ones with a hardcoded main/master check. Uses the rules API (covers
# both classic branch protection AND the newer repository rulesets — the
# classic branches/{branch}/protection endpoint 404s for repos that only use
# rulesets, which would otherwise fail this check open). Best-effort: requires
# `gh` auth against a github.com remote; fails open if either is unavailable,
# since this is a safety net, not the sole guard.
if [[ "$COMMAND" == *"git push"* ]] && [[ "$COMMAND" != *"--force"* ]] && [[ "$COMMAND" != *" -f "* ]] && [[ "$COMMAND" != *" -f" ]]; then
  # ALLOW_PROTECTED_PUSH=1 is the explicit escape valve for a genuinely authorized bypass
  if [[ -z "${ALLOW_PROTECTED_PUSH:-}" ]]; then
    PUSH_BRANCH=""
    if [[ "$COMMAND" =~ git[[:space:]]+push[[:space:]]+[A-Za-z0-9_.-]+[[:space:]]+([A-Za-z0-9_./-]+) ]]; then
      PUSH_BRANCH="${BASH_REMATCH[1]##*:}"
    fi
    [[ -z "$PUSH_BRANCH" ]] && PUSH_BRANCH=$(git -C "$TARGET_DIR" branch --show-current 2>/dev/null)

    REMOTE_URL=$(git -C "$TARGET_DIR" remote get-url origin 2>/dev/null)
    if [[ -n "$PUSH_BRANCH" && "$REMOTE_URL" == *"github.com"* ]]; then
      OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's#.*github\.com[:/]##; s#\.git$##')
      if RULES=$(gh api "repos/${OWNER_REPO}/rules/branches/${PUSH_BRANCH}" 2>/dev/null) && echo "$RULES" | jq -e 'any(.[]; .type == "pull_request")' >/dev/null 2>&1; then
        echo "[hook: protect-main] ERROR: '$PUSH_BRANCH' on ${OWNER_REPO} requires changes via pull request."
        echo ""
        echo "  Push a feature branch instead and open a PR:"
        echo "    git checkout -b <type>/<scope>"
        echo "    git push -u origin <type>/<scope>"
        echo "    gh pr create"
        echo ""
        echo "  If this push is genuinely authorized to bypass this rule, set ALLOW_PROTECTED_PUSH=1."
        exit 1
      fi
    fi
  fi
fi

exit 0
