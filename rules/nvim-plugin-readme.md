---
description: Neovim plugin README conventions — require install matrix (lazy.nvim + vim.pack + packer.nvim) in every plugin README. Fires on repo-root README.md; gates on Neovim-plugin repo shape (presence of lua/<name>/ or plugin/<name>.lua).
paths:
  - "README.md"
---

# Neovim Plugin README

Specializes `rules/readme-standard.md` for repositories that ship a Neovim plugin. Applies only when the current repo has the plugin shape:

- A top-level `lua/<name>/` directory, **and**
- A top-level `plugin/<name>.lua` (or `plugin/<name>.vim`) bootstrap file.

If either is absent, defer to the generic `rules/readme-standard.md` without the extensions below. If both are present, the Installation section of the root README is governed by the install-matrix rule here.

## Install matrix — mandatory

Every Neovim plugin README's Installation section **must** include install examples for all three of the mainstream approaches, so a user coming from any ecosystem can copy-paste without translating. These are not alternatives at the author's discretion — they are a mandatory trio.

1. **`lazy.nvim`** — the current community default
2. **native `vim.pack`** (Neovim ≥ 0.12) — the official in-core manager; many users are migrating here
3. **`packer.nvim`** — legacy, still widely deployed

Each block must:

- Show the actual module name in `require("<module>").setup({...})` — the plugin's `lua/<name>/` directory name, which can differ from the repo name (e.g. `invoke.nvim` repo → `require("invoke_nvim")`).
- List every runtime dependency the plugin loads at `require` time, so the user doesn't hit a missing-dep traceback on first use.

### `vim.pack` block — specifics

`vim.pack.add` does **not** run `setup()` or wire keymaps on the user's behalf — unlike lazy.nvim's `config = function() ... end` or packer's `config = function() ... end`, which hide those calls inside the spec. The `vim.pack` example must therefore make them explicit:

```lua
vim.pack.add({
  { src = "https://github.com/nvim-lua/plenary.nvim" },         -- dep
  { src = "https://github.com/<owner>/<plugin>.nvim", version = "v1.2.3" },
})

require("<module>").setup({})
vim.keymap.set("n", "<leader>x", "<Plug>(…)", { desc = "..." })  -- if the plugin exposes <Plug> mappings
```

Call out in the surrounding prose:

- `vim.pack.add` is idempotent — first call clones, subsequent calls are no-ops.
- `version = "..."` pins to a tag or branch; omit to track the default branch.
- Runtime dependencies are added as **separate `src` entries in the same table**, not nested under the plugin — `vim.pack.add` has no `dependencies` field.
- `:lua vim.pack.update()` pulls new upstream commits across every added source.

### Placement and layout

- The three blocks live inside a single `## Installation` section, in the order above (lazy.nvim first, then `vim.pack`, then packer).
- When the README is long, collapse each block under a `<details>` tag so the Installation section stays scannable; keep **lazy.nvim open by default** (the modal case).
- Do not substitute other managers in place of this trio (vim-plug, mini.deps, rocks.nvim, dein, lazyvim-extras). Those can be *added* as a fourth block when relevant to the plugin's audience, never as a *replacement* for one of the mandatory three.

## Mandatory behaviors

- When writing a new plugin README, add all three install blocks in the mandated order before publishing.
- When editing a plugin README that is missing one or more of the mandatory blocks, add the missing block in the same change rather than deferring to a follow-up — the asymmetry is user-visible on the landing page and compounds every day it ships that way.
- When adding or removing a runtime dependency on an existing plugin, update all three install blocks together — a dep listed in lazy.nvim's `dependencies` but missing from the vim.pack block will cause a first-launch traceback that is harder to diagnose than a complete fresh install.

## Reviewer checklist

Flag findings using `rules/findings-format.md`:

- **Must Fix** — any of the three mandatory blocks absent from a plugin README; `vim.pack` block missing the explicit `setup()` call that lazy.nvim and packer hide inside their spec; the module name used in `require(...)` doesn't match the actual `lua/<name>/` directory.
- **Should Fix** — `vim.pack` block documents dependencies nested under the plugin instead of as sibling `src` entries; an install block silently drops a required runtime dep (e.g. plenary, snacks); the three blocks are presented in a non-mandated order.
- **Consider** — three blocks laid out un-collapsed on a very long README (`<details>` grouping would scan better); missing one-line prose about `vim.pack.update()` for ongoing maintenance.

## Pragmatism guard

Do not apply this rule when:

- The repo is not a Neovim plugin (missing `lua/<name>/` or `plugin/<name>.lua`). Example: distributions like `yoda.nvim` that are cloned to `~/.config/nvim`; those have their own install model and should document that model instead.
- The repo is explicitly experimental, not meant for installation (noted in the README with language like "scratch", "WIP", "do not install").
- The author has an explicit audience decision to target only one manager (noted inline in the README, e.g. "this plugin is only maintained for mini.deps users"). The inline note itself must then be in the Installation section.

## See also

- `rules/readme-standard.md` — the general README standard this rule specializes.
- `skills/nvim/plugin.md` — the plugin-authoring workflow that cross-references this rule.
- `rules/nvim-docs.md` — governs `doc/*.txt` vimdoc, the other required documentation surface for a Neovim plugin.
