# /code review (Level 3 resource)

Read this file when `SKILL.md` step 1 dispatches to `review` (or when `grill` invokes review under adversarial mode). Handles scope identification, per-language linting, endpoint/Tauri surface detection, language-reviewer delegation, deterministic script checks, report compilation, and the `-f` / `-fc` auto-fix modes.

**Flag semantics.** `-f` = fix all Must Fix and Should Fix once. `-fc` = fix, re-review, fix again, cap at 5 passes. `--rest` = REST-convention review only (no language pass).

## Workflow

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

**Detect Tauri surface.** A changed file defines Tauri backend/IPC surface if it matches:

- `#[tauri::command]`, `tauri::Builder`, `.invoke_handler(`, `.manage(`
- A `capabilities/*.json` file, or `tauri.conf.json`
- Frontend: `@tauri-apps/api` imports, `invoke(`, `listen(`, `emit(`

If matched, invoke `tauri-reviewer` on those files **in addition to** the language-specific agent.

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
