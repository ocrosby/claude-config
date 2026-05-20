---
description: Guides development of new Python features following hexagonal architecture, delegating review to /code-review and relying on the always-on TDD rule.
aliases: py-feature
paths:
  - "**/*.py"
---

# Python Feature Development

Use this skill when implementing a new Python feature. This skill owns Python-specific design decisions (hexagonal layering, FastAPI/FastMCP patterns, Pydantic models, dependency injection). TDD enforcement (red-green-refactor with observable failure output) comes from the always-on `rules/tdd.md` — do not re-implement that rule inline. Final review delegates to `/code-review -fc`.

## Workflow

### 1. Understand the Feature

- Clarify what the feature does from the user's perspective
- Identify which layer it belongs to: domain, port, adapter, or application
- Determine if it needs new API endpoints, CLI commands, MCP tools, or background tasks

> Run `/architect` first only when the feature introduces a new module boundary, a new port/adapter pair, or significant domain abstractions. For incremental additions, skip it.

### 2. Design the Interface

- Define the public API: functions, classes, and their signatures with full type hints
- Define configuration with pydantic `Settings` if new config is needed
- Define request/response models with Pydantic `BaseModel`

### 3. Implement via TDD

The always-on `rules/tdd.md` enforces red-green-refactor. Apply that cycle in this order for Python features:

1. Domain models and services first — pure Python, no framework imports
2. Ports (Protocol classes) for new external dependencies
3. Adapters: FastAPI routes, DB repositories, API clients
4. Wire dependencies via injection (`Depends()` in FastAPI, constructor injection elsewhere)

Do not write production code in this skill before a failing test exists for that behavior.

### 4. Apply Python-Specific Structure

- One module per concern — split at 300 lines
- Domain logic has no I/O, no framework imports
- Adapters are thin: validate input, delegate to domain, return result
- FastAPI routes use `APIRouter`, one router per domain area
- FastMCP tools use `@mcp.tool()` with type hints and docstrings for schema derivation

### 5. Apply FastAPI Specifics (if applicable)

- Define request/response models with Pydantic `BaseModel`
- Use `Depends()` for shared logic (auth, DB sessions, config)
- Use `lifespan` context manager for startup/shutdown, not `on_event`
- Return explicit status codes (`status_code=201` for creation)
- Use `HTTPException` for error responses with appropriate status codes

### 6. Apply FastMCP Specifics (if applicable)

- Declare tools with `@mcp.tool()`, resources with `@mcp.resource()`
- Tool functions derive their schema from type hints and docstrings
- Keep tool functions thin: validate, delegate to domain, return
- Use `Context` for logging and progress reporting

### 7. Review via /code-review

Invoke `/code-review -fc` on the changed files. The review skill owns:

- Running `ruff check` and `ruff format --check`
- Delegating to `py-reviewer` for idiomatic, architectural, and type-safety checks
- Auto-fixing Must Fix and Should Fix findings, looping until clean

Do not re-implement the review checklist here — `py-reviewer` covers type hints, domain purity, dependency injection, Pydantic boundaries, and global state. If `/code-review -fc` reports findings that require manual judgment, address them before declaring the feature complete.
