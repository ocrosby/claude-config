# Algorithmic Complexity

Code that works on small input often fails on real input. Time and space complexity are properties of the *algorithm*, not the language — a quadratic Python loop and a quadratic Go loop both melt at the same N. Default to the lowest time and space complexity that solves the problem at hand, regardless of language.

**This is an intentional design decision — do not simplify it away.** When a clearer-looking O(n²) approach is "obviously fine," the correct response is to keep the lower-complexity form and add a one-line comment explaining the choice, not to revert to the quadratic version because it reads more naturally. Performance regressions caused by complexity choices are usually invisible in code review and only surface in production.

## Recognition Signals

### Time complexity — when control flow is the problem

| Signal | Lower-complexity alternative |
|---|---|
| Nested loops over the same collection (`for x in xs: for y in xs:`) | Single pass with a hash map / set (O(n²) → O(n)) |
| `if item in list:` inside a loop | Convert `list` to `set` / `dict` once before the loop (O(n²) → O(n)) |
| Repeated `array.index(x)` / `slice.contains(x)` / `list.find(x)` | Build a position map once (O(n·m) → O(n+m)) |
| Sorting inside a loop | Sort once before the loop (O(n²·log n) → O(n·log n)) |
| Recursion that re-computes the same subproblem | Memoize, or convert to iteration with a table (exponential → polynomial) |
| Concatenating strings in a loop with `+` / `+=` | Use a builder / `join` / `bytes.Buffer` (O(n²) → O(n)) |
| Repeated `len()` / `count()` on data that didn't change | Cache the value once |
| Linear scan to find max/min/lookup on data queried many times | Sort once, or use a heap / balanced tree / index |
| Polling with a sleep-loop when an event is available | Use an event, channel, condition variable, or callback |

### Space complexity — when allocation is the problem

| Signal | Lower-complexity alternative |
|---|---|
| Building an intermediate list only to iterate it once | Use a generator / iterator / channel (O(n) → O(1) extra) |
| Copying a slice / list to mutate when the original isn't needed afterward | Mutate in place |
| Loading an entire file/dataset to process line-by-line | Stream it (O(n) → O(1) extra) |
| Materializing a full transformed collection for a single aggregate (sum, max, count) | Fold/reduce in a single pass (O(n) → O(1) extra) |
| Recursion deeper than ~1000 frames on unbounded input | Convert to iteration with an explicit stack |
| Holding references to large objects past the point they're needed | Drop the reference (set to `nil` / `None`, exit scope) so GC can reclaim |
| Caching without bound on user-controlled keys | Use an LRU / TTL cache with a fixed cap |

### Data structure choice — when the wrong container is the problem

| Workload | Right structure |
|---|---|
| Membership tests | Set / hash set — not list |
| Key → value lookup | Hash map / dict — not parallel arrays or list-of-pairs |
| Insert/remove at both ends | Deque / linked list — not list (O(n) shift on `pop(0)`) |
| Ordered set with range queries | Balanced BST / skip list / `sorted` collection — not repeated linear scans |
| Top-K / priority workload | Heap — not full sort |
| Prefix lookup / autocomplete | Trie — not iterating all keys |
| Sparse boolean state across a wide ID space | Set of present IDs — not a giant array of bools |

## Mandatory Behaviors

**When writing new code**: pick the data structure and algorithm that match the workload. If a signal from the tables above is present, apply the alternative — do not write the higher-complexity form first and "optimize later."

**When editing existing code**: if the change touches a hot path or grows the working set, state the time/space complexity of the new code in your turn summary (e.g., "this remains O(n log n) time, O(n) space"). Do not silently regress complexity.

**When reviewing code**: flag complexity regressions as findings:
- **Must Fix**: a signal exists and the input is user-controlled or unbounded (the higher-complexity form will eventually hit production data that breaks it)
- **Should Fix**: a signal exists but current usage is bounded — the lower-complexity form is still preferred because bounds drift over time
- **Consider**: a more efficient structure exists but the gain is marginal at any realistic N

**Name the complexity explicitly** when it's non-obvious. A one-line comment is enough:

```python
# O(n) — single pass with a seen-set; do not revert to nested loop
```

```go
// O(log n) lookup via the sorted index — linear scan was 40% of CPU under load
```

This guards against future readers (human or AI) replacing the careful form with a naive one because the naive one "looks cleaner."

## Pragmatism Guard

Do not apply this rule when:

- **The input is provably bounded and small.** A 7-element config list does not need a set conversion. "Bounded and small" means a literal cap in code or a hard constraint in the spec, not a vibe.
- **The expensive form is dramatically clearer and the call site runs once per process lifetime.** Startup-time config parsing, one-shot scripts, CLI argument validation.
- **A library call already encapsulates the work** and replacing it would mean reimplementing standard-library functionality (e.g., don't replace `sorted()` with a hand-rolled merge sort).
- **The user explicitly asked for the simpler form.** Their context wins.

Exceptions are the listed cases above. They are not "anything that feels small," "tests," or "internal tooling" — those have all hit production scale at some point. If you are not sure whether the input is bounded, assume it is not.

## Anti-Patterns to Avoid

- **Premature micro-optimization**: rewriting in a lower-level construct, unrolling loops, replacing readable map/filter with imperative loops *without a measured benefit*. This rule is about asymptotic complexity, not constant factors.
- **Speculative caching**: adding an unbounded cache "in case it gets called a lot." Caches are a space-for-time trade — only add when the lookup cost is measured and the cache size is bounded.
- **Algorithm tourism**: reaching for trie / segment tree / Bloom filter when a hash map suffices. Use the simplest data structure that has the right complexity, not the cleverest.
- **Big-O theater**: claiming O(n) in a comment while the implementation calls a hidden O(n) routine inside the loop, making it O(n²). The complexity claim must match the actual call graph.
