---
description: "Create a new branch from a freshly pulled main. Building block for /git ship, /git sync, /git worktree."
argument-hint: "<branch-name>"
user-invocable: false
---

# Branch From Main

Use this command to create a clean feature or hotfix branch starting from the latest `main`. Stashes any uncommitted work first, restores it on the new branch, and never bases the new branch on a stale local `main`.

**If `$ARGUMENTS` is empty: stop and tell the caller to pass a branch name.**

## Steps

1. **Pre-flight: invoke `/check-branch-merged`.** If the starting branch was merged into `origin/main` or its remote ref was deleted, the working tree is now on a freshly pulled `main` and any stash the check created has already been popped. If the starting branch is unmerged and still active on the remote, the working tree is unchanged. Either way, proceed.
2. Run `git branch --show-current` to capture the starting branch.
3. Run `git status --porcelain`. If non-empty, stash with a labeled message:

   ```bash
   git stash push -u -m "branch-from-main: $ARGUMENTS"
   ```

   Remember whether a stash was created — the final step pops it.
4. Update local `main` from the remote:

   ```bash
   git fetch origin
   git checkout main
   git pull origin main
   ```

   If the `git pull` fails (network, conflict, detached HEAD), report the failure and stop. Do not force-update local `main`. When step 1 already reset to `main`, these calls are idempotent.
5. Create and check out the new branch:

   ```bash
   git checkout -b "$ARGUMENTS"
   ```

   If `$ARGUMENTS` already exists as a local branch, stop and tell the caller to choose a different name. Do not delete the existing branch.
6. If step 3 created a stash, pop it onto the new branch:

   ```bash
   git stash pop
   ```

   If `git stash pop` reports a conflict, stop and report it. Do not auto-resolve.
7. Run `git status --short` and confirm the new branch is the current branch and any stashed work is restored. Print the new branch name.

## Rules

- Never branch from a stale local `main` — always `git fetch origin` and `git pull` first.
- Never `--force` or `git reset --hard` on `main`.
- Never delete the starting branch, even if the caller is rebranching from a merged feature branch — that's the caller's decision.
- Never invoke `gh`, `git push`, or any remote-mutating command. This is a local-only operation.
