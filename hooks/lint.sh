#!/usr/bin/env bash
# PostToolUse lint hook — runs after Edit/Write tool calls
#
# Exit code contract (per Claude Code hooks docs — PostToolUse can't block,
# but the exit code still controls what Claude sees):
#   0 = clean, or every issue found was auto-fixed in place. Silent. Claude
#       still learns about auto-fixed files, because the harness diffs the
#       file on next touch and injects a "modified outside the Edit tool"
#       note — it does NOT come from this script's stdout/stderr.
#   2 = an issue was found that this hook could NOT auto-fix. Only exit code
#       2 gets the FULL stderr fed back to Claude as an actionable message in
#       the same turn ("any other exit code" only shows the first stderr line
#       in the transcript, which is not enough context to act on). Every
#       failure path below must use `exit 2`, never a tool's raw exit code.
#
# So the shape of every block is: run the fixer in write mode first (never
# --check-only), then only report + exit 2 for what the fixer could not
# resolve itself.
#
# After stowing, make executable: chmod +x ~/.claude/hooks/lint.sh
set -uo pipefail

INPUT=$(cat)
FILE=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)

# Exit silently if no file path or file doesn't exist
[[ -z "$FILE" ]] && exit 0
[[ ! -f "$FILE" ]] && exit 0

HOOK="[hook: lint]"
LOG="$HOME/.claude/hooks/hook-debug.log"

# Exit code 2 is the ONLY PostToolUse exit code that feeds stderr back into
# Claude's context. Exit 1 shows stderr to the user's UI but the model never
# sees it — which means Claude cannot act on the diagnostics. Force 2 here so
# every downstream exit path in this script becomes a Claude-visible blocking
# finding regardless of the underlying tool's code — the case blocks below
# already call `exit 2` explicitly at each failure site too, but the trap is
# the backstop if one of them ever drifts back to a bare `exit 1`.
# shellcheck disable=SC2154 # ec is assigned inside the single-quoted trap body at trap-fire time, not at parse time
trap '
  ec=$?
  if [[ $ec -ne 0 ]]; then
    echo "$HOOK ACTION: the issue(s) above survived auto-fixing. Fix them directly in the affected file(s), or explain in detail why a given one cannot be fixed (missing tool, ambiguous design choice, requires human input)." >&2
    exit 2
  fi
' EXIT

