---
description: Feature development dispatcher — auto-detects language (go, py, nvim, gherkin, rest) from cwd and routes to the matching layered/TDD-driven workflow. Override with /feature <language> [...].
argument-hint: "[language] [feature description]"
aliases: go-feat, py-feat, nvim-feat, gherkin-feat, rest-implement, go-feature, py-feature, nvim-feature, gherkin-feature
paths:
  - "**/*.go"
  - "**/*.py"
  - "**/*.lua"
  - "**/*.feature"
---

# Feature: Language-Aware Feature Development

Use this skill when implementing a new feature. The dispatcher detects the language from the working directory and applies the matching architectural conventions. TDD enforcement (red-green-refactor with observable failure output) comes from the always-on `rules/tdd.md`. Final review delegates to `/code review -fc`.

## Usage

```
/feature                            # auto-detect language from cwd
/feature go                         # force Go workflow
/feature py                         # force Python workflow
/feature nvim                       # force Neovim/Lua workflow
/feature gherkin                    # force Gherkin/BDD workflow
/feature rest <operationId>         # implement a REST handler against an existing OpenAPI spec
/feature <lang> <description>       # explicit language + feature description
```

## Workflow

### 1. Detect the language

Run the shared detector:

```bash
bash ~/.claude/scripts/detect_language.sh "${1-}"
```

The first token of `$ARGUMENTS` is treated as an explicit override. The script returns one of: `go`, `py`, `nvim`, `gherkin`, `rest`, `unknown`.

- If the detector returns `unknown`: stop and ask the user which language workflow to apply.
- Otherwise drop the consumed override token from `$ARGUMENTS` and dispatch to the matching step.

### 2. Dispatch — `go`

Replicates the prior `/go-feat` skill.

1. **Understand.** Clarify the feature from the user's perspective. Identify which layer it belongs to: domain / port / adapter / cmd. Determine if it needs HTTP endpoints, CLI commands, or background workers.

   Run `/architect` first **only when** the feature introduces a new package boundary, a new top-level abstraction, or crosses layer boundaries non-obviously. For incremental additions, skip.

2. **Design the interface.** Public API types and function signatures. Define interfaces at the consumer side — small and focused. Configure via struct fields or functional options. Accept `context.Context` as the first parameter on all I/O methods.

3. **Implement via TDD.** `rules/tdd.md` enforces red-green-refactor. Apply in this order:
   1. Domain types and service methods first — pure logic, no I/O.
   2. Port interfaces for new external dependencies.
   3. Adapters: HTTP handlers, DB repositories, API clients.
   4. Wire dependencies in `cmd/` via constructor injection.

   Do not write production code before a failing test exists for that behavior.

4. **Apply Go structure.** One package per concern — split at 500 lines. Domain logic has no external imports beyond stdlib. Adapters are thin: parse request, delegate, write response. HTTP uses stdlib `net/http` or a thin router.

5. **Apply Go error handling.** Wrap with context: `fmt.Errorf("creating user: %w", err)`. Define sentinel errors for expected conditions: `var ErrNotFound = errors.New("not found")`. Return early on error. Use custom error types when callers need to inspect.

6. **Apply Go concurrency (when needed).** Use `errgroup` for parallel work with error propagation. Pass `context.Context` for cancellation. Channels have a clear owner — one goroutine creates, one closes. Every goroutine must have a termination path.

7. **Review.** Invoke `/code review -fc` on the changed files. Do not re-implement the review checklist — `go-reviewer` covers error wrapping, interface placement, dependency injection, context propagation, global state, exported doc comments.

### 3. Dispatch — `py`

Replicates the prior `/py-feat` skill.

1. **Understand.** Identify which layer: domain / port / adapter / application. Determine if it needs new API endpoints, CLI commands, MCP tools, or background tasks.

   Run `/architect` first **only when** the feature introduces a new module boundary, a new port/adapter pair, or significant domain abstractions.

2. **Design the interface.** Public functions/classes with full type hints. Define configuration with `pydantic.Settings` if new config is needed. Define request/response models with Pydantic `BaseModel`.

3. **Implement via TDD.** Apply red-green-refactor in this order:
   1. Domain models and services first — pure Python, no framework imports.
   2. Ports (`Protocol` classes) for new external dependencies.
   3. Adapters: FastAPI routes, DB repositories, API clients.
   4. Wire dependencies via injection (`Depends()` in FastAPI, constructor injection elsewhere).

