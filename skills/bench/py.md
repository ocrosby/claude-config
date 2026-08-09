# Bench: Python

1. **Identify what to benchmark.** Functions called frequently, processing large inputs, or on latency-sensitive paths. One benchmark function per distinct operation or input class. If no benchmarks exist, write them before optimizing (measure first, optimize second).
2. **Write the benchmark.** Always use `pytest-benchmark`:
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
6. **Apply optimizations.** Each directive below already names its own trigger condition (hot path, tight loop, repeated identical inputs, etc.) — apply it whenever profiling shows that condition. Always use list comprehensions over manual `append` in measured hot paths. Always bind looked-up attributes to local variables before tight loops. Always use `__slots__` for classes with many small instances. Always use `functools.lru_cache`/`cache` for pure functions with repeated identical inputs. Always vectorize numeric loops with NumPy when the operation is element-wise. Never concatenate strings in a loop — use `io.BytesIO`/`io.StringIO` or `"".join()`. Always bind `len()` to a local if called in a tight loop.
7. **Verify.** Re-run the benchmark. Confirm the change is measurable and not within noise.

**Rules for `py`.** Never optimize without a benchmark showing the problem — measure first. A benchmark that passes instantly may be testing nothing; verify with `--benchmark-verbose`. Do not commit benchmarks requiring network or large fixtures without a `pytest.mark.slow` guard. Always assert a result in pytest-benchmark tests.
