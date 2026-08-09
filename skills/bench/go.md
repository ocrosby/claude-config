# Bench: Go

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
