---
description: Go error handling — wrapping, sentinels, typed-nil hazards, panic discipline.
paths:
  - "**/*.go"
---

# Go Error Handling

- Always check returned errors — never `_ = doSomething()`
- Wrap errors with context: `fmt.Errorf("creating user: %w", err)`
- Use sentinel errors (`var ErrNotFound = errors.New(...)`) for expected conditions
- Use custom error types when the caller needs to inspect error details
- Return early on error — avoid deep nesting
- Annotate and return in one expression: `return fmt.Errorf("opening config: %w", err)` — reduces the chance of logging and then forgetting to return
- Log OR return an error — never both; logging and returning creates duplicate messages and obscures origin
- Error strings should identify their origin with a prefix: `"image: unknown format"`
- Use `errors.As` / type assertions to inspect error details for recoverable failures
- `panic` only for truly unrecoverable situations (e.g., failed critical initialization)
- Real library functions should avoid `panic` — if it can be worked around, return an error
- Use `recover` only inside deferred functions to convert panics to errors at package boundaries

## Typed-nil interface hazard

A typed nil (`(*T)(nil)`) assigned to an interface variable produces a **non-nil interface**. Any function that accepts an `error` (or other interface) and stores it may silently preserve this hazard, causing unexpected non-nil checks and broken `Error()` output downstream.

**Rule**: functions that accept an `error` parameter and store it must guard against typed nils at the point of storage — do not leave the detection to callers or documentation.

```go
// Bad — silently stores a typed nil; downstream error checks behave unexpectedly
func Wrap(code ErrorCode, msg string, cause error) *AppError {
    return &AppError{code: code, message: msg, err: cause}
}

// Good — normalise typed nils to untyped nil at the boundary
func Wrap(code ErrorCode, msg string, cause error) *AppError {
    if cause != nil && reflect.ValueOf(cause).IsNil() {
        cause = nil
    }
    return &AppError{code: code, message: msg, err: cause}
}
```

The guard applies whenever:
- A function accepts an `error` parameter and stores it in a struct field, slice, or map
- The function is part of a library or shared package where callers are not fully controlled

A doc comment saying "don't pass a typed nil" is **not** a substitute for the guard — documentation is ignored; runtime guards are not.
