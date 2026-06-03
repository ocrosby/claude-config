---
description: Conventions for writing redistributable Neovim plugins in Lua per Neovim's official guide (https://neovim.io/doc/user/lua-plugin/) — file structure, lazy loading, setup() patterns, guard variables, health checks, LuaCATS annotations, vimdoc, and SemVer/deprecation. Use when authoring a standalone plugin, or when a yoda.nvim module is being extracted into one.
when_to_use: User is creating, modifying, or reviewing a redistributable Neovim plugin — including mentions of plugin structure, ftplugin, health.lua, :checkhealth, setup() functions, `<Plug>` mappings, LuaCATS annotations, vimdoc, panvimdoc. Trigger when working in a directory that looks like a plugin (top-level `plugin/`, `lua/<name>/`, `ftplugin/`, `doc/<name>.txt`). NOT for configuring your own Neovim — use `/nvim-config` for native configs or `/add-plugin` for yoda.nvim's lazy.nvim adds.
---

# Writing Neovim Plugins

Reference: https://neovim.io/doc/user/lua-plugin/.

Source: adapted from [fredrikaverpil/dotfiles](https://github.com/fredrikaverpil/dotfiles/blob/main/stow/shared/.claude/skills/nvim-plugin/SKILL.md).

## Context for Omar

You haven't published a standalone Neovim plugin yet (no `topic:neovim` repos under `ocrosby` or `jedi-knights` as of writing). The most likely use cases:

- A `lua/yoda/<module>` extracted from yoda.nvim into its own repo (e.g. one of the dependency-injection or logging modules under that tree)
- A net-new plugin to scratch a specific itch

If you're configuring your own Neovim setup (not authoring a redistributable plugin), this isn't the right skill:

- yoda.nvim / lazy.nvim adds → use **`/add-plugin`**
- Native vim.pack config work → use **`/nvim-config`**
- Driving a running Neovim from a `:terminal` → use **`/neovim`**

## File structure

Standard Neovim plugin layout. Neovim auto-discovers files in these paths — no registration needed.

```
myplugin.nvim/
├── plugin/
│   └── myplugin.lua      ← eagerly loaded at startup (keep minimal)
├── lua/
│   └── myplugin/
│       ├── init.lua      ← main module (required as 'myplugin')
│       ├── config.lua    ← option defaults + validation
│       └── health.lua    ← health checks (:checkhealth)
├── ftplugin/
│   └── <ft>.lua          ← filetype-specific init (optional)
├── doc/
│   └── myplugin.txt      ← vimdoc (generate with panvimdoc)
└── README.md
```

## Lazy loading

Keep `plugin/myplugin.lua` minimal. Defer `require()` into command and mapping bodies, not at the top of the file. This preserves startup time for users.

```lua
-- BAD: eager load — pays the cost even if MyCommand is never called
local myplugin = require("myplugin")
vim.api.nvim_create_user_command("MyCommand", function()
  myplugin.run()
end, {})

-- GOOD: deferred load — require() only runs when the command is invoked
vim.api.nvim_create_user_command("MyCommand", function()
  require("myplugin").run()
end, {})
```

## Keymapping patterns

Avoid creating keymaps automatically — it conflicts with user config. Two preferred approaches:

### `<Plug>` mappings (recommended for simple actions)

```lua
-- In plugin/myplugin.lua
vim.keymap.set("n", "<Plug>(MyPluginAction)", function()
  require("myplugin").do_action()
end)
```

Users then bind it themselves:

```lua
vim.keymap.set("n", "<leader>a", "<Plug>(MyPluginAction)")
```

### Lua functions (recommended for extensible actions)

```lua
-- Expose the function; let users decide the mapping
require("myplugin").do_action()  -- callable directly
```

For buffer-local mappings (custom UI, ftplugin), always pass `buffer = bufnr`:

```lua
vim.keymap.set("n", "<Plug>(MyPluginBufferAction)", function()
  require("myplugin").buffer_action()
end, { buffer = bufnr })
```

## Initialization: `setup()` patterns

### Pattern 1: separated config + init (preferred)

Plugin works out-of-the-box. `setup()` only overrides defaults — no `require()` calls, side effects, or expensive work. Initialization happens in `plugin/` or `ftplugin/` scripts, not inside `setup()`.

```lua
-- lua/myplugin/config.lua
local M = {}

M.defaults = {
  enabled = true,
  timeout = 500,
}

M.options = {}

function M.setup(opts)
  M.options = vim.tbl_deep_extend("force", M.defaults, opts or {})
  M.validate()
end

function M.validate()
  vim.validate({
    enabled = { M.options.enabled, "boolean" },
    timeout = { M.options.timeout, "number" },
  })
end

return M
```

### Pattern 2: combined `setup()` (use when init is complex or risky)

Requires the user to call `setup()` explicitly — even with defaults. Only choose this when misconfiguration risk is high.

```lua
-- lua/myplugin/init.lua
local M = {}

function M.setup(opts)
  local config = require("myplugin.config")
  config.setup(opts)
  -- initialization logic here
  M._initialized = true
end

return M
```

## Guard variables

Prevent re-initialization (e.g. if the file is sourced twice):

```lua
-- plugin/myplugin.lua
if vim.g.loaded_myplugin then
  return
end
vim.g.loaded_myplugin = true
```

For ftplugin (per-buffer, not per-session), no session-level guard is needed — `ftplugin` is intentionally per-buffer.

**Set `filetype` as late as possible** in custom UI buffers so users can override buffer-local settings via `FileType` autocmds.

## Health checks

Create `lua/<plugin>/health.lua`. `:checkhealth <plugin>` auto-discovers it.

```lua
-- lua/myplugin/health.lua
local M = {}

function M.check()
  vim.health.start("myplugin")

  -- Check initialization
  local ok, config = pcall(require, "myplugin.config")
  if not ok then
    vim.health.error("myplugin not loaded")
    return
  end

  -- Check config
  if config.options.timeout < 100 then
    vim.health.warn("timeout < 100ms may cause issues")
  else
    vim.health.ok("configuration looks good")
  end

  -- Check external deps
  if vim.fn.executable("some-tool") == 1 then
    vim.health.ok("some-tool found")
  else
    vim.health.error("some-tool not found in PATH")
  end
end

return M
```

## Type annotations (LuaCATS)

Annotate public APIs with LuaCATS for lua-language-server (luals):

```lua
---@class MyPlugin.Config
---@field enabled boolean
---@field timeout integer

---@param opts? MyPlugin.Config
function M.setup(opts) end

---@return MyPlugin.Config
function M.get_config() end
```

Integrate `lua-typecheck-action` in CI to catch type errors before users do.

## In-process LSP actions (advanced UI pattern)

For plugins with custom UIs, expose actions as LSP code-actions so users can invoke them via standard `vim.lsp.buf.code_action()`:

```lua
vim.lsp.buf.code_action({
  apply = true,
  filter = function(a)
    return a.title == "My Plugin Action"
  end,
})
```

## Versioning & deprecation

- Follow **SemVer**: `MAJOR.MINOR.PATCH`
- Use `vim.deprecate()` when removing or renaming APIs:

```lua
function M.old_function(opts)
  vim.deprecate("myplugin.old_function", "myplugin.new_function", "2.0.0", "myplugin")
  return M.new_function(opts)
end
```

- Automate releases with `luarocks-tag-release` or `release-please-action`
- Publish to **luarocks** if the plugin has Lua dependencies or is itself a dependency

## Documentation (vimdoc)

Provide vimdoc so users can access `:h myplugin` in Neovim.

Generate from Markdown using [`panvimdoc`](https://github.com/kdheepak/panvimdoc), then regenerate help-tags:

```vim
:helptags doc/
```

Reuse `/docs write` for the Markdown source (it dispatches to language-specific doc generators, including `nvim` → vimdoc).

## Development workflow

- Use `:restart` to reload plugin changes during development
- Profile startup impact: `nvim --startuptime /tmp/nvim-startup.log`
- Add `dev = true` to a lazy.nvim spec to load from a local path while iterating:

```lua
{
  "ocrosby/myplugin.nvim",
  dev = true,  -- loads from opts.dev.path/myplugin.nvim
}
```

- For native vim.pack configs, use the local-dev loader pattern from `/nvim-config` (a `lua/dev.lua` helper that falls back to `vim.pack.add()` when the local clone is absent)

## Testing

If the plugin is extracted from yoda.nvim or sits alongside it, reuse the same test stack:

- **Test runner**: `neospec` (yoda's runner) — specs use plenary-style `describe` / `it` blocks under `tests/unit/**/*_spec.lua`
- **Lint**: `stylua --check` over `.lua` files under `lua/` and `tests/`
- **Gate command**: `/validate` (or `make lint && make test` if a Makefile is present)

For a net-new plugin without yoda's tooling, the conventional choices are `plenary.nvim`'s `PlenaryBustedDirectory` for tests and `stylua` for lint. CI: a single GitHub Actions job that runs both.

## Code style

Match yoda.nvim's `stylua.toml` when working in-tree, or copy it as the starting point for a new plugin:

```toml
indent_type = "Spaces"
indent_width = 2
column_width = 150
quote_style = "AutoPreferDouble"
```

Sort requires via `stylua` (it groups and orders them deterministically). Avoid hand-rolled require ordering.

## Rules across the skill

- Never auto-create keymaps — use `<Plug>` mappings or expose functions for the user to bind
- Never put `require()` of your own modules at the top of `plugin/<name>.lua` — defer into command/mapping bodies
- `setup()` is for overrides; initialization belongs in `plugin/` or `ftplugin/` (Pattern 1 above)
- Every public API gets a LuaCATS annotation — the IDE-side feedback for users is worth the line cost
- Every plugin ships `:checkhealth <name>` — even a 10-line health check is better than none
