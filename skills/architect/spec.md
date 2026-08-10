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

4. **Apply the status-code checklist.** Use the status codes and required headers defined in `rules/rest-api-conventions.md` — authoritative there; do not restate the table here. The spec must declare every status code the handler will return; a status emitted by the handler but missing from the spec means the spec is wrong.

5. **Validate.** Run an OpenAPI validator if available (`swagger-cli validate`, `redocly lint`). If none configured, at minimum confirm: YAML parses, every `$ref` resolves, every operation has a unique `operationId`, every response declares a `description`. **If validation fails: stop and fix before handoff.**

6. **Hand off to `/feature rest`.** Report the spec entry added (operationId + path + method) and instruct the user to invoke `/feature rest <operationId>` to write the handler against this spec.
