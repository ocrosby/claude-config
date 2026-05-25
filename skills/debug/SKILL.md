---
description: Systematically triages and diagnoses bugs across Go, Python, Neovim, and Gherkin. Detects language from cwd, emits a minimal-repro artifact, delegates to a language debugger agent. Override with /debug <language>.
argument-hint: "[language] [description]"
aliases: bug-triage
paths:
  - "**/*.go"
  - "**/*.py"
  - "**/*.lua"
  - "**/*.feature"
---

# Debug: Language-Aware Bug Triage

Use this skill when a reported bug needs reproduction, isolation, and root-cause analysis. The skill produces a **minimal-repro artifact** (an isolated failing test or script) as its output. That artifact is the input passed to the language debugger agent and can also be consumed by other skills (`/code review`, `/code migrate`) or by CI.

## Usage

```
/debug                              # auto-detect language from cwd
/debug go [description]             # force Go debugger
/debug py [description]             # force Python debugger
/debug nvim [description]           # force Neovim/Lua debugger
/debug gherkin [description]        # force Gherkin/BDD debugger
```

## Workflow

### 1. Detect the language

```bash
bash ~/.claude/scripts/detect_language.sh "${1-}"
```

The first token of `$ARGUMENTS` is an explicit override. Returns `go`, `py`, `nvim`, `gherkin`, `rest`, or `unknown`. `rest` is not supported — recommend `/code review --rest` instead. `unknown` → stop and ask. Otherwise drop the consumed override token from `$ARGUMENTS` and continue.

### 2. Reproduce

Capture exact reproduction inputs into a session note:

- Steps, inputs, environment (runtime version, OS, dependency versions)
- Where it reproduces: tests, locally, only in production, only in CI
- **Go:** confirm whether `-race` is required
- **Neovim:** confirm whether `nvim --clean` reproduces it

**If reproduction cannot be established: stop and ask the user for missing inputs.** Do not guess.

### 3. Isolate — write the minimal-repro artifact

Write the smallest possible test or script that reproduces the failure. **This file is the output of the skill.** Place it at one of these conventional paths so downstream consumers can find it:

| Language | Artifact path |
|---|---|
| Go | `<pkg>/repro_<short-name>_test.go` (a `Test_repro_*` function) |
| Python | `tests/repro/test_<short_name>.py` |
| Neovim / Lua | `minimal_repro.lua` at repo root |
| Gherkin | `features/repro/<short_name>.feature` + the minimal step defs to run it |

Strip away unrelated code until the failure isolates to a single function, module, or scenario. The artifact must:

- Fail when run on the current code
- Fail for the bug's reason, not a setup error
- Run in under 10 seconds (when possible)
- Have no dependency on external services unless the bug is in the integration itself

**Neovim minimal repro template** (used at `minimal_repro.lua`):

```lua
vim.env.LAZY_STDPATH = ".repro"
load(vim.fn.system("curl -s https://raw.githubusercontent.com/folke/lazy.nvim/main/bootstrap.lua"))()
require("lazy.minit").repro({
  spec = { { "plugin-author/plugin-name", opts = {} } },
})
```

Run with: `nvim -u minimal_repro.lua`

Run the artifact and confirm it fails. Capture the failure output verbatim — that output is part of the artifact contract.

### 4. Escalate to language specialist

Invoke the matching debugger agent. Pass it the artifact path and the captured failure output as input — not a prose description.

| Language | Agent |
|---|---|
| Go | `go-debugger` |
| Python | `py-debugger` |
| Neovim / Lua | `nvim-debugger` |
| Gherkin | `gherkin-debugger` |

The agent identifies root cause, gathers evidence, and proposes a fix.

**Quick reference — orient before invoking the agent.**

*Go:*

| Symptom | Likely Cause |
|---|---|
| `nil pointer dereference` | Unchecked error return, nil receiver, uninitialized field |
| `data race detected` | Concurrent access without synchronization |
| `deadlock` | Goroutines waiting on each other, unbuffered channel with no reader |
| `context deadline exceeded` | Slow dependency, missing timeout propagation |
| Goroutine leak | Missing context cancellation, channel never closed |

*Python:*

| Symptom | Likely Cause |
|---|---|
| `TypeError` / `AttributeError` | Wrong type passed, missing attribute, None propagation |
| Works locally, fails in CI | Environment difference — missing env var, Python version |
| 422 from FastAPI | Pydantic validation failure — check request body against model |
| 500 from FastAPI | Unhandled exception in route — check logs for traceback |

*Neovim (Lua):*

| Symptom | Likely Cause |
|---|---|
| `E5108: Error executing lua` | Lua runtime error — read the stack trace |
| Broke after Neovim update | Deprecated API removed — check `:h deprecated` |
| Slow / freezes | Synchronous operation on main loop or unthrottled `CursorMoved` |

*Gherkin:*

| Symptom | Likely Cause |
|---|---|
| Step undefined | Missing step definition, typo in step text, wrong import |
| Passes alone, fails in suite | Scenario coupling — shared state leaking between scenarios |
| Passes locally, fails in CI | Environment difference — missing service, timing, browser version |

### 5. Verify the fix

Apply the agent's proposed fix and re-run the **same minimal-repro artifact** from step 3. The artifact is the contract: if it now passes, the bug is fixed.

- Confirm the artifact passes.
- Run the full test suite to confirm no regressions:
  - *Go:* `go test -race ./...`
  - *Python:* `pytest`
  - *Neovim:* full suite + the minimal repro config
  - *Gherkin:* the repro scenario in isolation, then the full suite
- Remove any debug logging added during diagnosis.

### 6. Decide the artifact's fate

The minimal-repro artifact is now a regression test that proves the fix. Choose one:

- **Keep it as a regression test** — rename from `repro_*` / `tests/repro/*` to a conventional name in the matching test directory. This is the default.
- **Delete it** — only if the behavior is already covered by an existing higher-level test and the artifact adds no signal.

**If neither option applies: stop and ask the user.** Never leave an orphaned `repro_*` file in the tree.

## Rules

- The minimal-repro artifact is the contract for both diagnosis and verification. Do not skip producing it.
- Pass the artifact path (not prose) to the debugger agent.
- Never delete the artifact silently — either keep it (default) or delete it consciously after the fix has been covered elsewhere.
