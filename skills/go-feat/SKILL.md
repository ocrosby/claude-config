---
description: Guides development of new Go features following clean architecture and idiomatic Go patterns, delegating review to /code-review and relying on the always-on TDD rule.
paths:
  - "**/*.go"
---

# Go Feature Development

Use this skill when implementing a new Go feature. This skill owns Go-specific design decisions (layers, interfaces, error wrapping, concurrency). TDD enforcement (red-green-refactor with observable failure output) comes from the always-on `rules/tdd.md` — do not re-implement that rule inline. Final review delegates to `/code-review -fc`.

## Workflow

### 1. Understand the Feature

- Clarify what the feature does from the user's perspective
- Identify which layer it belongs to: domain, port, adapter, or cmd
- Determine if it needs new HTTP endpoints, CLI commands, or background workers

> Run `/architect` first only when the feature introduces a new package boundary, a new top-level abstraction, or crosses layer boundaries in a way that is not obvious. For incremental additions, skip it.

### 2. Design the Interface

- Define the public API: types, functions, and their signatures
- Define interfaces at the consumer side — small, focused
- Configure via struct fields or functional options
- Accept `context.Context` as the first parameter on all I/O methods

### 3. Implement via TDD

The always-on `rules/tdd.md` enforces red-green-refactor: write the failing test, show the failure output, then minimal implementation, then refactor. Apply that cycle in this order for Go features:

1. Domain types and service methods first — pure logic, no I/O
2. Port interfaces for any new external dependencies
3. Adapters: HTTP handlers, DB repositories, API clients
4. Wire dependencies in `cmd/` via constructor injection

Do not write production code in this skill before a failing test exists for that behavior.

### 4. Apply Go-Specific Structure

- One package per concern — split at 500 lines
- Domain logic has no external imports beyond stdlib
- Adapters are thin: parse request, delegate to domain, write response
- HTTP handlers use stdlib `net/http` patterns or a thin router

### 5. Apply Go-Specific Error Handling

- Wrap errors with context: `fmt.Errorf("creating user: %w", err)`
- Define sentinel errors for expected conditions: `var ErrNotFound = errors.New("not found")`
- Return early on error — no deep nesting
- Use custom error types when callers need to inspect details

### 6. Apply Go-Specific Concurrency (if needed)

- Use `errgroup` for parallel work with error propagation
- Pass `context.Context` for cancellation
- Channels have a clear owner — one goroutine creates, one closes
- Every goroutine must have a termination path

### 7. Review via /code-review

Invoke `/code-review -fc` on the changed files. The review skill owns:

- Running `golangci-lint` and `go test -race`
- Delegating to `go-reviewer` for idiomatic and architectural checks
- Auto-fixing Must Fix and Should Fix findings, looping until clean

Do not re-implement the review checklist here — `go-reviewer` covers error wrapping, interface placement, dependency injection, context propagation, global state, and exported doc comments. If `/code-review -fc` reports findings that require manual judgment, address them before declaring the feature complete.
