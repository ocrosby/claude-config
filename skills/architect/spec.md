# OpenAPI Spec Authoring

Detailed workflow for the `/architect spec` subcommand. Output is a valid OpenAPI entry in `openapi.yaml` (or the project's existing spec file). The spec is the contract; the handler comes later via `/feature rest`. **Do not write handler code in this subcommand.**

## Workflow

1. **Identify the resource and operation.**
   - Resource: noun, lowercase, plural for collections, hyphens for multi-word.
   - HTTP method per REST semantics:
     - Collection: `GET /resources`, `POST /resources`
     - Document: `GET /resources/{id}`, `PUT /resources/{id}`, `PATCH /resources/{id}`, `DELETE /resources/{id}`
   - No verbs in paths — HTTP methods are the verbs.
   - Breaking change (incompatible response shape, removed field) → new version prefix (`/v2/`). Never mutate the existing URI.

2. **Ensure the spec file exists.** If no OpenAPI spec is present, create `openapi.yaml` at the project root with this minimal header:
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
   If a spec exists at a different path (`api/openapi.yaml`, `docs/openapi.yaml`), use that.

3. **Write the endpoint entry** under `paths:` with `operationId`, `summary`, parameters, request body (if any), and responses. Define reusable shapes under `components/`:

   ```yaml
   /users/{id}/orders:
     get:
       operationId: listUserOrders
       summary: List orders for a user
       parameters:
         - name: id
           in: path
           required: true
           schema: { type: string }
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
               schema: { $ref: "#/components/schemas/OrderList" }
         "401": { $ref: "#/components/responses/Unauthorized" }
         "404": { $ref: "#/components/responses/NotFound" }
   ```

4. **Apply the status code checklist.**

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

5. **Validate.** Run an OpenAPI validator if available (`swagger-cli validate`, `redocly lint`). If none configured, at minimum confirm: YAML parses, every `$ref` resolves, every operation has a unique `operationId`, every response declares a `description`. **If validation fails: stop and fix before handoff.**

6. **Hand off to `/feature rest`.** Report the spec entry added (operationId + path + method) and instruct the user to invoke `/feature rest <operationId>` to write the handler against this spec.
