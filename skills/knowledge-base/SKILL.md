---
description: Set up or refresh an AI-indexed knowledge base over a directory of raw assets — raw/ holds untouched originals, wiki/ is an AI-written index. Use when the user says "set up a knowledge base", "index this folder", "build a wiki over these files/notes/exports", or wants an auto-maintained table of contents over a pile of documents.
argument-hint: "[dir]"
arguments: [dir]
allowed-tools: Bash(python3 *) Bash(mkdir *) Bash(mv *) Bash(ls *) Bash(find *) Bash(wc *) Read Write AskUserQuestion
---

# Knowledge Base: raw/ + wiki/

Use this skill when the user wants an AI-maintained knowledge base over a folder of assets: `raw/` stores the original files untouched, `wiki/` is a regenerable AI-written index that points into `raw/`, and a pinned `CLAUDE.md` makes every future session honor those rules. Running it a second time re-indexes `wiki/` from the current `raw/`.

## Usage

```
/knowledge-base                 # operate on the current directory
/knowledge-base <dir>           # operate on <dir>
```

## Workflow

### 1. Resolve the target and detect the mode

Resolve `$dir` (default: current working directory). Then decide the mode:

- If both `$dir/raw/` and `$dir/wiki/` already exist → **reindex mode**; skip to step 5.
- Otherwise → **init mode**; continue to step 2.

### 2. Scan and propose a restructure (init mode only)

List the directory's current contents. **If the directory already contains files or folders**, present a restructure plan — what stays at the top level, what moves into `raw/`, and any renames — and ask for sign-off with `AskUserQuestion`. **Stop and do not create or move anything until the user approves the plan.** If the directory is empty, skip to step 3 without asking.

### 3. Create `raw/` and move originals in (init mode only)

Create `$dir/raw/`. Move the approved originals into it. **Never edit, rename, or reorganize anything under `raw/` after it lands — `raw/` is immutable.** The user's assets are preserved byte-for-byte.

### 4. Write the pinning `CLAUDE.md` (init mode only)

Write `$dir/CLAUDE.md`, **60 lines or fewer**, pinning these rules so future sessions honor them:

- `raw/` is immutable — never edit, rename, delete, or reorganize its contents.
- `wiki/` is AI-written only — never hand-edit it; regenerate with `/knowledge-base`.
- To add knowledge, drop files into `raw/` and re-run `/knowledge-base` to reindex.

**If `CLAUDE.md` exceeds 60 lines, cut it down before proceeding — the line cap is a hard limit.**

### 5. Generate `wiki/` (both modes)

Create `$dir/wiki/` if absent. Build the index skeleton with the script — it walks `raw/` and emits grouped Markdown with links, type, and size:

```bash
python3 ~/.claude/scripts/build_wiki_index.py $dir/raw
```

Take the script's output and **replace each `_summary pending — fill in from the asset_` placeholder with a real one-line summary** derived from reading the asset (Read the file for text assets; for binary/opaque assets describe from the name and type). Write the result to `$dir/wiki/index.md`, keeping the `<!-- AI-GENERATED — do not hand-edit; regenerate via /knowledge-base -->` banner as the first line. Do not hand-author structure the script did not produce.

### 6. Verify and summarize

- Confirm `$dir/raw/` and `$dir/wiki/index.md` exist. Confirm `$dir/CLAUDE.md` exists — **if it is absent (e.g. reindex mode after it was deleted): run step 4 now to recreate it before continuing.**
- Confirm `CLAUDE.md` is ≤60 lines (`wc -l`).
- Confirm every link in `wiki/index.md` resolves to a real file under `raw/`. **If any link is dangling: stop and re-run step 5.**
- Print a summary: mode (init vs reindex), what was created or updated, the asset count, and the pinned rules.

## When NOT to use

- **Hand-curated personal notes (PARA, daily notes, wikilinks)** → use `/obsidian`. This skill's `wiki/` is AI-written-only and gets overwritten on reindex; it is the wrong home for notes you edit by hand.
- **Cross-project behavioral preferences or config learnings** → use the memory system / `LEARNINGS.md`, not a `raw/`+`wiki/` tree. This skill indexes a pile of assets, it does not record how Claude should behave.
