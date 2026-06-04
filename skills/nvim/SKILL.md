---
description: Neovim dispatcher — rpc (talk to a running instance via msgpack-RPC), config (native vim.pack config conventions), plugin (authoring redistributable Neovim plugins). The first word of $ARGUMENTS selects the subcommand.
argument-hint: "<subcommand>"
aliases: neovim, nvim-config, nvim-plugin
---

# Nvim: Neovim Dispatcher

Use this skill for any Neovim work that is not about adding a plugin to a lazy.nvim config. The dispatcher routes between three disjoint sub-cases.

For yoda.nvim / lazy.nvim plugin adds, use `/add-plugin` instead — it covers the conservative-update checklist (stability gate, spec file under `lua/plugins/`, lazy-lock.json discipline, version pinning).

## Usage

```
/nvim                  # show this help
/nvim rpc              # interact with a running Neovim via msgpack-RPC
/nvim config           # native vim.pack config authoring reference
/nvim plugin           # authoring a redistributable Neovim plugin
```

## Workflow

### 1. Parse the subcommand

Split `$ARGUMENTS` on the first space. The first word is the subcommand.

- Empty or `help` → print **Usage** and stop.
- Not one of `rpc`, `config`, `plugin` → print **Usage** and stop.
- Dispatch to the matching step.

### 2. Dispatch — `rpc`

Use this when Claude Code runs inside a Neovim terminal (the `$NVIM` environment variable is set) and you need to query state, send commands, open files, or inspect the runtime via msgpack-RPC.

**If `$NVIM` is empty: stop and tell the user there is no running Neovim instance to talk to.**

Read `~/.claude/skills/nvim/rpc.md` and apply its workflow:

- Prerequisites and `NVIM_APPNAME` warning filtering
- `--remote-expr` for read-only queries, `--remote-send` for keystrokes, `--remote` / `--remote-tab` for opening files
- Common patterns (current buffer, cursor, options, LSP)
- Reading help, finding plugin source, lazy.nvim API
- Stale LSP diagnostics recovery
- Safety rules (never `:q`, never mutate buffers without confirmation)

### 3. Dispatch — `config`

Use this when modifying or designing a Neovim configuration that uses the **native** conventions (vim.pack, `plugin/*.lua`, `lsp/*.lua`, `after/`) without a plugin manager framework. Requires Neovim ≥ 0.12.

**If the config is lazy.nvim-based (has `lazy-lock.json`, `lua/plugins/<name>.lua` specs, or calls `require("lazy").setup`): stop and direct the user to `/add-plugin` instead.**

Read `~/.claude/skills/nvim/config.md` and apply its workflow:

- Startup sequence and runtime directories
- `vim.pack` plugin management and lockfile
- `after/lsp/` server config files
- The three loading patterns (eager, deferred-to-VimEnter, truly-lazy)
- Utility modules (`lazyload`, `merge`, `dev`)
- Plugin file layout templates
- Option interfaces, standard paths, common operations

### 4. Dispatch — `plugin`

Use this when authoring or modifying a redistributable Neovim plugin (a repo intended to be installed by others) — including when a `lua/yoda/<module>` is being extracted into its own repo.

**If the user is configuring their own Neovim (not authoring a redistributable plugin): stop and route them to `/nvim config` (native) or `/add-plugin` (lazy.nvim) instead.**

Read `~/.claude/skills/nvim/plugin.md` and apply its workflow:

- Standard file structure (`plugin/`, `lua/<name>/`, `ftplugin/`, `doc/`)
- Lazy loading conventions in `plugin/<name>.lua`
- Keymapping patterns (`<Plug>` mappings, Lua functions, no auto-bindings)
- `setup()` patterns (separated config + init vs combined)
- Guard variables, health checks, LuaCATS, SemVer/deprecation
- Vimdoc generation via panvimdoc, testing, code style

### 5. Final verification step

Each dispatch step ends with its own verification gate inside the referenced Level 3 file. Confirm the gate fired before exiting.

## Rules (apply across all subcommands)

- `rpc` is for talking to a running Neovim — never use it to mutate buffers without explicit user confirmation; prefer `--remote-expr` (read-only) over `--remote-send` (simulates typing).
- `config` and `plugin` are mutually exclusive scopes: `config` is for your own setup, `plugin` is for code that other people install. If unsure which applies, ask before proceeding.
- For RPC into a Neovim instance from within a `config` or `plugin` workflow, switch to `rpc` rather than reinventing its patterns.
