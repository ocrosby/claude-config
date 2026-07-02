# Prompts

Reusable prompts for auditing and building Claude skills. Each file is a single, self-contained prompt — paste its body into a session, or adapt it as a starting point. Each prompt has a single focus; run the one whose lens matches what you need today.

## Skill audits

Prompts that review your existing skills, each through a different lens:

- [Audit skills for improvements](audit_skills_for_improvements.md) — flags structural refactor opportunities: deterministic logic that should be a script, templated output that belongs in `assets/`, repeated config that belongs in `config.json`, setup that `AskUserQuestion` would simplify, and inputs that warrant an `arguments` frontmatter field.
- [Audit skill descriptions](audit_skill_descriptions.md) — checks each frontmatter description for whether it reads as a summary or a trigger condition, and rewrites summaries into triggers that tell Claude when to fire.
- [Audit skill buckets](audit_skill_buckets.md) — classifies skills into the four buckets (Utility, Verification, Data Enrichment, Orchestration), surfaces skills you should have but don't, and flags any skill that straddles buckets. Includes a Verification deep dive that finds skills producing output they never check and proposes objective Pass/Fail or graded verdicts.

## Verifiers

- [Build verifier skill](build_verifier_skill.md) — walks through building one new verification skill from scratch for a named target, from objective verdict to check steps to output format.
