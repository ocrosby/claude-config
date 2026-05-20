---
description: Implements a REST endpoint handler against an existing OpenAPI spec entry, with TDD-driven domain logic and a thin HTTP layer.
paths:
  - "**/*.go"
  - "**/*.py"
  - "**/*.ts"
  - "**/*.js"
---

# REST Implement — Handler Last

Use this skill when an OpenAPI spec entry exists and a handler needs to be written to satisfy it. **The input is an `operationId` (or a path+method pair) that already exists in `openapi.yaml`.** TDD enforcement is always-on via `rules/tdd.md`; review delegates to `/code-review -fc`. Do not re-implement those steps inline.

## Precondition

The OpenAPI spec entry must exist and validate. If it does not: stop and invoke `/rest-spec` first. Never implement a handler ahead of the spec.

## Workflow

### 1. Locate the Spec Entry

Read the OpenAPI spec file. Confirm the `operationId` (or path+method) the user named exists. Extract:

- HTTP method and path
- Path parameters, query parameters, request body schema
- Response shape per status code

If the entry cannot be found: stop and ask the user to confirm the operationId or run `/rest-spec`.

### 2. Define the Request and Response Types

Generate language-native types that match the spec exactly.

**Go:**
```go
type ListUserOrdersParams struct {
    UserID string
    Status string
}

type OrderList struct {
    Items  []Order `json:"items"`
    Total  int     `json:"total"`
    Cursor string  `json:"cursor,omitempty"`
}
```

**Python (FastAPI + Pydantic):**
```python
class OrderListResponse(BaseModel):
    items: list[Order]
    total: int
    cursor: str | None = None
```

If the project uses code generation from the spec (oapi-codegen, datamodel-code-generator), regenerate and use the generated types instead of hand-writing them.

### 3. Implement Domain Logic via TDD (Handler Last)

The always-on `rules/tdd.md` enforces red-green-refactor. Work domain-outward:

1. **Domain/service layer first** — write the business logic as a pure function with no HTTP concern. Failing test first, then minimal pass, then refactor.
2. **Port interface** — define the interface the handler will call (if a new external dependency is needed).
3. **HTTP handler last** — the handler is thin:
   - Parse request (path params, query params, body)
   - Validate input: `400 Bad Request` for malformed syntax; `422 Unprocessable Entity` for semantically invalid values
   - Call the domain method
   - Map the result to the response shape and status code declared in the spec
   - Write the response

The handler must contain no business logic. The order is always: (1) domain function + tests, (2) port interface if needed, (3) handler last. Never write the handler before the domain method exists.

### 4. Confirm Spec Conformance

For every status code declared in the spec, the handler must produce it under the matching condition. Cross-check:

- POST creating a resource → `201` + `Location` header set
- DELETE returning no body → `204`
- 401 vs 403 not conflated
- Validation failures map to 422, not 400
- Breaking change? Must be served from a new version prefix path

If the handler emits a status code not in the spec, the spec is wrong — go back to `/rest-spec` and update it. Spec and handler must stay synchronized.

### 5. Apply Caching Headers (GETs)

GET responses must set `Cache-Control` or `ETag` where appropriate. If the resource is cacheable per the project's policy and these headers are absent, add them.

### 6. Review via /code-review

Invoke `/code-review -fc` on the changed files. The review skill owns:

- Running language-specific linters (`golangci-lint`, `ruff`, etc.)
- Delegating to the language reviewer agent AND the `rest-reviewer` agent (auto-detected on route registrations)
- Auto-fixing Must Fix and Should Fix findings, looping until clean

Do not re-implement the REST review checklist here — `rest-reviewer` covers URI naming, HTTP method semantics, status code correctness, statelessness, and caching headers. If `/code-review -fc` reports findings that require manual judgment, address them before declaring the implementation complete.

## Rules

- Never implement a handler without a spec entry — invoke `/rest-spec` first
- Never put business logic in the handler — parse, delegate, respond
- Follow `rest-api-conventions.md` for status codes and headers — that rule is authoritative
- Keep the handler synchronized with the spec at all times; if they diverge, fix the spec first
