# /code migrate (Level 3 resource)

Read this file when `SKILL.md` step 1 dispatches to `migrate`. Replaces deprecated APIs/idioms with current equivalents. Behavior must be identical before and after.

**Scope.** File-level when invoked mid-task on a specific file (replace patterns in that file only, verify, do not expand without asking). Codebase-level when invoked standalone.

## Workflow (codebase-level)

1. **Scan.**
   ```bash
   python3 ~/.claude/scripts/migrate_scan.py [--language go|py|lua|gherkin|all] [--root <path>]
   ```
   The script walks the target (excluding `.git`, `node_modules`, `.venv`, `vendor`, `__pycache__`, build dirs), matches each pattern's regex against extension-matching files, emits a Markdown table per language: `file | line | category | deprecated → modern`.

   **If the script reports no findings: stop and report "no deprecated patterns found".**

2. **Plan replacements per finding.**
   - *Mechanical* (e.g. `ioutil.ReadAll` → `io.ReadAll`) — apply directly with Edit.
   - *Context-aware* (e.g. `unittest.TestCase` → pytest functions) — plan the rewrite per file.
   - *Not actually deprecated in context* (generated file, Windows-specific branch) — skip and note why.

3. **Apply replacements, verify per language:**

   | Language | Verify command |
   |---|---|
   | Go | `go test ./... -race` |
   | Python | `pytest && ruff check .` |
   | Neovim | `:checkhealth` in nvim |
   | Gherkin | Run all scenarios in isolation, then the full suite |

   **If any verify fails: stop and revert that language's changes.** Do not proceed to the next language until tests pass.

4. **Re-scan.** Remaining findings must be either (a) intentionally left (noted in commit body) or (b) zero. If new findings appear that weren't in the original report, you introduced new deprecated patterns — investigate before declaring done.

**Adding new deprecation patterns:** edit `PATTERNS` at the top of `~/.claude/scripts/migrate_scan.py`. Each entry: `{category, regex, deprecated, modern}`. No SKILL.md edit needed.

## Rules for `migrate`

Behavior must be identical — never combine migration with a behavior change. Always run the language's verify command after replacements. Skip findings in vendored/generated/third-party code — note them in the report.
