---
description: "Detect whether the current branch has been merged into origin/main and, if so, reset to a freshly pulled main. Building block for /branch-from-main."
argument-hint: ""
user-invocable: false
---

# Check Branch Merged

Use this command before any flow that needs a clean `main` as its starting point. If the current branch is `main`/`master`, this is a no-op. If the current branch has been merged into `origin/main` (or its remote ref was deleted), stash any local changes, switch to `main`, pull, and pop the stash. Otherwise leave the working tree alone and report.

This command is local-only: it never pushes or deletes branches. The starting branch ref is preserved even when merged — pruning it is the caller's decision.

## Steps

1. Capture the starting branch with `git branch --show-current`. If it is `main` or `master`, print `"already on main"` and stop. If `main` does not exist locally but `master` does, treat `master` as the base for the remainder of these steps.
2. Fetch the remote so the merge check uses fresh refs:

   ```bash
   git fetch origin
   ```

   If the fetch fails (network, no remote), report the failure and stop. Do not proceed with stale remote knowledge.
3. Determine whether the starting branch is merged or its remote ref was deleted:

   ```bash
   git branch -r --merged origin/main | grep "origin/<starting-branch>"
   git ls-remote --heads origin "<starting-branch>"
   ```

   - If the first command matches → the branch is merged into `origin/main`.
   - If the second command produces no output → the remote ref was deleted (typical after a squash-merge with branch auto-cleanup).
   - If neither: print `"<starting-branch> still active on remote — no reset"` and stop. Do not touch the working tree.
4. Stash any local changes so the switch to `main` is clean:

   ```bash
   git status --porcelain
   # if non-empty:
   git stash push -u -m "check-branch-merged: <starting-branch>"
   ```

   Remember whether a stash was created. Step 6 only pops if one was.
5. Switch to `main` and pull:

   ```bash
   git checkout main
   git pull origin main
   ```

   If `git pull` fails (network, conflict, detached HEAD), stop and report. Do not force-update local `main`.
6. If step 4 created a stash, pop it onto `main`:

   ```bash
   git stash pop
   ```

   If `git stash pop` reports a conflict, stop and report. Do not auto-resolve.
7. Run `git status --short` and print `"reset from <starting-branch> to main"`. Exit.

## Rules

- Never delete the starting branch, even if merged. That is the caller's decision.
- Never `--force` or `git reset --hard` on `main`.
- Never invoke `gh`, `git push`, or any remote-mutating command. This is a local-only operation.
- Treat an unmerged-and-active-on-remote branch as a normal state — report and exit gracefully so callers can proceed on the existing branch. Do not raise an error.
- If `main` does not exist locally but `master` does, substitute `master` everywhere `main` appears above.
