---
description: Use when generating per-language API docs (Go godoc, Python docstrings, Neovim vimdoc, Gherkin readme), auditing markdown against Write-the-Docs principles, or researching a topic and publishing to here.now. Invoke as /docs <write|review|research>. research publishes externally.
argument-hint: "<subcommand> [arguments]"
aliases: go-docs, py-docs, nvim-docs, gherkin-docs, doc-review, here-now
---

# Docs: Writing, Review, and Research Dispatcher

Use this skill when generating per-language API documentation (Go, Python, Neovim, Gherkin), auditing existing markdown files against Write-the-Docs principles, or producing a researched report and publishing it externally via here.now. Do not invoke for inline code comments, CHANGELOG edits, or file renames — those are covered by other skills.

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
- Dispatch to the matching step below.

### 2. Dispatch — `write`

Read `~/.claude/skills/docs/write.md` and follow it. Handles language detection and per-language workflows (go / py / nvim / gherkin).

### 3. Dispatch — `review`

Read `~/.claude/skills/docs/review.md` and follow it. Handles scope detection, deterministic rule check via `check_docs.py`, judgment-required checks, per-file reporting, optional auto-fix (`-f`) and continuous loop (`-fc`).

### 4. Dispatch — `research`

Read `~/.claude/skills/docs/research.md` and follow it. Handles topic parsing, live-source research via WebSearch/WebFetch, HTML synthesis, and here.now publish + verify.

### 5. Final verification step

Each Level 3 file ends with its own verification gate (regenerated tags, output file path, published URL, clean review loop). Before this skill exits, confirm the gate fired — if any verification was skipped, re-run it.

## Rules (apply across all subcommands)

- `rules/docs-principles.md` is authoritative for Write-the-Docs conventions. Do not duplicate its content.
- `rules/findings-format.md` is authoritative for the **Must Fix / Should Fix / Consider** buckets and the per-finding shape used by `review`. Do not restate the bucket definitions inline.
- For language-specific format conventions: the Documentation section of `rules/go-conventions.md`, `rules/py-docs.md`, `rules/nvim-docs.md`. Skill orchestrates, rule defines.
- `write` never modifies source code other than the documentation strings/files it generates.
- `review` is non-destructive without `-f`/`-fc`.
- `research` always publishes externally — treat as human-gated for content sensitivity.
