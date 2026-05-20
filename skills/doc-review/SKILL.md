---
description: Reviews documentation files against Write the Docs principles — structure, content quality, accuracy, accessibility, and UX copy — and reports findings by severity.
---

# Documentation Review

Reviews documentation against the principles in `rules/docs-principles.md`. Use this skill when you want an explicit audit of existing documentation rather than passive guidance during writing.

The deterministic rule checks (vague link text, broken heading hierarchy, missing alt text, missing code-block language hints, FAQ sections, README completeness) are bundled in `check_docs.py` so this body stays small. Judgment-required checks (technical accuracy, missing examples, voice/tone, terminology drift) stay inline because they need Claude's reading.

## When NOT to use

Do not run this skill against:
- Auto-generated documentation files (OpenAPI/Swagger JSON or YAML generated from code, godoc output, Sphinx auto-generated pages, JavaDoc)
- Files listed in `.docignore` if one exists in the repo
- Files that are intentionally stubs or work-in-progress placeholders (e.g. contain only `# TODO`)
- Vendored or third-party documentation checked in under `vendor/`, `third_party/`, or similar

## Usage

```
/doc-review                    # review all .md/.rst/.txt docs changed since last commit
/doc-review <file-or-glob>     # review specific files
/doc-review --all              # review all documentation files in the repo
/doc-review -f                 # review + automatically fix all Must Fix and Should Fix findings
/doc-review -fc                # review + fix + repeat until no findings remain
```

- `-f` — fix all Must Fix and Should Fix findings once, then stop
- `-fc` — fix, re-review, fix again, repeat until clean (implies `-f`)
- Without either flag, the skill only reports

## Workflow

### 1. Identify the Scope

**If no argument is given**: run `git diff --name-only HEAD` and filter for documentation files (`.md`, `.rst`, `.txt`, `.adoc`).

**If `--all` is given**: pass the repo root to the script — it walks `**/*.{md,rst,txt,adoc}` and excludes `.git`, `node_modules`, `.venv`.

**If a path or glob is given**: use it directly.

**If no documentation files are found**: stop and report "No documentation files found in scope."

### 2. Run the Deterministic Rule Checker

```bash
python3 ~/.claude/skills/doc-review/check_docs.py <paths>... [--severity must|should|consider|all] [--json]
```

The script applies these checks per file:

- **vague-link-text** (Must Fix): link text is "click here", "here", "this link", "this page", "read more"
- **heading-hierarchy** (Should Fix): heading skips a level (e.g. H2 → H4)
- **heading-title-case** (Consider): heading uses title case instead of sentence case
- **faq-section** (Should Fix): FAQ heading present (per docs-principles, replace with structured content)
- **image-no-alt** (Must Fix): image has no alt text
- **alt-text-long** (Consider): alt text exceeds two sentences
- **code-block-no-lang** (Consider): fenced code block opens without a language hint
- **raw-url** (Consider): raw `https://…` in prose (link text should describe the destination)
- **readme-no-install** / **readme-no-example** / **readme-no-license** (Must / Must / Should): README is missing standard sections

Output is Markdown findings grouped per file by severity.

### 3. Apply Judgment-Required Checks

Read each in-scope file fully. Add findings the script cannot detect:

- **Technical accuracy** (Must Fix): commands that don't work, deprecated syntax, behavior that the code no longer has
- **Missing code example** (Must Fix in tutorials/guides): step-by-step content needs runnable examples
- **Missing problem statement / project purpose** (Must Fix in READMEs)
- **Prerequisites stated after they are needed** (Must Fix in tutorials): violates Cumulative principle
- **Terminology drift** (Should Fix): same term spelled or capitalized differently across the document or related documents
- **Active voice absent** (Consider): passive voice used where active is clearer
- **Error message blames user / is vague / gives no next step** (Must Fix): per docs-principles error-message standard
- **API doc duplicates a data structure across endpoints** (Should Fix): define once, reference everywhere

### 4. Classify Each Document

For each file, the script reports its classification (`README`, `Changelog`, `Tutorial`, `Document`). Use it to weight findings — a README without a code example is Must Fix; a Changelog without a code example is N/A.

### 5. Compile the Report

Merge script findings and inline-judgment findings. Output per file:

```
## Review: <filename>

**Type**: <README | Tutorial | Reference | Guide | Changelog | UI Copy>

### Must Fix
- <rule_id or judgment> — <message> (line N)

### Should Fix
- <rule_id or judgment> — <message> (line N)

### Consider
- <rule_id or judgment> — <message> (line N)
```

If a file has no issues: `✓ <filename> — no issues found`.

**Cross-file findings** (terminology drift, duplicate content, broken cross-references) appear in a separate `## Cross-File Findings` section. The script does not detect these — they require reading every in-scope file before reporting.

### 6. Summary

After all files, write a one-paragraph summary:
- Overall state: publication-ready / needs work / significant gaps
- Most critical issue if any
- Any systemic pattern across files

### 7. Auto-Fix (only when `-f` is passed)

**If `-f` was not passed: stop here.**

Apply every **Must Fix** and **Should Fix** finding where the fix is mechanical:

| Rule | Auto-fix |
|---|---|
| `vague-link-text` | Replace with destination title (read the link target if needed) |
| `faq-section` | Delete FAQ heading; relocate Q&A pairs into appropriate sections, or mark `[TODO: relocate from FAQ]` |
| `image-no-alt` | Add `[TODO: alt text]` placeholder |
| `heading-hierarchy` | Bump intermediate heading level to fix the gap |
| `heading-title-case` | Convert to sentence case |
| `code-block-no-lang` | Infer language from content; add `bash`, `python`, `go`, etc. |

Findings that **cannot** be auto-fixed (report as **Needs Manual Fix**):
- Technical inaccuracies — require code reading
- Missing examples / sections — require domain knowledge
- Terminology drift — requires deciding the canonical term

Report after fixing:

```
## Fixes Applied
- <filename>:<line> — <what was fixed>

Remaining (Needs Manual Fix):
- <filename>:<line> — <issue>
```

### 8. Continuous Loop (only when `-fc` is passed)

**If `-fc` was not passed: stop here.**

After Step 7, re-run Steps 2–6 on the same scope. Repeat until:
- Zero Must Fix and Should Fix findings → print `✓ Clean` and stop
- 5 iterations completed → stop and report remaining findings as **Needs Manual Fix**
- A fix in pass N introduces a new finding not present in pass N-1 → stop immediately; mark the new finding as **Needs Manual Fix**

Print `--- Pass 2 ---`, `--- Pass 3 ---` at each iteration.

After the loop exits, print a **Session Summary** with all remaining findings and all Consider items collected across passes.

## Rules

- Read all files before reporting — cross-file consistency findings require the full picture
- Always run `check_docs.py` first; do not regenerate the rule logic inline
- Apply the document-type classification before checking — a changelog is not graded like a tutorial
- Report findings with file and line number when possible (script emits these automatically)
- Do not flag ARID (repetition) — some documentation repetition is correct and intentional
- Without `-f`: describe what to change and why — do not modify files
- With `-f` or `-fc`: apply automatable Must Fix and Should Fix changes directly; mark the rest as Needs Manual Fix
