---
paths:
  - "**/*.lua"
---

# Lua Idioms

> Neovim-specific Lua (vim.api usage, autocmd groups, plugin layout) lives in `nvim-lua.md`. This rule covers the language itself — it applies in Neovim, LÖVE, OpenResty, busted scripts, embedded Lua, and anywhere else Lua runs.

Lua is a permissive runtime: it will silently leak globals, swallow errors inside a stripped `pcall`, and build strings in O(n²) without complaint. The signal tables below name the common shapes and the idiomatic alternatives. Apply them as the default form when writing Lua — not as a separate polish pass.

## Recognition Signals

### Scoping — when global leakage is the problem

| Signal | Idiomatic alternative |
|---|---|
| `x = ...` at file top level (no `local`) | `local x = ...` — globals must be deliberate, not accidental |
| `function name() ... end` at top level | `local function name() ... end` — same reason |
| Reaching into `_G.something` to check existence | Pass the dependency in, or check `package.loaded[mod]` for modules |
| Cross-module communication via globals | Return values from `require` — modules are first-class |

### Modules — when structure is the problem

| Signal | Idiomatic alternative |
|---|---|
| Module returns a single function or value | `local M = {}` ... `return M` — leaves room for additional exports without breaking callers |
| Side effects run at `require` time (registering handlers, opening files, mutating globals) | Move setup into `M.setup(opts)` — `require` must be idempotent |
| `require("mod").fn(...)` called repeatedly in a hot path | `local fn = require("mod").fn` once at file top |
| Cyclic `require` between two modules | Extract the shared piece into a third module — do not lazy-require to paper over the cycle |

### Error handling — when failure modes are the problem

| Signal | Idiomatic alternative |
|---|---|
| `pcall` wrapping every internal call | Wrap only at boundaries (entry points, external I/O, untrusted input); let internal errors propagate |
| Swallowing the error: `local ok = pcall(f)` with no `err` capture | `local ok, err = pcall(f)` and decide what to do with `err` |
| `assert(cond, "msg")` for user-input validation | Return `nil, err` — `assert` is for invariants the caller can't violate, not input checking |
| `error(table_or_object)` thrown across module boundaries | `error(string)` — many handlers `tostring(err)` and lose structured info |
| Re-raising with `error(err)` after `pcall` (traceback is lost) | Use `xpcall` with `debug.traceback` if the traceback matters at the boundary |

### Tables and iteration — when data shape is the problem

| Signal | Idiomatic alternative |
|---|---|
| `pairs` when iteration order matters | `ipairs` — `pairs` has no order guarantee; `ipairs` is also faster for arrays |
| `#t` on a table with holes (`{1, nil, 3}`) | Track length explicitly; `#` is undefined when the array part has `nil` |
| `table.remove(t, 1)` inside a loop | Build a new table, or walk with read/write indices — `remove(t, 1)` is O(n) per call |
| Linear `for ... if v == x then` membership scan inside a loop | Build `local set = {} ; for _, k in ipairs(keys) do set[k] = true end` once before the loop (O(n·m) → O(n+m)) |
| Setting a key to `nil` to "clear" it while iterating with `pairs` | Collect keys-to-delete in a list first, then delete after the loop |
| Mixing dense array keys and string keys in the same table to "save allocations" | Use two tables — the runtime stores array and hash parts separately and the mix surprises iteration |

### Strings — when string building is the problem

| Signal | Idiomatic alternative |
|---|---|
| `s = s .. piece` inside a loop | `table.insert(parts, piece)` then `table.concat(parts)` — O(n²) → O(n) |
| `string.format("%s%s%s", a, b, c)` for plain concatenation | `a .. b .. c` — `format` is for templates with conversions, not joins |
| Repeated `string.sub` calls to walk a string | Iterate with `string.gmatch` or a single pass |
| Reaching for a regex library | Lua patterns are not PCRE but cover most cases — learn `%w`, `%s`, `%-`, `%b()`, captures, anchors |

## Mandatory Behaviors

**When writing new code**: every binding is `local` unless a global is deliberate and named. Modules return a table. `require` has no side effects. Errors propagate to a boundary; the boundary decides what to do with them.

**When editing existing code**: do not introduce an implicit global, a swallowed `pcall`, a `..=` string-building loop, or `table.remove(t, 1)` in a loop. If surrounding code already does one of these, fix it in the same change *only* when the fix is local — do not snowball into a refactor.

**When reviewing code**: flag findings per `rules/findings-format.md`:
- **Must Fix**: implicit globals; `pcall` results discarded with no `err` capture; `error(table)` thrown across module boundaries; `assert` used for user input
- **Should Fix**: `..=` string building in a loop; `table.remove(t, 1)` in a loop; linear membership scans inside a loop; side effects at `require` time
- **Consider**: missing `local` alias for a hot-path function; `string.format` used for plain joins

## Pragmatism Guard

Do not apply this rule when:
- **The script is a one-shot.** A 20-line config script does not need a module table.
- **The performance gain is irrelevant at the actual N.** Three string concatenations is not an O(n²) problem.
- **The user explicitly asked for the simpler form.**

## Stylua

When `stylua.toml` is present, defer to it for formatting (indent width, line length, quote style). This rule covers semantics, not layout — do not fight the formatter.
