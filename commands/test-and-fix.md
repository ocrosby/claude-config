---
description: "Run the project's test suite and fix any failures. Building block for /feature, /code, and /debug workflows."
user-invocable: false
---

# Test and Fix

Use this command to run the project's test suite and fix failures in place until the suite is green or a hard limit is reached.

**This command does:** detect the test command, run it, diagnose failures, apply fixes, re-run until green.

**This command does NOT:** stage files, commit, push, open a PR, modify CI config, or `--no-verify`-equivalent skip failing tests.

## Steps

1. **Detect the test command** for the project. Apply the first match:

   | Marker present in cwd | Command |
   |---|---|
   | `go.mod` (single module) | `go test ./...` |
   | `go.work` (workspace) | `find . -name go.mod -not -path "*/vendor/*" \| while read f; do (cd "$(dirname "$f")" && go test ./...) \|\| exit 1; done` |
   | `pyproject.toml` or `setup.py` | `pytest` |
   | `package.json` with a `test` script | `npm test` |
   | `Makefile` with a `test` target | `make test` |
   | `Taskfile.yml` with a `test` task | `task test` |
   | None of the above | **Stop and ask the user** which command to run. Do not guess. |

2. **Run the suite.** Capture full stdout/stderr.

3. **If all tests pass:** report `✓ Tests pass — <N> tests, <duration>` and stop.

4. **If tests fail:** for each failing test:
   - Read the failure output (assertion, traceback, panic, mismatch).
   - Identify the root cause. **Diagnose the cause before changing anything** — never edit a test to make it pass unless the test itself is provably wrong.
   - Apply the minimal fix to the implementation (or the test, if the test is wrong).
   - Re-run the suite.

5. **Iteration cap.** Stop after **3 unsuccessful fix attempts on the same failing test**. Report the remaining failure with its diagnosis and the attempted fixes — do not loop further. The caller will escalate (typically to a language `*-debugger` agent).

6. **Verify.** Final state must be either:
   - All tests pass — report `✓ Tests pass` with the count and duration.
   - At least one test still failing after the iteration cap — report `✗ <test-name> remains failing after N attempts` with the diagnosis.

## Rules

- Never modify a test to make it pass without proving the test was wrong. The default assumption is the implementation is at fault.
- Never `--no-verify`, `-x` skip, `--ignore`, `skip()`, `t.Skip()`, or otherwise bypass a failing test. Bypassing is not a fix.
- Never proceed to the next failure without re-running the suite to confirm the previous fix worked and introduced no regressions.
- Never commit, stage, or push from this command — the calling skill controls git state.
- Never modify CI config (`.github/workflows/`, `Taskfile.yml`, `Makefile`) to skip tests. If CI itself is broken, stop and tell the caller.
