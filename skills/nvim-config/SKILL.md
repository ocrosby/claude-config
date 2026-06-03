---
description: Reference for Neovim configs that use the built-in native conventions (vim.pack for plugin management, plugin/*.lua loading, lsp/*.lua auto-discovery, after/ overrides) WITHOUT a plugin manager framework. Requires Neovim ≥ 0.12. Use when designing, reviewing, or modifying a native nvim config — not lazy.nvim, packer, or any other framework.
when_to_use: User is working in a Neovim config that calls vim.pack.add() / vim.lsp.enable() / uses plugin/*.lua loading; user explicitly says "native nvim config", "vim.pack", "no plugin manager", or "switching off lazy.nvim". Trigger phrases — "convert to native", "vim.pack lockfile", "after/lsp override", "plugin/lang/<ft>.lua pattern".
---

# Native Neovim Config Reference

Reference for Neovim configs using the built-in conventions (`vim.pack`, `plugin/`, `lsp/`, `after/`) without a plugin manager framework. Requires Neovim ≥ v0.12.0.

Source: adapted from [fredrikaverpil/dotfiles](https://github.com/fredrikaverpil/dotfiles/blob/main/stow/shared/.claude/skills/nvim-config/SKILL.md). Omar's actual configs (`yoda.nvim`, `nvim-personal`, etc.) are lazy.nvim-based; this skill is reference material if/when a native config experiment happens.

## When NOT to use

Do **not** apply this skill's patterns when working in a **lazy.nvim-based config**. Omar's current configs all fall under this exclusion:

- `~/src/github.com/jedi-knights/yoda.nvim` (has `lazy-lock.json`, `lua/plugins/<name>.lua` spec files)
- `~/.config/nvim-personal` (lazy.nvim-based)
- `~/.config/nvim` and the other `nvim-{astro,chad,kickstart,lazy,lunar,yoda}` siblings (all lazy.nvim or framework-based)

For yoda.nvim-specific lazy.nvim work, use **`/add-plugin`** instead — it covers the conservative-update checklist (stability gate, spec file under `lua/plugins/`, lazy-lock.json discipline, version pinning, validation).

A config is **lazy.nvim-based** when any of these are true: `lazy-lock.json` exists, `lua/plugins/<name>.lua` files declare specs with `{ "owner/repo", ... }` tables, or `init.lua` calls `require("lazy").setup(...)`. A config is **native** when `vim.pack.add(...)` calls appear in `init.lua` or `plugin/*.lua`.

## Documentation

**Local disk** — docs ship with Neovim at `$VIMRUNTIME/doc/`. With Bob-managed installs the path is `~/.local/share/bob/nightly/share/nvim/runtime/doc/`. Read with `:h <tag>` inside Neovim or directly.

Key help files for native config work:

| Topic | Help tag | File |
|---|---|---|
| Startup & init order | `:h initialization` | `starting.txt` |
| Native package manager | `:h vim.pack` | `pack.txt` |
| packages / packpath | `:h packages` | `pack.txt` |
| LSP config auto-discovery | `:h lsp-config` | `lsp.txt` |
| Enable/disable servers | `:h vim.lsp.enable()` | `lsp.txt` |
| ftplugin directory | `:h ftplugin` | `usr_41.txt` |
| after/ directory | `:h after-directory` | `options.txt` |
| runtimepath | `:h runtimepath` | `options.txt` |
| autoload/ | `:h autoload` | `userfunc.txt` |
| colors/ | `:h colorscheme` | `syntax.txt` |

**Online** — https://neovim.io/doc/user/ mirrors the same help pages.

For RPC into a running instance (querying state, listing runtime files, finding plugin source), see `/neovim`.

## Startup sequence (`:h initialization`)

| Step | What happens |
|---|---|
| 1 | Set `'shell'` from `$SHELL` |
| 2 | Process arguments, execute `--cmd` args, create buffers (not loaded yet) |
| 3 | Start server, set `v:servername` |
| 4 | Wait for UI to connect (if `--embed`) |
| 5 | Setup default mappings and autocmds |
| 6 | Enable filetype and indent plugins (`:runtime! ftplugin.vim indent.vim`) |
| **7a** | System vimrc (`sysinit.vim`) |
| **7b** | **User config (`init.lua`)** — leader keys, `require("options")`, etc. |
| **7c** | **`.nvim.lua` (exrc)** — project-local config, if `'exrc'` is on |
| 8 | Enable filetype detection (`:runtime! filetype.lua`) |
| 9 | Enable syntax highlighting |
| 10 | Set `v:vim_did_init = 1` |
| **11** | **Load plugins**: `plugin/**/*.lua`, then packages, then `after/` plugins |
| 12–16 | shellpipe, updatecount, binary, ShaDa, quickfix |
| 17 | Open windows, load buffers → triggers **`VimEnter`**, then **`UIEnter`** |

**Key takeaway:** all `plugin/` files run at step 11; `VimEnter` (step 17) fires *after* everything. A deferred-setup helper module queues setup callbacks for VimEnter/UIEnter so the cost lands after the first paint.

## Runtime directories

Neovim searches these directories in every runtimepath entry (`:h 'runtimepath'`):

| Directory | When | Purpose |
|---|---|---|
| `init.lua` | Step 7b, once | Leader keys, `require("options")`, diagnostics |
| `lua/` | On `require()` | Lua modules (never auto-sourced) |
| `plugin/**/*.lua` | Step 11, once | Plugin install + setup (alphabetical, subdirs included) |
| `ftplugin/<ft>.lua` | Per-buffer, on FileType | Buffer-local settings (`vim.opt_local`) |
| `indent/<ft>.lua` | Per-buffer, on FileType | Indent expressions |
| `syntax/<ft>.vim` | Per-buffer, on FileType | Legacy syntax highlighting (treesitter overrides) |
| `lsp/<server>.lua` | Startup (discovery) | LSP config tables, auto-discovered by `vim.lsp.config` |
| `parser/<lang>.so` | On demand | Treesitter parsers |
| `queries/<lang>/*.scm` | On demand | Treesitter queries (highlights, injections, folds, indents) |
| `colors/<name>.{vim,lua}` | On demand | Colorschemes, loaded by `:colorscheme` |
| `autoload/` | On first call | Auto-loaded Vimscript/Lua functions |
| `compiler/` | On `:compiler` | Compiler settings |
| `spell/` | On demand | Spell checking files |

### after/ directory

The `after/` tree loads *after* all non-after paths. When using nvim-lspconfig for base LSP server configs, put **overrides** in `after/lsp/` (not `lsp/`) so they take precedence over the package defaults. Docs: `:h after-directory`.

### Per-project overrides (exrc)

With `vim.opt.exrc = true`, Neovim sources `.nvim.lua` from the current working directory at **step 7c** — before `plugin/` files (step 11) and before filetype detection (step 8). Native equivalent of lazy.nvim's `.lazy.lua`. Docs: `:h exrc`.

Because `.nvim.lua` runs before plugins, direct `require("conform").setup()` calls will be overwritten by plugin setup at VimEnter. Use an override hook that runs after all VimEnter callbacks:

```lua
-- .nvim.lua (project root)
require("lazyload").on_override(function()
  require("conform").setup({
    formatters_by_ft = { markdown = { "mdformat" } },
  })
end)
```

`lazyload.on_override` is a convention — see "Utility modules you'll need" below for the shape.

## Architecture: layers

A framework-less config gives each directory a single responsibility:

| Layer | Directory | Role |
|---|---|---|
| **options** | `lua/options.lua` | All `vim.opt` settings, required from `init.lua` |
| **utility** | `lua/` | Shared Lua modules: `lazyload.lua`, `merge.lua`, etc. |
| **plugins** | `plugin/` | Self-contained plugin files: install + setup + keymaps |
| **lang plugins** | `plugin/lang/` | Per-language plugin installs, autocmds, editor settings, setup |
| **server config** | `after/lsp/` | All LSP server config tables (in `after/` to override package defaults) |

Each plugin file is **self-contained** — it installs its own packages, sets up the plugin inline, and defines its own keymaps. No central manifest.

**Cross-plugin data sharing** uses a global config table (e.g. `_G.Config`). Write at file scope of the producer (outside `on_vim_enter`); read inside the consumer's lazyload block. Top-level assignments execute at step 11, before any `VimEnter` callback fires.

## vim.pack — built-in plugin management

```lua
vim.pack.add({
  "https://github.com/user/repo",                                              -- string form
  { src = "https://github.com/user/repo" },                                    -- table form
  { src = "https://github.com/user/repo", name = "repo" },                     -- custom name
  { src = "https://github.com/user/repo", version = "main" },                  -- branch/tag/commit
  { src = "https://github.com/user/repo", version = vim.version.range("1.*") },-- semver range
})
```

- **`load` option**:
  - During `init.lua`/`plugin/` sourcing, defaults to `false` — runtimepath only, plugin's own `plugin/` files deferred to Neovim's normal runtime pass at step 11
  - After startup, defaults to `true` — `:packadd` without bang sources `plugin/` and `after/plugin/` immediately
  - Pass `load = function() end` to register on disk but stay off the packpath entirely until `vim.cmd.packadd("<name>")` is called explicitly — the foundation of the "truly lazy" pattern below
- **Install location**: `stdpath("data") .. "/site/pack/core/opt/<name>"`
- **Lockfile**: `$XDG_CONFIG_HOME/nvim/nvim-pack-lock.json` — commit to VCS for reproducible installs

```lua
vim.pack.update()                              -- interactive update with confirmation buffer
vim.pack.update({"name"}, { force = true })    -- update specific plugin, skip confirm
vim.pack.del({"name"})                         -- remove from disk
vim.pack.get()                                 -- list all managed plugins
```

## after/lsp/ config files

Each file returns a `vim.lsp.Config` table. Filename (without `.lua`) becomes the server name. Placed in `after/lsp/` to override base configs shipped by packages.

```lua
-- after/lsp/gopls.lua
---@type vim.lsp.Config
return {
  cmd = { "gopls" },
  filetypes = { "go", "gomod", "gowork", "gosum" },
  root_markers = { "go.work", "go.mod", ".git" },
  settings = {
    gopls = {
      analyses = { unusedparams = true },
      staticcheck = true,
    },
  },
}
```

Enable servers in `plugin/lsp.lua` via `vim.lsp.enable(servers)`. Disable: `vim.lsp.enable("gopls", false)`.

## Three loading patterns

Pick the pattern based on **when the plugin's code needs to run**, not how fancy the file looks.

### Pattern 1: eager (setup at step 11)

Use when the plugin must take effect before the first paint, or when another plugin's deferred setup callback or pre-VimEnter autocmd `require()`s it. Examples: colorscheme, dashboard, icons, treesitter, completion engine (if it's a dependency of LSP's `LspAttach` callback).

```lua
-- plugin/oil.lua
vim.pack.add({
  { src = "https://github.com/stevearc/oil.nvim" },
})

require("oil").setup({
  view_options = { show_hidden = true },
})

vim.keymap.set("n", "-", "<cmd>Oil<cr>", { desc = "Open file explorer" })
```

### Pattern 2: deferred to VimEnter (pack.add inside the callback)

The **default** pattern for plugins that load every session but don't need to be ready before the first paint. Fold `vim.pack.add` into the same `on_vim_enter` callback as `setup()` so both the install/source cost and the setup cost land after startup:

```lua
-- plugin/conform.lua
vim.g.auto_format = true

require("lazyload").on_vim_enter(function()
  vim.pack.add({
    { src = "https://github.com/stevearc/conform.nvim" },
  })

  require("conform").setup({
    formatters_by_ft = {
      go = { "goimports", "gci", "gofumpt", "golines" },
      lua = { "stylua" },
    },
  })
end)

vim.keymap.set("n", "<leader>uf", require("toggle").auto_format, { desc = "Toggle auto-format" })
```

**Why not bare `vim.schedule()`?** A `lazyload` helper gives sync-vs-async control, a VimEnter/UIEnter split, and an `on_override` hook for exrc overrides — bare `vim.schedule` provides none of these.

**Build hooks (`PackChanged`) must stay eager** when the plugin uses Pattern 2. Register the autocmd at file scope *before* the `on_vim_enter` call — autocmd registration is cheap and the hook needs to be live by the time the deferred `vim.pack.add` triggers a first-bootstrap install.

### Pattern 3: truly lazy via `{ load = function() end }` (first use)

Use for plugins that may never run in a session: debuggers, test runners, diff viewers. The empty `load` callback registers on disk (install + lockfile still work) but keeps the plugin off the packpath entirely. Invisible until the first-use gate (keymap, command, filetype autocmd) calls `vim.cmd.packadd`:

```lua
-- plugin/dap.lua
local packages = {
  { src = "https://codeberg.org/mfussenegger/nvim-dap", name = "nvim-dap" },
  { src = "https://github.com/rcarriga/nvim-dap-ui", name = "nvim-dap-ui" },
  { src = "https://github.com/nvim-neotest/nvim-nio", name = "nvim-nio" },
}
vim.pack.add(packages, { load = function() end })

local initialized = false

local function init()
  if initialized then return end
  initialized = true

  for _, p in ipairs(packages) do
    vim.cmd.packadd(p.name)
  end

  require("dapui").setup()
end

vim.keymap.set("n", "<leader>dc", function()
  init()
  require("dap").continue()
end, { desc = "Continue" })
```

Notes:

- **Give every spec an explicit `name`** — the `init()` loop uses those names for `:packadd`
- **`after/plugin/` files of the lazy-loaded plugin do not source automatically** via bare `:packadd`; if the plugin ships `after/plugin/*.lua` and you rely on them, source them manually in `init()`
- **Compared to Pattern 2**: Pattern 2 still loads every session, just not during startup. Pattern 3 doesn't load at all if the user never triggers the gate — zero cost on sessions where you never use it

### Deferred filetype-specific plugin

Wrap `require()` + `.setup()` in a `FileType` autocmd with `once = true`:

```lua
-- plugin/lang/csv.lua
vim.pack.add({
  { src = "https://github.com/hat0uma/csvview.nvim" },
})

vim.api.nvim_create_autocmd("FileType", {
  pattern = "csv",
  once = true,
  callback = function()
    require("csvview").setup()
  end,
})
```

### Build hooks

```lua
vim.api.nvim_create_autocmd("PackChanged", {
  callback = function(ev)
    if ev.data.spec.name == "nvim-treesitter" then
      vim.cmd("TSUpdate")
    end
  end,
})

vim.pack.add({
  { src = "https://github.com/nvim-treesitter/nvim-treesitter", version = "main" },
})
```

**PackChanged hooks must be registered BEFORE the `vim.pack.add()` call** that installs the plugin — otherwise the hook won't fire on first bootstrap.

Event data: `ev.data.kind` (`"install"`, `"update"`, `"delete"`), `ev.data.spec` (plugin spec), `ev.data.path` (full path to plugin directory).

## Utility modules you'll need

If you start a native config from scratch, you'll need a few small Lua modules under `lua/` — they don't ship with Neovim. Minimum viable shapes:

**`lua/lazyload.lua`** — VimEnter/UIEnter deferred-setup queues. Provides:
- `on_vim_enter(fn, opts?)` — queue `fn` for `VimEnter`. Default async (via `vim.schedule()`); pass `{ sync = true }` for synchronous (e.g. statusline that must be ready before paint).
- `on_ui_enter(fn, opts?)` — same shape but for `UIEnter`.
- `on_override(fn)` — runs after all VimEnter callbacks, for project-local overrides from `.nvim.lua`.

**`lua/merge.lua`** — deep-merge helper. Appends and deduplicates lists, recurses into dicts, overwrites scalars. Use `vim.NIL` as a value to explicitly remove a key. (Neovim's `vim.tbl_deep_extend` doesn't dedupe lists.)

**`lua/dev.lua`** — local dev plugin loader. Loads a plugin from a local clone if it exists; otherwise falls back to `vim.pack.add()`. Used like:

```lua
require("dev").use({
  dev = "~/code/public/my-plugin",
  fallback = function()
    vim.pack.add({ { src = "https://github.com/me/my-plugin" } })
  end,
})
```

## Plugin file layout templates

**Eager (Pattern 1):**

```lua
-- 1. Build hooks (must be registered BEFORE vim.pack.add)
vim.api.nvim_create_autocmd("PackChanged", { ... })

-- 2. Install + load
vim.pack.add(...)

-- 3. Setup
require("plugin").setup({ ... })

-- 4. Keymaps
vim.keymap.set(...)
```

**Deferred to VimEnter (Pattern 2):**

```lua
-- 1. File-scope setup that doesn't need the plugin loaded (globals, etc.)
vim.g.some_flag = true

-- 2. Build hooks (must be registered BEFORE the deferred vim.pack.add fires)
vim.api.nvim_create_autocmd("PackChanged", { ... })

-- 3. Install + load + setup, all deferred
require("lazyload").on_vim_enter(function()
  vim.pack.add(...)
  require("plugin").setup({ ... })
end)

-- 4. Keymaps (file scope — Neovim routes them to the plugin after load)
vim.keymap.set(...)
```

**Truly lazy (Pattern 3):**

```lua
-- 1. Register on disk without loading
local packages = { { src = "...", name = "plugin-name" } }
vim.pack.add(packages, { load = function() end })

-- 2. First-use gate
local initialized = false
local function init()
  if initialized then return end
  initialized = true
  for _, p in ipairs(packages) do
    vim.cmd.packadd(p.name)
  end
  require("plugin").setup({ ... })
end

-- 3. Keymaps / commands / FileType autocmds call init() before first use
vim.keymap.set("n", "<leader>xx", function() init(); ... end, ...)
```

## Option interfaces

Neovim exposes several Lua interfaces for setting options (`:h vim.o`, `:h vim.opt`). Convention: use **`vim.opt`** in `init.lua` and `lua/options.lua`, use **`vim.opt_local`** in `FileType` autocmds within `plugin/lang/` files.

| Interface | Equivalent to | Notes |
|---|---|---|
| `vim.o` | `:set` | Raw string get/set — no table support |
| `vim.bo` | `:setlocal` (buffer) | Raw buffer-scoped options |
| `vim.wo` | `:setlocal` (window) | Raw window-scoped options |
| `vim.go` | `:setglobal` | Global-only (skips local copy) |
| **`vim.opt`** | `:set` | Rich `Option` object: tables, `:append()`, `:remove()`, `:prepend()` |
| **`vim.opt_local`** | `:setlocal` | Same as `vim.opt` but buffer/window-local |

## Standard paths

| Purpose | Lua | Typical path |
|---|---|---|
| Config dir | `vim.fn.stdpath("config")` | `~/.config/nvim` |
| Data dir | `vim.fn.stdpath("data")` | `~/.local/share/nvim` |
| Plugin install | `stdpath("data") .. "/site/pack/core/opt/"` | — |
| State dir | `vim.fn.stdpath("state")` | `~/.local/state/nvim` |
| Runtime | `vim.fn.expand("$VIMRUNTIME")` | `.../share/nvim/runtime` |
| Cache | `vim.fn.stdpath("cache")` | `~/.cache/nvim` |

With `NVIM_APPNAME=<name>`, every path swaps `nvim` for `<name>` — useful for parallel configs (`nvim-personal`, `nvim-yoda`, etc.).

## Common operations

### Profile startup

```sh
NVIM_APPNAME=<name> nvim --startuptime /tmp/startup.log --headless +q
```

Columns:

| Column | Meaning |
|---|---|
| **clock** | Wall clock time since process start (ms) |
| **self+sourced** | Total time for a file including everything it `require()`'d |
| **self** | Time spent in that file alone (excluding nested requires) |

### Add a new language

1. Add LSP server to the `servers` list in `plugin/lsp.lua`
2. Add mason tools to the `ensure_installed` list in `plugin/mason.lua`
3. Add formatters to `formatters_by_ft` in `plugin/conform.lua`
4. Add linters to `linters_by_ft` in `plugin/lint.lua`
5. Create `plugin/lang/<ft>.lua` — editor settings (`vim.opt_local` via `FileType` autocmd), language-specific plugins, autocmds
6. *(optional)* `after/lsp/<server>.lua` — override base config

### Add a shared utility

1. Create `lua/<name>.lua` returning a module table
2. `require("<name>")` from whatever `plugin/` file needs it

## Rules across the skill

- Always pass `{ clear = true }` to `nvim_create_augroup` — prevents duplicate autocmds if the file is re-sourced
- Do **not** defer plugins needed from the first frame or first keystroke (colorscheme, dashboard) — use Pattern 1
- Per-filetype editor settings live in `plugin/lang/` files via `FileType` autocmds, not in `ftplugin/` — keeps each language file self-contained
- The `LspAttach` autocmd (typically in `plugin/lsp.lua`) bridges startup and per-buffer behavior: register the autocmd once at startup, but keymap registration happens per-buffer when the LSP server attaches
