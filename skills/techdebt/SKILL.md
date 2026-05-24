---
description: End-of-session codebase cleanup — find and kill duplicated and dead code.
aliases: techdebt
# Human gate: this skill deletes code. Block model auto-invocation; require explicit user request.
disable-model-invocation: true
---

# Techdebt: Codebase Cleanup Sweep

Use this skill when you want to find and remove duplicated blocks and dead code before they accumulate, typically at the end of a working session.

## Usage

```
/techdebt
```

No arguments. Operates on the current working directory's git repository.

## Workflow

### 1. Scan

Scan the codebase for:
- Duplicated code blocks — three or more similar lines appearing in two or more places
- Dead exports, functions, types, and variables — declared but with no callers in the repo or its public API

### 2. Group and present findings

Present findings grouped by file, with line numbers. For each item, name the duplication or the dead symbol and show the affected paths.

### 3. Ask before fixing

Ask which items to fix now. Do not begin removing code without explicit user approval per item or per batch.

### 4. Apply fixes one at a time

For each approved item:
1. Make the change in place.
2. Run the project's test suite (`go test ./...`, `pytest`, `make test`, etc. — whichever applies).
3. **If tests fail: stop and report the regression. Do not proceed to the next item.**
4. If tests pass, move to the next item.

### 5. Commit

Once the approved batch is clean, invoke `/conventional-commit-msg` to commit. Use `chore` or `refactor` as the type — never `feat` (cleanup never adds new behavior).

### 6. Verify

Re-run the full test suite once more after the commit. Confirm green before reporting done.

## Rules

- Never delete code whose removal is not covered by tests. If a function is dead but uncovered, write a test that exercises a known caller path first, then confirm there are no callers.
- Never bundle cleanup into a feature commit. Cleanup ships as its own commit (or PR) with a `chore` or `refactor` type.
- A "duplicate" of three lines that share an obvious idiom (`if err != nil { return err }`) is not duplication — do not flag it.
