# docs write — Neovim (vimdoc)

Applied when `write.md` detects `nvim`. Generates a vimdoc help file. Format conventions are authoritative in `rules/nvim-docs.md`.

**When NOT to use.** Personal Neovim config (`~/.config/nvim/`) — vimdoc is overkill. Doc already current — use `/code migrate` for deprecated pattern updates.

1. **Discover the surface.** Read public API, user commands, keymaps, config options:
   ```bash
   ls lua/ doc/
   test -f doc/*.txt && echo "EXISTS" || echo "MISSING"
   ```
   **If `doc/<plugin>.txt` already exists and no explicit override: stop and ask whether to audit, regenerate, or extend.**

2. **Generate the help file** following the skeleton below; apply `rules/nvim-docs.md` for tags, references, separator lines, 78-col width, modeline. Include only sections that apply — omit empty ones.

3. **Regenerate help tags.**
   ```bash
   nvim --headless -c "helptags doc/" -c "q"
   ```
   **If `helptags` reports errors: stop and fix the offending tag.**

4. **Verify** every section, command, function, and option tag resolves:
   ```bash
   nvim --headless -c "help <plugin-name>" -c "q"
   ```
   **If any tag is broken or unreachable: stop.**

   *Vimdoc skeleton:*
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
