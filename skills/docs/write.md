# /docs write (Level 3 resource)

Read this file when `SKILL.md` step 1 dispatches to `write`. Generates per-language API documentation.

## Entry point

Run the language detector. The second token of `$ARGUMENTS` (after `write`) is an explicit override:

```bash
bash ~/.claude/scripts/detect_language.sh "${2-}"
```

Returns `go`, `py`, `nvim`, `gherkin`, `rest`, or `unknown`. If `unknown`: stop and ask the user which language. `rest` is not supported by `write` — recommend `/architect spec` instead. Then dispatch to the matching language workflow below.

## write go — godoc

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

## write py — Google-style docstrings

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

6. **FastAPI routes** — add `summary` and `description` to any route whose path alone does not convey the operation. Example: `POST /users` does not need a description; `POST /users/{id}/notifications/batch` does. Also add to any route with query params that affect behavior beyond filtering:
   ```python
   @router.post("/users", status_code=201,
       summary="Register a new user",
       description="Creates a user account and sends a verification email. "
                   "Returns 409 if the email is already registered.",
       tags=["users"])
   ```

7. **Verify.** `python -m pydoc <module>` or `make docs` for mkdocs/sphinx.

**Checklist:** every public module has a docstring; every public class describes purpose and key attributes; functions document Args/Returns/Raises where applicable; no empty sections; FastAPI routes have `summary` for non-obvious endpoints; private/internal code omits docstrings unless non-obvious.

## write nvim — vimdoc

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

## write gherkin — living documentation from feature files

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

5. **Write output.** Default path `docs/features.md` — create `docs/` if missing. **If the user has not confirmed the output path: stop and ask. Do not write without an explicit path confirmation.**

6. **Verify** output file exists, feature count matches parser's input file count, every feature has at least one scenario row. **If any check fails: stop.**

**Rules for `write gherkin`.** Read-only on `.feature` files. If a feature has no `Feature:` line, parser emits `""` → call it `(no name)`. Flag `@wip`/`@skip` scenarios as excluded; flag scenarios with no tags as potentially uncategorized.
