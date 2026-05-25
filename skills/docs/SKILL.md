---
description: Documentation dispatcher — write (language auto-detect), review (Write-the-Docs audit), research (publish to here.now). The first word of $ARGUMENTS selects the subcommand; research publishes externally.
argument-hint: "<subcommand> [arguments]"
aliases: go-docs, py-docs, nvim-docs, gherkin-docs, doc-review, here-now
paths:
  - "**/*.go"
  - "**/*.py"
  - "**/*.lua"
  - "**/*.feature"
  - "**/*.md"
  - "**/*.rst"
  - "**/*.txt"
  - "**/*.adoc"
---

# Docs: Writing, Review, and Research Dispatcher

Use this skill for any documentation work: generating per-language API docs, auditing existing documentation against Write-the-Docs principles, or producing a researched report and publishing it externally.

## Usage

```
/docs                              # show this help
/docs write                        # auto-detect language, generate or audit API docs
/docs write <language>             # force language (go, py, nvim, gherkin)
/docs review [paths] [-f|-fc]      # audit .md/.rst/.txt against rules/docs-principles.md
/docs review --all                 # review every doc file in the repo
/docs research <topic>             # research and publish to here.now (24h link)
/docs research <topic> --keep      # publish permanently (requires HERE_NOW_API_KEY)
```

## Workflow

### 1. Parse the subcommand

Split `$ARGUMENTS` on the first space. The first word is the subcommand.

- Empty or `help` → print **Usage** and stop.
- Not one of `write`, `review`, `research` → print **Usage** and stop.
- Dispatch to the matching step.

### 2. Dispatch — `write`

Run the language detector. The second token of `$ARGUMENTS` (after `write`) is an explicit override:

```bash
bash ~/.claude/scripts/detect_language.sh "${2-}"
```

Returns `go`, `py`, `nvim`, `gherkin`, `rest`, or `unknown`. If `unknown`: stop and ask the user which language. `rest` is not supported by `write` — recommend `/architect spec` instead. Then dispatch to the matching language workflow.

#### 2a. `write go` — godoc

Replicates the prior `/go-docs` skill.

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

3. **Document exported symbols** per godoc conventions:
   ```go
   // UserService manages user lifecycle operations.
   // It is safe for concurrent use.
   type UserService struct { ... }

   // CreateUser creates a new user with the given name and email.
   // It returns [ErrDuplicateEmail] if the email is already registered.
   // The ctx parameter is used for cancellation and deadline propagation.
   func (s *UserService) CreateUser(ctx context.Context, name, email string) (*User, error)
   ```

4. **Format rules.** First sentence starts with the symbol name, present tense, third person (`CreateUser creates...`, not `Create a user`). Document all error return conditions with sentinel references. State concurrency safety explicitly when relevant. Use `[SymbolName]` cross-reference syntax. Do not document unexported symbols unless logic is genuinely non-obvious.

5. **Verify.**
   ```bash
   go doc ./...
   godoc -http=:6060
   ```

**Checklist:** every exported type's doc starts with its name; functions document error returns; package-level comment exists; concurrency safety stated on shared types; `[SymbolName]` cross-references used; no placeholder `// TODO: document this` comments.

#### 2b. `write py` — Google-style docstrings

Replicates the prior `/py-docs` skill.

1. **Scan for missing docstrings.** `grep -n "^def [a-z]\|^class [A-Z]" **/*.py`. Report public symbols missing docstrings (skip `_private` and `__dunder__` unless non-obvious).

2. **Write module docstrings** as the first statement of every public module.

3. **Document public classes** with Google-style format including an `Attributes:` section.

4. **Document public functions/methods:**
   ```python
   def create_user(name: str, email: str, role: str = "member") -> User:
       """Create a new user and send a welcome notification.

       Args:
           name: Display name for the user.
           email: Email address — must be unique across all accounts.
           role: Authorization role. Defaults to "member".

       Returns:
           The newly created user with a generated ID and timestamps.

       Raises:
           DuplicateEmailError: If the email is already registered.
           ValidationError: If the email format is invalid.
       """
   ```

