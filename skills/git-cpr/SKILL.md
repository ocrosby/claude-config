---
description: Commits and ships current changes. Single group → commit, push, and open a PR on the current feature branch. Multi-group → split into separate branches/PRs from main, one PR per conceptual group.
aliases: commit-push-pr
# Human gate: this skill pushes to remote and opens PRs — external, hard-to-reverse side effects.
disable-model-invocation: true
allowed-tools: Bash(git add *) Bash(git commit *) Bash(git push *) Bash(git status *) Bash(git diff *) Bash(git log *) Bash(git branch *) Bash(git fetch *) Bash(git pull *) Bash(git checkout *) Bash(git stash *) Bash(git restore *) Bash(gh pr view *) Bash(gh pr create *)
---

# Commit → Push → PR

Use this skill for daily shipping. When the diff is one conceptual change, it commits on the current branch and opens a PR. When the diff spans multiple groups, it creates a fresh branch per group from `main` and opens one PR per group.

For direct-to-main commits or to trigger a patch release, use `/git-ship -m` or `/git-ship -p`.

The skill orchestrates the atomic building blocks `/branch-from-main`, `/conventional-commit-msg`, and `/open-pr`, plus the shared grouping script. It does not re-implement their mechanics.

## Usage

```
/git-cpr
```

No arguments. Branches, messages, and PR bodies are derived from the working tree.

## When NOT to use

- A direct-to-`main` commit is needed → use `/git-ship -m` or `/git-ship -p`
- A force-push or `--no-verify` commit is needed → refused

## Workflow

### 1. Inspect state

```bash
git branch --show-current
git status --short
```

**If the working tree is clean: stop and do not proceed.**

### 2. Identify conceptual groups

Run the shared grouping script:

```bash
python3 ~/.claude/scripts/git_group.py
```

The script emits JSON: `{branch, is_main, groups: [{type, scope, files, suggested_branch}]}`. Validate against these override signals:

- Two suggested groups represent the same intent end-to-end → merge
- One suggested group mixes intents → split
- A `*_test.go` group was separated from its implementation counterpart → consider merging

If the validated grouping is exactly one group, go to step 3. If multiple groups, go to step 4.

### 3. Single-group flow

**If on `main`/`master`: stop. Recommend `/git-ship` instead.**

1. Stage exactly this group's files (never `git add -A`).
2. Invoke `/conventional-commit-msg` to commit on the current branch.
3. Invoke `/open-pr` to push and open (or update) the PR.
4. Print the PR URL.

### 4. Multi-group flow

Present the proposed split to the user and wait for explicit confirmation. Format:

```
Found N conceptual groups in the working tree. Proposed PRs:

  1. feat(auth): add OAuth2 token refresh  →  feature/add-oauth2-token-refresh
     Files: internal/auth/token.go, internal/auth/token_test.go

  2. fix(api): correct 404 on missing resource  →  hotfix/fix-404-on-missing-resource
     Files: internal/api/handler.go

Proceed with all N, or adjust the grouping?
```

Once confirmed, stash everything once so per-group branches start clean:

```bash
git stash push -u -m "git-cpr: split into PRs"
```

Then for each group in sequence:

1. Invoke `/branch-from-main <suggested-branch>` to create a clean branch from latest `main`.
2. Restore only this group's files from the stash:

   ```bash
   git checkout stash@{0} -- <file1> <file2> ...
   git status --short   # confirm only this group's files are modified
   ```

3. Stage exactly this group's files. In multi-group mode, never stage files from another group.
4. Invoke `/conventional-commit-msg`. If a pre-commit hook fails, fix the underlying issue and re-commit — never `--no-verify` or amend.
5. Invoke `/open-pr`. If a dependency on another group was detected during build/staging, pass a `Depends on #N` note when prompted.
6. Print the PR URL on its own line before starting the next group.

After the last group:

```bash
git stash drop
```

### 5. Verify

Confirm the change reached the remote and the PR is reachable. In multi-group mode, emit a consolidated list of every PR URL.

## Rules

- Never commit to `main`/`master` directly — refuse (recommend `/git-ship -m`).
- Never `--no-verify`, never `--force`, never amend a pushed commit.
- Single-group flow requires being on a feature branch; on `main`/`master` it refuses.
- Multi-group flow branches each group from the **latest** `main` via `/branch-from-main` — never from another group's branch.
- Multi-group flow never stages files from a different group in the same commit.
- Always assign every PR to `@me`.
- If a PR already exists for a branch, `/open-pr` updates it via push — never opens a duplicate.