4. **Apply Python structure.** One module per concern — split at 300 lines. Domain has no I/O, no framework imports. Adapters are thin: validate input, delegate, return result. FastAPI uses `APIRouter`, one router per domain area. FastMCP tools use `@mcp.tool()` with type hints and docstrings for schema derivation.

5. **FastAPI specifics (when applicable).** Pydantic `BaseModel` for request/response. `Depends()` for shared logic (auth, DB sessions, config). `lifespan` context manager for startup/shutdown, not `on_event`. Explicit status codes (`status_code=201` for creation). `HTTPException` for error responses with appropriate status codes.

6. **FastMCP specifics (when applicable).** Declare tools with `@mcp.tool()`, resources with `@mcp.resource()`. Tool functions derive schema from type hints and docstrings. Keep tool functions thin: validate, delegate, return. Use `Context` for logging and progress reporting.

7. **Review.** Invoke `/code review -fc`. `py-reviewer` covers type hints, domain purity, dependency injection, Pydantic boundaries, global state.

### 4. Dispatch — `nvim`

Replicates the prior `/nvim-feat` skill.

1. **Understand.** Identify which Neovim APIs are needed (`vim.api`, `vim.fn`, `vim.keymap`, `vim.treesitter`, etc.). Determine if the feature needs autocommands, user commands, keymaps, highlights.

   Run `/architect` first **only when** the feature introduces a new module, a new public API surface, or significant structural decisions.

2. **Design the interface.** Public API functions. Configuration via `setup(opts)` or `config` pattern with sensible defaults. Keep command/keymap surface area minimal.

3. **Implement with tests first.** For any feature with observable behavior, `rules/tdd.md` requires a failing test first. Use `plenary.busted` or `mini.test` per `rules/nvim-testing.md`.

   For purely declarative features (a new keymap binding, a new autocommand group with no logic), TDD is not required — note the exception in the commit message.

4. **Apply Neovim API conventions.** Use `vim.api.nvim_*` over Vimscript. `vim.keymap.set` over `vim.api.nvim_set_keymap`. `vim.api.nvim_create_autocmd` and `vim.api.nvim_create_augroup` for autocommands. `vim.api.nvim_create_user_command` for user commands. `vim.notify` for user-facing messages. Namespace all autocommand groups. Make `setup()` idempotent — guard against re-sourcing.

5. **Apply structure.** One module per concern: separate core, UI, commands, config. Entry point exposes `setup(opts)` that merges user config with defaults via `vim.tbl_deep_extend`. Keep buffer-local and window-local state explicit. Use `vim.validate` for input validation on public functions.

6. **Keymap and autocommand conventions.**
   - Keymaps: always `vim.keymap.set` with a `desc` field. Use `<leader>` sub-groups. Set only in the modes that make sense. `buffer` option for buffer-local. Follow Vim grammar (`]` next, `[` prev, `g` prefix for variants).
   - Autocommands: every one belongs to a group created with `nvim_create_augroup("Name", { clear = true })`. Always `callback` (function), not `command` (string). Always include `desc`. `buffer` for buffer-local, `pattern` for global. `once = true` for one-shot. Debounce `CursorMoved`/`CursorMovedI` — prefer `CursorHold` when possible.

7. **Review.** Invoke `/code review -fc`. `nvim-reviewer` covers deprecated API calls, keymap `desc` presence, autocommand group cleanup, user command flags, `setup()` idempotency, global state pollution.

### 5. Dispatch — `gherkin`

Replicates the prior `/gherkin-feat` skill.

1. **Understand the behavior.** Clarify the capability from the user's perspective. Identify actors (who triggers it?) and outcomes (what is observable on success? on failure?). Gather concrete examples from stakeholders — examples become scenarios.

   Run `/architect` first **only when** the feature spans multiple domain areas or requires designing the full suite structure.

2. **Write the feature file.** Start with user story (`As a / I want / So that`). Happy path scenario first. Add edge cases and error scenarios. `Background` for shared preconditions. `Scenario Outline` for data-driven variations.

3. **Design steps.** Declarative — describe intent, not mechanics. Parameterize reusable values in quotes or angle brackets. One `When` per scenario — one action under test. `Then` steps assert observable outcomes only.