5. **Format rules.** First line is a concise imperative summary. `Args:` one per parameter — type info lives in the signature. `Returns:` describes what is returned, not its type. `Raises:` lists only exceptions the caller should handle. Omit sections that don't apply.

6. **FastAPI routes** — add `summary` and `description` to non-obvious endpoints:
   ```python
   @router.post("/users", status_code=201,
       summary="Register a new user",
       description="Creates a user account and sends a verification email. "
                   "Returns 409 if the email is already registered.",
       tags=["users"])
   ```

7. **Verify.** `python -m pydoc <module>` or `make docs` for mkdocs/sphinx.

**Checklist:** every public module has a docstring; every public class describes purpose and key attributes; functions document Args/Returns/Raises where applicable; no empty sections; FastAPI routes have `summary` for non-obvious endpoints; private/internal code omits docstrings unless non-obvious.

#### 2c. `write nvim` — vimdoc

Replicates the prior `/nvim-docs` skill. Format conventions are authoritative in `rules/nvim-docs.md`.

**When NOT to use.** Personal Neovim config (`~/.config/nvim/`) — vimdoc is overkill. Doc already current — use `/code migrate` for deprecated pattern updates.

1. **Discover the surface.** Read public API, user commands, keymaps, config options:
   ```bash
   ls lua/ doc/
   test -f doc/*.txt && echo "EXISTS" || echo "MISSING"
   ```
   **If `doc/<plugin>.txt` already exists and no explicit override: stop and ask whether to audit, regenerate, or extend.**

2. **Generate the help file** following the skeleton below; apply `rules/nvim-docs.md` for tags, references, separator lines, 78-col width, modeline. Include only sections that apply — omit empty ones.

3. **Regenerate help tags.**
   ```bash
   nvim --headless -c "helptags doc/" -c "q"
   ```
   **If `helptags` reports errors: stop and fix the offending tag.**

4. **Verify** every section, command, function, and option tag resolves:
   ```bash
   nvim --headless -c "help <plugin-name>" -c "q"
   ```
   **If any tag is broken or unreachable: stop.**

   *Vimdoc skeleton:*
   ```vimdoc
   *plugin-name.txt*  Short one-line description

   Author: Name
   License: MIT

   ==============================================================================
   CONTENTS                                              *plugin-name-contents*

     1. Introduction .......................... |plugin-name-introduction|
     2. Setup ................................ |plugin-name-setup|
     3. Configuration ........................ |plugin-name-configuration|
     4. Commands ............................. |plugin-name-commands|
     5. Keymaps .............................. |plugin-name-keymaps|
     6. API .................................. |plugin-name-api|
     7. Highlights ........................... |plugin-name-highlights|

   ==============================================================================
   INTRODUCTION                                      *plugin-name-introduction*

   Description of what the plugin does and why.

   ==============================================================================
   SETUP                                                    *plugin-name-setup*

   >lua
     require("plugin-name").setup({
       -- default configuration shown here
     })
   <

    vim:tw=78:ts=8:ft=help:norl:
   ```

#### 2d. `write gherkin` — living documentation from feature files

Replicates the prior `/gherkin-docs` skill.

1. **Parse feature files** via the shared script:
   ```bash
   python3 ~/.claude/scripts/parse_gherkin.py <path-or-glob>... [--summary]
   ```
   The script walks `.feature` files (excluding `node_modules/`, `.venv/`) and emits JSON. **If no `.feature` files found: stop and report "No feature files in scope".**

2. **Group by domain.** The script returns features in file-system order. Group by parent directory — each directory typically represents a domain (auth/, users/, payments/).

