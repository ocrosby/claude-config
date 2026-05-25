---
description: Generates Neovim plugin documentation in vimdoc format.
---

# Neovim Documentation Writer

Use this skill when you want to generate or audit `doc/<plugin>.txt` for a Neovim plugin in vimdoc format. Format conventions live in `rules/nvim-docs.md` — this skill orchestrates and produces the file.

## Usage

```
/nvim-docs                          # generate or audit doc for the current plugin
/nvim-docs <plugin-name>            # explicit plugin name
```

## When NOT to use

- The plugin is a personal Neovim config (`~/.config/nvim/`), not a distributable plugin — vimdoc is overkill
- The doc already exists and is current; use `/migrate` to update deprecated patterns instead

## Workflow

### 1. Discover the plugin surface

Read the plugin's public API, user commands, keymaps, and config options. Run:

```bash
ls lua/ doc/
test -f doc/*.txt && echo "EXISTS" || echo "MISSING"
```

**If `doc/<plugin>.txt` already exists and the user did not pass an explicit override: stop and ask whether to audit, regenerate, or extend.**

### 2. Generate the help file

Generate `doc/<plugin>.txt` following the [Vimdoc Skeleton](#vimdoc-skeleton) below. Apply the format rules in `rules/nvim-docs.md` (tags, references, separator lines, 78-col line width, modeline). Include only sections that apply to this plugin — omit empty ones rather than including them as placeholders.

### 3. Regenerate help tags

```bash
nvim --headless -c "helptags doc/" -c "q"
```

**If `helptags` reports errors: stop and fix the offending tag before continuing.**

### 4. Verify

For every section, command, function, and option documented, confirm the tag resolves:

```bash
nvim --headless -c "help <plugin-name>" -c "q"
```

**If any tag is broken or unreachable: stop and do not proceed.**

---

## Vimdoc Skeleton

```vimdoc
*plugin-name.txt*  Short one-line description

Author: Name
License: MIT

==============================================================================
CONTENTS                                              *plugin-name-contents*

  1. Introduction .......................... |plugin-name-introduction|
  2. Setup ................................ |plugin-name-setup|
  3. Configuration ........................ |plugin-name-configuration|
  4. Commands ............................. |plugin-name-commands|
  5. Keymaps .............................. |plugin-name-keymaps|
  6. API .................................. |plugin-name-api|
  7. Highlights ........................... |plugin-name-highlights|

==============================================================================
INTRODUCTION                                      *plugin-name-introduction*

Description of what the plugin does and why.

==============================================================================
SETUP                                                    *plugin-name-setup*

>lua
  require("plugin-name").setup({
    -- default configuration shown here
  })
<

 vim:tw=78:ts=8:ft=help:norl:
```

Tag, reference, formatting, and content conventions live in `rules/nvim-docs.md` — do not duplicate them here. If a convention is unclear, consult the rule, not this skeleton.
