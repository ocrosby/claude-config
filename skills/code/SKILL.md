---
description: Code quality dispatcher — review (with --grill / --rest), refactor, migrate, techdebt, simplify. The first word of $ARGUMENTS selects the subcommand. techdebt deletes code; grill enforces strictest verdict.
argument-hint: "<subcommand> [arguments]"
aliases: code-review, rest-review, refactor, migrate, techdebt, simplify, grill
paths:
  - "**/*.go"
  - "**/*.py"
  - "**/*.lua"
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.feature"
---

# Code: Quality and Transformation Dispatcher

Use this skill for any audit, transformation, or cleanup of existing code: structured review, REST-convention check, refactor, deprecation migration, dead-code sweep, or adversarial pre-ship review.

Delegates to language-specialist agents (`go-reviewer`, `py-reviewer`, `nvim-reviewer`, `gherkin-reviewer`, `rest-reviewer`) and to shared deterministic scripts in `~/.claude/scripts/`.

## Usage

```
/code                                    # show this help
/code review [paths|refs] [-f|-fc]       # structured language review (auto-routes REST)
/code review --rest [paths]              # REST-convention review only (no language pass)
/code grill                              # /code review under strictest verdict, looped to SHIP IT
/code refactor [file]                    # structural improvement (Go/Python/Neovim/Lua)
/code migrate [language] [path]          # replace deprecated patterns
/code techdebt                           # end-of-session sweep: duplicates + dead code
/code simplify                           # delegate to the external /simplify skill
```

**Flag semantics for `review`:**

- `-f` — fix all Must Fix and Should Fix findings once, then stop
- `-fc` — fix, re-review, fix again, repeat until clean (implies `-f`); cap at 5 passes
- `--rest` — REST-convention review only (skip language reviewer pass)

## Workflow

### 1. Parse the subcommand

Split `$ARGUMENTS` on the first space. The first word is the subcommand.

- Empty or `help` → print **Usage** and stop.
- Not one of `review`, `grill`, `refactor`, `migrate`, `techdebt`, `simplify` → print **Usage** and stop.
- Dispatch to the matching step.

### 2. Dispatch — `review`

Replicates the prior `/code-review` skill.

**Identify scope.** If no path/ref argument: `git diff --name-only HEAD`. If an argument: use it as the file list or as a git ref. Group files by language.

**Run linters per file.** Lint failures are **Must Fix** — do not proceed without reporting them.

For Go files, resolve the module root first (don't run from the changed file's directory — that misses sibling packages):

```bash
MODULE_ROOT=$(dirname <file>); while [ ! -f "$MODULE_ROOT/go.mod" ] && [ "$MODULE_ROOT" != "/" ]; do MODULE_ROOT=$(dirname $MODULE_ROOT); done
```

| Extension | Linter command (run from module/project root) |
|---|---|
| `.lua` | Run `stylua --check <file>` — if the binary is absent, skip and note the gap in the Lint section. Then run `luacheck --quiet <file>` — if `.luacheckrc` is absent, skip and note. |
| `.py` | `ruff check --quiet <file> && ruff format --check --quiet <file>` |
| `.go` | `cd <module-root> && golangci-lint run ./... && go test -race ./...` |
| `.feature` | Run `gherkin-lint <file>` — if the binary is absent, skip and note the gap in the Lint section. |

If `golangci-lint` is unavailable, fall back to `go vet ./...` but note the gap. Report lint failures under a **Lint** section before the semantic review. Do not proceed to semantic review until lint failures are resolved.

**Detect REST endpoints.** A changed file defines HTTP endpoints if it matches:

- Route registrations: `router.GET`, `router.POST`, `app.get(`, `@app.route`, `http.HandleFunc`, `mux.Handle`, `router.Handle`, `APIRouter()`, `@router.get`, `@router.post`, `r.GET`, `r.POST`, `r.PUT`, `r.PATCH`, `r.DELETE`
- Path under `**/routes/**`, `**/handlers/**`, `**/controllers/**`, `**/views/**`, `**/api/**`

If matched, invoke `rest-reviewer` on those files **in addition to** the language-specific agent.

**Delegate to language-reviewer agents.**

