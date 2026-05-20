---
description: Guides development of new Neovim plugin features using idiomatic Lua and the Neovim API, delegating review to /code-review.
aliases: nvim-feature
paths:
  - "**/*.lua"
---

# Neovim Plugin Feature Development

Use this skill when implementing a new Neovim plugin feature. This skill owns Neovim-specific design decisions (API choices, autocommand groups, keymap conventions, `setup()` idempotency). It **delegates** the final review pass to `/code-review -fc`. Do not re-implement the review checklist inline.

## Workflow

### 1. Understand the Feature

- Clarify what the feature does from the user's perspective
- Identify which Neovim APIs are needed (`vim.api`, `vim.fn`, `vim.keymap`, `vim.treesitter`, etc.)
- Determine if the feature needs autocommands, user commands, keymaps, or highlights

> Run `/architect` first only when the feature introduces a new module, a new public API surface, or significant structural decisions. For incremental additions, skip it.

### 2. Design the Interface

- Define the public API: functions the user or other modules will call
- Define configuration with sensible defaults using a `setup()` or `config` pattern
- Keep the command and keymap surface area minimal

### 3. Implement with Tests First

For any feature with observable behavior, the always-on `rules/tdd.md` requires a failing test before the implementation. Use `plenary.busted` or `mini.test` per `rules/nvim-testing.md`.

For features that are purely declarative (a new keymap binding, a new autocommand group with no logic), TDD is not required — note the exception in the commit message.

### 4. Apply Neovim API Conventions

- Use `vim.api.nvim_*` over Vimscript wherever possible
- Use `vim.keymap.set` over `vim.api.nvim_set_keymap`
- Use `vim.api.nvim_create_autocmd` and `vim.api.nvim_create_augroup` for autocommands
- Use `vim.api.nvim_create_user_command` for user commands
- Use `vim.notify` for user-facing messages with appropriate log levels
- Namespace all autocommand groups to avoid collisions
- Make `setup()` idempotent — guard against re-sourcing

### 5. Apply Structure Rules

- One module per concern: separate core logic, UI, commands, and config
- Entry point exposes `setup(opts)` that merges user config with defaults via `vim.tbl_deep_extend`
- Keep buffer-local and window-local state management explicit
- Use `vim.validate` for input validation on public functions

### 6. Apply Keymap and Autocommand Conventions

**Keymaps:**

- Always use `vim.keymap.set` with a `desc` field for which-key discoverability
- Plugin keymaps use `<leader>` sub-groups to avoid conflicts with core mappings
- Set keymaps only in the modes where they make sense
- Use `buffer` option for buffer-local keymaps
- Follow Vim grammar: `]` for next, `[` for prev, `g` prefix for variants

**Autocommands:**

- Every autocommand belongs to a group created with `vim.api.nvim_create_augroup("Name", { clear = true })`
- Always use `callback` (function) instead of `command` (string)
- Always include `desc` for debuggability
- Use `buffer` for buffer-local autocommands, `pattern` for global
- Use `once = true` for one-shot autocommands
- Debounce `CursorMoved`/`CursorMovedI` — prefer `CursorHold` when possible

### 7. Review via /code-review

Invoke `/code-review -fc` on the changed files. The review skill owns:

- Running `stylua --check` and `luacheck --quiet` if available
- Delegating to `nvim-reviewer` for API usage, idiomatic Lua, and performance checks
- Auto-fixing Must Fix and Should Fix findings, looping until clean

Do not re-implement the review checklist here — `nvim-reviewer` covers deprecated API calls, keymap `desc` presence, autocommand group cleanup, user command flags, `setup()` idempotency, and global state pollution. If `/code-review -fc` reports findings that require manual judgment, address them before declaring the feature complete.
