---
paths:
  - "**/*.lua"
---

# Lua & Neovim Conventions

> Core Lua idioms (scoping, modules, error-handling boundaries, table iteration, string building) live in `lua-idioms.md`. It loads alongside this file on any `.lua` source. This rule covers Neovim-specific patterns only.

## Neovim API

- Use `vim.keymap.set` for all keymaps — never `vim.api.nvim_set_keymap` or `nvim_buf_set_keymap`
- Use `vim.api.nvim_create_autocmd` and `vim.api.nvim_create_augroup` — never `vim.cmd("autocmd ...")`
- Use `vim.api.nvim_create_user_command` — never `vim.cmd("command! ...")`
- Use `vim.api.nvim_set_hl` for highlights — never `vim.cmd("highlight ...")`
- Use `vim.o`, `vim.bo[buf]`, `vim.wo[win]` for options — never `nvim_set_option`, `nvim_buf_set_option`, `nvim_win_set_option`
- Use `vim.lsp.get_clients()` — never `buf_get_clients()`
- Use `vim.fn.fn(args)` — never `vim.api.nvim_call_function`
- Use `vim.notify` with appropriate log levels for user-facing messages
- Use `vim.ui.input` and `vim.ui.select` for async user prompts
- Use `vim.ui.open(url_or_path)` (0.10+) to open URLs/files in the OS default handler
- Use `vim.hl.on_yank()` (0.11+) — never `vim.highlight.on_yank()` (deprecated)

## Keymaps

- Every `vim.keymap.set` must include a `desc` field for which-key discoverability
- Use function references as callbacks, not strings
- Use `{ buffer = bufnr }` for buffer-local keymaps
- Follow Vim grammar: `]` for next, `[` for prev, `g` prefix for variants
- Plugin keymaps use `<leader>` sub-groups; filetype keymaps use `<localleader>`

## Autocommands

- Every autocommand must belong to a group: `nvim_create_augroup("Name", { clear = true })`
- Always use `callback` (function), not `command` (string)
- Always include `desc`
- Use `buffer = bufnr` for buffer-scoped autocommands
- Use `once = true` for one-shot autocommands
- Debounce `CursorMoved` / `CursorMovedI` — prefer `CursorHold` when possible
- `BufEnter` callbacks must guard with early returns (filetype check, buffer validity)

## Idiomatic Lua

- Iterate directly over tables, never `for i = 1, #tbl` unless index arithmetic is needed
- Use `vim.iter()` (0.10+) for functional iteration over lists and tables — prefer it over
  `vim.tbl_map` / `vim.tbl_filter` when chaining operations:

  ```lua
  local names = vim.iter(items):filter(function(x) return x.active end):map(function(x) return x.name end):totable()
  ```
- Use `vim.tbl_deep_extend("force", defaults, opts)` for merging config tables
- Use `vim.tbl_contains` for membership checks
- Use `vim.inspect` for debug output, never string concatenation of tables
- Use `vim.validate` for input validation on public functions

## Error Handling

- Wrap fallible external calls in `pcall` / `xpcall`
- Check buffer and window validity before access (`nvim_buf_is_valid`, `nvim_win_is_valid`)
- Use `vim.notify(msg, vim.log.levels.ERROR)` for user-facing errors

## Async Processes (0.10+)

Use `vim.system()` for subprocess calls — it is the modern replacement for
`vim.fn.system()` / `vim.fn.jobstart()`:

```lua
-- Async (preferred)
vim.system({ 'git', 'log', '--oneline' }, { text = true }, function(obj)
  if obj.code == 0 then
    vim.schedule(function() process(obj.stdout) end)
  end
end)

-- Sync (only when result is needed immediately and blocking is acceptable)
local obj = vim.system({ 'git', 'rev-parse', 'HEAD' }, { text = true }):wait()
```

- Always pass an argument list, never a shell string — avoids shell injection
- Use `{ text = true }` to get stdout/stderr as strings instead of byte arrays
- Callbacks run on a non-main thread — wrap any vim API calls in `vim.schedule()`

## libuv

Use `vim.uv` (0.10+, stable alias) — `vim.loop` is deprecated:

```lua
-- Good
vim.uv.fs_stat(path, function(err, stat) ... end)

-- Deprecated
vim.loop.fs_stat(path, function(err, stat) ... end)
```

## Documentation

- Every module, public function, and non-trivial private function gets a `---` LuaLS doc comment describing what it does
- Use `---@param`, `---@return`, and `---@field` annotations for type information

