---
description: Benchmarking dispatcher — auto-detects language (go, py, nvim) from cwd and routes to the matching write/run/analyze workflow. Override with /bench <language>.
argument-hint: "[language] [description]"
aliases: go-bench, py-bench, nvim-bench
allowed-tools: Read, Grep, Glob, Edit, Write, Bash(go test *), Bash(go tool *), Bash(benchstat *), Bash(pytest *), Bash(python *), Bash(py-spy *), Bash(nvim *), Bash(uv *)
---

# Bench: Language-Aware Benchmarking

Use this skill to write, run, or analyze benchmarks. The dispatcher detects the language from cwd and applies the matching tools and patterns.

## Usage

```
/bench                              # auto-detect language from cwd
/bench go [description]             # Go benchmarks (testing.B, benchstat, pprof)
/bench py [description]             # Python benchmarks (pytest-benchmark, cProfile, py-spy)
/bench nvim [description]           # Neovim plugin benchmarks (vim.loop.hrtime, --startuptime)
```

## Workflow

### 1. Detect the language

```bash
bash ~/.claude/scripts/detect_language.sh "${1-}"
```

Returns `go`, `py`, `nvim`, `gherkin`, `rest`, or `unknown`. `gherkin` and `rest` are not supported by `bench` — stop and tell the user. `unknown` → stop and ask. Otherwise drop the consumed override token and dispatch.

### 2. Dispatch — `go`

Replicates the prior `/go-bench` skill.

1. **Read the code under test.** Target function signatures, hot paths, allocations, data structures. **If the target is ambiguous: stop and ask which function or package.**
2. **Check existing benchmarks.** Grep for existing `Benchmark*` functions covering the target. **If a comparable benchmark already exists: stop and report it.** Do not duplicate.
3. **Write or update the benchmark.** Pick the right pattern:
   - Single function → basic `for b.Loop()` pattern
   - Variants or sizes → sub-benchmark with `b.Run()`
   - Concurrent code → `b.RunParallel()`
   - Throughput-bound → `b.SetBytes()`
