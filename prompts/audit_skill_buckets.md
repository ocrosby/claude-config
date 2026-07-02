# Audit Skill Buckets

Look at my EXISTING skills and my past chat history to find potential skills I should have. For each, tell me which of the 4 buckets it falls into — and flag any existing skill that straddles buckets and could be adjusted to fit one cleanly.

Buckets:

1. **Utility** — one small reusable thing, every time
2. **Verification** — checks final output quality
3. **Data Enrichment** — pulls EXTERNAL data in
4. **Orchestration** — chains other skills into a multi-step playbook

Rule: the best skills fit cleanly in ONE bucket; ones that straddle several confuse the agent. Orchestration coordinating other skills is NOT straddling.

Do this:

1. Scan my chat history for repeated tasks I do by hand that should be skills. For each: proposed name, bucket, the one job it does.
2. Review my existing skills. Flag any that straddle 2+ buckets, and say how to adjust it to fit one cleanly (split or trim scope).

## Deep dive: the Verification bucket

Verification is the bucket most often missing or done badly, so give it a closer pass. A good verifier has an OBJECTIVE output: a clear Pass/Fail, or a grade out of 10. It checks one of three things:

- **Correctness** — does the output actually run/compile/pass tests, match a schema or API contract, or satisfy a lint/style rule?
- **Fidelity** — are facts, config values, version numbers, or referenced docs/commands real and accurate (not hallucinated flags, deprecated APIs, wrong paths)?
- **Quality** — does the output meet a bar I care about (idiomatic Go, consistent commit-message format, PR description that actually explains the "why," docs that match the current CLI surface)?

For this bucket specifically:

3. Flag any skill that PRODUCES output but never CHECKS it (generators, drafters, scaffolders — e.g. something that writes commit messages, PR descriptions, Go boilerplate, config files, docs). For each: what would a Pass/Fail or /10 check on its output look like, and what would it check against (test suite, schema, style guide, actual repo state)?
4. Flag any skill that already verifies something but gives a vague, subjective verdict ("looks good," "seems fine"). Say exactly how to make its output objective — what's the pass criterion, what's the failing signal.
5. Recommend which existing skill to BORROW from instead of building new — e.g. a style/lint-convention skill that a `/pr-reviewer` could call to pass/fail formatting, or a schema-validation skill that a docs-generator could call to catch drift between docs and actual API/CLI behavior.
6. Rank by impact: which 2-3 verification tweaks would raise output quality the most.

Be blunt. Focus on real candidates and real straddlers — skip skills that are already clean.