## Code Quality

- Functions ≤ 40 lines, cyclomatic complexity ≤ 7
- Files ≤ 500 lines; split into focused modules when exceeded

## Performance

- Never block the main loop with synchronous I/O or network calls
- Wrap expensive callbacks in `vim.schedule()` or `vim.defer_fn()`
- Avoid unnecessary `require()` in callbacks — resolve at module scope

## Plugin Architecture

### Structure

Every plugin follows this layout:

```
plugin-name/
├── lua/plugin-name/
│   ├── init.lua        -- setup(opts), public API
│   ├── config.lua      -- defaults, schema, merge logic
│   ├── commands.lua    -- user command registration
│   ├── keymaps.lua     -- keymap registration
│   ├── autocmds.lua    -- autocommand setup
│   ├── highlights.lua  -- highlight group definitions
│   └── core/           -- domain logic (no vim.api imports)
├── plugin/plugin-name.lua  -- bootstrap user commands
├── doc/plugin-name.txt     -- vimdoc help file
└── tests/
    ├── minimal_init.lua
    └── plugin-name/
```

### Module Responsibilities

- **init.lua**: exposes `setup(opts)` and the public API — delegates everything else
- **config.lua**: defines defaults, merges user options with `vim.tbl_deep_extend`, validates with `vim.validate`
- **commands.lua / keymaps.lua / autocmds.lua**: registration only — call into `init` or `core` for behavior
- **core/**: pure business logic with no `vim.api` imports — testable without a Neovim runtime

### Design Rules

- One module per concern — split when a file exceeds 300 lines
- `setup()` must be idempotent: clear augroups, guard re-registration, merge config cleanly
- No global state — use module-local tables returned by `require`
- Dependency direction flows inward: UI/commands → init → core
- Keep `plugin/` minimal — only bootstrap user commands so lazy-loading works
- Use `vim.validate` on all public function parameters
- Expose configuration schema as the single source of truth for options

### Lifecycle

- `plugin/plugin-name.lua` registers commands that lazy-trigger `require("plugin-name").setup()`
- `setup(opts)` merges config, registers keymaps/autocmds/highlights, and initializes state
- Teardown (if needed) clears the augroup and deletes user commands

## Security

> See `owasp-top-10.md` for the general signal table and mandatory behaviors. This section covers Neovim/Lua-specific idioms only — patterns that exist because of the editor's API surface.

### Shell command execution — `vim.system()` over `vim.fn.system()`

`vim.fn.system()` and `io.popen()` invoke a shell, so any unescaped string is a shell injection vector. `vim.system()` (Neovim 0.10+) takes an argument list and does not invoke a shell:

```lua
-- Bad — shell injection risk
vim.fn.system("grep " .. user_input .. " " .. filepath)

-- Good — argument list via vim.system, no shell interpretation
vim.system({ "grep", "--", user_input, filepath }, { text = true }, function(obj)
  if obj.code == 0 then
    vim.schedule(function() handle(obj.stdout) end)
  end
end)
```

Prefer Neovim API operations (`nvim_buf_get_lines`, `nvim_exec_autocmds`) over shelling out whenever the API covers the task.

### Dynamic code execution — never on untrusted input

`vim.api.nvim_exec()`, `loadstring()`, and `load()` evaluate arbitrary Vimscript/Lua. Never pass strings sourced from a buffer, file, user prompt, or remote response. If dynamic dispatch is required, use a strict allowlist of permitted values:

```lua
local actions = { open = open_fn, close = close_fn, reload = reload_fn }
local fn = actions[user_choice]
if fn then fn() end
```

### File path safety — confine to a base directory

```lua
local function safe_path(base, user_path)
  local resolved = vim.fn.resolve(vim.fn.fnamemodify(user_path, ":p"))
  if resolved:sub(1, #base) ~= base then
    error("path traversal detected: " .. user_path)
  end
  return resolved
end
```

`vim.fn.fnamemodify(..., ":p")` produces an absolute path; `vim.fn.resolve` follows symlinks.

### Sensitive state — module-local, never `vim.g.*`

`vim.g.*` is process-global and readable by every other plugin in the same Neovim instance. Tokens, credentials, and session state must live in module-local Lua variables:

```lua
-- Bad — any other plugin can read this
vim.g.myplugin_api_token = token

-- Good — closed over by the module, not exposed
local _api_token = token
```

This is unique to the Neovim plugin model — there is no isolation between plugins beyond Lua scope.
