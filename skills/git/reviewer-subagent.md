# `/git reviewer` — sub-agent contract

The `reviewer` subcommand of `/git` dispatches one sub-agent per open PR, in parallel, each in its own isolated `git worktree`. This file defines the exact prompt each sub-agent receives and the exact JSON shape it must return. The orchestrator (Section 8 of `skills/git/SKILL.md`) substitutes the placeholders below and passes the result as the `prompt` argument to `Agent()`.

Do not paraphrase this contract inside `SKILL.md` — the skill names this file and trusts it.

## Placeholders

The orchestrator must substitute every placeholder before dispatching. Missing substitutions are a defect — sub-agents receive the literal `<...>` token and will fail to parse it.

| Placeholder | Value |
|---|---|
| `<N>` | PR number |
| `<owner>/<repo>` | resolved once by orchestrator via `gh repo view --json owner,name` |
| `<worktree_path>` | absolute path, `.claude/worktrees/pr-<N>-<run_id>` |
| `<headRefName>` | PR head branch |
| `<run_id>` | 8-char suffix unique per invocation |
| `<original_cwd>` | absolute path the user started `/git reviewer` from |
| `<failed_checks_block>` | pre-classified failed checks (format below) |
| `<review_comments_block>` | unresolved review comments (format below) |

## Prompt template

```
You are handling PR #<N> for <owner>/<repo>.

Working directory: <worktree_path>
Head branch: <headRefName>
Run ID: <run_id>

Your first action: `cd "<worktree_path>"`. If this fails, return outcome
"failed" with error "worktree missing" and stop — do not touch any other
directory. Do NOT `cd` anywhere else during the run. For any command that
must run in the main repo (worktree cleanup), use `git -C "<original_cwd>"`.

## Work to do (pre-collected by the orchestrator; do NOT re-fetch)

Failed checks:
<failed_checks_block>

Unresolved review comments:
<review_comments_block>

## Rules

- Only push to <headRefName>. Never touch main. Never force-push.
  Never `--no-verify`. Never amend a pushed commit.
- Per failed check:
  - **auto-fixable** → apply the formatter/linter fix locally.
  - **bug**          → fix the underlying code or test.
  - **flaky**        → rerun once with `gh run rerun --failed <run-id>`;
                       if it fails again on the same step, reclassify as
                       ambiguous.
  - **ambiguous**    → do not guess; record under `needs_input`.
- Per review comment: implement it — including nits (naming, wording,
  formatting). For ambiguous, subjective, or behavior-changing comments,
  do not guess — record under `needs_input`.
- Run repo lint/tests (per the ship pre-flight table in
  `skills/git/SKILL.md`) before every push. If they fail, fix or stop —
  never `--no-verify`.
- Commit format:
  - `fix(ci): resolve <check>`   for check fixes
  - `fix(review): address <area>` for review-comment fixes
- After the last push, wait for CI to finish:
  `gh pr checks <N> --watch --interval 60 --required`
  with a **25-minute wall-clock cap**.
  - Green → `outcome: "addressed"` (or `"clean"` if you made no changes).
  - Red *again* after your fixes → make **exactly one** further iteration
    on the newly-failing check. If still red after that, `outcome:
    "needs_input"` with `kind: "post_fix_still_red"` and the failing-step
    excerpt.
  - Timeout → `outcome: "needs_input"`, `kind: "ci_timeout"`,
    `final_check_status: "timeout"`.
- Reply to each addressed review thread: `Addressed in <sha>.`
  Never resolve a thread you did not address.
- Before returning: run `git status --porcelain` — it must be empty.
  If it is not, either commit tracked changes or delete untracked
  artifacts (coverage files, generated docs) — do not leak them into
  the worktree removal step.
- Cleanup — always run, even if outcome is `"failed"` or `"needs_input"`:
  `git -C "<original_cwd>" worktree remove "<worktree_path>"`
  If that fails (uncommitted work, permission error), try once with
  `--force`. Report the outcome in `cleanup_status`.

## Return exactly this JSON and nothing else — no prose wrapper, no code fence

{
  "pr": <N>,
  "worktree_path": "<worktree_path>",
  "head_branch": "<headRefName>",
  "outcome":            "clean" | "addressed" | "needs_input" | "failed",
  "checks_fixed":       [{"check": "<name>", "commit": "<sha>"}],
  "comments_addressed": [{"path": "<file>", "line": <n>, "reviewer": "<login>", "commit": "<sha>"}],
  "pushed_commits":     ["<sha>", "..."],
  "needs_input":        [{"kind": "ambiguous_check" | "ambiguous_review" | "post_fix_still_red" | "ci_timeout", "excerpt": "..."}],
  "final_check_status": "green" | "red" | "pending" | "timeout" | "n/a",
  "cleanup_status":     "removed" | "leaked" | "failed",
  "error":              null
}
```

Malformed, missing, or non-JSON output is treated by the orchestrator as `outcome: "failed"` with the raw text captured under `needs_input`.

## `<failed_checks_block>` format

One entry per failed check, blank line between. If empty, substitute the literal string `(none)`.

```
- <check name> [<classification: auto-fixable | bug | flaky | ambiguous>]
  Failing step: <name>
  Excerpt: <first ~20 lines of the failing log>
```

## `<review_comments_block>` format

One entry per unresolved comment. If empty, substitute the literal string `(none)`.

```
- <path>:<line> — <reviewer_login>: <comment body>
```
