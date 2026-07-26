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
2. **Require green checks.**
   ```bash
   gh pr checks <N>
   ```
   If any required check is failing or still pending → **stop the run** and report which check. Never merge a red or in-flight PR.
3. **Merge.** Build the command from the parsed flags — do not hardcode `--squash`/`--delete-branch`:
   - Method token: `--squash` (default), or `--merge` / `--rebase` when the user passed one.
   - Branch flag: include `--delete-branch` **unless** `--keep-branch` was passed; omit it when it was.
   ```bash
   gh pr merge <N> <--squash|--merge|--rebase> [--delete-branch]
   ```
   Example — default flags: `gh pr merge 31 --squash --delete-branch`. With `--rebase --keep-branch`: `gh pr merge 31 --rebase`.
4. **Sync `main` between PRs.** Dispatch to the `main` subcommand in `SKILL.md` to checkout `main`, pull, and prune the merged branch. This is the "sync main between" step. **Note:** the `main` dispatch prunes *every* local branch fully merged into `main`, not only the branches in this merge set — so an unrelated, already-merged local branch (even one you were sitting on before the run) can be cleaned up here. This is harmless (`git branch -d` refuses unmerged branches, so nothing with unmerged work is ever deleted), but do not assume the only branch removed is the one just merged.
5. **Bring the next PR up to date.** If more PRs remain, run `gh pr update-branch` on the next one — it is idempotent (a no-op when the branch is already current), so run it unconditionally rather than guessing whether branch protection requires it:
   ```bash
   gh pr update-branch <next-N>
   ```
   If the output reports the branch is already up to date, continue immediately. **If it updates the branch, its checks are now pending — stop the run and tell the user checks are re-running on `#<next-N>`; do not proceed until they re-invoke `/git merge` after checks pass.** (Do not poll or block waiting for CI.)

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
