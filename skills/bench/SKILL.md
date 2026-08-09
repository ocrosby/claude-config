---
description: Use when writing, running, or analyzing benchmarks in a Go, Python, or Neovim/Lua codebase. Auto-detects language from cwd; override with /bench <go|py|nvim> [description].
argument-hint: "[language] [description]"
aliases: go-bench, py-bench, nvim-bench
allowed-tools: Read, Grep, Glob, Edit, Write, Bash(go test *), Bash(go tool *), Bash(benchstat *), Bash(pytest *), Bash(python *), Bash(py-spy *), Bash(nvim *), Bash(uv *)
---

# Bench: Language-Aware Benchmarking

Use this skill when writing, running, or analyzing benchmarks in a Go, Python, or Neovim codebase. The dispatcher detects the language from cwd and applies the matching tools and patterns.

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
set -- $ARGUMENTS
bash ~/.claude/scripts/detect_language.sh "${1-}"
```

`set --` populates shell positional params from `$ARGUMENTS` so `${1-}` resolves to the first token (the explicit override, possibly empty). **If the script is not found or exits non-zero: stop and do not proceed. Tell the user to reinstall via `stow -t ~/.claude -d ~/src/github.com/ocrosby claude-config`.** Returns `go`, `py`, `nvim`, `gherkin`, `rest`, or `unknown`. `gherkin` and `rest` are not supported by `bench` — **stop and do not proceed**. On `unknown`: **stop and do not proceed** — ask the user. Otherwise drop the consumed override token and dispatch.

### 2. Dispatch — `go`

Read `~/.claude/skills/bench/go.md` and apply its workflow:

- Reading the code under test, checking for existing benchmarks
- Benchmark patterns (`b.Loop()`, `b.Run()`, `b.RunParallel()`, `b.SetBytes()`) with templates
- Running (`-run=^$`, `-benchmem`, `-count`, `-cpu`) and comparing with `benchstat`
- Profiling (`-cpuprofile`/`-memprofile`, `go tool pprof`)
- Optimization checklist (Go)

### 3. Dispatch — `py`

Read `~/.claude/skills/bench/py.md` and apply its workflow:

- Identifying what to benchmark
- `pytest-benchmark` templates (parameterized sizes, `timeit` one-offs)
- Running and comparing (`--benchmark-only`, `--benchmark-save`/`--benchmark-compare`)
- Profiling with `cProfile` and `py-spy`
- Interpreting output and applying optimizations
- Rules for `py`

### 4. Dispatch — `nvim`

Read `~/.claude/skills/bench/nvim.md` and apply its workflow:

- Identifying the benchmark category (startup, callbacks, expensive ops, comparison)
- Timing templates (`vim.loop.hrtime()`, `os.clock()`, `--startuptime`, `:Lazy profile`)
- Running and comparing before/after with module-cache reset
- Interpreting measurements and red flags
- Applying optimizations
- Rules for `nvim`

### 5. Final verification step

Each dispatch above ends with a verification gate (re-run benchmark, confirm change is measurable, not within run-to-run variance). Before exiting, confirm the gate fired.

## Rules (apply across all languages)

- Always measure before optimizing.
- For comparisons, always use the language's significance tool (`benchstat`, `pytest-benchmark --benchmark-compare`, `vim.loop.hrtime` diff).
- Never include race detection or coverage instrumentation in a benchmark run — both distort timing.
- A benchmark that produces sub-µs results "too fast to be real" almost always indicates dead-code elimination, cached imports, or measurement noise — verify before trusting.
