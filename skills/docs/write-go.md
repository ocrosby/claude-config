# docs write — Go (godoc)

Applied when `write.md` detects `go`. Generates godoc-style API documentation.

1. **Scan for missing docs.** Find exported symbols without preceding doc comments:
   ```bash
   grep -n "^func [A-Z]\|^type [A-Z]\|^var [A-Z]\|^const [A-Z]" **/*.go
   ```
   Cross-reference against symbols that already have a comment on the preceding line. Report undocumented exports.

2. **Write package doc.** If the package lacks a package-level comment, add it to `doc.go` (create if missing) or the primary file:
   ```go
   // Package users manages user lifecycle operations including creation,
   // authentication, and profile management.
   //
   // The primary entry point is [UserService], which requires a [Repository]
   // implementation to be injected at construction time.
   package users
   ```

3. **Document exported symbols** following `rules/go-conventions.md` § Godoc conventions — that rule is authoritative for the format and carries the reference example.

4. **Format rules** — apply `rules/go-conventions.md` § Godoc conventions for the symbol-name-first summary, error-return documentation, `[SymbolName]` cross-references, and concurrency-safety notes. Authoritative there; do not restate here.

5. **Verify.**
   ```bash
   go doc ./...
   godoc -http=:6060
   ```

**Checklist:** every exported symbol documented per `rules/go-conventions.md` § Godoc; package-level comment exists; no placeholder `// TODO: document this` comments; `go doc ./...` renders cleanly.
