---
description: Design-phase dispatcher — design (language auto-detect), patterns (GoF advisor), spec (OpenAPI design-first), catalog (Backstage init). The first word of $ARGUMENTS selects the subcommand; catalog commits and pushes.
argument-hint: "<subcommand> [arguments]"
aliases: architect, patterns, rest-spec, backstage-catalog-init, backstage-init
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Architect: Design-Phase Dispatcher

Use this skill for any design-time work: language-specific architecture, GoF pattern recommendations, OpenAPI specification authoring, or Backstage catalog registration.

This skill delegates to the architect agents (`go-architect`, `py-architect`, `nvim-architect`, `gherkin-architect`) and to the shared scripts in `~/.claude/scripts/`. Pattern recognition signals live in `rules/design-patterns-application.md`; the full GoF catalog is bundled here as `design-patterns.md` (Level 3) and loaded only on demand.

## Usage

```
/architect                              # show this help
/architect design                       # auto-detect language, invoke architect agent
/architect design <language>            # force go, py, nvim, or gherkin
/architect patterns [file-or-glob]      # GoF pattern advisor over changed files
/architect patterns "<problem text>"    # GoF pattern advisor for a described problem
/architect spec                         # write/update an OpenAPI entry (design-first)
/architect catalog                      # create Backstage catalog-info.yaml + commit + push
```

## Workflow

### 1. Parse the subcommand

Split `$ARGUMENTS` on the first space. The first word is the subcommand.

- Empty or `help` → print **Usage** and stop.
- Not one of `design`, `patterns`, `spec`, `catalog` → print **Usage** and stop.
- Dispatch to the matching step.

### 2. Dispatch — `design`

Replicates the prior `/architect` skill.

1. **Detect language.**
   ```bash
   bash ~/.claude/scripts/detect_language.sh "${2-}"
   ```
   The second token of `$ARGUMENTS` (after `design`) is an explicit override. Returns `go`, `py`, `nvim`, `gherkin`, `rest`, or `unknown`. `rest` is not supported by `design` — recommend `/architect spec` instead. `unknown` → stop and ask.

2. **Understand the context.** Before invoking the agent, gather:
   - What is the application's purpose?
   - What is the entry point (HTTP server, CLI, MCP server, plugin)?
   - What external dependencies exist (database, APIs, message queues)?
   - What constraints apply (performance, team conventions, existing codebase)?
   - Is this greenfield or a redesign of existing code?

3. **Invoke the architect agent** matching the language.

   | Language | Agent |
   |---|---|
   | Go | `go-architect` |
   | Python | `py-architect` |
   | Neovim / Lua | `nvim-architect` |
   | Gherkin / BDD | `gherkin-architect` |

   Pass the agent the context from step 2, plus any existing code that should be analyzed.

4. **Review the output.** The architect agent returns: package/module map with responsibilities, dependency graph and layer boundaries, public API surface, configuration schema, trade-offs and alternatives considered. Review the proposal with the user before implementation begins. **Architecture decisions are expensive to reverse — confirm before proceeding.**

5. **Capture decisions.** After the user approves the design: document key decisions in `ARCHITECTURE.md` or `docs/architecture.md` if one doesn't exist. Note the *why* behind non-obvious choices — future readers need the reasoning.

**Rules for `design`.** Never start implementing before the design is confirmed. If the user asks to just start coding, recommend at least a 5-minute design sketch first. For greenfield projects, always invoke the agent before writing any production code. For redesigns, always read the existing code before invoking the agent.

### 3. Dispatch — `patterns`

Replicates the prior `/patterns` skill. Advisory only — never implements.

**When NOT to use.** Config files (YAML, TOML, JSON, `.env`), data schema files (SQL migrations, Protobuf, OpenAPI), test fixtures and factory data, Markdown docs. GoF patterns apply to runtime behavior; non-runtime files are not candidates.

1. **Identify input.** If the argument after `patterns` is a file path or glob, read those files. If a quoted string, treat as a problem description (skip to step 3). If none, run `git diff --name-only HEAD` for changed files and read them. **If no files and no description: stop and ask.**

2. **Read the code** in full per file. Identify the language and note relevant idioms (Go interfaces, Python `Protocol`, Lua module tables).

