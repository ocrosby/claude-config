# /git ship (Level 3 resource)

Read this file when `SKILL.md` step 1 dispatches to `ship`. Subsumes the prior `/git-ship` and `/git-cpr` skills.

## Flag parsing

Inspect the argument string for these flags before doing anything else:

- `--quick` — skip the **Pre-flight** block below; the workflow proceeds directly to the **Branch state** inspection.
- `-m` — direct-to-main mode. Mutually exclusive with `-p`.
- `-p` — direct-to-main patch mode (forces commit type to `fix`). Mutually exclusive with `-m`.

Remaining positional words after flags are the optional `<branch-name>` or `feature`/`hotfix` prefix override.

## Pre-flight

Unless `--quick` was passed, run lint and tests before touching git:

| Tool | Command |
|---|---|
| uv lockfile | `uv lock && git add uv.lock` (always, when `uv.lock` exists) |
| ruff | `ruff check . && ruff format --check .` |
| golangci-lint (single module) | `golangci-lint run ./...` |
| golangci-lint (Go workspace, `go.work` present) | iterate per-module — `task lint` if `Taskfile.yml` exists |
| stylua / luacheck | `stylua --check . && luacheck .` |
| Go tests (single module) | `go test ./...` |
| Go tests (workspace) | `find . -name go.mod -not -path "*/vendor/*" \| while read f; do (cd "$(dirname "$f")" && go test -race -count=1 ./...) \|\| exit 1; done` |
| Python tests | `pytest` |
| Node tests | `npm test` |
| Lua tests | `make test` or `busted` |

**If lint or tests fail: stop and do not proceed.** Never `--no-verify` or auto-fix lint without the user asking.

## Branch state

If `-m` or `-p`: skip to the Direct-to-Main block. Otherwise check `git branch --show-current`:

- On `main`/`master`: continue.
- On a feature branch: `git fetch origin`, then `git branch -r --merged origin/main | grep "origin/<current-branch>"`.
  - Merged or remote-deleted → stash, checkout main, pull, pop. Continue.
  - Unmerged or first push → keep current branch. Skip branch creation; staging and committing happen here.

Note: `/branch-from-main` performs this same merge-check internally via `/check-branch-merged`, so any caller that always branches from main gets the cleanup for free. The inline check above stays because ship needs to make a behavior decision the building block cannot — *commit on the current branch* vs. *start fresh* — and that decision must happen before grouping and stashing kick in.

## Identify conceptual groups

Run the shared grouping script:

```bash
python3 ~/.claude/scripts/git_group.py
```

Validate the JSON output against these override signals:

- Two groups share end-to-end intent (handler + model + test) → merge
- One group mixes intents → split
- A `*_test.go` group was separated from its implementation → merge

If multiple groups, present the proposed split and wait for explicit confirmation, then process each sequentially.

## Per group

1. **Derive the branch name.** Use the user's explicit name if given. Otherwise from `(type, scope)`: `feat` → `feature/`, `fix` → `hotfix/`, anything else → `feature/`. An explicit `feature`/`hotfix` argument overrides the inferred prefix.
2. **Create the branch.** Invoke `/branch-from-main <prefix>/<derived-name>`.
3. **Multi-group only — restore this group's files:**
   ```bash
   git checkout stash@{0} -- <file1> <file2> ...
   git status --short
   ```
4. **Isolation check (multi-group):** build/test just the affected module. Fail outside the group → declare `Depends on #N` in the PR body; fail inside → stop, fix, restart.
5. **Stage exactly this group's files.** Never `git add -A` across groups.
6. **Commit.** Invoke `/conventional-commit-msg`.
7. **Push and open the PR.** Invoke `/open-pr`. It pushes with `-u` and either creates the PR or updates the existing one. Print the URL.

After the last group: `git stash drop`.

## Direct-to-Main (`-m` / `-p`)

- `-m` and `-p` are mutually exclusive. If both are passed: stop and ask.
- Ensure on `main` (stash, checkout, pull, pop if needed).
- Stage relevant files.
- Invoke `/conventional-commit-msg`. **If `-p`**: override the commit type to `fix` regardless of what the diff suggests.
- Commit with the protect-main bypass:
  ```bash
  ALLOW_MAIN_COMMIT=1 git commit -m "..."
  ```
- Push:
  ```bash
  git push origin main
  ```
- Report the pushed commit hash. Do not open a PR.

## Verify

- **Branch mode:** PR URL is reachable and state is `OPEN`.
- **Direct-to-main:** `git log -1 origin/main --oneline` shows the new commit.