| Extension / Path | Reviewer Agent |
|---|---|
| `.go` | `go-reviewer` |
| `.py` | `py-reviewer` |
| `.lua` | `nvim-reviewer` |
| `.feature` | `gherkin-reviewer` |
| `skills/*/SKILL.md` | `skill-reviewer` |
| Other | Review inline: general quality, OWASP Top 10, readability |

**Run CI-config deterministic checks.** For `action.yml` / `action.yaml`:

```bash
python3 ~/.claude/scripts/check_action_yml.py <file>... [--severity must|should|consider] [--json]
```

For `.github/workflows/*.yml`:

```bash
python3 ~/.claude/scripts/check_workflows.py <file-or-dir>... [--repo-root <path>] [--severity must|should|consider] [--json]
```

Merge script findings into the per-file report alongside the language-reviewer output. Scripts emit `file:line — rule_id — message` consistent with `check_rest.py` / `check_docs.py`.

**REST review path (`--rest` flag, no language pass).** Identify HTTP endpoint files via the same patterns as above, or use the `$ARGUMENTS` path. Run the REST deterministic pre-check:

```bash
python3 ~/.claude/scripts/check_rest.py <file-or-glob>... [--severity must|should|consider] [--json]
```

Rules the script applies: `uri-has-verb` (Must), `uri-uppercase` / `uri-snake-case` / `uri-trailing-slash` (Should/Consider), `get-with-body` (Must), `post-no-201` / `post-no-location` (Should), `delete-with-body` (Should), `405-no-allow` (Should), `get-no-cache-headers` (Consider).

Then invoke `rest-reviewer` with the same files, passing the script findings as context so the agent focuses on auth, pagination, error envelope, HATEOAS, versioning, bulk-operation design.

**Compile the report.** Aggregate findings per file using the shape from `rules/findings-format.md`:

```
## Review: <filename>

### Must Fix
- `path/to/file.ext:42` — <what>. **Why:** <why>. **Fix:** <fix>.

### Should Fix
- `path/to/file.ext:88` — <what>. **Why:** <why>. **Fix:** <fix>.

### Consider
- `path/to/file.ext:120` — <what>. **Why:** <why>.
```

Omit a bucket entirely when it has no entries — do not print an empty `### Must Fix` header. If a file has no issues at all: `✓ <filename> — no issues found`. End with a one-paragraph summary: overall verdict, most important issue, cross-cutting patterns.

**Auto-fix (`-f` flag).** **If `-f` was not passed: stop after the report.**

Apply every Must Fix and Should Fix finding (not Consider). For each: Edit or Write directly, no confirmation — the `-f` flag is the authorization. Order: all Must Fix → all Should Fix. After fixes, re-run the relevant linters from the linter step. Print:

```
## Fixes Applied
- <filename>:<line> — <what was fixed>

Linters: ✓ clean  (or list any remaining failures)
```

Findings that cannot be automatically fixed (architectural change required, missing context, external dep) → **Needs Manual Fix**.

**Continuous loop (`-fc` flag).** **If `-fc` was not passed: stop.**

After auto-fix, re-run the full review on the same scope. If Must Fix or Should Fix findings remain, fix and loop again. Stop when:

- Zero Must Fix and Should Fix → print `✓ Clean — no further findings`
- 5 iterations reached → stop and mark remaining as **Needs Manual Fix**

Print `--- Pass 2 ---`, `--- Pass 3 ---` headers. Consider items never trigger another loop pass. At exit, print a **Session Summary** with all remaining findings + all Consider items collected across passes (de-duplicated).

### 3. Dispatch — `grill`

Adversarial review. Same pipeline as `review` but the reviewer agents are instructed to apply the strictest interpretation and the verdict scale is binary.

1. Invoke the `review` workflow above with this explicit instruction passed to each reviewer agent: **"Adversarial mode — apply the strictest interpretation. Default to NEEDS WORK unless every issue is conclusively resolved."**
2. Override the summary verdict with this scale:
   - **SHIP IT** — zero Must Fix, zero Should Fix, zero Consider items
   - **NEEDS WORK** — any Should Fix or Consider items remain
   - **BLOCK** — any Must Fix items, OR new/changed behavior missing tests, OR breaking change to a public API