3. **Load pattern signals:**
   ```bash
   python3 ~/.claude/scripts/pattern_signals.py [--language go|py|lua] [--category creational|structural|behavioral|all]
   ```
   The script emits JSON: `{signals: [{pattern, category, signal}], language_notes: [{pattern, note}]}`. The catalog mirrors `rules/design-patterns-application.md`. Use the script — do not re-parse rule prose every invocation.

   **Only when a specific pattern needs validation against the full GoF catalog**, read `~/.claude/skills/architect/design-patterns.md` (Level 3 reference).

4. **Identify pattern signals.** Match the script's `signals` array exactly — do not substitute your own judgment. Use `language_notes` for implementation-style guidance specific to the language. For each signal record: exact code location (file, line or function name), which pattern it maps to, why (the specific structural problem present). **If no signals found: skip to step 6.**

5. **Generate recommendations.** One block per signal:

   ~~~
   ### <Pattern Name> (<Category>)

   **Signal:** <exact code location and what was observed>

   **Why it fits:** <1–2 sentences on the specific structural problem this pattern solves here>

   **Participants in this context:**
   - <Role from pattern>: `<actual class/function/module name in the code>`
   - (list all key roles)

   **Sketch:**
   ```<language>
   // minimal pseudocode showing the structural change — not a full implementation
   // name the pattern participants as they would appear in the real code
   ```

   **Trade-off:** <what applying this costs vs. what it gains in this specific context>
   ~~~

   **Hard limits:** never recommend more than 3 patterns per file (if more signals exist, list the top 3 by current pain severity); never recommend without citing the specific signal; never implement the refactoring — this is advisory only.

6. **Flag pattern misuse.** If a pattern name appears in the code (class name, comment, doc) but the implementation violates the pattern's contract, flag it separately:

   ```
   ### Misuse: <Pattern Name>

   **Location:** <file and line>
   **Issue:** <what the current code does that violates the pattern>
   **Fix:** <what correct application requires>
   ```

7. **Deliver the report.**
   ```
   ## Pattern Analysis: <filename or "Problem Description">

   ### Opportunities
   <one block per recommendation — highest-priority first>

   ### Misuse
   <any misapplied patterns found>

   ### No-Pattern Zones
   <note any sections intentionally kept simple — validate the simplicity is appropriate>

   ### Summary
   <one paragraph: how many signals found, highest-priority fix, overall design health>
   ```
   If no opportunities: `"No pattern opportunities identified — the current structure is appropriate for its complexity."`

8. **Confirm before implementing.** If the user asks to implement a recommended pattern: confirm the specific pattern, the participants, and target files before writing any code. Delegate to the appropriate language agent (`go-architect`, `py-architect`, `nvim-architect`). **Do not write production code in this skill.**

9. **Verify the report.** Before delivering:
   - Every recommendation cites a specific file and line number or function name — remove any that does not.
   - No file has more than 3 recommendations.
   - Every sketch is syntactically plausible for the target language.
   - Report structure matches the template from step 7 exactly.

   **If any check fails: fix the report before responding.**

**Rules for `patterns`.** Always read actual code before making recommendations — never recommend from the description alone when files are available. Distinguish "high priority" (maintainability or testability suffering now) from "low priority" (future improvement). If the user says the code is "fine as-is", accept it and close.

### 4. Dispatch — `spec`

