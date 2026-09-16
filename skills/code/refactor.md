# /code refactor (Level 3 resource)

Read this file when `SKILL.md` step 1 dispatches to `refactor`. Structural improvement without behavior change. Distinct from `migrate` (which replaces deprecated patterns).

## Workflow

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
