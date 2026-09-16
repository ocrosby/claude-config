---
description: Use when the user asks to review, grill (strictest verdict), refactor, migrate deprecated patterns, sweep tech debt, or simplify existing code. Invoke as /code <review|grill|refactor|migrate|techdebt|simplify>. techdebt deletes code; grill loops to SHIP IT or Needs Manual Fix.
argument-hint: "<subcommand> [arguments]"
aliases: code-review, rest-review, refactor, migrate, techdebt, simplify, grill
paths:
  - "**/*.go"
  - "**/*.py"
  - "**/*.lua"
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.feature"
  - "**/*.rs"
  - "**/capabilities/*.json"
  - "**/tauri.conf.json"
---

# Code: Quality and Transformation Dispatcher

Use this skill for any audit, transformation, or cleanup of existing code: structured review, REST-convention check, refactor, deprecation migration, dead-code sweep, or adversarial pre-ship review.

Delegates to language-specialist agents (`go-reviewer`, `py-reviewer`, `nvim-reviewer`, `gherkin-reviewer`, `rest-reviewer`, `tauri-reviewer`, `electron-reviewer`, `skill-reviewer`) and to shared deterministic scripts in `~/.claude/scripts/`. Heavy subcommand dispatch lives in Level 3 files (`review.md`, `refactor.md`, `migrate.md`) — this file stays thin.

## Usage

```
/code                                    # show this help
/code review [paths|refs] [-f|-fc]       # structured language review (auto-routes REST)
/code review --rest [paths]              # REST-convention review only (no language pass)
/code grill                              # /code review under strictest verdict, looped to SHIP IT
/code refactor [file]                    # structural improvement (Go/Python/Neovim/Lua)
/code migrate [language] [path]          # replace deprecated patterns
/code techdebt                           # end-of-session sweep: duplicates + dead code
/code simplify                           # delegate to the external /simplify skill
```

**Flag semantics for `review`:** `-f` = fix Must Fix and Should Fix once. `-fc` = fix, re-review, repeat (cap 5). `--rest` = REST-convention only (no language pass).

## Workflow

### 1. Parse the subcommand

Split `$ARGUMENTS` on the first space. The first word is the subcommand.

- Empty or `help` → print **Usage** and stop.
- Not one of `review`, `grill`, `refactor`, `migrate`, `techdebt`, `simplify` → print **Usage** and stop.
- Dispatch to the matching step below.

### 2. Dispatch — `review`

Read `~/.claude/skills/code/review.md` and follow it. Handles scope identification, per-language linting, endpoint/Tauri surface detection, language-reviewer delegation (with `model: "haiku"` pinning), deterministic script checks, report compilation, and `-f` / `-fc` auto-fix modes.

### 3. Dispatch — `grill`

Adversarial review. Same pipeline as `review` but reviewer agents apply the strictest interpretation and the verdict scale is binary.

1. Invoke the `review` workflow from `code/review.md` with this explicit instruction passed to each reviewer agent: **"Adversarial mode — apply the strictest interpretation. Default to NEEDS WORK unless every issue is conclusively resolved."** Under `grill`, do **not** pin reviewer agents to Haiku — the verdict-shifting judgment is stronger on the default model.
2. Override the summary verdict with the SHIP IT / NEEDS WORK / BLOCK scale defined in `rules/findings-format.md` (Verdict labels) — authoritative there; do not restate the thresholds here.
3. On NEEDS WORK or BLOCK, list every issue with file, line, and the specific fix. **Quote the reviewer agent verbatim — do not paraphrase.**
4. After fixes are applied, re-run from step 1. Loop a maximum of 5 passes. **On pass 5, if issues remain: mark them "Needs Manual Fix" and stop — do not proceed to another loop iteration.**
5. Only return SHIP IT after a clean pass with zero remaining items.

**Rules for `grill`.** Never lower the verdict to accommodate effort already spent. Never collapse Must Fix into Should Fix. Breaking change to a public API is always BLOCK until justified in commit message or restored. Missing tests for new/changed behavior is always BLOCK.

### 4. Dispatch — `refactor`

Read `~/.claude/skills/code/refactor.md` and follow it. Structural improvement without behavior change: understand-first, identify-the-smell (per language), plan-and-confirm, characterization tests, small-step refactor, verify.

### 5. Dispatch — `migrate`

Read `~/.claude/skills/code/migrate.md` and follow it. Replaces deprecated APIs/idioms via `migrate_scan.py`; behavior identical before and after.

### 6. Dispatch — `techdebt`

End-of-session sweep for duplicated and dead code.

1. **Scan** the codebase for:
   - Duplicated code blocks — three or more similar lines appearing in two or more places
   - Dead exports/functions/types/variables — declared but with no callers in the repo or its public API

2. **Group and present findings** by file with line numbers.

3. **Ask before fixing.** Do not begin removing code without explicit user approval per item or per batch.

4. **Apply approved fixes one at a time.** For each: make the change, then run the project's test suite — `go test ./...` for Go, `pytest` for Python, `make test` if a Makefile defines a `test` target. **If none of those apply: stop and ask the user which command to run before continuing.** **If tests fail: stop and report the regression. Do not proceed.**

5. **Commit** via `/conventional-commit-msg`. Use `chore` or `refactor` — never `feat`.

6. **Verify.** Re-run the full test suite once more after the commit. Confirm green before reporting done.

**Rules for `techdebt`.** Never delete code whose removal is not covered by tests — write a test that exercises a known caller path first if needed. Never bundle cleanup into a feature commit. Three lines that share an obvious idiom (`if err != nil { return err }`) are not duplication.

### 7. Dispatch — `simplify`

Delegate to the external `/simplify` skill (which reviews changed code for reuse, quality, and efficiency, then fixes the issues found). Invoke it directly with whatever follows `simplify` in `$ARGUMENTS`. Do not re-implement its logic here.

### 8. Final verification step

Each dispatch (or its Level 3 file) ends with its own verification gate. Confirm the gate fired before exiting:

- `review` / `grill` → report compiled, summary printed
- `refactor` → tests pass and the verify command for the language ran clean
- `migrate` → re-scan shows zero or intentionally-kept findings
- `techdebt` → final test run after commit is green

If any verification was skipped, re-run it before declaring the subcommand done.

## Rules (apply across all subcommands)

- `rules/findings-format.md` is authoritative for the **Must Fix / Should Fix / Consider** buckets and the per-finding shape. Do not restate the bucket definitions inline.
- Report issues with file and line number when possible (`file:line — rule_id — message` for script-derived findings).
- Distinguish blocking issues from suggestions — not everything is a Must Fix.
- Without `-f`/`-fc`: describe what to change and why; do not modify code.
- With `-f` or `-fc`: apply Must Fix and Should Fix changes directly; never silently skip a finding (mark as Needs Manual Fix).
- Refactor and migrate must never combine with a behavior change. Techdebt must never bundle into a feature commit.
- Lint failures always block semantic review until resolved.
