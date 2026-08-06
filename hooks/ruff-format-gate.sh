#!/usr/bin/env bash
# PreToolUse gate: block `git commit` when any staged .py file fails
# `ruff format --check`. Fills the gap that PostToolUse `lint.sh` cannot
# cover — files modified via Bash (sed / redirect), by an external editor,
# or that pre-date the hook — from re-entering the codebase unformatted.
#
# Exit code contract (per Claude Code hooks docs — PreToolUse exit 2 blocks
# the tool call and feeds stderr back to Claude as an actionable message):
#   0 = no staged .py files, or all staged .py files match ruff format
#   2 = one or more staged .py files need reformatting
#
# After stowing, make executable: chmod +x ~/.claude/hooks/ruff-format-gate.sh
set -uo pipefail

HOOK="[hook: ruff-format-gate]"

# Skip silently outside a git repo (e.g. a `git commit` typo before `git init`).
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

# Staged files added/copied/modified/renamed, filtered to .py. Use a while-read
# loop (not `mapfile`) so this works on macOS's /bin/bash 3.2. Explicit
# `PY_FILES=()` init so `${#PY_FILES[@]}` never reads as unbound under `set -u`.
PY_FILES=()
while IFS= read -r f; do
  [[ -n "$f" ]] && PY_FILES+=("$f")
done < <(git diff --cached --name-only --diff-filter=ACMR | grep -E '\.py$' || true)
[[ ${#PY_FILES[@]} -eq 0 ]] && exit 0

# ruff resolution, same priority as hooks/lint.sh — repo-pinned first so the
# gate uses the version CI/tasks use, uvx as the universal fallback so the
# gate works even in repos with no ruff dependency declared. Silent degrade
# if none of the paths resolve: gating on tooling absence would block every
# commit on a machine without uv, which is worse than a missed check.
PROJ_DIR="$(git rev-parse --show-toplevel)"
RUFF=()
if command -v uv &>/dev/null && [[ -f "$PROJ_DIR/pyproject.toml" ]]; then
  if (cd "$PROJ_DIR" && uv run --extra dev ruff --version &>/dev/null); then
    RUFF=(uv run --extra dev ruff)
  elif (cd "$PROJ_DIR" && uv run ruff --version &>/dev/null); then
    RUFF=(uv run ruff)
  fi
fi
if [[ ${#RUFF[@]} -eq 0 ]]; then
  if command -v uvx &>/dev/null; then
    RUFF=(uvx ruff)
  elif command -v ruff &>/dev/null; then
    RUFF=(ruff)
  else
    exit 0
  fi
fi

# `ruff format --check` exits non-zero when any file would be reformatted;
# stdout lists the offending paths.
if ! OUT=$(cd "$PROJ_DIR" && "${RUFF[@]}" format --check "${PY_FILES[@]}" 2>&1); then
  echo "$HOOK ACTION: staged Python file(s) fail \`ruff format --check\`. Reformat and re-stage before committing:" >&2
  echo "" >&2
  echo "$OUT" >&2
  echo "" >&2
  echo "  ${RUFF[*]} format ${PY_FILES[*]}" >&2
  echo "  git add ${PY_FILES[*]}" >&2
  exit 2
fi

exit 0