4. **Implement step definitions.** Thin: parse parameters, delegate, assert. Extract interaction logic into page objects or API client helpers. Share state via the World/context object. Reuse existing step definitions — check common steps first.

5. **Wire up support.** `Before`/`After` hooks for scenario isolation (reset state, clean data). Environment config (base URLs, credentials, browser setup). Custom parameter types for domain concepts.

6. **Verify parsing and the happy path.** Run the framework. Confirm: feature file parses without syntax errors, step definitions discovered (no undefined-step warnings), happy path passes end-to-end. **If any of these fail: stop and fix before review.**

7. **Review.** Invoke `/code review -fc` on the feature files and step definitions. `gherkin-reviewer` covers declarative vs imperative steps, scenario isolation, state leakage, Background overuse.

### 6. Dispatch — `rest` (handler-against-spec)

Replicates the prior `/rest-implement` skill.

**Precondition:** the OpenAPI spec entry must already exist. **If it does not: stop and recommend `/architect spec` first.** Never implement a handler ahead of the spec.

1. **Locate the spec entry.** Read the OpenAPI spec file. Confirm the `operationId` (or path+method) named by the user exists. Extract HTTP method and path, parameters, request body schema, response shape per status code.

   If the entry cannot be found: stop and ask the user to confirm the operationId or run `/architect spec`.

2. **Define request and response types** language-natively to match the spec exactly.

   *Go:*
   ```go
   type ListUserOrdersParams struct {
       UserID string
       Status string
   }
   type OrderList struct {
       Items  []Order `json:"items"`
       Total  int     `json:"total"`
       Cursor string  `json:"cursor,omitempty"`
   }
   ```

   *Python (FastAPI + Pydantic):*
   ```python
   class OrderListResponse(BaseModel):
       items: list[Order]
       total: int
       cursor: str | None = None
   ```

   If the project uses code generation from the spec (`oapi-codegen`, `datamodel-code-generator`), regenerate and use generated types instead of hand-writing.

3. **Implement domain logic via TDD (handler last).** Work domain-outward:
   1. Domain/service layer first — pure function, no HTTP concern. Failing test first, then minimal pass, then refactor.
   2. Port interface — define the interface the handler will call (if a new external dependency is needed).
   3. HTTP handler last — thin: parse request → validate (400 for malformed syntax, 422 for semantically invalid values) → call the domain method → map result to the response shape and status code → write the response.

   The handler must contain no business logic. Never write the handler before the domain method exists.

4. **Confirm spec conformance.** For every declared status code, the handler must produce it under the matching condition. Cross-check: POST creating a resource → `201` + `Location` header; DELETE no body → `204`; 401 vs 403 not conflated; validation failures map to 422 not 400; breaking change served from a new version prefix path.

   If the handler emits a status code not in the spec, the spec is wrong — go back to `/architect spec` and update it. Spec and handler must stay synchronized.

5. **Apply caching headers (GETs).** GET responses must set `Cache-Control` or `ETag` where appropriate. If cacheable per the project's policy and these headers are absent, add them.

6. **Review.** Invoke `/code review -fc`. Both the language reviewer agent and `rest-reviewer` (auto-detected on route registrations) run. `rest-reviewer` covers URI naming, HTTP method semantics, status code correctness, statelessness, caching headers.

### 7. Final verification step

Every dispatch ends with `/code review -fc`. Before declaring done:

- The review loop has exited clean (`✓ Clean — no further findings`) or has explicitly stopped at the 5-iteration cap with remaining findings recorded as **Needs Manual Fix**.
- Any **Needs Manual Fix** items have been addressed by the user.
- For `rest`: the handler's status codes match the spec one-for-one.
- For `gherkin`: the happy-path scenario passes.

If any of the above is incomplete, do not report the feature as done.

## Rules (apply across all languages)

- The always-on `rules/tdd.md` is authoritative for the red-green-refactor cycle. Do not bypass it.
- The skill does not own the review checklist — the language-specialist reviewer agents (`go-reviewer`, `py-reviewer`, `nvim-reviewer`, `gherkin-reviewer`, `rest-reviewer`) do, via `/code review -fc`.
- `/architect` is invoked only for non-incremental work (new boundary, new abstraction, new layer crossing). For incremental additions, skip it.
- For `rest`: a spec entry must precede the handler. Never implement ahead of the spec.
