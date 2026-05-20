---
description: Writes or updates the OpenAPI spec entry for a new or changed REST endpoint, before any handler code exists.
---

# REST Spec — Design First

Use this skill when adding or changing a REST endpoint. **The output is a valid OpenAPI entry in `openapi.yaml`** (or the project's existing spec file). The spec is the contract; the handler comes later via `/rest-implement`. Do not write handler code in this skill.

## When to use

- A new endpoint is being added
- An existing endpoint is changing shape (new param, new response, new status code)
- A new resource hierarchy is being introduced — run `/architect` first, then this skill

## Workflow

### 1. Identify the Resource and Operation

- Name the resource (noun, lowercase, plural for collections, hyphens for multi-word)
- Pick the HTTP method using REST semantics:
  - Collection: `GET /resources`, `POST /resources`
  - Document: `GET /resources/{id}`, `PUT /resources/{id}`, `PATCH /resources/{id}`, `DELETE /resources/{id}`
- No verbs in paths — HTTP methods are the verbs
- If the change is breaking (incompatible response shape, removed field), use a new version prefix (`/v2/`) — never mutate the existing URI

### 2. Ensure the Spec File Exists

If no OpenAPI spec file exists in the project, create `openapi.yaml` at the project root with this minimal header before adding the endpoint:

```yaml
openapi: "3.0.3"
info:
  title: API
  version: "1.0.0"
paths: {}
components:
  schemas: {}
  responses: {}
```

If a spec file exists at a different path (`api/openapi.yaml`, `docs/openapi.yaml`), use that one.

### 3. Write the Endpoint Entry

Add the endpoint under `paths:` with `operationId`, `summary`, parameters, request body (if any), and responses. Example:

```yaml
/users/{id}/orders:
  get:
    operationId: listUserOrders
    summary: List orders for a user
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: string
      - name: status
        in: query
        schema:
          type: string
          enum: [pending, fulfilled, cancelled]
    responses:
      "200":
        description: Paginated list of orders
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/OrderList"
      "401":
        $ref: "#/components/responses/Unauthorized"
      "404":
        $ref: "#/components/responses/NotFound"
```

Define reusable shapes (`OrderList`, `Unauthorized`, `NotFound`) under `components/` — never inline a response schema that two endpoints share.

### 4. Apply the Status Code Checklist

| Condition | Required status code |
|---|---|
| POST created a new resource | `201 Created` + `Location: /resources/{id}` header |
| Successful GET/PUT/PATCH with body | `200 OK` |
| Successful DELETE or no-content response | `204 No Content` (no body) |
| Resource not found | `404 Not Found` |
| Invalid credentials or missing auth | `401 Unauthorized` + `WWW-Authenticate` header |
| Valid identity, insufficient permission | `403 Forbidden` |
| Semantic validation failure | `422 Unprocessable Entity` |
| Malformed request syntax | `400 Bad Request` |
| Method not supported on this resource | `405 Method Not Allowed` + `Allow` header |

The spec must declare every status code the handler will return. If a status is missing from the spec but emitted by the handler, the spec is wrong.

### 5. Validate the Spec

Run an OpenAPI validator if available (`swagger-cli validate`, `redocly lint`, or the project's chosen tool). If no validator is configured, at minimum confirm:

- YAML parses
- Every `$ref` resolves
- Every operation has a unique `operationId`
- Every response declares a `description`

**If validation fails: stop and fix before proceeding to `/rest-implement`.**

### 6. Hand Off to /rest-implement

Report the spec entry that was added (operationId + path + method) and instruct the user to invoke `/rest-implement <operationId>` to write the handler against this spec. The spec is now the authoritative input to that skill.

## Rules

- Never write handler code in this skill — that is `/rest-implement`'s job
- Follow `rest-api-conventions.md` for naming, methods, status codes, and headers — that rule is authoritative; do not duplicate it here
- Breaking changes require a new version prefix, not in-place mutation
