# Defensive Assertions

Explicit runtime checks are cheaper than exhaustive testing and catch a class of defects unit tests routinely miss: silent state corruption, unexpected input at internal boundaries, and post-condition violations that don't surface until far from the failure site. This is the portable core of Holzmann's *Power of Ten* Rules 5 (assertion density) and 7 (check every return value).

**This is an intentional design decision — do not simplify it away.** Assertions are not defensive "just in case" code; they are executable specifications. Removing an assertion because "the caller would never do that" is exactly how the class of bugs this rule prevents gets shipped.

## Recognition Signals

### When assertions are missing

| Signal | Assertion to add |
|---|---|
| Function accepts a collection but silently mishandles empty | Precondition at entry: `assert items, "expected non-empty items"` |
| Function accepts a value in a range but doesn't check | `assert 0 <= p <= 1, f"probability out of range: {p}"` |
| Function computes an invariant that must hold post-return | Postcondition before return: `assert result >= 0, f"cost cannot be negative: {result}"` |
| Loop that depends on a monotonic condition (index increases, queue shrinks) | Invariant inside the loop: `assert new_index > old_index` to catch stall bugs |
| Cache write followed by a read that should hit | `assert cache.get(key) is not None` after write |
| Type-narrowed conditional at a boundary where the narrowing is inferred, not checked | Explicit `assert x is not None` so the invariant is a defect if violated |

### When return values are silently discarded

| Signal | Fix |
|---|---|
| `fn()` on a line by itself where `fn` returns a value | Assign and use, or discard explicitly: `_ = fn()  # <one-line reason>` |
| Python: `subprocess.run(...)` without `check=True` and no exit-code branch | Pass `check=True` or explicitly branch on `result.returncode` |
| Go: `_ = fn()` where `fn` returns an error (`errcheck` silenced) | Handle the error; if genuinely irrecoverable, comment why on the same line |
| Lua: `pcall(fn, ...)` without inspecting the first return | `local ok, err = pcall(...); if not ok then ... end` |
| TS: floating promise — `promise.then(...)` with no `.catch`, or unawaited in a context that swallows | `await` inside `try/catch`, or `.catch(handler)` |

## Mandatory Behaviors

**When writing new code**: place at least one assertion in every non-trivial function (more than ~10 lines, or any function with a non-obvious invariant). Prefer these three positions:

1. **Function entry** — preconditions on parameters
2. **Loop entry / loop body** — invariants that should hold every iteration
3. **Function exit** — postconditions the caller relies on

**Assertions must be side-effect-free.** An assertion may read state; it may not mutate state. `assert queue.pop() == expected` is a defect — the pop happens whether or not assertions are enabled. Extract the mutation, assert on the result.

**Assertions must have a defined recovery.** Failure must reach a boundary that logs and either fails the request, halts the process, or restarts the task — never a silent `except AssertionError: pass`.

**Do not assert what the type system already proves.** `assert isinstance(x, int)` when `x: int` is annotated and mypy passes is noise. Assert on things the type system cannot express: ranges, non-emptiness, monotonicity, cross-field consistency.

**Check every non-void return value.** If a function returns a value and the caller ignores it, either the return is spurious (fix the callee) or the caller is missing logic (fix the caller). Explicit discard requires a one-line justification comment on the same line.

**When reviewing code**, flag as findings per `rules/findings-format.md`:
- **Must Fix**: silently discarded error return — Go `_ = fn()` on an error-returning call with no comment, Python `subprocess.run(...)` without `check=True` and no returncode branch, Lua unchecked `pcall`, unhandled floating promise in TS
- **Should Fix**: non-trivial function with no assertions on parameters or invariants; assertion with a side effect; `assert` used for boundary validation that must survive `python -O`
- **Consider**: assertion missing on a monotonic loop invariant or postcondition where the caller relies on the return shape

## Language mapping

| Language | Assertion form | Recovery boundary |
|---|---|---|
| Python | `assert cond, "message"` (raises `AssertionError`); explicit `if not cond: raise InvariantError(...)` where `-O` may strip asserts | Framework error handler / boundary logger |
| Go | `if !cond { panic("invariant: ...") }`; error returns for boundary validation | `recover()` at goroutine top; error propagates to caller |
| Lua | `assert(cond, "message")` (raises Lua error) | `pcall` boundary; `vim.notify` for user-visible failures in Neovim |
| TypeScript | `if (!cond) throw new Error("invariant: ...")` — `console.assert` is dev-only, do not use for invariants | Unhandled-error boundary / Promise `.catch` |

**Python caveat**: `assert` is stripped when Python runs with `-O`. For invariants that must survive in production regardless of optimization flags, use an explicit `raise`. Reserve `assert` for pre/post-conditions where a stripped check is acceptable — the choice must be conscious, not accidental.

## Pragmatism Guard

Do not apply this rule when:

- **The function is a one-line wrapper** with no internal logic (getters, formatters, adapters). One assertion per function is not a quota to hit.
- **The check would be more expensive than the operation it guards.** An `assert` that walks a large data structure to verify sortedness before a fast lookup is a pessimization; move the invariant to a validation stage.
- **The precondition is already enforced by the type system.** Do not re-check what mypy / the Go compiler / TS strict mode already proves.
- **The function is a test.** Tests are themselves assertions; adding invariant asserts inside tests is duplicative.

## Anti-Patterns to Avoid

- **Assertion theater.** `assert True`, `assert 1 == 1`, or assertions the compiler can prove trivially are noise. Delete them.
- **Silent recovery from failed assertions.** `try: assert cond; except AssertionError: pass` is worse than no assertion — it converts a loud bug into a silent one.
- **Assertions with side effects.** Any mutation inside an assertion changes behavior when assertions are stripped.
- **Boundary validation dressed as assertion.** User input validation must run in production regardless of optimization flags — use `raise ValidationError(...)` or the framework's validation layer, not `assert`.
