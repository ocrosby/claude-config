---
description: Gherkin feature-file style: declarative not imperative steps, one behavior per scenario, Given/When/Then discipline, one action per scenario. Fires on `.feature` files.
paths:
  - "**/*.feature"
---

# Gherkin Conventions

## Principles

- Features describe **behavior from the user's perspective**, not implementation details
- Each scenario is a single, independent example — no coupling between scenarios
- Write declarative steps (what), not imperative steps (how)
- Feature files are living documentation — readable by non-technical stakeholders

## Structure

```gherkin
Feature: User registration
  A new visitor can create an account and access the platform.

  Background:
    Given the registration page is open

  Scenario: Successful registration with valid details
    When the visitor registers with name "Alice" and email "alice@example.com"
    Then the account is created
    And a welcome email is sent

  Scenario: Registration fails with duplicate email
    Given a user exists with email "alice@example.com"
    When the visitor registers with name "Bob" and email "alice@example.com"
    Then the error "Email already registered" is shown
    And no new account is created
```

## Given / When / Then

- **Given**: establish preconditions — the system state before the action
- **When**: the action the user performs — exactly one action per scenario
- **Then**: the observable outcome — what the user can verify
- **And / But**: continue the previous step type — never start a scenario with And/But
- Keep each step on a single line where possible

## Writing Good Steps

### Declarative over imperative

```gherkin
# GOOD: declarative — what, not how
When the visitor registers with name "Alice" and email "alice@example.com"

# BAD: imperative — UI mechanics
When I click the "Name" field
And I type "Alice"
And I click the "Email" field
And I type "alice@example.com"
And I click "Submit"
```

### Consistent voice and tense

- Given: past tense or present state — "a user exists", "the page is open"
- When: present tense — "the visitor registers", "the visitor submits the form"
- Then: plain present tense — "the error is shown", "the account is created"
- Prefer third person and name the actor; use one person per scenario. Keep first person only where a repo's existing steps already use it

### Parameterize for reuse

```gherkin
# GOOD: parameterized — step definition reusable
Then the error "<message>" is shown

# BAD: hardcoded — new step definition per message
Then the duplicate email error is shown
```

## Scenario Outlines

Use for data-driven scenarios with multiple examples:

```gherkin
Scenario Outline: Password validation
  When the visitor registers with password "<password>"
  Then "<result>" is shown

  Examples:
    | password   | result                        |
    | ab         | Password must be 8+ characters |
    | abcdefgh   | Account created                |
    | abcDE12!@  | Account created                |
```

Use only when scenarios share identical steps and differ only in data.

## Tags

- `@wip` — work in progress, not yet automated
- `@smoke` — critical path tests for quick validation
- `@slow` — long-running scenarios, exclude from fast feedback loops
- Domain tags: `@auth`, `@billing`, `@onboarding` — group by feature area
- Never use tags to control step behavior — tags are for filtering and organization
- Lowercase, hyphenated, short; no near-duplicates. Put shared tags on `Feature:`/`Rule:`, specific ones on the scenario

## Background

- Use for preconditions shared by **every** scenario in the feature
- Keep it short — if Background exceeds 3 steps, the scenarios may belong in separate features
- Never put When or Then in Background — only Given steps

## Rules, Choices and Data

- Group scenarios under `Rule:` when a feature has several business rules; do not list rules in the description or link them with comments
- No "Or" steps — express variation with a Scenario Outline
- `Then` asserts something observable; no timed waits
- Do not assert volatile data (live values, timestamps, counts); assert shape, range or status
- Keep user stories and open questions out of feature files; resolve questions into rules or examples first

## Anti-Patterns

- **Scenario coupling**: scenarios that depend on state from previous scenarios
- **Imperative steps**: clicking buttons and filling fields instead of describing intent
- **Incidental details**: including data that doesn't affect the outcome
- **God feature**: one feature file with 20+ scenarios — split by behavior
- **Testing implementation**: steps that reference database tables, API endpoints, or CSS selectors
- **Conjunctive steps**: "Given A and B and C" — split into separate Given lines
- **Missing examples**: Scenario Outline without meaningful variation in the Examples table
