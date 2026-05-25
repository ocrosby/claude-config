---
description: Write, run, and analyze Go benchmarks. Use when the user asks to benchmark Go code, optimize performance, compare benchmark results, or investigate allocations and throughput.
argument-hint: "[description]"
allowed-tools: Read, Grep, Glob, Edit, Write, Bash(go test *), Bash(go tool *), Bash(benchstat *)
---

# Go Benchmarking

Use this skill when you want to write, run, or analyze Go benchmarks for a function, package, or performance comparison.

## Usage

```
/go-bench                           # benchmark the current package, derive intent from context
/go-bench <description>             # natural-language description of what to measure
```

## Workflow

### 1. Read the code under test

Read the target function signatures, hot paths, allocations, and data structures before writing anything. **If the target is ambiguous: stop and ask which function or package to benchmark.**

### 2. Check existing benchmarks

Grep the package for existing `Benchmark*` functions covering the target code. **If a comparable benchmark already exists: stop and report it.** Do not duplicate.

### 3. Write or update the benchmark

Use the patterns under [Writing Benchmarks](#writing-benchmarks). Apply the right pattern for the target:
- Single function → basic `for b.Loop()` pattern
- Variants or sizes → sub-benchmark with `b.Run()`
- Concurrent code → `b.RunParallel()`
- Throughput-bound → `b.SetBytes()`

### 4. Run the benchmark

Use the commands under [Running Benchmarks](#running-benchmarks). For a quick check, one run is fine; for comparisons or any decision-relevant number, always use `-count=10` with `benchstat`.

### 5. Analyze results

Identify hotspots and allocation patterns using the [Optimization Checklist](#optimization-checklist). If raw benchmark numbers are insufficient, profile with `-cpuprofile` / `-memprofile`.

### 6. Report

Present:
- Benchmark output (formatted `go test -bench` results)
- Key findings: hotspots, allocation patterns, throughput
- Specific optimization suggestions with code, ordered by expected impact
- For before/after: `benchstat` output with significance analysis

### 7. Verify

Confirm the benchmark compiles and runs cleanly without `-race` distortion. **If the benchmark fails to compile or panics: stop and fix before reporting results.**

---

## Writing Benchmarks

### Basic pattern

Always use `b.Loop()` for the benchmark loop.

```go
func BenchmarkParse(b *testing.B) {
    input := []byte(`{"key": "value"}`)
    for b.Loop() {
        Parse(input)
    }
}
```

### Timer control

Always call `b.ResetTimer()` after expensive one-time setup.

```go
func BenchmarkProcess(b *testing.B) {
    data := generateLargeDataset()
    b.ResetTimer()
    for b.Loop() {
        Process(data)
    }
}
```

### Sub-benchmarks

Always use `b.Run()` when comparing variants, input sizes, or implementations.

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

### Throughput

Always call `b.SetBytes(n)` when the benchmark processes a known amount of data.

```go
func BenchmarkRead(b *testing.B) {
    buf := make([]byte, 4096)
    b.SetBytes(int64(len(buf)))
    for b.Loop() {
        Read(buf)
    }
}
```

### Parallel benchmarks

Use `b.RunParallel()` to measure performance under concurrent load.

```go
func BenchmarkConcurrentGet(b *testing.B) {
    cache := NewCache()
    b.ResetTimer()
    b.RunParallel(func(pb *testing.PB) {
        for pb.Next() {
            cache.Get("key")
        }
    })
}
```

### Custom metrics

Use `b.ReportMetric()` for domain-specific measurements:

```go
b.ReportMetric(float64(itemsProcessed)/elapsed.Seconds(), "items/s")
```

---

## Running Benchmarks

Always use `-run=^$` to skip unit tests. Always use `-benchmem`. Never use `-race` when benchmarking — it distorts timings.

### Quick run

```bash
go test -bench=BenchmarkName -benchmem -run=^$ ./path/to/package
```

### Statistically rigorous run

```bash
go test -bench=BenchmarkName -benchmem -run=^$ -count=10 ./path/to/package
```

### Across CPU counts

```bash
go test -bench=BenchmarkName -benchmem -run=^$ -cpu=1,2,4,8 ./path/to/package
```

### Comparing before/after

Always use `benchstat` — never eyeball raw numbers.

```bash
go test -bench=BenchmarkName -benchmem -run=^$ -count=N ./pkg > old.txt
# ... make changes ...
go test -bench=BenchmarkName -benchmem -run=^$ -count=N ./pkg > new.txt
benchstat old.txt new.txt
```

Focus on **time/op** change with p-value, **allocs/op**, **B/op**, and any regressions even if small.

### Profiling

```bash
go test -bench=BenchmarkName -run=^$ -cpuprofile=cpu.out -memprofile=mem.out ./pkg
go tool pprof -top cpu.out
```

Available profiles: `-cpuprofile`, `-memprofile`, `-blockprofile`, `-mutexprofile`.

---

## Optimization Checklist

When analyzing results, check for:

- **High allocs/op** — allocations inside hot loops (slices without size hints, string concatenation, interface boxing, closures capturing variables)
- **Unnecessary copies** — large structs passed by value, `range` over large values
- **String/byte conversions** — repeated `[]byte(s)` or `string(b)` in hot paths
- **Map overhead** — map operations in hot loops; profile to confirm hash cost is justified
- **Sync overhead** — lock contention under concurrent load; profile with `-mutexprofile`
- **Interface dispatch** — hot-path virtual calls; consider generics or concrete types
- **Inefficient I/O** — unbuffered reads/writes; wrap with `bufio`
