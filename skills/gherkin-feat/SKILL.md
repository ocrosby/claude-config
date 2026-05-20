---
description: Guides writing new Gherkin feature files and step definitions, delegating review to the gherkin-reviewer agent and /code-review.
aliases: gherkin-feature
paths:
  - "**/*.feature"
---

# Gherkin Feature Development

Use this skill when writing a new Gherkin feature file and its supporting step definitions. This skill owns BDD-specific design decisions (scenario shape, step granularity, World/context state). It **delegates** review to the `gherkin-reviewer` agent and `/code-review -fc`. Do not re-implement the review checklist inline.

## Workflow

### 1. Understand the Behavior

- Clarify the capability from the user's perspective
- Identify the actors: who triggers the behavior?
- Identify the outcomes: what is observable when it succeeds? When it fails?
- Gather concrete examples from stakeholders — examples become scenarios

> Run `/architect` first only when the feature spans multiple domain areas or requires designing the full suite structure (feature file organization, step definition boundaries). For single-feature additions, skip it.

### 2. Write the Feature File

- Start with the user story: As a / I want / So that
- Write the happy path scenario first
- Add edge cases and error scenarios
- Use `Background` for shared preconditions across all scenarios
- Use `Scenario Outline` for data-driven variations

### 3. Design Steps

- Write declarative steps — describe intent, not mechanics
- Parameterize reusable values in quotes or angle brackets
- Keep to one `When` step per scenario — one action under test
- `Then` steps assert observable outcomes only

### 4. Implement Step Definitions

- Create thin step definitions: parse parameters, delegate, assert
- Extract interaction logic into page objects or API client helpers
- Share state between steps via the World/context object
- Reuse existing step definitions — check common steps before writing new ones

### 5. Wire Up Support

- Set up `Before`/`After` hooks for scenario isolation (reset state, clean data)
- Configure environment (base URLs, credentials, browser setup)
- Add custom parameter types for domain concepts

### 6. Verify the Feature Parses and the Happy Path Runs

Run the test framework to confirm:

- The feature file parses without syntax errors
- Step definitions are discovered (no undefined-step warnings)
- The happy path scenario passes end-to-end

If any of these fail: stop and fix before proceeding to review.

### 7. Review via /code-review

Invoke `/code-review -fc` on the changed feature files and step definitions. The review skill owns:

- Running `gherkin-lint` if available
- Delegating to the `gherkin-reviewer` agent for BDD best practices, scenario coupling, and step reuse
- Auto-fixing Must Fix and Should Fix findings, looping until clean

Do not re-implement the review checklist here — `gherkin-reviewer` covers declarative vs imperative steps, scenario isolation, state leakage, and Background overuse. If `/code-review -fc` reports findings that require manual judgment, address them before declaring the feature complete.