4. **Run.** Quick: `go test -bench=BenchmarkName -benchmem -run=^$ ./path/to/package`. Statistically rigorous (always for comparisons): `-count=10` with `benchstat`. Across CPU counts: `-cpu=1,2,4,8`.
5. **Analyze.** Identify hotspots and allocations via the [Optimization Checklist](#optimization-checklist-go). If raw numbers are insufficient, profile with `-cpuprofile`/`-memprofile`.
6. **Report.** Formatted `go test -bench` output, key findings (hotspots, allocations, throughput), specific optimization suggestions with code ordered by expected impact. For before/after: `benchstat` output with significance analysis.
7. **Verify.** Confirm the benchmark compiles and runs cleanly. **If it fails to compile or panics: stop and fix before reporting.**

**Patterns to follow.** Use `b.Loop()` for the benchmark loop. Call `b.ResetTimer()` after expensive one-time setup. Use `b.Run()` for sub-benchmarks. Use `b.SetBytes(n)` when processing a known amount of data. Use `b.RunParallel()` for concurrent measurement. `b.ReportMetric()` for domain-specific measurements.

```go
func BenchmarkParse(b *testing.B) {
    input := []byte(`{"key": "value"}`)
    for b.Loop() {
        Parse(input)
    }
}
```

```go
func BenchmarkEncode(b *testing.B) {
    sizes := []int{64, 256, 1024, 4096}
    for _, size := range sizes {
        b.Run(fmt.Sprintf("size=%d", size), func(b *testing.B) {
            data := make([]byte, size)
            b.ResetTimer()
            for b.Loop() {
                Encode(data)
            }
        })
    }
}
```

**Running.** Always use `-run=^$` to skip unit tests. Always use `-benchmem`. **Never use `-race` when benchmarking — it distorts timings.**

**Comparing before/after.** Always use `benchstat` — never eyeball raw numbers.

```bash
go test -bench=BenchmarkName -benchmem -run=^$ -count=N ./pkg > old.txt
# ... make changes ...
go test -bench=BenchmarkName -benchmem -run=^$ -count=N ./pkg > new.txt
benchstat old.txt new.txt
```

Always report **time/op** change with p-value, **allocs/op**, and **B/op**. Never omit a regression because it is small — regardless of magnitude, a regression is a regression.

**Profiling.**

```bash
go test -bench=BenchmarkName -run=^$ -cpuprofile=cpu.out -memprofile=mem.out ./pkg
go tool pprof -top cpu.out
```

Available: `-cpuprofile`, `-memprofile`, `-blockprofile`, `-mutexprofile`.

#### Optimization checklist (Go)

- **High allocs/op** — slices without size hints, string concatenation, interface boxing, closures capturing variables in hot loops
- **Unnecessary copies** — large structs passed by value, `range` over large values
- **String/byte conversions** — repeated `[]byte(s)` or `string(b)` in hot paths
- **Map overhead** — map operations in hot loops; profile to confirm hash cost is justified
- **Sync overhead** — lock contention; profile with `-mutexprofile`
- **Interface dispatch** — hot-path virtual calls; consider generics or concrete types
- **Inefficient I/O** — unbuffered reads/writes; wrap with `bufio`

### 3. Dispatch — `py`

Replicates the prior `/py-bench` skill.

1. **Identify what to benchmark.** Functions called frequently, processing large inputs, or on latency-sensitive paths. One benchmark function per distinct operation or input class. If no benchmarks exist, write them before optimizing (measure first, optimize second).
2. **Write the benchmark.** Prefer `pytest-benchmark`:
   ```python
   def test_foo_benchmark(benchmark):
       input_data = prepare_input()
       result = benchmark(foo, input_data)
       assert result is not None  # always assert to prevent dead-code elimination
   ```
   Parameterize for input sizes:
   ```python
   @pytest.mark.parametrize("n", [10, 100, 1000, 10_000])
   def test_foo_benchmark(benchmark, n):
       input_data = make_input(n)
       benchmark(foo, input_data)
   ```
   `timeit` for quick one-off measurements:
   ```python
   import timeit
   result = timeit.timeit(stmt="foo(input_data)",
       setup="from mymodule import foo; input_data = prepare_input()", number=10_000)
   print(f"{result / 10_000 * 1e6:.2f} µs per call")
   ```
3. **Run.**
   ```bash
   pytest --benchmark-only
   pytest --benchmark-only tests/test_foo.py::test_foo_benchmark
   pytest --benchmark-only --benchmark-save=baseline
   pytest --benchmark-only --benchmark-compare=baseline
   pytest --benchmark-only --benchmark-histogram
   ```
   Install if needed: `uv add --dev pytest-benchmark`.
4. **Profile for root cause.** `cProfile` for function-level call counts and times: `python -m cProfile -s cumtime -m pytest tests/test_foo.py::test_foo_benchmark`. `py-spy` for sampling without code changes: `py-spy top --pid <PID>` or `py-spy record -o profile.svg -- python -m pytest tests/test_foo.py` (install with `uv tool install py-spy`).
5. **Interpret pytest-benchmark output.** `Min` (best-case, most representative for CPU-bound), `Mean` (watch StdDev/Mean > 10% for noise), `Rounds` (how many iterations). Red flags: high StdDev relative to Mean → move I/O and allocation out of the measured call; linear growth in time as input grows when O(1)/O(log n) expected; unexpected regressions in `--benchmark-compare`.
6. **Apply optimizations.** Apply each directive when profiling identifies the matching pattern; do not apply blindly. Always use list comprehensions over manual `append` in measured hot paths. Always bind looked-up attributes to local variables before tight loops. Always use `__slots__` for classes with many small instances. Always use `functools.lru_cache`/`cache` for pure functions with repeated identical inputs. Always vectorize numeric loops with NumPy when the operation is element-wise. Never concatenate strings in a loop — use `io.BytesIO`/`io.StringIO` or `"".join()`. Always bind `len()` to a local if called in a tight loop.
7. **Verify.** Re-run the benchmark. Confirm the change is measurable and not within noise.

**Rules for `py`.** Never optimize without a benchmark showing the problem — measure first. A benchmark that passes instantly may be testing nothing; verify with `--benchmark-verbose`. Do not commit benchmarks requiring network or large fixtures without a `pytest.mark.slow` guard. Always assert a result in pytest-benchmark tests.

### 4. Dispatch — `nvim`

Replicates the prior `/nvim-bench` skill.

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

6. **Apply optimizations.** Apply each directive when profiling identifies the matching pattern. Always cache `require()` results at the top of the file — never inside callbacks. Always use `vim.schedule` for deferred non-urgent work. Always batch API calls (one `nvim_buf_set_lines` for the whole range, not one per line). Always pre-allocate option tables used in tight loops. Always lazy-load plugin submodules with `__index`. Never call `vim.tbl_deep_extend` on large tables in hot paths.
7. **Verify.** Re-run with a fresh `nvim`. Confirm the change is measurable per `vim.loop.hrtime()` and not within noise. **If within noise or regresses: revert and report.**

**Rules for `nvim`.** Never optimize without a measurement. Exclude `require()` from the timed loop unless module load time is the target. For startup benchmarks, always use a fresh process. **Never `:source` a benchmark in a running session** — the Lua module cache persists across `:source` and gives misleading sub-µs results. Always `package.loaded["my_module"] = nil` before re-requiring in function-level benchmarks. Do not commit benchmark scripts to `lua/` — place them in `bench/` and `.gitignore` the directory.

### 5. Final verification step

Each dispatch above ends with a verification gate (re-run benchmark, confirm change is measurable, not within run-to-run variance). Before exiting, confirm the gate fired.

## Rules (apply across all languages)

- Always measure before optimizing.
- For comparisons, always use the language's significance tool (`benchstat`, `pytest-benchmark --benchmark-compare`, `vim.loop.hrtime` diff).
- Never include race detection or coverage instrumentation in a benchmark run — both distort timing.
- A benchmark that produces sub-µs results "too fast to be real" almost always indicates dead-code elimination, cached imports, or measurement noise — verify before trusting.
