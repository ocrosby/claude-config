# /git merge (Level 3 resource)

Read this file when `SKILL.md` step 1 dispatches to `merge`. Merges a set of open PRs **in the order given**, refreshing local `main` between each so every PR merges against the latest base.

This is a single operation with one job: land a queue of PRs sequentially. It does not review, rebase-for-cleanliness, or trigger follow-on builds — for review-then-merge use `/git reviewer` first; for the "wait for a release, then bump and un-skip" playbook use the dedicated orchestration, not this subcommand.

**Merging is a remote mutation — only ever run this on explicit `/git merge` invocation, and only merge PRs that are green and conflict-free.**

## Flag and argument parsing

Inspect the argument string first:

- `--all` — target every open PR authored by `@me` in the current repo, in ascending PR-number order. Mutually exclusive with an explicit number list. **If both `--all` and one or more bare integers are present: stop and ask which the user meant.**
- Bare integers (`30 31 32`) — the exact PRs to merge, **in the order written**. Order matters; never reorder them.
- `--keep-branch` — keep the remote head branch. Default is to delete it after a successful merge.
- `--merge` / `--rebase` — merge method. Default is `--squash`. `--merge`, `--rebase`, and `--squash` are mutually exclusive; **if more than one is present: stop and ask.**

## Resolve the PR list

- `--all`:
  ```bash
  gh pr list --author @me --state open --json number,title,headRefName --jq 'sort_by(.number)[]'
  ```
  If none, print `No open PRs authored by you — nothing to merge.` and stop. `headRefName` is fetched so the confirmation step can name the branches that deletion will remove.
- Explicit numbers: use them verbatim in the given order.

## Confirm before mutating

Print the ordered list as `#<N> <title> (<headRefName>)` and the resolved options (method, and — when deletion is on — the exact branches that will be removed). For `--all`, or any list of more than one PR, **wait for explicit confirmation** before merging anything — the order and set are the user's decision.

## Per PR, in order

1. **Inspect state.**
   ```bash
   gh pr view <N> --json number,title,state,isDraft,mergeable,mergeStateStatus,headRefName
   ```
   - `state != OPEN` → skip with a note (already merged/closed); continue to the next PR.
   - `isDraft: true` → **stop the run** and report; do not merge a draft.
   - `mergeable == CONFLICTING` → **stop the run**, name the conflict, and do not force. The user resolves conflicts (via `/git sync` on that branch) before re-running.
   - `mergeStateStatus == BLOCKED` (required reviews outstanding, an unmet branch-protection rule, etc.) → **stop the run** and report the blocking reason. Do not attempt the merge — `gh pr merge` will fail. This is a distinct fourth stop condition, not a conflict or a red check.
   - `mergeStateStatus == BEHIND` or `UNSTABLE` is NOT a stop condition here — step 3 handles both via the try-auto-then-poll flow.
2. **Require green checks.** Skip this pre-check when `mergeStateStatus == BEHIND` — the branch is going to be rebased in step 3, which invalidates the current check run anyway. For every other state:
   ```bash
   gh pr checks <N>
   ```
   If any required check is failing (not pending) → **stop the run** and report which check. Never merge a red PR. Pending checks are fine — step 3's fallback will bounded-poll them.