Replicates the prior `/rest-spec` skill. Output is a valid OpenAPI entry in `openapi.yaml` (or the project's existing spec file). The spec is the contract; the handler comes later via `/feature rest`. **Do not write handler code in this subcommand.**

**When to use.** A new endpoint being added; an existing endpoint changing shape (new param, new response, new status code); a new resource hierarchy (run `/architect design` first, then this subcommand).

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

**Rules for `spec`.** Never write handler code — that's `/feature rest`'s job. Follow `rules/rest-api-conventions.md` for naming, methods, status codes, headers — that rule is authoritative. Breaking changes require a new version prefix, not in-place mutation.

### 5. Dispatch — `catalog`

Replicates the prior `/backstage-catalog-init` skill. Creates a `catalog-info.yaml` Backstage descriptor for a repo that does not yet have one.

**When NOT to use.** The repo already has a `catalog-info.yaml` — edit the existing file. The repo registers more than one `kind: Component` — this subcommand creates a single descriptor.

1. **Check for an existing descriptor.**
   ```bash
   test -f catalog-info.yaml && echo "EXISTS" || echo "MISSING"
   ```
   **If the file exists: stop and do not proceed.** Show its current contents.

2. **Run the inference script.**
   ```bash
   python3 ~/.claude/scripts/backstage_infer.py
   ```
   Emits JSON with: `slug`, `repo_name`, `branch`, `title`, `description`, `type`, `lifecycle`, `owner_candidates`, `system_candidates`, `errors`. Each candidate carries a `source` field (CODEOWNERS, sibling catalog, name-prefix).

   **If `errors` is non-empty: stop and do not proceed.** Surface the error.

3. **Resolve owner.**
   - All `owner_candidates` agree → use that value, tell user where it came from.
   - Candidates differ → present every candidate and source, ask which to use.
   - Empty → ask: "What Backstage group should own this component? (e.g. `qa-engineering`, `platform-engineering`)". **Do not guess. Do not proceed without confirmed owner.**

4. **Resolve system.**
   - All `system_candidates` agree → propose, wait for explicit confirmation.
   - Multiple or none → ask: "Which Backstage system does this component belong to? (e.g. `weather-infrastructure`)". Wait for explicit answer.

5. **Write the file** using script's values + resolved owner and system:
   ```yaml
   apiVersion: backstage.io/v1alpha1
   kind: Component
   metadata:
     name: <repo_name>
     title: <title>
     description: <description>
     annotations:
       github.com/project-slug: <slug>
       backstage.io/managed-by-location: url:https://github.com/<slug>/blob/<branch>/catalog-info.yaml
       backstage.io/managed-by-origin-location: url:https://github.com/<slug>/blob/<branch>/catalog-info.yaml
   spec:
     type: <type>
     lifecycle: <lifecycle>
     owner: <owner>
     system: <system>
   ```

6. **Verify the written file.** `cat catalog-info.yaml`. Confirm every field is present and non-empty:
   - `metadata.name`
   - `metadata.annotations["github.com/project-slug"]` — must be `org/repo` format, no `.git` suffix
   - `spec.type`, `spec.lifecycle`, `spec.owner`, `spec.system`

   **If any field is missing or empty: stop and do not proceed.**

7. **Confirm and commit.** Print the file contents, ask: "Ready to commit this as `chore: add Backstage catalog-info.yaml`? (yes / edit first)".

   - **yes** → stage, commit, push:
     ```bash
     git add catalog-info.yaml
     git commit -m "chore: add Backstage catalog-info.yaml"
     git push
     ```
     **If `git push` fails: stop.** Tell the user the commit is local-only and they must push manually before importing.

   - **edit first** → show the file and wait. Do not commit until confirmed.

8. **Print the import URL** after a successful push:
   ```
   Register this component in Backstage by importing:
   https://github.com/<slug>/blob/<branch>/catalog-info.yaml
   ```

**Rules for `catalog`.** Never guess owner or system. Never overwrite an existing `catalog-info.yaml`. Never push if `git push` failed — tell the user to push manually.

### 6. Final verification step

Each dispatch above ends with its own verification gate:

- `design` → user confirmation of the proposal; ARCHITECTURE.md updated if applicable
- `patterns` → report passes all 4 checks in step 9 (cited locations, ≤3 per file, plausible sketches, matches template)
- `spec` → OpenAPI validator clean, handoff to `/feature rest` reported
- `catalog` → file verified, committed, pushed, import URL printed

If any verification was skipped, re-run it before exiting.

## Rules (apply across all subcommands)

- This skill is design-first — never write production handler code from within it (`spec` is followed by `/feature rest`, not by inline handler authoring).
- `patterns` is advisory only. Implementation delegates to the language architect agents.
- `catalog` mutates remote git history — treat as human-gated.
- `rules/rest-api-conventions.md` and `rules/design-patterns-application.md` are authoritative for REST and pattern signals respectively. Do not duplicate their content here.