3. **Render Markdown** with this shape:
   ```markdown
   # Feature Coverage

   > Generated from {N} feature files across {M} domain areas.

   ## Summary

   | Domain | Features | Scenarios | Smoke |
   |---|---|---|---|
   | auth | 3 | 14 | 5 |
   | users | 2 | 9 | 3 |
   | **Total** | **5** | **23** | **8** |

   ---

   ## {Domain Area}

   ### {Feature Title}

   > {Feature description if present}

   | Scenario | Tags | Steps |
   |---|---|---|
   | {Scenario name} | `@smoke` `@auth` | Given ... / When ... / Then ... |

   **Background:** {Background steps if present}

   ---
   ```

   For Scenario Outlines, show one representative row from Examples and note "N variants". Truncate step summaries at 80 characters.

4. **Add coverage summary.** Compute totals: features, scenarios, `@smoke` (or other priority) tag counts per domain. Insert at top.

5. **Write output.** Default path `docs/features.md` — create `docs/` if missing. Confirm path before writing.

6. **Verify** output file exists, feature count matches parser's input file count, every feature has at least one scenario row. **If any check fails: stop.**

**Rules for `write gherkin`.** Read-only on `.feature` files. If a feature has no `Feature:` line, parser emits `""` → call it `(no name)`. Flag `@wip`/`@skip` scenarios as excluded; flag scenarios with no tags as potentially uncategorized.

### 3. Dispatch — `review`

Replicates the prior `/doc-review` skill. Audits documentation against `rules/docs-principles.md`.

**When NOT to use.** Auto-generated docs (OpenAPI/Swagger JSON, godoc output, Sphinx auto-generated, JavaDoc), files in `.docignore`, intentional stubs (contains only `# TODO`), vendored docs under `vendor/`/`third_party/`.

1. **Identify scope.**
   - No argument → `git diff --name-only HEAD`, filter for `.md` / `.rst` / `.txt` / `.adoc`.
   - `--all` → pass repo root to the script (walks `**/*.{md,rst,txt,adoc}`, excludes `.git`, `node_modules`, `.venv`).
   - Path or glob → use directly.
   - **If no documentation files in scope: stop and report.**

2. **Run the deterministic rule checker.**
   ```bash
   python3 ~/.claude/scripts/check_docs.py <paths>... [--severity must|should|consider|all] [--json]
   ```
   Rules applied: `vague-link-text` (Must), `heading-hierarchy` (Should), `heading-title-case` (Consider), `faq-section` (Should), `image-no-alt` (Must), `alt-text-long` (Consider), `code-block-no-lang` (Consider), `raw-url` (Consider), `readme-no-install` / `readme-no-example` (Must), `readme-no-license` (Should).

3. **Apply judgment-required checks** by reading each file fully:
   - **Technical accuracy** (Must Fix): commands that don't work, deprecated syntax, behavior the code no longer has.
   - **Missing code example** (Must Fix in tutorials): step-by-step content needs runnable examples.
   - **Missing problem statement / project purpose** (Must Fix in READMEs).
   - **Prerequisites stated after they are needed** (Must Fix in tutorials): violates Cumulative principle.
   - **Terminology drift** (Should Fix): same term spelled/capitalized differently across the doc.
   - **Active voice absent** (Consider).
   - **Error message blames user / vague / no next step** (Must Fix per docs-principles).
   - **API doc duplicates a data structure across endpoints** (Should Fix): define once, reference everywhere.

4. **Classify** each document. The script reports its classification (`README`, `Changelog`, `Tutorial`, `Document`). Weight findings — README without a code example is Must Fix; Changelog without a code example is N/A.

5. **Compile the per-file report.**
   ```
   ## Review: <filename>

   **Type**: <README | Tutorial | Reference | Guide | Changelog | UI Copy>

   ### Must Fix
   - <rule_id or judgment> — <message> (line N)

   ### Should Fix
   ### Consider
   ```
   `✓ <filename> — no issues found` if clean. Cross-file findings (terminology drift, duplicate content, broken cross-references) go in a separate `## Cross-File Findings` section.

6. **One-paragraph summary.** Publication-ready / needs work / significant gaps; most critical issue; systemic pattern.

