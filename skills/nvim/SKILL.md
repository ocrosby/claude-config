---
description: Neovim dispatcher — rpc (talk to a running instance via msgpack-RPC), config (native vim.pack config conventions), plugin (authoring redistributable Neovim plugins). The first word of $ARGUMENTS selects the subcommand.
argument-hint: "<subcommand>"
aliases: neovim, nvim-config, nvim-plugin
---

# Nvim: Neovim Dispatcher

Use this skill for any Neovim work. The dispatcher routes between three disjoint sub-cases: talking to a running instance (`rpc`), authoring a native config (`config`), or authoring a redistributable plugin (`plugin`).

**For lazy.nvim plugin adds** (yoda.nvim and similar): no dedicated skill exists yet. Apply this conservative-update checklist inline:

1. **Stability gate** — verify the plugin has ≥ 6 months of releases and no critical unresolved issues before adding.
2. **Spec file** — create `lua/plugins/<plugin_name>.lua` returning a lazy.nvim spec table. One plugin per file.
3. **Version pin** — pin to a tag (`version = "v1.2.3"`) or a commit (`commit = "abc123..."`). Never track `main`.
4. **Lockfile** — after `:Lazy sync`, commit `lazy-lock.json` in the same change as the spec file.
5. **Lazy-load** — set `event`, `cmd`, `ft`, or `keys` where possible; avoid eager loading unless the plugin runs at startup by design.

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

**If the config is lazy.nvim-based (has `lazy-lock.json`, `lua/plugins/<name>.lua` specs, or calls `require("lazy").setup`): stop and do not proceed with `/nvim config`.** Apply the lazy.nvim conservative-update checklist from the top of this file instead — the native `config` workflow does not fit lazy-managed setups.

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

**If the user is configuring their own Neovim (not authoring a redistributable plugin): stop and do not proceed.** For native configs, route to `/nvim config`. For lazy.nvim configs, apply the conservative-update checklist from the top of this file.

Read `~/.claude/skills/nvim/plugin.md` and apply its workflow:

- Standard file structure (`plugin/`, `lua/<name>/`, `ftplugin/`, `doc/`)
- Lazy loading conventions in `plugin/<name>.lua`
- Keymapping patterns (`<Plug>` mappings, Lua functions, no auto-bindings)
- `setup()` patterns (separated config + init vs combined)
- Guard variables, health checks, LuaCATS, SemVer/deprecation
- Vimdoc generation via panvimdoc, testing, code style

### 5. Final verification step

Each dispatch step ends with its own verification gate inside the referenced Level 3 file. After the dispatch returns, confirm concretely:

- For `rpc`: the `$NVIM` socket is still live (`--remote-expr '1'` returns `1`) and the last expression returned a non-empty result.
- For `config` and `plugin`: the file(s) written parse (`nvim --headless -c "luafile <path>" -c quit`) and no `E5108` was raised.

**If the applicable check does not pass: stop and do not report success.** Return to the failing sub-step.

## Rules (apply across all subcommands)

- `rpc` is for talking to a running Neovim — never use it to mutate buffers without explicit user confirmation. Always use `--remote-expr` for read-only queries; use `--remote-send` only when keystroke simulation is explicitly required.
- `config` and `plugin` are mutually exclusive scopes: `config` is for your own setup, `plugin` is for code that other people install. **If unsure which applies: stop and do not proceed — ask before proceeding.**
- For RPC into a Neovim instance from within a `config` or `plugin` workflow, always switch to `rpc` — never reinvent its patterns.
