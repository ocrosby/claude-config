---
description: Creates a feature or hotfix branch, commits staged changes, pushes to remote, and opens a detailed PR against main. Supports -m to commit directly to main, or -p to commit a patch fix directly to main.
aliases: ship
---

# Ship: Branch → Commit → Push → PR

Use this skill when the user wants to ship work on a new branch and open a pull request. The skill orchestrates the atomic building blocks `/branch-from-main`, `/conventional-commit-msg`, and `/open-pr`, plus the shared grouping script. It does not re-implement their mechanics.

## Usage

```
/git-ship                          # infer everything from the diff and proceed automatically
/git-ship <branch-name>            # use this name, infer prefix from commit type
/git-ship feature <branch-name>    # force feature/ prefix
/git-ship hotfix <branch-name>     # force hotfix/ prefix
/git-ship -m                       # commit and push directly to main — no branch, no PR
/git-ship -p                       # patch release: commit directly to main, force fix: commit type
```

**`-m`**: skips branch creation and PR. Commits directly to `main` and pushes. Use for trivial changes (docs, config, typos).
**`-p`**: identical to `-m` but the commit message must use `fix:` to trigger a patch release.
**`-m` and `-p` are mutually exclusive.** If both passed: stop and ask which one.

## Workflow

### 1. Pre-flight: Lint and Tests

Run lint and the test suite before touching git. Detect what's available:

| Tool | Command |
|---|---|
| uv lockfile | If `uv.lock` exists: `uv lock && git add uv.lock` (always, even if no changes) |
| ruff | `ruff check . && ruff format --check .` |
| golangci-lint (single module) | `golangci-lint run ./...` |
| golangci-lint (Go workspace, `go.work` present) | iterate per-module — `task lint` if `Taskfile.yml` exists |
| stylua / luacheck | `stylua --check . && luacheck .` |
| Go tests (single module) | `go test ./...` |
| Go tests (workspace) | `find . -name go.mod -not -path "*/vendor/*" \| while read f; do (cd "$(dirname "$f")" && go test -race -count=1 ./...) \|\| exit 1; done` |
| Python tests | `pytest` |
| Node tests | `npm test` |
| Lua tests | `make test` or `busted` |

**If lint or tests fail: stop, report the failure, do not proceed.** Never `--no-verify` or attempt to auto-fix lint errors unless the user asks.

### 2. Branch state

If `-m` or `-p`: skip to step 7 (Direct-to-Main).

Otherwise, check the current branch:

```bash
git branch --show-current
```

- If on `main`/`master`: proceed to step 3.
- If on a feature branch: run `git fetch origin`, then check whether the branch is merged into `main`:

  ```bash
  git branch -r --merged origin/main | grep "origin/<current-branch>"
  ```

  - **Merged or remote-deleted:** the branch is stale. `git stash`, checkout main, pull, pop. Continue to step 3.
  - **Unmerged or first push:** keep the current branch. Skip step 5; staging and committing happen on the existing branch. After step 6's commit, push via `/open-pr` (which handles "PR already exists" idempotently).

### 3. Identify conceptual groups

Run the shared grouping script:

```bash
python3 ~/.claude/scripts/git_group.py
```

The script emits JSON: `{branch, is_main, groups: [{type, scope, files, suggested_branch}]}`. Validate against these override signals:

- Two suggested groups share end-to-end intent (handler + model + test for one feature) → merge
- One suggested group mixes intents (new CLI flag + unrelated bug fix) → split
- A `*_test.go` group was separated from its implementation counterpart → consider merging

If the validated grouping is a single group, continue to step 4 with one group. If multiple groups, present the proposed split to the user and wait for explicit confirmation. Then process each group sequentially through steps 4–6.

### 4. Derive the branch name

If the user passed `<branch-name>` explicitly, use it. Otherwise derive from the group's `(type, scope)`:

| Group type | Branch prefix |
|---|---|
| `feat` | `feature/` |
| `fix` | `hotfix/` |
| anything else | `feature/` |

An explicit `feature` or `hotfix` argument overrides the inferred prefix.

### 5. Create the branch

Invoke `/branch-from-main <prefix>/<derived-name>`. This stashes uncommitted work, fetches origin, pulls main, creates the branch, and pops the stash onto it.

**In multi-group mode**, after `/branch-from-main` creates the branch, restore only this group's files from the stash:

```bash
git checkout stash@{0} -- <file1> <file2> ...
git status --short   # confirm only this group's files are modified
```

### 6. Stage and commit

Stage exactly this group's files (never `git add -A` across groups). In multi-group mode: also run an isolation check before staging:

- Go workspace: `cd <module-dir> && go build ./...` and `go test -race -count=1 ./...` for each module the group touches
- Other languages: equivalent build/type-check step
- If the build fails for files **outside** this group: declare the dependency in the PR body (`Depends on #N`) and continue
- If the build fails for files **inside** this group: stop, fix, restart

Once staged, invoke `/conventional-commit-msg` to produce the message and commit.

### 7. Push and open the PR

Invoke `/open-pr`. It pushes with `-u`, detects whether a PR already exists, and either opens a new one or updates the existing one. It returns the PR URL.

In multi-group mode, print the URL between groups and emit a consolidated list after the last group. After the last group:

```bash
git stash drop
```

### 8. Direct-to-Main (`-m` / `-p` only)

If `-m` or `-p` was passed:

1. Ensure on `main`:

   ```bash
   git branch --show-current
   ```

   If not on `main`: `git stash`, `git checkout main && git pull origin main`, `git stash pop`.

2. Stage relevant files.

3. Invoke `/conventional-commit-msg`. **If `-p`**: override the type to `fix` regardless of what the diff suggests (this triggers the patch release).

   The commit must be prefixed with `ALLOW_MAIN_COMMIT=1` to bypass the protect-main hook:

   ```bash
   ALLOW_MAIN_COMMIT=1 git commit -m "..."
   ```

   (Adjust the `/conventional-commit-msg` invocation to use this env var when committing on main.)

4. Push directly:

   ```bash
   git push origin main
   ```

   Do not open a PR. Report the pushed commit hash.

### 9. Verify

Confirm the change reached its destination:
- Branch mode: PR URL from `/open-pr` is reachable and state is `OPEN`
- Direct-to-main mode: `git log -1 origin/main --oneline` shows the new commit

## Rules

- Never `--force`, never `--no-verify`, never amend a pushed commit.
- Without `-m`/`-p`: never commit to `main`/`master`. With `-m`: commit directly to main, no branch, no PR. With `-p`: same as `-m` but force `fix:` type.
- If the working tree is clean: stop and tell the user there is nothing to ship.
- In multi-group mode: every group's branch comes from the latest `main` — never base one group on another's branch. Never stage files from a different group in the same commit.
- `-m` / `-p` always ship as a single commit regardless of how many groups exist — multi-PR grouping does not apply.
