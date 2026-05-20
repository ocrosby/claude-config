---
description: Reviews HTTP handler and route code for REST API convention compliance — resource naming, HTTP methods, status codes, statelessness, and caching.
---

# REST Review

Use this skill when reviewing any code that defines HTTP endpoints — handlers, routers, controllers, or route definitions — to check for REST convention compliance.

A deterministic pre-check runs first (`check_rest.py`) to catch mechanical violations fast (verb-in-URI, wrong status code for the method, missing Location header on POST creating). The `rest-reviewer` agent then handles cross-cutting concerns the script cannot mechanize (auth flow, pagination shape, HATEOAS, error envelope consistency).

## When to use

Invoke `/rest-review` after implementing or modifying HTTP endpoint code, before opening a PR, or when a code review surfaces REST design questions. Do not invoke on non-HTTP code (business logic, domain models, repositories).

`/code-review` routes to `rest-reviewer` automatically when HTTP patterns are detected. Use `/rest-review` directly when you want an isolated REST compliance review without a full language-level review.

## Workflow

### 1. Identify HTTP endpoint files

Search the working tree for files that define HTTP routes or handlers. If `$ARGUMENTS` names a specific file or directory, review only that path. Otherwise discover endpoint files:

```bash
# Go
grep -rl "http.HandleFunc\|router\.\(GET\|POST\|PUT\|PATCH\|DELETE\|Handle\)\|gin\.\|echo\.\|chi\.\|mux\." --include="*.go" .

# Python
grep -rl "@app\.\|@router\.\|APIRouter\|@.*\.route\|FastAPI\|Flask" --include="*.py" .

# TypeScript/JavaScript
grep -rl "router\.\|app\.\(get\|post\|put\|patch\|delete\)\|express\(\)\|Hono\|Fastify" --include="*.ts" --include="*.js" .
```

**If no HTTP endpoint files are found: stop and report "No HTTP endpoint definitions found in the current working tree."**

### 2. Run the deterministic pre-check

```bash
python3 ~/.claude/skills/rest-review/check_rest.py <file-or-glob>... [--severity must|should|consider] [--json]
```

The script applies these rules per route registration:

| Rule | Severity | What it catches |
|---|---|---|
| `uri-has-verb` | Must Fix | Path uses a verb (`/getUser`) instead of a noun |
| `uri-uppercase` | Should Fix | URI segments contain uppercase letters |
| `uri-snake-case` | Should Fix | URI segments use `snake_case` instead of `kebab-case` |
| `uri-trailing-slash` | Consider | Path ends with `/` (consistency) |
| `get-with-body` | Must Fix | GET handler reads request body (violates idempotency) |
| `post-no-201` | Should Fix | POST handler returns 200 instead of 201 |
| `post-no-location` | Should Fix | POST returns 201 but no Location header |
| `delete-with-body` | Should Fix | DELETE returns a body with 200 (use 204) |
| `405-no-allow` | Should Fix | 405 response without an Allow header |
| `get-no-cache-headers` | Consider | GET omits Cache-Control / ETag |

Output is Markdown findings grouped by file and severity. If the script reports zero findings, continue to step 3 (the agent may still surface judgment-level issues).

### 3. Delegate to the rest-reviewer agent

Invoke the `rest-reviewer` agent with the same list of endpoint files. Pass the script's findings as additional context so the agent does not re-flag mechanical issues — it focuses on:

- Auth flow correctness (Bearer vs cookie, scope handling)
- Pagination shape (cursor vs offset, response envelope)
- Error envelope consistency across endpoints
- HATEOAS / link header strategy
- Versioning approach (URI prefix vs header)
- Bulk-operation design

### 4. Merge findings and report

Combine the script's mechanical findings with the agent's judgment findings into a single report using the three-severity format:

- **Must Fix** — violates REST constraints that will cause interoperability or correctness problems
- **Should Fix** — convention violations that hurt API usability or discoverability
- **Consider** — improvements that make the API more idiomatic

Group findings by file. Cite which finding came from the script (with rule_id like `uri-has-verb`) vs the agent (descriptive prose). If no issues are found, say so explicitly.

### 5. Verify

Confirm the report includes:

- A file-count and total-findings summary
- At least one of: script findings, agent findings, or an explicit "no issues found"

**If the report is empty without either source reporting clean: stop and re-run.** Empty output indicates a tooling failure, not a clean review.
