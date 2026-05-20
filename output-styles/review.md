# Review Style

Format the response as a three-severity findings report. Use these section headings exactly, in this order:

## Must Fix

Findings that block the change: correctness defects, security issues, broken contracts, incorrect documentation, failing tests, violations of mandatory rules in `rules/`.

Each finding follows this shape:

- `path:line` — one-sentence description of the defect — one-sentence concrete fix.

## Should Fix

Findings that do not block but represent real drift: convention violations, missing tests for new code, inconsistency with existing patterns in the same file or module, non-skimmable structure in docs, missing entries in `rules/` or `README.md` index where one is required.

Same `path:line — description — fix` shape.

## Consider

Optional improvements where the existing code is defensible: stylistic preferences, additional examples, cross-references, alternative pattern applications. The author may decline these without justification.

Same shape.

---

Rules for the report:

- Group findings under the severity heading they belong to, not by file.
- If a section has no findings, write `None.` under the heading — do not omit the heading.
- Do not write a "Summary" section. Do not write an "Overall" paragraph. Do not write a "Strengths" or "Praise" section. The headings *are* the structure.
- Do not hedge severity. If you wrote "this could perhaps be considered for must-fix," it is a Must Fix or a Should Fix — pick one.
- If the review surfaces a missing rule, hook, or skill that would have caught a Must Fix, name the proposed file path in the Prevention line of that finding.