3. **Merge — try `--auto` first, fall back to bounded polling.** Server-side auto-merge handles rebase + CI wait + merge without blocking the caller, so a single `/git merge` invocation lands the PR (or queues it) even when the branch is BEHIND or checks are pending. When the repo has `allow_auto_merge` disabled, fall back to a bounded-poll flow so the invocation still completes without a stop.

   Build the flag list from parsed args:
   - Method token: `--squash` (default), or `--merge` / `--rebase` when the user passed one.
   - Branch flag: include `--delete-branch` **unless** `--keep-branch` was passed.

   Flow:
   ```bash
   # 3a. First try server-side auto-merge. Succeeds if repo has
   # allow_auto_merge=true; PR is either merged immediately (if fully green)
   # or queued for GitHub to merge when checks pass + branch is up to date.
   if gh pr merge <N> <method> [--delete-branch] --auto 2>/tmp/merge_err; then
     # Poll for state == MERGED so the invocation blocks until the merge
     # actually lands, giving in-session confirmation and letting step 4
     # sync main unconditionally. Cap at 5 minutes -- typical merges land
     # in under a minute once queued, so this cap only fires when CI
     # itself is genuinely slow or stuck. Bounded with bash's builtin
     # SECONDS counter, not the external `timeout` binary -- `timeout` /
     # `gtimeout` is absent by default on macOS without coreutils installed,
     # and this flow must not depend on an optional package.
     SECONDS=0
     until [ "$(gh pr view <N> --json state --jq .state)" = "MERGED" ]; do
       if [ "$SECONDS" -ge 300 ]; then
         echo "PR #<N> did not reach MERGED within 5 minutes"
         exit 1
       fi
       sleep 15
     done
   elif grep -q "Auto merge is not allowed" /tmp/merge_err; then
     # 3b. Fallback: repo has auto-merge disabled. Update the branch if
     # needed, wait for CI, then merge directly.
     gh pr update-branch <N>
     # Bounded poll: check every 15s, cap at 3 minutes via SECONDS -- same
     # portability reason as 3a, no external `timeout` dependency.
     SECONDS=0
     until gh pr checks <N> --json state --jq '
         if length == 0 then true
         else [.[].state] | all(. == "SUCCESS" or . == "NEUTRAL" or . == "SKIPPED")
         end' | grep -qx true; do
       if [ "$SECONDS" -ge 180 ]; then
         echo "checks did not go green within 3 minutes on #<N>"
         exit 1
       fi
       sleep 15
     done
     gh pr merge <N> <method> [--delete-branch]
   else
     # Other failure (conflict surfaced, blocked ruleset, etc.) — propagate.
     cat /tmp/merge_err
     exit 1
   fi
   ```

   Rationale: the previous flow always required at least two `/git merge` invocations per BEHIND-or-pending PR (one to update-branch and stop, one to actually merge). `--auto` collapses that to one invocation server-side; the bounded-poll fallback preserves the same UX for repos without auto-merge enabled. Both paths now block until the merge actually lands (5-min cap on the `--auto` path, 3-min cap on the fallback), so the caller has in-session confirmation and step 4 can sync main unconditionally. The bound is implemented with bash's builtin `SECONDS` variable rather than the external `timeout`/`gtimeout` binary: a live run on macOS without GNU coreutils hit `command not found: timeout` mid-merge, so the flow must not assume that binary exists.

4. **Sync `main` between PRs.** Dispatch to the `main` subcommand in `SKILL.md` to checkout `main`, pull, and prune the merged branch. Both step 3 paths guarantee the PR is MERGED (not just queued) before we reach this step, so `git pull` picks up the squash commit and `git branch -d` succeeds on the local topic branch.

   **Note:** the `main` dispatch prunes *every* local branch fully merged into `main`, not only the branches in this merge set — so an unrelated, already-merged local branch (even one you were sitting on before the run) can be cleaned up here. This is harmless (`git branch -d` refuses unmerged branches, so nothing with unmerged work is ever deleted), but do not assume the only branch removed is the one just merged.

5. **Bring the next PR up to date.** No longer needed — step 3 handles the up-to-date requirement inline for each PR via `--auto` (server-side) or the bounded-poll fallback. Removed to eliminate the "stop and wait for the user to re-invoke" cycle that used to fire once per PR in a batch.

## Stop semantics

On the first draft / conflict / BLOCKED / red-check PR, stop the whole run — do not skip ahead to later PRs, because a queue is usually ordered for a reason (a later PR may depend on an earlier one). Report exactly which PRs merged and which remain untouched.

## Verify

For each PR that was merged:
```bash
gh pr view <N> --json state --jq .state    # expect MERGED
```

Confirm local `main` is at the latest (`git log -1 origin/main --oneline`). Print a summary table:

| PR | Title | Result | Branch |
|----|-------|--------|--------|

with Result one of `merged` / `skipped (not open)` / `stopped (<reason>)` and Branch `deleted` / `kept`.

## Rules

Never merge a PR with failing/pending checks or a conflict. Never force. Never reorder the requested PR list. Confirm the set and order before merging when more than one PR is targeted. Only merge PRs in the current repo; for `--all`, only PRs authored by `@me`.
