# Bench: Neovim

1. **Identify what to benchmark.** Target exactly one category per timed block: startup cost (`--startuptime`), hot-path callbacks (autocmds, keymaps, LSP handlers), expensive operations (treesitter queries, file reads, API batching loops), or comparison (two implementations). **If the target spans multiple categories: stop and split into separate benchmarks.**
2. **Write the benchmark.**

   *Inline timing with `vim.loop.hrtime()`* (nanosecond resolution, wall-clock latency — the user-visible number):
   ```lua
   local function bench(label, fn, iterations)
     iterations = iterations or 1000
     local start = vim.loop.hrtime()
     for _ = 1, iterations do
       fn()
     end
     local elapsed_ns = vim.loop.hrtime() - start
     local per_call_us = (elapsed_ns / iterations) / 1000
     vim.notify(string.format("%s: %.2f µs/call (%d iterations)", label, per_call_us, iterations))
   end

   bench("my_module.process", function()
     require("my_module").process(sample_input)
   end)
   ```

   *CPU time with `os.clock()`* (excludes I/O wait, use only when isolating pure compute):
   ```lua
   local function bench_cpu(label, fn, iterations)
     iterations = iterations or 1000
     local start = os.clock()
     for _ = 1, iterations do fn() end
     local elapsed_s = os.clock() - start
     local per_call_ms = (elapsed_s / iterations) * 1000
     vim.notify(string.format("%s: %.3f ms/call (cpu)", label, per_call_ms))
   end
   ```

   *Startup time profiling:*
   ```bash
   nvim --startuptime /tmp/startup.log +q
   sort -k2 -n /tmp/startup.log | tail -20

   nvim --startuptime /tmp/before.log +q
   # make your change
   nvim --startuptime /tmp/after.log +q
   diff <(sort -k2 -n /tmp/before.log) <(sort -k2 -n /tmp/after.log)
   ```

   *lazy.nvim profile:* `:Lazy profile` inside Neovim.

3. **Run.** Place the bench block in a scratch buffer or dedicated `bench/`, then `:source bench/my_bench.lua` or `:luafile %`. For startup benchmarks, always use a clean `nvim` invocation — never an already-running instance.
4. **Compare before/after.** For function-level, capture both runs and reload between:
   ```lua
   bench("before", before_fn, 10000)
   package.loaded["my_module"] = nil
   bench("after", require("my_module").process, 10000)
   ```
   For startup, use the `diff` approach above.
5. **Interpret.**

   | Measurement | Typical concern |
   |---|---|
   | `> 1 ms/call` on a keymap or autocmd handler | Noticeable input lag above 5–10 calls/sec |
   | `> 50 ms` added to startup | Perceptible delay; investigate with `--startuptime` |
   | High variance across runs | Benchmark noise — ensure module is pre-loaded; exclude `require()` from hot loop |

   Red flags: `require()` inside the timed loop (cached after first call → misleading sub-µs results); repeated `vim.api.*` calls that can be batched with `nvim_buf_call` or `vim.schedule`; table construction inside tight loops (GC pressure); inconsistent runs caused by background plugin state — re-run in `nvim --clean --noplugin`.

6. **Apply optimizations.** Each directive below already names its own trigger condition (callback, hot path, tight loop, large table) — apply it whenever profiling shows that condition. Always cache `require()` results at the top of the file — never inside callbacks. Always use `vim.schedule` for deferred non-urgent work. Always batch API calls (one `nvim_buf_set_lines` for the whole range, not one per line). Always pre-allocate option tables used in tight loops. Always lazy-load plugin submodules with `__index`. Never call `vim.tbl_deep_extend` on large tables in hot paths.
7. **Verify.** Re-run with a fresh `nvim`. Confirm the change is measurable per `vim.loop.hrtime()` and not within noise. **If within noise or regresses: revert and report.**

**Rules for `nvim`.** Never optimize without a measurement. Exclude `require()` from the timed loop unless module load time is the target. For startup benchmarks, always use a fresh process. **Never `:source` a benchmark in a running session** — the Lua module cache persists across `:source` and gives misleading sub-µs results. Always `package.loaded["my_module"] = nil` before re-requiring in function-level benchmarks. Do not commit benchmark scripts to `lua/` — place them in `bench/` and `.gitignore` the directory.
