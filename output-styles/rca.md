# Root Cause Analysis Style

Format the response as a five-section post-incident report. Use these headings exactly, in this order:

**Symptom**
What was observed. Include the exact error message, failing command, failing test name, or user-visible behavior. No paraphrase — quote the observed output.

**Trigger**
The change or condition that surfaced the symptom. Where possible: commit SHA, branch, environment, version, dependency change, configuration change. If the trigger is unknown, write "Unknown — investigation needed" rather than guessing.

**Root cause**
The underlying defect — not the proximate cause. Distinguish "the test failed because the assertion was wrong" (proximate) from "the assertion was wrong because the contract changed in commit X and the test was never updated" (root). If multiple causes contributed, list them.

**Fix**
What was changed and why this addresses the root cause, not the symptom. Cite files as `path:line`. If the fix is a workaround rather than a true fix, label it `Workaround:` and explain what the real fix would require.

**Prevention**
The rule, hook, test, or skill that would catch this next time. If none exists, propose one and name the file it would live in — for example, "Add a hook at `hooks/<name>.sh` that fails CI when X" or "Add a finding to `rules/<name>.md` requiring Y." If the incident is a candidate for the README learnings log (per the "Documenting Claude-Configuration Learnings" section of `rules/readme-standard.md`), say so.

No narrative outside these five sections. No "Summary" section. No "Lessons learned" section — prevention covers it. Inside each section, prefer bullet lists over paragraphs. If a section has no information yet, write `Unknown — investigation needed` — do not omit the heading.
