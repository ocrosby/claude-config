# docs write — Gherkin (living documentation)

Applied when `write.md` detects `gherkin`. Generates living documentation from feature files.

1. **Parse feature files** via the shared script:
   ```bash
   python3 ~/.claude/scripts/parse_gherkin.py <path-or-glob>... [--summary]
   ```
   The script walks `.feature` files (excluding `node_modules/`, `.venv/`) and emits JSON. **If no `.feature` files found: stop and report "No feature files in scope".**

2. **Group by domain.** The script returns features in file-system order. Group by parent directory — each directory typically represents a domain (auth/, users/, payments/).

3. **Render Markdown** with this shape:
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

   For Scenario Outlines, show one representative row from Examples and note "N variants". Truncate step summaries at 80 characters.

4. **Add coverage summary.** Compute totals: features, scenarios, `@smoke` (or other priority) tag counts per domain. Insert at top.

5. **Write output.** Default path `docs/features.md` — create `docs/` if missing. **If the user has not confirmed the output path: stop and ask. Do not write without an explicit path confirmation.**

6. **Verify** output file exists, feature count matches parser's input file count, every feature has at least one scenario row. **If any check fails: stop.**

**Rules for `write gherkin`.** Read-only on `.feature` files. If a feature has no `Feature:` line, parser emits `""` → call it `(no name)`. Flag `@wip`/`@skip` scenarios as excluded; flag scenarios with no tags as potentially uncategorized.
