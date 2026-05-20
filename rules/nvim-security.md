---
description: Neovim plugin security — editor-API-specific idioms. The general signal table lives in owasp-top-10.md.
paths:
  - "**/*.lua"
---

# Neovim Plugin Security

> See `owasp-top-10.md` for the general signal table and mandatory behaviors. This file covers Neovim/Lua-specific idioms only — patterns that exist because of the editor's API surface.

## Shell command execution — `vim.system()` over `vim.fn.system()`

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

## Dynamic code execution — never on untrusted input

`vim.api.nvim_exec()`, `loadstring()`, and `load()` evaluate arbitrary Vimscript/Lua. Never pass strings sourced from a buffer, file, user prompt, or remote response. If dynamic dispatch is required, use a strict allowlist of permitted values:

```lua
local actions = { open = open_fn, close = close_fn, reload = reload_fn }
local fn = actions[user_choice]
if fn then fn() end
```

## File path safety — confine to a base directory

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

## Sensitive state — module-local, never `vim.g.*`

`vim.g.*` is process-global and readable by every other plugin in the same Neovim instance. Tokens, credentials, and session state must live in module-local Lua variables:

```lua
-- Bad — any other plugin can read this
vim.g.myplugin_api_token = token

-- Good — closed over by the module, not exposed
local _api_token = token
```

This is unique to the Neovim plugin model — there is no isolation between plugins beyond Lua scope.