3. On NEEDS WORK or BLOCK, list every issue with file, line, and the specific fix. **Quote the reviewer agent verbatim — do not paraphrase.**
4. After fixes are applied, re-run from step 1. Loop a maximum of 5 passes. **On pass 5, if issues remain: mark them "Needs Manual Fix" and stop — do not proceed to another loop iteration.**
5. Only return SHIP IT after a clean pass with zero remaining items.

**Rules for `grill`.** Never lower the verdict to accommodate effort already spent. Never collapse Must Fix into Should Fix. Breaking change to a public API is always BLOCK until justified in commit message or restored. Missing tests for new/changed behavior is always BLOCK.

### 4. Dispatch — `refactor`

Replicates the prior `/refactor` skill. Structural improvement without behavior change. Distinct from `migrate` (which replaces deprecated patterns).

1. **Understand before changing.** Read target file(s). Answer: what is this responsible for? Why was it written this way (`git log --follow -p <file>`)? What constraints drove the current design? Do not refactor what you do not yet understand.

2. **Identify the smell** by language:

   *Go:* god struct/package, layering violation, interface too wide (>5 methods, callers use 2-3), concrete dependency, implicit coupling, duplicated logic (Rule of Three), shallow abstraction.

   *Python:* god module/class, layering violation (domain imports FastAPI/SQLAlchemy/requests), concrete dependency (not Protocol), circular imports, duplicated logic, mutable shared state, fat route handler.

   *Neovim/Lua:* god `init.lua`, global state pollution, vimscript leakage (`vim.cmd` where Lua API exists), missing idempotency, unchecked API calls (no `pcall`), hardcoded buffer numbers, hot-path `require()`.

3. **Plan and confirm.** State what changes, what does not change (behavior, public API), what tests need writing first. Get user confirmation before proceeding.

4. **Write characterization tests first (mandatory).** Do not touch production code until the current behavior is pinned by tests. Use `t.Run`/`pytest`/plenary `describe` to capture *current* behavior, not ideal.

5. **Refactor in small steps.** Apply one change at a time, run tests after each.

   *Go:* extract a package (`go test ./... && go vet ./...`), narrow an interface to its consumer (`UserStore`, `SessionStore` instead of one big `Store`), fix layering by moving logic into the domain service and injecting interfaces via constructor.

   *Python:* extract a module (`python -c "import mypackage" && pytest`), replace concrete dep with `Protocol`, fat-route-handler fix (body ≤5 lines — delegate to service).

   *Neovim/Lua:* split god `init.lua` into `config.lua` / `commands.lua` / `keymaps.lua` / `autocmds.lua` / `core.lua` (no `vim.api` imports in core); fix global state with module-local `local _config = {}` and a `vim.deepcopy` accessor; make `setup()` idempotent with `_initialized` flag and `{ clear = true }` augroup.

6. **Verify.**

   ```bash
   # Go
   go test ./... -race && go vet ./... && golangci-lint run

   # Python
   pytest && ruff check . && ruff format --check .
   # Run `mypy .` only if mypy is configured (mypy.ini, [tool.mypy] in pyproject.toml, or .mypy.ini present)

   # Neovim/Lua
   nvim --headless -u tests/minimal_init.lua \
     -c "PlenaryBustedDirectory tests/ {minimal_init = 'tests/minimal_init.lua'}"
   stylua --check lua/ && luacheck lua/   # luacheck if configured
   ```

   Confirm public API is unchanged, or explicitly note what changed and why.

**Refactor checklist.** No behavior changes; tests written before refactoring; all tests pass after; Go layers respected and interfaces at consumer side; Python domain has no framework/I/O imports; Neovim `setup()` idempotent and no global state exported; no circular imports/requires; no new mutable module-level state.

### 5. Dispatch — `migrate`

Replicates the prior `/migrate` skill. Replaces deprecated APIs/idioms with current equivalents. Behavior must be identical before and after.

**Scope.** File-level when invoked mid-task on a specific file (replace patterns in that file only, verify, do not expand without asking). Codebase-level when invoked standalone.

**Workflow (codebase-level).**