7. **Auto-fix (`-f` flag).** **If `-f` was not passed: stop.**

   Apply Must Fix and Should Fix where mechanical:

   | Rule | Auto-fix |
   |---|---|
   | `vague-link-text` | Replace with destination title (read the link target if needed) |
   | `faq-section` | Delete FAQ heading; relocate Q&A pairs, or mark `[TODO: relocate from FAQ]` |
   | `image-no-alt` | Add `[TODO: alt text]` placeholder |
   | `heading-hierarchy` | Bump intermediate heading level |
   | `heading-title-case` | Convert to sentence case |
   | `code-block-no-lang` | Infer language from content; add `bash`, `python`, `go`, etc. |

   Findings that cannot be auto-fixed (technical inaccuracies, missing examples/sections, terminology drift) → **Needs Manual Fix**.

   ```
   ## Fixes Applied
   - <filename>:<line> — <what was fixed>

   Remaining (Needs Manual Fix):
   - <filename>:<line> — <issue>
   ```

8. **Continuous loop (`-fc` flag).** **If `-fc` was not passed: stop.**

   After auto-fix, re-run steps 2–6. Repeat until: zero Must Fix and Should Fix → print `✓ Clean`; 5 iterations → stop, mark remaining as **Needs Manual Fix**; a fix in pass N introduces a new finding not present in pass N-1 → stop immediately, mark new finding as **Needs Manual Fix**. Print `--- Pass 2 ---`, `--- Pass 3 ---` headers. After exit, print a **Session Summary** with remaining findings and all Consider items collected across passes (de-duplicated).

**Rules for `review`.** Read all files before reporting — cross-file findings require the full picture. Always run `check_docs.py` first — do not regenerate the rule logic inline. Apply document-type classification before checking (a Changelog is not graded like a tutorial). Report with file and line number. **Do not flag ARID (repetition) — some documentation repetition is correct and intentional.**

### 4. Dispatch — `research`

Replicates the prior `/here-now` skill. Publishes a researched report to here.now.

**When to use.** Invoke when the user wants a researched topic synthesized into a shareable report with a live URL. Do not invoke for conversational answers — this subcommand always publishes externally.

1. **Parse the topic** from the argument. **If no topic given: ask for one and do not proceed.** Derive a URL slug: lowercase, spaces → hyphens, max 40 chars. Example: "quantum computing" → `quantum-computing`.

2. **Research.** Use WebSearch to find 4–6 authoritative sources. Use WebFetch on each to extract: key definitions/concepts, current state or recent developments, notable perspectives or debates, quantitative data. **Do not rely on training knowledge alone — always fetch live sources.** Record each source URL and the facts drawn from it.

3. **Synthesize the report** as a complete self-contained HTML document at `/tmp/study-{slug}.html`. Structure:
   ```html
   <!DOCTYPE html>
   <html lang="en">
   <head>
     <meta charset="UTF-8">
     <meta name="viewport" content="width=device-width, initial-scale=1.0">
     <title>{Topic}</title>
     <style>
       :root { color-scheme: light dark; }
       body { font-family: system-ui, sans-serif; max-width: 800px; margin: 2rem auto;
              padding: 0 1rem; line-height: 1.6; }
       h1 { font-size: 2rem; margin-bottom: 0.25rem; }
       .meta { color: #666; font-size: 0.9rem; margin-bottom: 2rem; }
       h2 { border-bottom: 1px solid #ddd; padding-bottom: 0.3rem; margin-top: 2rem; }
       blockquote { border-left: 3px solid #ccc; margin: 1rem 0; padding: 0.5rem 1rem;
                    color: #555; }
       ol.sources { padding-left: 1.2rem; }
       ol.sources li { margin-bottom: 0.4rem; }
       a { color: #0070f3; }
     </style>
   </head>
   <body>
     <header>
       <h1>{Topic}</h1>
       <p class="meta">Researched {YYYY-MM-DD} · {N} sources</p>
     </header>
     <main>
       <section id="summary"><h2>Summary</h2><p>{2–3 sentence overview}</p></section>
       <section id="details"><h2>Key Points</h2><!-- substantive content --></section>
       <section id="sources"><h2>Sources</h2>
         <ol class="sources">
           <li><a href="{url}">{title or domain}</a></li>
         </ol>
       </section>
     </main>
   </body>
   </html>
   ```

