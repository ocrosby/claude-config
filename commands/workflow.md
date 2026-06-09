---
description: Reference map for the full development workflow — orientation to which skill, agent, command, hook, and rule fires at each stage (architect → feature → code review → git ship → git main), plus maintenance commands, debugging paths, and automated quality gates.
---

# Development Workflow

Complete reference for the development workflow and when to use each skill, agent, and hook.

## Standard Feature Workflow

```
/architect design → /feature (TDD) → /code review → /git ship → /git main
```

### 1. `/architect design` — design before implementing
Invoke for anything beyond a trivial change: new packages, significant new abstractions, cross-cutting concerns. Auto-detects language and routes to `go-architect`, `py-architect`, `nvim-architect`, or `gherkin-architect`. Output: module map, dependency graph, public API surface, trade-offs. Capture decisions in `ARCHITECTURE.md`. Also supports `/architect patterns`, `/architect spec`, `/architect catalog`.

### 2. `/feature` — implement with TDD
Auto-detects language and dispatches to the matching workflow (go, py, nvim, gherkin, rest). The `tdd` rule auto-enforces red-green-refactor. The lint hook runs automatically after every file save.

### 3. `/code review` — catch issues before shipping
Delegates to `go-reviewer`, `py-reviewer`, `nvim-reviewer`, or `gherkin-reviewer` for deep, criteria-driven review. Auto-routes to `rest-reviewer` when HTTP handler patterns are detected. The `skill-suggest` rule recommends this after significant implementation. For an adversarial pass, use `/code grill`.

### 4. `/git ship` — branch, commit, push, open PR
Pre-flight runs lint + tests (skip with `--quick` for daily iteration on a branch with established CI coverage). Validates conventional commit format. Never commits directly to main (hook enforced) unless `-m` or `-p` is passed. Returns the PR URL.

### 5. `/git main` — after PR merges
Checkout main, pull latest, delete merged branches.

---

## Branch Management

| Situation | Command |
|---|---|
| Feature branch needs to catch up with main | `/git sync` — rebase onto main, handle conflicts |
| PR merged, ready for next task | `/git main` — checkout + pull + clean |
| Spin up a parallel worktree | `/git worktree [name]` |
| Generate release notes from commits | `/git release-notes [range]` |

---

## Maintenance

| Task | Command | When |
|---|---|---|
| Deprecated API calls | `/code migrate` | Suggested by `skill-suggest` rule when old patterns detected |
| Structural design issues | `/code refactor` | Go, Python, and Neovim supported |
| Missing documentation | `/docs write` | Suggested by `skill-suggest` rule when public API added without docs |
| Post-review code quality | `/code simplify` | After `/code review` to apply fixes for reuse, quality, and efficiency (delegates to external `/simplify`) |
| REST API compliance | `/code review --rest` | Review HTTP handlers for REST convention compliance (resource naming, status codes, statelessness) |
| End-of-session cleanup | `/code techdebt` | Find and remove duplicates and dead code |
| Benchmarking | `/bench` | Auto-detects Go / Python / Neovim and runs the matching workflow |
| Design pattern decisions | `/architect patterns` | When designing architecture or reviewing structural code decisions |
| Documentation review | `/docs review` | After writing or updating public-facing docs |
| OpenAPI design-first | `/architect spec` | Before implementing a new REST endpoint |
| Backstage catalog init | `/architect catalog` | First-time Backstage registration for a repo |
| Author or improve skills | `/skill author` | When adding or modifying a Claude skill |

---

## Debugging

| Situation | Tool |
|---|---|
| Test failure or bug | `/debug` — language auto-detect; produces a minimal-repro artifact, then escalates |
| Need deep root cause | Invoke `go-debugger`, `py-debugger`, `nvim-debugger`, or `gherkin-debugger` directly |

---

## Running Tests

Use `/test-and-fix` (building-block command, invoked by other skills) or run tests directly. `/bdd <feature-file>` runs a Gherkin BDD feature file with the correct environment and region.

| Language | Command |
|---|---|
| Go | `go test -race ./...` |
| Python | `pytest` |
| Neovim/Lua | `nvim --headless -u tests/minimal_init.lua -c "PlenaryBustedDirectory tests/"` |

---

## Automated Quality Gates

These run without being asked:

| Trigger | What runs | Effect |
|---|---|---|
| Every file edit (Edit/Write) | `lint.sh` — py: ruff; go: golangci-lint/go vet; lua: stylua+luacheck; sh: shellcheck; yaml: actionlint/yamllint; toml: uv lock --check; feature: gherkin-lint | Shows lint errors for Claude to fix |
| Before every `git commit` | `protect-main.sh` — checks current branch | Blocks commits directly to main/master |
| After every `git commit` | `commit-msg.sh` — validates conventional commits | Warns Claude to amend if format is wrong |

---

## Rules That Fire Automatically

| Rule | Fires when | Suggests |
|---|---|---|
| `tdd` | Implementing new features or bug fixes | Red-green-refactor cycle (no skill invocation; the rule itself enforces) |
| `skill-suggest` | After significant implementation, deprecated patterns, or new public APIs | `/code review`, `/code migrate`, or `/docs write` |

---

## Utilities

| Tool | Command | Description |
|---|---|---|
| Daily task journal | `/work` | Add, list, complete, and note tasks in a date-structured work log at `~/work/` |
| Research and publish | `/docs research <topic>` | Research any topic via live web sources and publish a self-contained report to here.now — returns a live URL |
| Skill catalog gaps | `/skill gaps` | Identify repeating tasks with no skill coverage |
| Skill catalog usage | `/skill usage` | Count invocations and recommend retirement |
| System audit | `/audit system` | Audit the whole `.claude/` system (rules, agents, hooks, skills, commands, settings) |
| Per-skill audit | `/audit skill` | Run `skill-reviewer` on every SKILL.md |
