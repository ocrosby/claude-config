---
paths:
  - "**/*.go"
  - "**/go.mod"
  - "**/go.sum"
---

# Go Conventions

> Concurrency patterns live in `go-concurrency.md`. It loads alongside this file when editing `.go` sources.

## Principles

- Simplicity over cleverness — write boring, obvious code
- Accept interfaces, return structs
- Composition over inheritance — embed structs, don't simulate class hierarchies
- Dependency injection via constructor functions — pass dependencies in, never use globals
- Push side effects to the edges; keep core logic pure and testable
- Errors are values — handle them explicitly, never ignore
- Design types so the zero value is useful without initialization (like `sync.Mutex`, `bytes.Buffer`)
- Do not communicate by sharing memory; share memory by communicating
- A little copying is better than a little dependency — avoid importing a package just to use one function
- Reflection is never clear — prefer type-safe code; use `reflect` only when no alternative exists
- Leave concurrency to the caller — functions should be synchronous by default; callers can always wrap with goroutines

**These principles are intentional design decisions — do not simplify them away.** When code grows complex (many injected dependencies, verbose constructors, large interfaces), the correct response is to split and simplify the design, not to revert to globals, singletons, or package-level state. Complexity is a signal to refactor, not to abandon the principle.

## Interfaces

- Keep interfaces small — one or two methods
- Define interfaces where they are consumed, not where they are implemented
- Use `io.Reader`, `io.Writer`, `fmt.Stringer` and other stdlib interfaces where they fit
- Name single-method interfaces with the `-er` suffix: `Reader`, `Validator`, `Notifier`

## Naming

- Short, descriptive variable names — `r` for reader, `ctx` for context, `cfg` for config
- Avoid stuttering: `user.Name` not `user.UserName`
- Exported names are PascalCase, unexported are camelCase
- Package names are lowercase, single word — no underscores or mixedCaps
- Package names describe the service provided, not the types contained: `encoding` not `encoders`
- Avoid generic package names that communicate nothing: `utils`, `helpers`, `common`, `base` signal a design problem — split by function instead
- Test helpers start with `test` or `new` in test files
- Getters omit `Get`: `Owner()` not `GetOwner()`, setters use `Set`: `SetOwner()`
- Don't reuse canonical method names (`Read`, `Write`, `Close`, `String`) unless the signature and meaning match
- When the package exports a single primary type, name the constructor `New` (e.g., `ring.New`), otherwise `NewTypeName`
- MixedCaps or mixedCaps for multi-word names — never underscores
- Acronyms are uniformly cased: exported `OAuthEnabled`, `HTTPClient`; unexported `oauthEnabled`, `httpClient` — never `oAuthEnabled` or `hTTPClient`
- Variable names must not include type suffixes: `users` not `usersMap`, `cfg` not `configPtr` — the type system enforces types, names should communicate purpose
- Identifier length scales with scope: single-letter (`i`, `r`) for innermost scopes; full descriptive names for package-level declarations
- Omit unused receiver names: `func (foo) Method()` not `func (f foo) Method()` when the receiver is not accessed

## Allocation and Data

- Understand `new` vs `make`: `new(T)` returns `*T` zeroed; `make` initializes slices, maps, and channels
- Prefer composite literals with named fields: `&File{fd: fd, name: name}` over field-by-field assignment
- Prefer slices over arrays — arrays are values (copied on assignment/pass), slices are references
- Always reassign the result of `append`: `s = append(s, x)` — the underlying array may change
- Use the comma-ok idiom to distinguish missing map keys from zero values: `v, ok := m[key]`
- Use maps with `bool` values for sets: `seen[item] = true`

## Control Flow

- Return early on error — eliminate `else` when the `if` body ends in `return`, `break`, or `continue`
- Use expression-less `switch` for cleaner `if-else` chains
- Use type switches for interface value inspection: `switch v := x.(type)`
- Use labeled `break`/`continue` to escape an outer loop from inside a `switch` or inner loop
- No automatic fall-through in `switch` — use comma-separated cases: `case ' ', '?', '&':`
- Use `defer` for cleanup (close files, unlock mutexes) — place it right after the resource is acquired
- Deferred calls execute LIFO; arguments are evaluated at the `defer` statement, not at execution

## Error Handling

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

### Typed-nil interface hazard

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

## API Design

- Synchronous API by default — expose sync functions; callers decide whether to call from a goroutine
- Prefer variadic parameters over slice parameters when callers pass a variable number of items: `Process(ids ...string)` not `Process(ids []string)`
- Avoid multiple parameters of the same type side-by-side — they invite silent argument ordering bugs; use named types or a struct instead:

```go
// Bad — src and dst are easily swapped
func CopyFile(src, dst string) error

// Good — named type makes intent unambiguous
type Destination string
func CopyFile(src string, dst Destination) error
```

