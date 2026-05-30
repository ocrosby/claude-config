# Development Workflow

Run `/workflow` to see the complete development workflow reference (architect → implement → review → ship).

---

# Context-First Development

The mark of a high-quality codebase is that it explains its *reasoning*, not just its behavior — it communicates **why**, not just **what**.

Apply this principle consistently in every session:

- **Before making changes**: Understand why the existing code is written the way it is. Read surrounding context, related files, and patterns before proposing modifications. Don't change what you don't yet understand.
- **When writing or suggesting code**: Make the reasoning behind decisions evident. Don't just implement mechanically — surface the intent so that future readers (human or AI) understand why a choice was made.
- **When exploring unfamiliar code**: Identify the *why* behind design choices, constraints, and patterns — not just the *what*. Architectural decisions, naming conventions, and structure all carry meaning.
- **When something is unclear**: Ask about purpose and context, not just mechanics. "Why does this need to work this way?" is often more important than "How does this work?"
- **Treat context as first-class information**: Business rules, architectural constraints, prior decisions, and team conventions are as important as the code itself. Surface and preserve this reasoning rather than optimizing it away.

Code that loses its reasoning becomes legacy code. Every interaction should add clarity about *why*, not just *what*.

# Algorithmic Complexity

Favor the lowest time and space complexity that solves the problem, in every language. Recognize the signals in `rules/algorithmic-complexity.md` (nested loops over the same collection, `in list` checks inside a loop, recomputed subproblems, intermediate lists for single aggregates, wrong-container choices) and apply the lower-complexity alternative as the default form — not as a follow-up "optimization." When the higher-complexity form is intentional (small bounded N, one-shot script, dramatically clearer at a single-use call site), say so explicitly.

# Task Tracking

When working on complex tasks (multi-step implementations, multi-file changes, bug hunts, refactors — anything where tracking progress adds value), create a `TODO.md` file at the root of the current git repo with a checklist of planned steps. Check off items as they are completed.

Always ensure `TODO.md` is listed in the repo's `.gitignore`. If it isn't, add it as part of the first write.

# Commit Messages

Always use Conventional Commits: `<type>(<scope>): <description>` — lowercase, imperative mood, no period.
Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`. Breaking changes use `!` and a `BREAKING CHANGE:` footer.

# PR Discipline

One PR = one `type(scope)` pair. Before creating a branch, committing, or pushing, ask: "Can I describe all of these changes with a single conventional commit subject line?" If the answer contains "and" — there are mixed concerns that must be split.

**When starting work:** name the branch after the intended commit (e.g. `chore/remove-junitxml`, `test/bdd-v2-steps`) before touching any files. Don't let unrelated changes accumulate on the same branch.

**When mixed concerns are detected mid-stream:**
1. Stash all uncommitted changes: `git stash push -u -m "split: <description>"`
2. Create one branch from `main` per concern
3. Apply only the relevant files to each branch from the stash
4. Each branch gets its own PR targeting `main`

**Before pushing:** run `git fetch origin main` and check whether the files you changed also changed on main since the branch diverged. If they did, rebase before opening the PR: `git rebase origin/main`.

# Installing this configuration

This repository (`ocrosby/claude-config`) is a GNU Stow package. Its contents are linked directly into `~/.claude/`. To (re)install or re-link, run from the repo root:

```bash
mkdir -p ~/.claude
stow -t ~/.claude -d "$(dirname "$PWD")" "$(basename "$PWD")"
```

Equivalent absolute form, works from anywhere:

```bash
stow -t ~/.claude -d ~/src/github.com/ocrosby claude-config
```

Never add a `.claude/` wrapper directory inside this repo. The repo root *is* the stow package; its top-level items (`agents/`, `skills/`, `rules/`, `commands/`, `hooks/`, `output-styles/`, `CLAUDE.md`, `settings.json`, …) are what get linked into `~/.claude/`. **This is an intentional design decision — do not simplify it away.** Stow's default ignore list excludes `README.*`, `LICENSE.*`, `.git`, and `.gitignore`, so those stay in the repo only.

# Self-Improvement

After every correction or mistake, update the relevant rule, skill, or `CLAUDE.md` itself with a guard to prevent repeating it. Claude is good at writing rules for itself.

When ending a correction, prompt with: "Now update the relevant rule/skill/CLAUDE.md so you don't make that mistake again."

Iterate until the mistake rate measurably drops.

# Working with Plan Mode

- Start every complex task in plan mode (shift+tab to cycle).
- Pour energy into the plan so Claude can 1-shot the implementation.
- When something goes sideways, switch back to plan mode and re-plan. Don't keep pushing.
- Use plan mode for verification steps too, not just for the build.

# Parallel Work

- For tasks that need more compute, use subagents to work in parallel.
- Offload individual tasks to subagents to keep the main context window clean and focused.
- When working in parallel, only one agent should edit a given file at a time.
- For fully parallel workstreams, use git worktrees: `git worktree add .claude/worktrees/<name> origin/main`.

# Session Management

- `/branch` forks a session (or `claude --resume <session-id> --fork-session` from CLI).
- `/btw` answers quick side queries without interrupting the agent's current work.
- `/teleport` continues a cloud session on your local machine.
- `/remote-control` controls a local session from your phone or browser.
- `/voice` (CLI) or the voice button (Desktop) enables voice input.

# Multi-Repo Work

- Use `--add-dir` (or `/add-dir`) to give Claude access to additional repositories.
- Add `"additionalDirectories"` to `settings.json` to always load extra folders on startup (this repo's `settings.json` already has `/tmp` here).
