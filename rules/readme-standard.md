---
description: Enforces professional structure and up-to-date workflow badges in root README.md files
paths:
  - "README.md"
---

# README Standard — Root README.md

**Every root `README.md` must conform to this standard. Do not ship a README that violates it.**

This rule's `paths` glob (`README.md`, bare) anchors to the repository root, so the rule only fires on the root README — README files in subdirectories are covered by their own local conventions, not this rule.

## Required Sections — In This Order

Every root `README.md` must contain all of the following H2 sections. If a section is genuinely not applicable (e.g., no configuration exists), keep the heading and write "N/A" rather than omitting it.

1. **Project title** — H1 with the repository name, followed immediately by a one-sentence description
2. **Badges** — workflow status badges (see below), license, and any relevant quality badges
3. **Table of Contents** — required when the README exceeds four sections
4. **Overview** — what the project does and why it exists, written to the Explanation Contract below
5. **Features** — bullet list of capabilities or highlights
6. **Requirements** — runtime and tooling prerequisites with version constraints
7. **Installation** — step-by-step setup using fenced code blocks for all commands
8. **Usage** — at least one working example with output; more for complex tools
9. **Examples** — worked, verified, progressively deeper applications (see below). Required unless a single Usage example fully demonstrates the surface.
10. **Configuration** — environment variables, config files, flags, and their defaults
11. **Development** — how to set up the local dev environment, run tests, and build
12. **Contributing** — how to open issues and PRs; reference `CONTRIBUTING.md` if it exists
13. **License** — one line naming the license; reference `LICENSE` file

## The At-a-Glance Test

**A reader in the target audience must understand what the project is for, and why they'd want it, from the first screen alone** — title, one-liner, and Overview. No scrolling, no clicking through to docs, no reading the API.

Before writing, name the assumed reader in one sentence: *"someone already comfortable with Neovim motions but who has never written an operator."* Every subsequent choice — which jargon is free, which must be taught, which comparison lands — follows from that line. Calibrating to "everyone" produces a README that teaches the expert nothing and the novice too little.

A README that passes structural checks but fails this test is **not** compliant. Structure is the floor, not the goal.

## Overview — The Explanation Contract

The Overview is the only section most visitors read. It must do four things, in order. Two to six short paragraphs; if it exceeds one screen, it is doing the Usage section's job.

1. **Anchor** — connect the unfamiliar thing to something the assumed reader already knows and uses. Never define jargon with more jargon. *"An operator is a verb that waits for a motion. `d` is an operator, so is `y`, `c`, and `gU`."*
2. **Gap** — name what people do today instead, and where it falls short. Be specific about the failure, not dismissive. *"Most plugins ship a command or a keymap that hardcodes one scope — so it doesn't compose, doesn't take a text object, and doesn't repeat."*
3. **Cost** — enumerate concretely what doing it properly by hand actually requires. "It's tedious" is not a cost; a list of the six fiddly things you'd have to get right is. This paragraph is what converts a curious reader into a user.
4. **Payoff** — the smallest complete snippet that works, immediately followed by a concrete enumeration of what it bought. Show the combinatorial surface rather than asserting it exists.

The Anchor→Gap→Cost→Payoff shape is mandatory for any project whose core concept the assumed reader may not hold. For a project whose purpose is self-evident from its name and one-liner (a CLI that formats JSON), Anchor and Cost may collapse into a single sentence — but Gap and Payoff always stay.

### Signals the Overview is not doing its job

| Signal | Fix |
|---|---|
| Opens with implementation detail, architecture, or a dependency list | Lead with what the reader gets; mechanism goes in API or Development |
| Describes capability in the abstract ("flexible", "powerful", "ergonomic") with no concrete instance | Replace every adjective with a snippet or an enumerated outcome |
| Defines the core noun using terms only an existing user would know | Anchor to something in the reader's current toolkit |
| Reader must reach the API section to learn why the project exists | Move the payoff into Overview |
| No mention of what people currently do instead | Add the Gap paragraph — without it the project reads as unmotivated |
| Prose asserts composability/extensibility without demonstrating it | Enumerate the actual combinations, or show a table of them |

## Examples — Worked, Verified, Progressive

The Usage section proves the project runs. The Examples section proves it is worth running. These are different jobs; do not collapse them.

- **Two to four examples, progressively deeper.** Order them so each introduces exactly one new idea: the obvious win first, then a case exposing a real subtlety (boundary handling, an inclusive index, an error path), then a case that reframes what the tool is for.
- **Each example states why you'd reach for it**, in one line, before or after the code. A code block with no motivation is reference material, not an example.
- **Name the gotchas inline.** If a parameter is inclusive, a column is 0-indexed, or a callback receives a different type in one mode, say so at the point of use — that is precisely where the reader will otherwise get it wrong.
- **Show the resulting surface, not just the call.** A short table mapping inputs to outcomes communicates a combinatorial API faster than any paragraph.

## Verify Every Claim Before Writing It

**Do not write literal commands, keys, flags, function names, or output from memory or by pattern-matching the surrounding prose.** A wrong literal in a README is worse than a missing one: the reader trusts it, tries it, and it fails silently or does something else entirely.

Required before finalizing:

1. **Run the examples.** Execute each Examples and Usage snippet against the real project — a scratch script, a headless run, an actual invocation. Reading the source and reasoning that it should work is not verification. Delete or fix any snippet that does not run.
2. **Grep every literal against the code.** Command names, flags, env vars, `<Plug>` mappings, config keys, exported symbols — confirm each exists as written.
3. **Re-derive advertised behavior from the source**, especially keys or commands the project overrides. A README that advertises a default the project shadows is a Must Fix.
4. **Check Development commands actually exist** — every `make` target, script, or task named must be present in the Makefile / package.json / task file.

State in your turn summary that examples were executed and how. If a snippet genuinely cannot be run in the current environment, mark it in the README as illustrative and say so in the summary — do not present unverified code as working.

## Findings Severity

When reviewing a README, report findings per `rules/findings-format.md`:

- **Must Fix** — an unverified or incorrect literal (command, key, flag, symbol); an example that does not run; a missing required section; a badge pointing at a deleted or renamed workflow; an Overview that fails the At-a-Glance Test for its stated audience.
- **Should Fix** — Overview missing the Gap or Cost move; capability asserted with adjectives instead of demonstrated; Examples section absent where the surface is combinatorial; gotchas documented far from the code that trips on them.
- **Consider** — an additional example that would cover a distinct use case; a surface table that would replace a dense paragraph; tighter ordering of the example progression.

## Workflow Badges — Mandatory Synchronization

**Every workflow file in `.github/workflows/` must have exactly one badge in the README.** If a workflow is added or removed, the badge row must be updated in the same change.

### How to generate a badge

For each file at `.github/workflows/<filename>.yml`, the badge is:

```markdown
![<Workflow Name>](https://github.com/<owner>/<repo>/actions/workflows/<filename>.yml/badge.svg)
```

Where `<Workflow Name>` is the value of the top-level `name:` field in the workflow file.

To find the correct owner/repo, read the remote URL: `git remote get-url origin`.

### Deriving badges — required steps

When writing or updating `README.md`:

1. Run `ls .github/workflows/` to list all workflow files
2. For each file, read the `name:` field from line 1–5 of the file
3. Confirm the badge URL uses the exact filename (including `.yml` extension)
4. Verify every workflow file has a badge — no workflow may be undocumented
5. Remove any badge whose workflow file no longer exists

### Badge placement

Place all badges in a single row immediately below the H1 title, before any prose. Example:

```markdown
# my-project

One-sentence description of what it does.

![CI](https://github.com/ocrosby/my-project/actions/workflows/ci.yml/badge.svg)
![Lint](https://github.com/ocrosby/my-project/actions/workflows/lint.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
```

## Formatting Standards

- Use H1 (`#`) for the project title only — never for sections
- Use H2 (`##`) for all required sections listed above
- Use H3 (`###`) for subsections within a required section
- All shell commands must be in fenced code blocks with a language hint: ` ```bash `, ` ```go `, ` ```python `
- No raw URLs in prose — link text must describe the destination
- No trailing whitespace on any line
- No more than one blank line between any two elements

## What "Professional" Means in Practice

- The README must be readable by someone unfamiliar with the project
- Every code example must be complete enough to copy-paste and run
- Section headings must match the actual content (no "Usage" section that only has a link)
- The badge row must not contain broken or stale badges — a badge pointing to a deleted or renamed workflow is worse than no badge
- Do not use emoji in section headings unless the project style already uses them consistently throughout

## Anti-Patterns to Avoid

- **Adjective-driven description.** "Fast, flexible, and ergonomic" tells the reader nothing. Every claim is a snippet, a number, or an enumerated outcome — or it is cut.
- **Jargon defined with jargon.** If explaining the core noun requires a second unfamiliar noun, the Anchor move has not been made.
- **Feature-list-as-Overview.** A bulleted list of capabilities is the Features section. The Overview must argue *why*, not inventory *what*.
- **Examples written from the API surface rather than from a use case.** An example that exists to exercise a parameter is documentation of that parameter; move it to the API section.
- **Copying a literal from elsewhere in the README instead of from the code.** This is how a wrong key or flag propagates through every section at once.
- **Deferring the point to the docs.** "See the docs for what this does" in an Overview means the README has no Overview.
- **Silent narrowing of a claim.** If a behavior only applies to one mode, one platform, or one motion type, say which — an unqualified claim that holds 70% of the time is a defect.

## Before finalizing any README change

1. Confirm all required sections are present
2. Confirm the Overview passes the At-a-Glance Test for a named assumed reader
3. Confirm every Usage and Examples snippet was **executed**, not merely reviewed
4. Confirm every literal (command, key, flag, symbol, make target) was grepped against the code
5. Confirm badges match the current `.github/workflows/` directory exactly
6. Confirm all code blocks have language hints
7. Confirm the H1/H2/H3 hierarchy is correct

## See also

- `rules/docs-principles.md` — general documentation principles (skimmable, exemplary, current, human-centered errors). This rule is the root-README specialization; where both apply, both hold.
- `rules/findings-format.md` — the three severity buckets used when reporting README review findings.
- `rules/learnings-standard.md` — how to record repo-committed insights about Claude configuration in `LEARNINGS.md` (dotfiles repo only). Do **not** put learnings content in `README.md`.