- Don't use `nil` as a stand-in for optional parameters — prefer functional options or explicit config structs
- Use `time.Duration` for time values: `30 * time.Second` not bare integer constants with a comments explaining units

## Methods and Receivers

- Value receivers for read-only methods; pointer receivers when the method mutates the receiver or the struct is large
- Value methods can be invoked on both pointers and values; pointer methods only on pointers (or addressable values)
- If any method has a pointer receiver, all methods on that type should use pointer receivers for consistency

## Embedding

- Embed types for method promotion — avoids manual forwarding methods
- Embedded type's methods receive the inner type as receiver, not the outer type (not subclassing)
- An outer field or method shadows an embedded one with the same name
- Use embedding to satisfy interfaces (e.g., embed `io.Reader` in a struct to implement `io.Reader`)
- Initialize embedded fields in constructors: `&Job{command, log.New(os.Stderr, "Job: ", log.Ldate)}`

## Blank Identifier

- Never discard errors: `fi, _ := os.Stat(path)` is a bug waiting to happen
- Use blank import for side effects only: `import _ "net/http/pprof"`
- Use compile-time interface checks: `var _ json.Marshaler = (*MyType)(nil)`
- Only add interface compliance checks when there are no static conversions already in the code

## Comments and Spelling

- Spell using American English: `marshaling`, `unmarshaling`, `canceling`, `canceled`, `cancellation` (not British variants)
- Single space between sentences in doc comments — not double space
- Compiler directives use no space: `//go:generate`, `//go:build` — this distinguishes them from regular comments

## Idiomatic Go

- Use `context.Context` for cancellation, deadlines, and request-scoped values
- Use `table-driven tests` for data variations
- Use `t.Helper()` in test helper functions
- Prefer `strings.Builder` for string concatenation
- Use `slices` and `maps` packages (Go 1.21+) over manual loops where they simplify
- Use structured logging (`log/slog`) over `log.Printf`
- Export interfaces, not types, when a type exists only to implement an interface — return the interface from constructors
- Use the `HandlerFunc` adapter pattern to convert functions into interface implementations
- Use `var x T` when declaring without initializing; use `x := val` when declaring and initializing — makes initialization intent explicit
- Check empty string as `s == ""`, not `len(s) == 0` — the former makes it clear `s` is a string, not a slice
- Place a mutex immediately above the fields it protects, separated from unrelated fields by a blank line; this communicates protection scope without a comment:

```go
type Cache struct {
    client *http.Client  // unprotected

    mu    sync.RWMutex
    items map[string]Item  // protected by mu
}
```

## Security

> See `owasp-top-10.md` for the general signal table and mandatory behaviors. This section lists the Go-specific *how*.

### SQL — parameterized queries

Use the driver's placeholder (`$1` for pgx/lib-pq, `?` for mysql/sqlite). Never `fmt.Sprintf` or `+` to build SQL.

```go
row := db.QueryRowContext(ctx, "SELECT * FROM users WHERE email = $1", email)
```

### Subprocess — argument list, never `sh -c`

```go
exec.Command("grep", "--", userInput, filename)   // no shell
```

Use `--` to terminate flag parsing before any user-supplied positional argument.

### Path traversal — confine to base

```go
clean := filepath.Clean(filepath.Join(baseDir, userPath))
if !strings.HasPrefix(clean, baseDir+string(os.PathSeparator)) {
    return errors.New("path traversal")
}
```

### CSPRNG — `crypto/rand`, never `math/rand`

```go
b := make([]byte, 32)
_, err := cryptorand.Read(b)
```

For tokens, take bytes from `crypto/rand` and base64-encode.

### Constant-time comparison — `hmac.Equal`

Never `==` or `bytes.Equal` on secrets, signatures, or HMACs.

### TLS — `MinVersion: tls.VersionTLS12`, verification on

Never `InsecureSkipVerify: true` outside explicit local test fixtures. If a cert chain fails, fix the chain.

### Outbound HTTP — block redirect chains when not needed

```go
&http.Client{CheckRedirect: func(*http.Request, []*http.Request) error {
    return http.ErrUseLastResponse
}}
```

Prevents the redirect-after-allowlist pivot to internal hosts.

### Request body bounds — `http.MaxBytesReader`

```go
r.Body = http.MaxBytesReader(w, r.Body, 1<<20) // 1 MiB cap
```

### Password hashing — `golang.org/x/crypto/bcrypt`

`bcrypt.GenerateFromPassword` / `bcrypt.CompareHashAndPassword`. Never `crypto/sha256` for passwords.

## Code Quality

- `go vet` and `staticcheck` for linting
- `gofmt` and `goimports` for formatting
- `golangci-lint` as the meta-linter
- Functions ≤ 40 lines, cyclomatic complexity ≤ 7
- Files ≤ 500 lines; split when exceeded
