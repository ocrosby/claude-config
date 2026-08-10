---
description: Use when the user needs design-phase work — language-specific architecture, GoF pattern advice, OpenAPI spec authoring, Backstage catalog registration, plan-mode interviewing, or adversarial plan stress-testing. Invoke as /architect <design|patterns|spec|catalog|interview|grill>. catalog commits and pushes to remote.
argument-hint: "<subcommand> [arguments]"
aliases: patterns, rest-spec, backstage-catalog-init, backstage-init, plan-interview
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Architect: Design-Phase Dispatcher

Use this skill for any design-time work: language-specific architecture, GoF pattern recommendations, OpenAPI specification authoring, Backstage catalog registration, the pre-plan interview that surfaces open questions before a detailed plan is written, or the adversarial grill that stress-tests an existing plan or decision one question at a time.

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
/architect interview                    # surface open questions + outline before a plan
/architect grill                        # stress-test an existing plan/decision one Q at a time
```

## Workflow

### 1. Parse the subcommand

Split `$ARGUMENTS` on the first space. The first word is the subcommand.

- Empty or `help` → print **Usage** and stop.
- Not one of `design`, `patterns`, `spec`, `catalog`, `interview`, `grill` → print **Usage** and stop.
- Dispatch to the matching step.

### 2. Dispatch — `design`

1. **Detect language.**
   ```bash
   set -- $ARGUMENTS
   bash ~/.claude/scripts/detect_language.sh "${2-}"
   ```
   `set --` populates shell positional params from `$ARGUMENTS` so `${2-}` resolves to the token after `design` (the explicit override, possibly empty). Returns `go`, `py`, `nvim`, `gherkin`, `rest`, or `unknown`. **If `rest`: stop and direct the user to `/architect spec` instead — `design` does not handle REST APIs.** **If `unknown`: stop and ask which language to apply.**

2. **Gather the context.** Collect answers to every item below before invoking the agent. **If any answer is missing: stop and ask the user — do not proceed to step 3.**
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

4. **Review the output.** The architect agent returns: package/module map with responsibilities, dependency graph and layer boundaries, public API surface, configuration schema, trade-offs and alternatives considered. Present the proposal to the user. **If the user has not explicitly approved the design: stop and do not proceed to step 5.** Architecture decisions are expensive to reverse.

5. **Capture decisions.** After the user approves the design: document key decisions in `ARCHITECTURE.md` or `docs/architecture.md` if one doesn't exist. Note the *why* behind non-obvious choices — future readers need the reasoning.

**Rules for `design`.** Never start implementing before the design is confirmed. If the user asks to just start coding, stop and require a design sketch before any production code is written. For greenfield projects, always invoke the agent before writing any production code. For redesigns, always read the existing code before invoking the agent.

### 3. Dispatch — `patterns`

Advisory only — never implements.

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

5. **Generate recommendations.** The recommendation, misuse, and report output templates live in `~/.claude/skills/architect/patterns.md` — read it and apply them for steps 5–7. Produce one block per signal per the recommendation template.

   **Hard limits:** never recommend more than 3 patterns per file (if more signals exist, list the top 3 by current pain severity); never recommend without citing the specific signal; never implement the refactoring — this is advisory only.

6. **Flag pattern misuse.** If a pattern name appears in the code (class name, comment, doc) but the implementation violates the pattern's contract, flag it separately per the misuse template.

7. **Deliver the report** per the report template. If no opportunities: `"No pattern opportunities identified — the current structure is appropriate for its complexity."`

8. **Confirm before implementing.** If the user asks to implement a recommended pattern: confirm the specific pattern, the participants, and target files before writing any code. Delegate to the appropriate language agent (`go-architect`, `py-architect`, `nvim-architect`). **Do not write production code in this skill.**

9. **Verify the report.** Before delivering:
   - Every recommendation cites a specific file and line number or function name — remove any that does not.
   - No file has more than 3 recommendations.
   - Every sketch is syntactically plausible for the target language.
   - Report structure matches the template from step 7 exactly.

   **If any check fails: fix the report before responding.**

**Rules for `patterns`.** Always read actual code before making recommendations — never recommend from the description alone when files are available. Distinguish "high priority" (maintainability or testability suffering now) from "low priority" (future improvement). If the user says the code is "fine as-is", accept it and close.

### 4. Dispatch — `spec`

Output is a valid OpenAPI entry in `openapi.yaml` (or the project's existing spec file). The spec is the contract; the handler comes later via `/feature rest`. **Do not write handler code in this subcommand.**

**When to use.** A new endpoint being added; an existing endpoint changing shape (new param, new response, new status code); a new resource hierarchy (run `/architect design` first, then this subcommand).

Read `~/.claude/skills/architect/spec.md` and apply its workflow:

- Identify the resource (noun, lowercase, plural for collections) and HTTP method per REST semantics — no verbs in paths; breaking change → new version prefix, never mutate the existing URI
- Ensure the spec file exists — create `openapi.yaml` with the minimal header if none is present
- Write the endpoint entry under `paths:` with `operationId`, `summary`, parameters, request body, and responses; define reusable shapes under `components/`
- Apply the status-code checklist so the spec declares every status the handler will return
- Validate — YAML parses, every `$ref` resolves, unique `operationId`, every response has a `description`; **if validation fails: stop and fix before handoff**
- Hand off to `/feature rest` — report the spec entry added (operationId + path + method)

**Rules for `spec`.** Never write handler code — that's `/feature rest`'s job. Follow `rules/rest-api-conventions.md` for naming, methods, status codes, headers — that rule is authoritative. Breaking changes require a new version prefix, not in-place mutation.

### 5. Dispatch — `catalog`

Creates a `catalog-info.yaml` Backstage descriptor for a repo that does not yet have one. **This subcommand commits and pushes to remote.**

**When NOT to use.** The repo already has a `catalog-info.yaml` — edit the existing file. The repo registers more than one `kind: Component` — this subcommand creates a single descriptor.

Read `~/.claude/skills/architect/catalog.md` and apply its workflow:

- Check for an existing descriptor — **if `catalog-info.yaml` exists: stop and do not proceed;** show its current contents
- Run `backstage_infer.py`; **if `errors` is non-empty: stop and do not proceed**
- Resolve owner and system — **never guess;** ask the user when candidates disagree or are empty, and wait for explicit confirmation
- Write the `catalog-info.yaml` from the script's values plus the resolved owner and system
- Verify every field is present and non-empty; **if any field is missing or empty: stop**
- Confirm, then commit and push (`chore: add Backstage catalog-info.yaml`) — **if `git push` fails: stop** and tell the user the commit is local-only
- Print the import URL after a successful push

**Rules for `catalog`.** Never guess owner or system. Never overwrite an existing `catalog-info.yaml`. Never push if `git push` failed — tell the user to push manually.

### 6. Dispatch — `interview`

Use this when the user asks for a plan / design / implementation strategy AND key questions are unresolved — surface the unknowns and a high-level outline first, iterate, then commit to a detailed plan.

**When to skip.** The user said "just plan it" / "skip the interview"; all needed context is already on the table; you're inside `/architect design` (which runs its own interview step).

Read `~/.claude/skills/architect/interview.md` and apply its workflow:

- List 3–8 open questions grouped by Scope / Constraints / Inputs / Outputs / Risks
- Sketch a 3–5 bullet outline tagged with `(Q1)`, `(Q3)`, etc.
- Send questions + outline; iterate; restart from step 1 if scope reframes
- Commit to the detailed plan once questions are resolved

This subcommand is the information-gathering phase that precedes Claude Code's plan mode (Shift+Tab) — the two are complementary. Per `CLAUDE.md`'s "Working with Plan Mode" rule, pour energy into the plan so Claude can 1-shot the implementation.

### 7. Dispatch — `grill`

Adversarial one-question-at-a-time stress-test of an *existing* plan, decision, or design. Adapts [mattpocock/skills — productivity/grill-me](https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me) (MIT).

**When to use.** A plan, decision, or design is already on the table and the user wants its weak points surfaced before committing to implementation.

**When to skip.** The user wants a *new* plan built from scratch (use `interview` instead); the user asks for adversarial *code* review (use `/code grill`); the user said "just do it" / "skip the grill".

Read `~/.claude/skills/architect/grill.md` and apply its workflow:

- Restate the target in one sentence before any question
- Look up every fact from the environment before asking — questions are for decisions only
- Ask exactly one question per turn, with the recommended answer and the failure mode of the recommendation
- Walk the decision tree in dependency order; prune closed branches
- Summarize as `What stood / What changed / What got dropped`; wait for the user's confirmation of the summary
- Do not begin implementation, editing, or follow-up planning in the same turn as confirmation

### 8. Final verification step

Each dispatch above ends with its own verification gate:

- `design` → user confirmation of the proposal; ARCHITECTURE.md updated if applicable
- `patterns` → report passes all 4 checks in step 9 (cited locations, ≤3 per file, plausible sketches, matches template)
- `spec` → OpenAPI validator clean, handoff to `/feature rest` reported
- `catalog` → file verified, committed, pushed, import URL printed
- `interview` → open questions surfaced + outline shared; the detailed plan is written only after the user has answered
- `grill` → step 6 self-check passes (every heading populated or explicitly `_(none)_`; every answered question reflected in exactly one section; unanswered questions listed under `### Unresolved`; no invalidated recommendation lingers); the user then explicitly confirms the summary before any implementation starts

If any verification was skipped, re-run it before exiting.

## Rules (apply across all subcommands)

- This skill is design-first — never write production handler code from within it (`spec` is followed by `/feature rest`, not by inline handler authoring).
- `patterns` is advisory only. Implementation delegates to the language architect agents.
- `catalog` mutates remote git history — treat as human-gated.
- `interview` does not write the detailed plan in the same turn the questions are surfaced — wait for the user's answers.
- `grill` never batches questions and never begins implementation in the same turn as the user's summary confirmation — the two are always separate turns.
- `rules/rest-api-conventions.md` and `rules/design-patterns-application.md` are authoritative for REST and pattern signals respectively. Do not duplicate their content here.
