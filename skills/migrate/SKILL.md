---
description: Identifies and replaces deprecated or outdated patterns across Go, Python, Neovim, and Gherkin.
paths:
  - "**/*.go"
  - "**/*.py"
  - "**/*.lua"
  - "**/*.feature"
---

# Migrate

Use this skill to replace deprecated APIs, outdated idioms, and anti-patterns with current equivalents. This is distinct from `/refactor` (which improves design) — migration replaces specific known-bad patterns with known-good replacements. Behavior must be identical before and after.

The deprecation catalog (~50 patterns across four languages) lives in the bundled script `migrate_scan.py` so this body stays small. The script returns a Markdown table; the **replacement** is the user's job because most modernizations require context-aware edits.

## Scope

`/migrate` operates in two modes:

**File-level** — when invoked mid-task after spotting a deprecated pattern in a specific file:
1. Replace the deprecated pattern(s) in that file only
2. Verify with the appropriate test command
3. Do not expand to the rest of the codebase unless explicitly asked

**Codebase-level** — when invoked standalone to modernize an entire project. Follow the workflow below.

If invoked without a specific file context, default to codebase-level. If invoked while already working on a file, default to file-level and ask before expanding scope.

## Usage

```
/migrate                           # scan all languages at the current repo
/migrate <language>                # scan a single language (go|py|lua|gherkin)
/migrate <language> <path>         # scan a single language under a given path
```

## Workflow (codebase-level)

### 1. Scan

```bash
python3 ~/.claude/skills/migrate/migrate_scan.py [--language go|py|lua|gherkin|all] [--root <path>]
```

The script:

- Walks the target directory excluding `.git`, `node_modules`, `.venv`, `vendor`, `__pycache__`, build directories
- Matches each deprecated pattern's regex against every line in matching-extension files
- Emits a Markdown table per language: `file | line | category | deprecated → modern`

**If the script reports no findings: stop and report "no deprecated patterns found".**

### 2. Plan Replacements

Read the script's output table. For each finding, decide:

- **Mechanical replacement** (e.g. `ioutil.ReadAll` → `io.ReadAll`) — apply directly with Edit
- **Context-aware replacement** (e.g. `unittest.TestCase` → pytest functions, requires restructuring) — plan the rewrite per file
- **Not actually deprecated in context** (e.g. `interface{}` in a generated file, an `os.path.join` call inside a Windows-specific branch) — skip and note why

### 3. Apply Replacements

Edit each file. Group by language and verify after each language:

| Language | Verify command |
|---|---|
| Go | `go test ./... -race` |
| Python | `pytest && ruff check .` |
| Neovim | `:checkhealth` in nvim |
| Gherkin | Run all scenarios in isolation, then the full suite |

**If any verify fails: stop and revert that language's changes.** Do not proceed to the next language until tests pass.

### 4. Re-Scan

Re-run the scanner. The remaining findings should be:

- Patterns the script flagged but you intentionally left (note them in the commit body)
- Zero — the codebase is now modernized

If new findings appear that weren't in the original report, you introduced new deprecated patterns — investigate before declaring done.

## Adding new deprecation patterns

The pattern catalog lives in `PATTERNS` at the top of `migrate_scan.py`. Each entry: `{category, regex, deprecated, modern}`. Add new entries to the appropriate language list and re-run; no SKILL.md edit needed.

## Rules

- Behavior must be identical before and after — never combine migration with a behavior change
- Always run the language's verify command after replacements; treat failures as a hard stop
- When a finding requires judgment (Gherkin imperative steps, Python `unittest.TestCase` migrations), explain the rewrite before applying
- Skip findings in vendored, generated, or third-party code — note them in the report rather than editing