4. **Compute file metadata.**
   ```bash
   FILE="/tmp/study-{slug}.html"
   SIZE=$(wc -c < "$FILE" | tr -d ' ')
   HASH=$(python3 -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "$FILE")
   ```

5. **Create the publication.** POST file manifest to the here.now API:
   ```bash
   MANIFEST=$(python3 -c "
   import json, sys, os
   api_key = os.environ.get('HERE_NOW_API_KEY', '')
   print(json.dumps({
     'files': [{
       'path': 'index.html',
       'size': int(sys.argv[1]),
       'contentType': 'text/html; charset=utf-8',
       'hash': sys.argv[2]
     }],
     'viewer': {
       'title': sys.argv[3],
       'description': 'Researched by Claude'
     }
   }))" "$SIZE" "$HASH" "{Topic}")

   AUTH_HEADER=""
   if [ -n "$HERE_NOW_API_KEY" ]; then
     AUTH_HEADER="-H \"Authorization: Bearer $HERE_NOW_API_KEY\""
   fi

   RESPONSE=$(curl -s -X POST https://here.now/api/v1/publish \
     -H "Content-Type: application/json" \
     -H "X-HereNow-Client: claude-code/study" \
     $AUTH_HEADER \
     -d "$MANIFEST")
   ```

   Extract: `SITE_URL`, `UPLOAD_URL` (`upload.uploads[0].url`), `FINALIZE_URL` (`upload.finalizeUrl`), `VERSION_ID` (`upload.versionId`). **If POST returns non-2xx or an error field: stop, report, clean up temp file.**

6. **Upload the file.**
   ```bash
   curl -s -X PUT "$UPLOAD_URL" \
     -H "Content-Type: text/html; charset=utf-8" \
     --data-binary "@$FILE"
   ```
   **If non-2xx: stop, report, clean up.**

7. **Finalize.**
   ```bash
   curl -s -X POST "$FINALIZE_URL" \
     -H "Content-Type: application/json" \
     -d "{\"versionId\":\"$VERSION_ID\"}"
   ```
   **If non-2xx: stop and report.**

8. **Verify and report.**
   ```bash
   STATUS=$(curl -s -o /dev/null -w "%{http_code}" --head "$SITE_URL")
   rm -f "$FILE"
   ```

   On status 200, report:
   ```
   Published: {SITE_URL}
   Topic: {Topic} · {N} sources
   Expires: 24 hours from now
   ```
   If `HERE_NOW_API_KEY` was set, replace `Expires` with `Permanent`. On non-200, report the URL anyway and note it may still be propagating.

**Rules for `research`.** Always fetch live sources — never publish based solely on training knowledge. Never publish content violating here.now's terms (malware, phishing, spam, illegal content, content exploiting minors). Always clean up `/tmp/study-{slug}.html` even on failure. If `HERE_NOW_API_KEY` is unset, always tell the user the link expires in 24 hours. If `--keep` is passed but `HERE_NOW_API_KEY` is unset: stop and tell the user to set the env var.

### 5. Final verification step

Each dispatch above ends with its own verification gate (regenerated tags, output file path, published URL, clean review loop). Before this skill exits, confirm the gate fired — if any verification was skipped, re-run it.

## Rules (apply across all subcommands)

- `rules/docs-principles.md` is authoritative for Write-the-Docs conventions. Do not duplicate its content.
- For language-specific format conventions: `rules/go-docs.md`, `rules/py-docs.md`, `rules/nvim-docs.md`. Skill orchestrates, rule defines.
- `write` never modifies source code other than the documentation strings/files it generates.
- `review` is non-destructive without `-f`/`-fc`.
- `research` always publishes externally — treat as human-gated for content sensitivity.