case "${FILE##*.}" in
  py)
    echo "$(date -u +%FT%TZ) $HOOK py: $FILE" >> "$LOG"

    # Walk up to the project root (where pyproject.toml lives) first — ruff is
    # a per-project `uv` dev dependency in these repos, not a globally
    # installed binary, so `command -v ruff` alone would silently no-op on
    # every repo that doesn't happen to have a global install.
    PROJ_DIR="$(dirname "$FILE")"
    while [[ "$PROJ_DIR" != "/" && ! -f "$PROJ_DIR/pyproject.toml" ]]; do
      PROJ_DIR="$(dirname "$PROJ_DIR")"
    done

    # Resolution order, most-authoritative first:
    #   1. This project's pinned ruff via its "dev" extra — matches the exact
    #      version CI/tasks.py use. Most sun-*-acceptance-tests repos declare
    #      ruff under [project.optional-dependencies].dev, which `uv sync`
    #      does NOT install by default — `uv run ruff` alone 404s even though
    #      pyproject.toml lists ruff, unless the extra has been synced.
    #   2. Already-synced project venv (dependency-groups or an extra synced
    #      some other way) — plain `uv run ruff`.
    #   3. `uvx ruff` — ephemeral, isolated, cached. Works regardless of this
    #      project's venv/extras state, at the cost of possible version drift
    #      from the repo's pin.
    #   4. A globally installed `ruff` binary, if one happens to exist.
    RUFF_CMD=""
    if [[ -f "$PROJ_DIR/pyproject.toml" ]] && command -v uv &>/dev/null; then
      if (cd "$PROJ_DIR" && uv run --extra dev ruff --version &>/dev/null 2>&1); then
        RUFF_CMD="uv-dev"
      elif (cd "$PROJ_DIR" && uv run ruff --version &>/dev/null 2>&1); then
        RUFF_CMD="uv"
      fi
    fi
    if [[ -z "$RUFF_CMD" ]]; then
      if command -v uvx &>/dev/null; then
        RUFF_CMD="uvx"
      elif command -v ruff &>/dev/null; then
        RUFF_CMD="global"
      else
        exit 0
      fi
    fi

    run_ruff() {
      case "$RUFF_CMD" in
        uv-dev) (cd "$PROJ_DIR" && uv run --extra dev ruff "$@") ;;
        uv) (cd "$PROJ_DIR" && uv run ruff "$@") ;;
        uvx) uvx ruff "$@" ;;
        global) ruff "$@" ;;
      esac
    }

    # Auto-fix in place: logical fixes first, then formatting (ruff's own
    # recommended order — check --fix can change code shape that format then
    # normalizes).
    run_ruff check --fix --quiet "$FILE" >/dev/null 2>&1
    run_ruff format --quiet "$FILE" >/dev/null 2>&1

    RUFF_OUT=$(run_ruff check --quiet "$FILE" 2>&1)
    if [[ $? -ne 0 ]]; then
      echo "$HOOK ruff: auto-fixed what it could in $FILE; issue(s) below need a manual call:" >&2
      echo "$RUFF_OUT" >&2
      exit 2
    fi

    # Complexity — skip test files (excluded from the CI complexity gate too).
    # Not auto-fixable: reducing cyclomatic complexity requires a real refactor.
    [[ "$FILE" == */test_*.py || "$FILE" == *_test.py || "$FILE" == */tests/* ]] && exit 0
    [[ ! -f "$PROJ_DIR/pyproject.toml" ]] && exit 0
    (cd "$PROJ_DIR" && uv run cyclo --help &>/dev/null 2>&1) || exit 0
    MAX_C=$(grep -A2 '\[tool\.ruff\.lint\.mccabe\]' "$PROJ_DIR/pyproject.toml" 2>/dev/null \
      | grep 'max-complexity' | grep -oE '[0-9]+' | head -1)
    MAX_C="${MAX_C:-7}"
    FILE_DIR="$(dirname "$FILE")"
    REL_DIR="${FILE_DIR#"${PROJ_DIR}"/}"
    CYCLO_OUT=$(cd "$PROJ_DIR" && uv run cyclo -m "$MAX_C" "$FILE_DIR" 2>&1)
    if [[ $? -ne 0 ]]; then
      echo "$HOOK cyclo: complexity exceeds max $MAX_C in $REL_DIR — not auto-fixable, needs a refactor:" >&2
      echo "$CYCLO_OUT" >&2
      exit 2
    fi
    exit 0
    ;;
  go)
    echo "$(date -u +%FT%TZ) $HOOK go: $FILE" >> "$LOG"
    command -v go &>/dev/null || exit 0

    # Auto-fix formatting/imports first — goimports is a superset of gofmt.
    if command -v goimports &>/dev/null; then
      goimports -w "$FILE" >/dev/null 2>&1
    elif command -v gofmt &>/dev/null; then
      gofmt -w "$FILE" >/dev/null 2>&1
    fi

    # Walk up to the module root so we lint the whole module, not just one package
    MODULE_ROOT="$(dirname "$FILE")"
    while [[ "$MODULE_ROOT" != "/" && ! -f "$MODULE_ROOT/go.mod" ]]; do
      MODULE_ROOT="$(dirname "$MODULE_ROOT")"
    done
    # No go.mod found anywhere in the tree — skip linting
    [[ ! -f "$MODULE_ROOT/go.mod" ]] && exit 0

    # Per-package relative path used by the `go tool` and global paths.
    PKG_DIR="$(dirname "$FILE")"
    if [[ "$PKG_DIR" == "$MODULE_ROOT" ]]; then
      REL_PKG="."
    else
      REL_PKG="${PKG_DIR#"${MODULE_ROOT}"/}"
    fi

    # 1. Repo-pinned golangci-lint via go.mod `tool` directive (Go 1.24+).
    # Built with the local Go SDK, so no version-mismatch is possible. Fastest
    # per-edit path because we keep per-package scoping. --fix applies
    # whatever the enabled linters can auto-fix; whatever's left is reported.
    if (cd "$MODULE_ROOT" && go tool 2>/dev/null | grep -qE '(^|/)golangci-lint$'); then
      LINT_OUT=$(cd "$MODULE_ROOT" && go tool golangci-lint run --fix "./$REL_PKG" 2>&1)
      if [[ $? -ne 0 ]]; then
        echo "$HOOK go tool golangci-lint: auto-fixed what it could in ./$REL_PKG; issue(s) below need a manual call:" >&2
        echo "$LINT_OUT" >&2
        exit 2
      fi
      exit 0
    fi

    # 2. Repo-defined `task lint` — the repo decides what "lint" means and what
    # version of golangci-lint (or other linters) backs it. Scoping is whatever
    # the Taskfile chose; may be slower than per-package but matches CI exactly.
    # No --fix here: we don't control what the task runs, so just report.
    if command -v task &>/dev/null; then
      for tf in "$MODULE_ROOT/Taskfile.yml" "$MODULE_ROOT/Taskfile.yaml"; do
        if [[ -f "$tf" ]] && grep -qE '^[[:space:]]+lint:' "$tf"; then
          LINT_OUT=$(cd "$MODULE_ROOT" && task lint 2>&1)
          if [[ $? -ne 0 ]]; then
            echo "$HOOK task lint: issue(s) in $MODULE_ROOT (no auto-fix — repo-defined task):" >&2
            echo "$LINT_OUT" >&2
            exit 2
          fi
          exit 0
        fi
      done
    fi

    # 3. Globally-installed golangci-lint. Used when the repo has not opted into
    # a pinned version via go.mod tool directive or Taskfile.
    if command -v golangci-lint &>/dev/null; then
      # Fail if local golangci-lint version is incompatible with the module's Go
      # version. Do NOT fall back to go vet — it misses godot, goimports, gocyclo
      # and other linters that CI enforces. A false-clean local lint is worse
      # than a clear error. Not auto-fixable — it's a local tooling mismatch.
      LINT_BUILD_GO=$(golangci-lint --version 2>/dev/null | grep -oE 'built with go[0-9.]+' | grep -oE '[0-9]+\.[0-9]+([0-9.]+)?' | head -1)
      MOD_GO_VERSION=$(grep -m1 '^go ' "$MODULE_ROOT/go.mod" 2>/dev/null | awk '{print $2}')
      if [[ -n "$LINT_BUILD_GO" && -n "$MOD_GO_VERSION" ]]; then
        LINT_MINOR=$(echo "$LINT_BUILD_GO" | cut -d. -f2 | sed 's/[^0-9].*//')
        MOD_MINOR=$(echo "$MOD_GO_VERSION" | cut -d. -f2 | sed 's/[^0-9].*//')
        if [[ -n "$LINT_MINOR" && -n "$MOD_MINOR" && "$LINT_MINOR" -lt "$MOD_MINOR" ]]; then
          echo "$HOOK ERROR: golangci-lint was built with go${LINT_BUILD_GO} but go.mod declares go ${MOD_GO_VERSION}." >&2
          echo "golangci-lint will not run and lint issues will reach CI undetected. Not auto-fixable — pick one:" >&2
          echo "" >&2
          echo "  a) Pin per-repo (recommended for repos at different Go versions):" >&2
          echo "       cd $MODULE_ROOT && go get -tool github.com/golangci/golangci-lint/v2/cmd/golangci-lint@latest" >&2
          echo "       Commit the updated go.mod/go.sum; the hook will use 'go tool' next time." >&2
          echo "  b) Rebuild your global binary against the current Go SDK:" >&2
          echo "       go install github.com/golangci/golangci-lint/v2/cmd/golangci-lint@latest" >&2
          echo "  c) Add a 'lint' task to Taskfile.yml — the hook will run 'task lint' instead." >&2
          exit 2
        fi
      fi
      # Lint only the package containing the changed file, not the whole
      # module. Faster per-edit; run golangci-lint ./... manually for a full
      # module check. --fix applies whatever the enabled linters can rewrite.
      LINT_OUT=$(cd "$MODULE_ROOT" && golangci-lint run --fix "./$REL_PKG" 2>&1)
      if [[ $? -ne 0 ]]; then
        CONFIG_FILE=$(find "$MODULE_ROOT" -maxdepth 1 -name ".golangci*" | head -1)
        CONFIG_FILE="${CONFIG_FILE:-$MODULE_ROOT/.golangci.yml}"
        # Detect golangci-lint v2 config error: formatter listed under linters
        if echo "$LINT_OUT" | grep -qE "can't load config:.*is a formatter"; then
          BAD_NAME=$(echo "$LINT_OUT" | grep -oE "[a-z]+ is a formatter" | awk '{print $1}' | head -1)
          echo "$HOOK ERROR: '${BAD_NAME}' is a formatter in golangci-lint v2 — it cannot appear under linters.enable. Not auto-fixable:" >&2
          echo "Fix: move '${BAD_NAME}' from linters.enable to formatters.enable in ${CONFIG_FILE}" >&2
        # Detect golangci-lint v2 config error: linter name removed or renamed
        elif echo "$LINT_OUT" | grep -qE "unknown linters:"; then
          BAD_NAMES=$(echo "$LINT_OUT" | grep -oE "unknown linters: '[^']+'" | grep -oE "'[^']+'")
          echo "$HOOK ERROR: unknown linter(s) in ${CONFIG_FILE}: ${BAD_NAMES}. Not auto-fixable:" >&2
          echo "These were likely removed or renamed in golangci-lint v2. Run: golangci-lint help linters" >&2
        else
          echo "$HOOK golangci-lint: auto-fixed what it could in ./$REL_PKG; issue(s) below need a manual call:" >&2
          echo "$LINT_OUT" >&2
        fi
        exit 2
      fi
      exit 0
    fi

    echo "$HOOK WARNING: golangci-lint not found — install it to catch lint issues before CI:" >&2
    echo "  go install github.com/golangci/golangci-lint/v2/cmd/golangci-lint@latest" >&2
    VET_OUT=$(cd "$MODULE_ROOT" && go vet ./... 2>&1)
    if [[ $? -ne 0 ]]; then
      echo "$HOOK go vet: issue(s) found (best-effort fallback since golangci-lint is missing — not auto-fixable):" >&2
      echo "$VET_OUT" >&2
      exit 2
    fi
    exit 0
    ;;
  lua)
    echo "$(date -u +%FT%TZ) $HOOK lua: $FILE" >> "$LOG"
    if command -v stylua &>/dev/null; then
      STYLUA_OUT=$(stylua "$FILE" 2>&1)
      if [[ $? -ne 0 ]]; then
        echo "$HOOK stylua: could not auto-format $FILE — likely a syntax error:" >&2
        echo "$STYLUA_OUT" >&2
        exit 2
      fi
    fi
    if command -v luacheck &>/dev/null; then
      LUACHECK_OUT=$(luacheck --quiet "$FILE" 2>&1)
      if [[ $? -ne 0 ]]; then
        echo "$HOOK luacheck: issue(s) in $FILE (not auto-fixable — luacheck doesn't rewrite code):" >&2
        echo "$LUACHECK_OUT" >&2
        exit 2
      fi
    fi
    exit 0
    ;;
  feature)
    command -v gherkin-lint &>/dev/null || exit 0
    GL_OUT=$(gherkin-lint "$FILE" 2>&1)
    if [[ $? -ne 0 ]]; then
      echo "$HOOK gherkin-lint: issue(s) in $FILE (no auto-fix available):" >&2
      echo "$GL_OUT" >&2
      exit 2
    fi
    exit 0
    ;;
  toml)
    if [[ "$(basename "$FILE")" == "pyproject.toml" ]]; then
      command -v uv &>/dev/null || exit 0
      PROJ_DIR="$(dirname "$FILE")"
      [[ -f "$PROJ_DIR/uv.lock" ]] || exit 0
      if ! (cd "$PROJ_DIR" && uv lock --check) >/dev/null 2>&1; then
        # Auto-fixable: relock in place rather than just reporting drift.
        LOCK_OUT=$(cd "$PROJ_DIR" && uv lock 2>&1)
        if [[ $? -ne 0 ]]; then
          echo "$HOOK uv lock: pyproject.toml changed but relocking failed — needs a manual look:" >&2
          echo "$LOCK_OUT" >&2
          exit 2
        fi
      fi
    fi
    exit 0
    ;;
  yml|yaml)
    # Use actionlint for GitHub Actions workflows; yamllint for other YAML
    # files. Neither tool rewrites files, so there's nothing to auto-fix here.
    case "$FILE" in
      */.github/workflows/*)
        if command -v actionlint &>/dev/null; then
          AL_OUT=$(actionlint "$FILE" 2>&1)
          if [[ $? -ne 0 ]]; then
            echo "$HOOK actionlint: issue(s) in $FILE (no auto-fix available):" >&2
            echo "$AL_OUT" >&2
            exit 2
          fi
        fi
        ;;
      *)
        if command -v yamllint &>/dev/null; then
          YL_OUT=$(yamllint -d '{extends: relaxed, rules: {line-length: {max: 120}}}' "$FILE" 2>&1)
          if [[ $? -ne 0 ]]; then
            echo "$HOOK yamllint: issue(s) in $FILE (no auto-fix available):" >&2
            echo "$YL_OUT" >&2
            exit 2
          fi
        fi
        ;;
    esac
    exit 0
    ;;
  sh)
    echo "$(date -u +%FT%TZ) $HOOK sh: $FILE" >> "$LOG"
    command -v shellcheck &>/dev/null || exit 0
    SC_OUT=$(shellcheck "$FILE" 2>&1)
    if [[ $? -ne 0 ]]; then
      echo "$HOOK shellcheck: issue(s) in $FILE (no auto-fix available):" >&2
      echo "$SC_OUT" >&2
      exit 2
    fi
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
