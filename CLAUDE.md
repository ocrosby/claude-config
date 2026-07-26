# Development Workflow

Run `/workflow` to see the complete development workflow reference (architect → implement → review → ship).

---

# Token Efficiency & Speed (mandatory)

Every token loaded costs latency **and** compounds across every turn until compaction. Optimize aggressively — my time is worth more than context breadth.

**Defaults that must always apply:**

- **Offload to scripts/CLIs first.** Any deterministic parsing, scanning, classifying, aggregating, or format-checking work goes into a `scripts/*.py` (or `.sh`) that returns structured output. Do not reason through it in chat. Signals to extract: multi-step sed/awk/jq pipelines, repeated parsing across invocations, format-stable output, >20 lines of logic, work that would be re-derived on the next invocation. Exemplar: `scripts/tally_invocations.py`.
- **Prefer one-shot CLIs over multi-step tool loops.** `rg -l pattern` beats N Grep calls. `git diff --stat main...HEAD` beats iterating files. `gh pr list --json ...` with `jq` beats a subagent. `find -printf` with `sort -rn` beats a bespoke walker. If a single shell pipeline can answer the question, run it — do not delegate.
- **Batch parallel tool calls.** Independent Reads/Bashes/Greps in one message, never serialized. Serialize only on genuine data dependency.
- **Skip discovery when not needed.** Do not read README/CONTRIBUTING/ARCHITECTURE/docs unless the current task requires that context. `rules/session-startup.md` is opt-in — override the default for narrow tasks (single-file edits, quick lookups, config tweaks).
- **Use subagents surgically, not reflexively.** Spawn `Explore` / `general-purpose` only when the answer takes >3 tool calls **and** the output pollutes the main context. A one-line `grep` or `rg` is faster and cheaper than any agent.
- **Never restate a referenced rule.** If a section links to `rules/foo.md`, the linking file gets a one-line pointer and (optionally) the trigger signals — never a paragraph paraphrase. Duplicated rule content in `CLAUDE.md`, skills, or agents is a Must Fix at review time.
- **Keep Level 2 tight.** Any `SKILL.md` over ~200 lines needs justification; move reference material to Level 3 files the workflow reads only when needed. Same for `agents/*.md` — descriptions load every session.
- **Prefer terse, action-first responses.** No preamble, no recap. State results and next step; skip narration of tool calls the user can already see.

**Self-improvement loop:** when a task felt slow or context-heavy, name the culprit before ending the turn (which file, which extra load, which redundant tool call) and either fix it now or add a follow-up. Do not let heavy patterns re-appear.

# Context-First Development

High-quality code communicates **why**, not just **what**. Before changing code, understand why it's written that way. When writing new code, make the reasoning evident. When something is unclear, ask about purpose, not mechanics. Preserve business rules, architectural constraints, and prior decisions rather than optimizing them away.

# Always-on rule references (pointer only — do not paraphrase)

- **Algorithmic complexity** → `rules/algorithmic-complexity.md`. Triggers: nested loops over the same collection, `in list` inside a loop, recomputed subproblems, wrong-container choice, unbounded loop on external input (every such loop must name a cap).
- **Defensive assertions** → `rules/defensive-assertions.md`. Every non-trivial function carries at least one pre/post-condition or invariant; assertions are side-effect-free; every non-void return is used or explicitly discarded with a one-line reason. Never silently discard an error return.
- **Lint suppression** → `rules/lint-suppression.md`. Every `# noqa` / `//nolint` / `# type: ignore` / `eslint-disable` needs the rule code **and** an inline reason. Disable globally if annoying; do not sprinkle.
- **Unit testing (in order)** → `rules/black-box-testing.md` (shape, non-negotiable) → coverage as detector → `rules/mutation-testing.md` (assertion strength). Never invert the order.
- **Tool language selection** → `rules/tool-language-selection.md`. Rust for tree-sitter / AST-heavy scans / stylua-shelf ecosystem; Go for CI plumbing / cloud-native / existing-Go-tool code-sharing. Name the signal that drove the pick.

# Task Tracking

For multi-step work, create `TODO.md` at the repo root with a checklist; add to `.gitignore` on first write.

# Commit Messages

Conventional Commits: `<type>(<scope>): <description>` — lowercase, imperative, no period. Types: `feat|fix|docs|style|refactor|perf|test|build|ci|chore`. Breaking = `!` + `BREAKING CHANGE:` footer.

# PR Discipline

One PR = one `type(scope)` pair. If the description contains "and", split the concerns. Name the branch after the intended commit before touching files.

**Mixed concerns mid-stream:** `git stash push -u -m "split: <desc>"` → one branch from main per concern → apply relevant files → PR each targeting main.

**Before pushing:** `git fetch origin main` and rebase if branch's changed files also changed on main.

**Before pushing to any protected branch (main/master/etc.):** check **both** legacy branch protection **and** rulesets — separate GitHub features; a 404 from one is not proof of "unprotected."

```bash
owner=... repo=... branch=main
gh api "repos/$owner/$repo/branches/$branch/protection" \
  --jq '.required_pull_request_reviews // .required_status_checks // "protected"' 2>/dev/null
gh api "repos/$owner/$repo/rules/branches/$branch" \
  --jq '[.[] | select(.type == "pull_request" or .type == "required_status_checks" or .type == "required_signatures" or .type == "required_deployments")] | length'
```

Direct push is fine **only if BOTH** clear (protection 404 *and* rulesets `0`). Otherwise open a PR. A successful bypass is not permission to bypass. **If the remote reports `Bypassed rule violations`, surface it immediately — do not treat exit 0 as success.**

# Self-Improvement

After every correction or mistake, update the relevant rule/skill/`CLAUDE.md` with a guard. Prompt ending a correction: "Now update the relevant rule/skill/CLAUDE.md so you don't make that mistake again."

Each learning has exactly one home:
- **Rule / skill / `CLAUDE.md` guard** — enforceable behavior change (default).
- **`LEARNINGS.md`** — repo-committed insights about how rules/skills/hooks/agents behave (drift, gotchas). See `rules/readme-standard.md`.
- **Memory system** — cross-project, user-specific behavioral preferences.

# Neovim Integration

When `$NVIM` is set, Claude Code runs inside a Neovim terminal and can talk to the parent via msgpack-RPC. Treat `skills/nvim/rpc.md` as **auto-applicable reference** — do not wait for `/nvim rpc`.

- Apply RPC when the question is about the live editor (buffer, cursor, LSP, runtime files).
- Opening a user-requested file: `nvim --server "$NVIM" --remote <path>` (or `--remote-tab`).
- After external edits, refresh LSP via the reload/`:LspRestart` sequence in `skills/nvim/rpc.md`.
- Safety: prefer `--remote-expr` (read-only) over `--remote-send`; never send `:q`/`:qa`/`:bdelete` or modify buffer contents without explicit confirmation.

# Reference

- **Install/reinstall (stow):** see `README.md`. Never add a `.claude/` wrapper inside this repo — the repo root *is* the stow package.
- **Plan mode / session mgmt / parallel work (worktrees, subagents) / multi-repo (`--add-dir`, `additionalDirectories`):** see `docs/OPERATING.md`.
- **External references for prior-art lookup:** `worldflowai/everything-claude-code`, `obra/superpowers`.
