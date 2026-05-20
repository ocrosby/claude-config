---
description: Generates living documentation from Gherkin feature files as readable Markdown summaries.
paths:
  - "**/*.feature"
---

# Gherkin Documentation Writer

Use this skill to generate human-readable documentation from feature files — useful for sharing test coverage with non-technical stakeholders, building a product spec, or auditing what behaviors are actually tested.

The `.feature` file parsing (multi-line steps, tags, Background, Scenario Outlines with Examples) lives in the bundled `parse_gherkin.py` script so this body stays small. The skill consumes the parsed JSON and renders the final Markdown.

## Usage

```
/gherkin-docs                        # document all feature files
/gherkin-docs <path>                 # document a specific file or directory
/gherkin-docs --summary              # one-line-per-feature summary only
```

## Workflow

### 1. Parse Feature Files

```bash
python3 ~/.claude/skills/gherkin-docs/parse_gherkin.py <path-or-glob>... [--summary]
```

The script walks `.feature` files (excluding `node_modules/`, `.venv/`) and emits JSON: an array of `{file, feature_name, description, tags, background_steps, scenarios: [{name, tags, steps, outline, examples}], rules}`. With `--summary`, it emits a one-line-per-file Markdown summary instead.

**If no `.feature` files are found: stop and report "No feature files in scope".**

### 2. Group Features by Domain

The script returns features in file-system order. Group them by their parent directory — each directory typically represents a domain area (auth/, users/, payments/).

### 3. Render Markdown

Produce a Markdown document structured as:

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

For Scenario Outlines, show one representative row from the Examples table and note "N variants".

Truncate step summaries at 80 characters. Preserve the feature ordering from the parser output (file-system order).

### 4. Add Coverage Summary

Compute totals from the parsed JSON: total features, total scenarios, count of `@smoke` (or other priority) tags per domain. Insert the summary table at the top of the document.

### 5. Write Output

Default output path: `docs/features.md` — create `docs/` if it does not exist. If the user specified a different path, use it. Confirm the output path before writing.

### 6. Verify

After writing, confirm:

- The output file exists at the expected path
- The feature count matches the parser's input file count
- Every feature has at least one scenario row (parsing did not silently drop content)

**If any check fails: stop and report which check failed.** Do not declare the documentation complete.

## Rules

- Do not modify feature files — this skill is read-only except for writing the output doc
- If a feature file has no `Feature:` line, the parser emits `feature_name: ""` — call it out as `(no name)` in the output
- Flag scenarios with `@wip` or `@skip` tags in the summary as excluded
- Flag scenarios with no tags as potentially uncategorized