1. **Scan.**
   ```bash
   python3 ~/.claude/scripts/migrate_scan.py [--language go|py|lua|gherkin|all] [--root <path>]
   ```
   The script walks the target (excluding `.git`, `node_modules`, `.venv`, `vendor`, `__pycache__`, build dirs), matches each pattern's regex against extension-matching files, emits a Markdown table per language: `file | line | category | deprecated → modern`.

   **If the script reports no findings: stop and report "no deprecated patterns found".**

2. **Plan replacements per finding.**
   - *Mechanical* (e.g. `ioutil.ReadAll` → `io.ReadAll`) — apply directly with Edit.
   - *Context-aware* (e.g. `unittest.TestCase` → pytest functions) — plan the rewrite per file.
   - *Not actually deprecated in context* (generated file, Windows-specific branch) — skip and note why.

3. **Apply replacements, verify per language:**

   | Language | Verify command |
   |---|---|
   | Go | `go test ./... -race` |
   | Python | `pytest && ruff check .` |
   | Neovim | `:checkhealth` in nvim |
   | Gherkin | Run all scenarios in isolation, then the full suite |

   **If any verify fails: stop and revert that language's changes.** Do not proceed to the next language until tests pass.

4. **Re-scan.** Remaining findings must be either (a) intentionally left (noted in commit body) or (b) zero. If new findings appear that weren't in the original report, you introduced new deprecated patterns — investigate before declaring done.

**Adding new deprecation patterns:** edit `PATTERNS` at the top of `~/.claude/scripts/migrate_scan.py`. Each entry: `{category, regex, deprecated, modern}`. No SKILL.md edit needed.

**Rules for `migrate`.** Behavior must be identical — never combine migration with a behavior change. Always run the language's verify command after replacements. Skip findings in vendored/generated/third-party code — note them in the report.

### 6. Dispatch — `techdebt`

Replicates the prior `/techdebt` skill. End-of-session sweep for duplicated and dead code.

1. **Scan** the codebase for:
   - Duplicated code blocks — three or more similar lines appearing in two or more places
   - Dead exports/functions/types/variables — declared but with no callers in the repo or its public API

2. **Group and present findings** by file with line numbers.

3. **Ask before fixing.** Do not begin removing code without explicit user approval per item or per batch.

4. **Apply approved fixes one at a time.** For each: make the change, then run the project's test suite — `go test ./...` for Go, `pytest` for Python, `make test` if a Makefile defines a `test` target. **If none of those apply: stop and ask the user which command to run before continuing.** **If tests fail: stop and report the regression. Do not proceed.**

5. **Commit** via `/conventional-commit-msg`. Use `chore` or `refactor` — never `feat`.

6. **Verify.** Re-run the full test suite once more after the commit. Confirm green before reporting done.

**Rules for `techdebt`.** Never delete code whose removal is not covered by tests — write a test that exercises a known caller path first if needed. Never bundle cleanup into a feature commit. Three lines that share an obvious idiom (`if err != nil { return err }`) are not duplication.

### 7. Dispatch — `simplify`

Delegate to the external `/simplify` skill (which reviews changed code for reuse, quality, and efficiency, then fixes the issues found). Invoke it directly with whatever follows `simplify` in `$ARGUMENTS`. Do not re-implement its logic here.

### 8. Final verification step

Each dispatch block above ends with its own verification gate. Confirm the gate fired before exiting:

- `review` / `grill` → report compiled, summary printed
- `refactor` → tests pass and the verify command for the language ran clean
- `migrate` → re-scan shows zero or intentionally-kept findings
- `techdebt` → final test run after commit is green

If any verification was skipped, re-run it before declaring the subcommand done.

## Rules (apply across all subcommands)

- `rules/findings-format.md` is authoritative for the **Must Fix / Should Fix / Consider** buckets and the per-finding shape. Do not restate the bucket definitions inline.
- Report issues with file and line number when possible (`file:line — rule_id — message` for script-derived findings).
- Distinguish blocking issues from suggestions — not everything is a Must Fix.
- Without `-f`/`-fc`: describe what to change and why; do not modify code.
- With `-f` or `-fc`: apply Must Fix and Should Fix changes directly; never silently skip a finding (mark as Needs Manual Fix).
- Refactor and migrate must never combine with a behavior change. Techdebt must never bundle into a feature commit.
- Lint failures always block semantic review until resolved.
