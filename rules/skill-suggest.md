---
description: Unified end-of-response skill recommendations — docs, migration, code review.
paths:
  - "**/*.go"
  - "**/*.py"
  - "**/*.lua"
  - "**/*.feature"
---

# Skill Suggestions

After completing work in a code file, recommend the appropriate skill at the end of your response. Keep each recommendation to one line. Do not stack more than one recommendation per response — pick the most relevant trigger.

**Do not recommend any skill when**:
- The user has already run that skill in this session for these files
- The file is a test file (`_test.go`, `test_*.py`, `*_spec.lua`)
- Only documentation, config, or non-code files were changed

## After implementation → `/code review`

Recommend `/code review` before shipping when:

- A new function, class, module, or package has been written
- A bug fix touches more than one file
- A refactor moves or restructures code

Do not recommend for single-line fixes (typo, comment, minor rename).

> Run `/code review` before shipping to catch any issues.

## Public API added or changed → `/docs write`

Recommend `/docs write` when an exported/public symbol is added or modified without a doc comment or docstring. Undocumented public APIs are a maintenance liability. The dispatcher auto-detects the language from cwd.

| Language | Recommended invocation | Condition |
|---|---|---|
| Go | `/docs write go` | Exported symbol (`PascalCase`) added or changed without a preceding `//` comment |
| Python | `/docs write py` | Public function or class (no `_` prefix) added or changed without a docstring |
| Neovim/Lua | `/docs write nvim` | Public module function in `lua/*/init.lua` added or changed without a comment block |
| Gherkin | `/docs write gherkin` | A new `.feature` file is added to the suite |

Do not recommend when the symbol already has a doc comment / docstring, or the change is private/unexported/internal only.

> Run `/docs write` to document the new exported symbols.

## Deprecated patterns detected → `/code migrate`

Recommend `/code migrate` (file-level mode — targets the current file) when reading or writing code that contains deprecated or outdated patterns. The user can expand scope by running `/code migrate` standalone.

**Go** triggers:
- `ioutil.` (any function — deprecated since Go 1.16)
- `interface{}` (use `any`)
- `log.Printf` / `log.Println` in a context where `slog` would be appropriate
- `context.TODO()` in production code (not test files)
- `sort.Slice` where `slices.SortFunc` applies

**Python** triggers:
- `from typing import List, Dict, Tuple, Optional, Union`
- `unittest.TestCase` or `unittest.mock`
- `@app.on_event("startup")` / `@app.on_event("shutdown")`
- `os.path.join` (use `pathlib.Path`)
- `setup.py` or bare `requirements.txt`

**Neovim/Lua** triggers:
- `nvim_set_keymap` or `nvim_buf_set_keymap`
- `nvim_set_option` / `nvim_buf_set_option` / `nvim_win_set_option`
- `vim.cmd("au` / `vim.cmd("autocmd`
- `vim.cmd("hi` / `vim.cmd("highlight`
- `buf_get_clients`

**Gherkin** triggers:
- Steps containing "click", "type", "navigate", "field", "button"
- Feature files with more than 10 scenarios
- `sleep` or `time.sleep` in step definitions
- Multiple `When` steps in a single scenario

Do not recommend when the file is already being migrated in the current session.

> This file contains deprecated patterns — run `/code migrate` to modernize them.
