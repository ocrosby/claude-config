# /docs review (Level 3 resource)

Read this file when `SKILL.md` step 1 dispatches to `review`. Audits documentation against `rules/docs-principles.md`.

**When NOT to use.** Auto-generated docs (OpenAPI/Swagger JSON, godoc output, Sphinx auto-generated, JavaDoc), files in `.docignore`, intentional stubs (contains only `# TODO`), vendored docs under `vendor/`/`third_party/`.

## Workflow

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

5. **Compile the per-file report** using the per-finding shape from `rules/findings-format.md`.
   ```
   ## Review: <filename>

   **Type**: <README | Tutorial | Reference | Guide | Changelog | UI Copy>

   ### Must Fix
   - `path/to/file.md:42` — <what>. **Why:** <why>. **Fix:** <fix>.

   ### Should Fix
   - `path/to/file.md:88` — <what>. **Why:** <why>. **Fix:** <fix>.

   ### Consider
   - `path/to/file.md:120` — <what>. **Why:** <why>.
   ```
   Omit a bucket entirely when it has no entries. `✓ <filename> — no issues found` if clean. Cross-file findings (terminology drift, duplicate content, broken cross-references) go in a separate `## Cross-File Findings` section.

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

## Rules

Read all files before reporting — cross-file findings require the full picture. Always run `check_docs.py` first — do not regenerate the rule logic inline. Apply document-type classification before checking (a Changelog is not graded like a tutorial). Report with file and line number. **Do not flag ARID (repetition) — some documentation repetition is correct and intentional.**
