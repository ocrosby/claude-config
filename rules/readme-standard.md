---
description: Enforces professional structure and up-to-date workflow badges in root README.md files; also covers how to document Claude-configuration learnings in the dotfiles README.
paths:
  - "README.md"
  - "./README.md"
  - ".claude/**"
---

# README Standard — Root README.md

**This rule applies only to the `README.md` at the repository root. Do not apply it to README files in subdirectories.**

If the file being edited is not at the root of the repository (i.e., its path contains a directory component such as `src/foo/README.md`), ignore this rule entirely.

**Every root `README.md` must conform to this standard. Do not ship a README that violates it.**

## Required Sections — In This Order

Every root `README.md` must contain all of the following H2 sections. If a section is genuinely not applicable (e.g., no configuration exists), keep the heading and write "N/A" rather than omitting it.

1. **Project title** — H1 with the repository name, followed immediately by a one-sentence description
2. **Badges** — workflow status badges (see below), license, and any relevant quality badges
3. **Table of Contents** — required when the README exceeds four sections
4. **Overview** — what the project does and why it exists; 2–5 sentences
5. **Features** — bullet list of capabilities or highlights
6. **Requirements** — runtime and tooling prerequisites with version constraints
7. **Installation** — step-by-step setup using fenced code blocks for all commands
8. **Usage** — at least one working example with output; more for complex tools
9. **Configuration** — environment variables, config files, flags, and their defaults
10. **Development** — how to set up the local dev environment, run tests, and build
11. **Contributing** — how to open issues and PRs; reference `CONTRIBUTING.md` if it exists
12. **License** — one line naming the license; reference `LICENSE` file

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

## When This Rule Triggers

This rule fires whenever `README.md` at the repository root is edited. Before finalizing any README change:

1. Confirm all required sections are present
2. Confirm badges match the current `.github/workflows/` directory exactly
3. Confirm all code blocks have language hints
4. Confirm the H1/H2/H3 hierarchy is correct

---

## Documenting Claude-Configuration Learnings (claude-config repo only)

The remainder of this rule applies only when editing the `README.md` of the `claude-config` dotfiles repo, or any file under `.claude/**`. In other projects, ignore this section.

When a session produces a new insight about how Claude rules, skills, hooks, or agents work — or reveals a pattern that caused drift, cycles, or inconsistency — update `README.md` in the `.claude/` directory and push it to main.

### When to trigger this

A learning has occurred when any of these happen:

- A rule was changed because it was too soft, too vague, or contradicted another rule
- A hook or skill was found to not enforce what it claimed to enforce
- A contradiction between two files caused Claude to alternate between behaviors
- A new pattern was discovered that makes rules more durable (e.g., "always" vs "suggest")
- A specific configuration decision is made that future sessions might undo without context
- A language-specific practice (Go, Python, Lua) is found to work better than the previous approach
- A CI debugging loop required multiple rounds of iteration — the root cause is a candidate lesson
- A tooling version compatibility issue was discovered (e.g., linter built with wrong Go version)
- A build/test failure was caused by a pattern that an existing rule or hook should have caught
- An audit (`/audit`) revealed gaps between stated behavior and actual enforcement

**These are high-priority triggers.** If a session involved 3+ rounds of CI debugging to fix an issue that a rule could have prevented, that is always worth a README entry.

### What to write

Each entry should be placed under the appropriate section heading in `README.md`. Write it as a short, concrete lesson — not a description of what was changed, but what was learned and why it matters for future rule authoring.

Structure:
- **One sentence stating the lesson**
- Optional: a before/after example showing the drift pattern and the fix
- Optional: the specific consequence that prompted the change

Do not pad entries. If the lesson can be stated in one sentence, use one sentence.

### How to update

1. Read the current `README.md`
2. Add the new entry under the appropriate section (or create a new section if none fits)
3. Run `/git ship -m` to commit directly to main and push without a PR — use commit message `docs(claude): add learning — <one-line summary>`
4. Do not batch learnings across sessions — ship immediately after each session that produced a new learning

### Sections in README.md

- **Rule Authoring** — lessons about writing durable, enforceable rules
- **TDD Enforcement** — lessons about test-driven development consistency
- **Go-Specific** — Go tooling, patterns, and reviewer behavior
- **Python-Specific** — Python tooling, patterns, and reviewer behavior
- **Lua/Neovim-Specific** — Lua plugin conventions and reviewer behavior
- **Complexity** — code quality limits and their rationale
- **Concurrency (Go)** — goroutine, channel, and context patterns
- Add new sections when learnings don't fit existing ones
