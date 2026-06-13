---
description: Git workflow dispatcher — ship, sync, main, worktree, release-notes, cli. The first word of $ARGUMENTS selects the subcommand. Subcommands ship and worktree push to remote or mutate parallel checkouts; treat them as human-gated.
argument-hint: "<subcommand> [arguments]"
aliases: git-ship, git-cpr, git-sync, git-main, worktree, release-notes, ship, sync, main, commit-push-pr, gh-cli
allowed-tools: Bash(git *) Bash(gh *) Bash(uv lock) Read
# Human-gated: ship pushes commits, worktree mutates parallel checkouts. Block model auto-invocation; users invoke the slash command explicitly.
disable-model-invocation: true
---

# Git: Workflow Dispatcher

Use this skill for any git-graph or GitHub-CLI operation: shipping a branch (creating it from main or committing onto your existing branch), rebasing, switching to main, creating a parallel worktree, generating release notes, or looking up `gh` commands that the workflow subcommands do not already wrap.

The orchestration delegates to atomic building blocks: `/branch-from-main`, `/conventional-commit-msg`, `/open-pr`, and the shared scripts at `~/.claude/scripts/git_group.py` and `~/.claude/scripts/classify_commits.py`. This skill never re-implements their mechanics.

## Usage

```
/git                                  # show this help
/git ship                             # branch (or current) → commit → push → PR (multi-group aware)
/git ship <branch-name>               # use this name, infer prefix from commit type
/git ship feature <branch-name>       # force feature/ prefix
/git ship hotfix <branch-name>        # force hotfix/ prefix
/git ship -m                          # commit directly to main, no branch, no PR
/git ship -p                          # patch: commit directly to main with fix: prefix
/git ship --quick                     # skip pre-flight lint + tests (daily iteration)
/git sync [<base>]                    # rebase current branch onto main (or <base>)
/git main                             # checkout main, pull, prune merged branches
/git worktree [<name>]                # create parallel worktree under .claude/worktrees/
/git release-notes [<range>]          # generate changelog (default: since last tag)
/git cli                              # GitHub CLI quick reference (gh api, runs, reviews, issues)
```

`/git ship` subsumes the previous `/git cpr` subcommand. If you are already on a feature branch with a prior push, the branch is kept; only pre-flight, commit, push, and PR run. The `--quick` flag skips pre-flight for the same daily-iteration use case.

## Workflow

### 1. Parse the subcommand

Split `$ARGUMENTS` on the first space. The first word is the subcommand; everything after is its argument string.

- If the subcommand is empty or `help`: print the **Usage** block above and stop.
- If the subcommand is `cpr`: print `/git cpr was merged into /git ship — for the daily-iteration ergonomics use /git ship --quick`, then dispatch to `ship` with `--quick` prepended to the remaining argument string. If `--quick` is already present in the remaining argument string, do not prepend a duplicate — treat the argument string as-is.
- If the subcommand is not one of `ship`, `sync`, `main`, `worktree`, `release-notes`, `cli`: stop and print the **Usage** block.
- Dispatch to the matching step.

### 2. Dispatch — `ship`

Subsumes the prior `/git-ship` and `/git-cpr` skills.

**Flag parsing.** Inspect the argument string for these flags before doing anything else:

- `--quick` — skip the **Pre-flight** block below; the workflow proceeds directly to the **Branch state** inspection.
- `-m` — direct-to-main mode. Mutually exclusive with `-p`.
- `-p` — direct-to-main patch mode (forces commit type to `fix`). Mutually exclusive with `-m`.

Remaining positional words after flags are the optional `<branch-name>` or `feature`/`hotfix` prefix override.

**Pre-flight.** Unless `--quick` was passed, run lint and tests before touching git:

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

**Branch state.** If `-m` or `-p`: skip to the Direct-to-Main block. Otherwise check `git branch --show-current`:

- On `main`/`master`: continue.
- On a feature branch: `git fetch origin`, then `git branch -r --merged origin/main | grep "origin/<current-branch>"`.
  - Merged or remote-deleted → stash, checkout main, pull, pop. Continue.
  - Unmerged or first push → keep current branch. Skip branch creation; staging and committing happen here.

Note: `/branch-from-main` now performs this same merge-check internally via `/check-branch-merged`, so any caller that always branches from main gets the cleanup for free. The inline check above stays because ship needs to make a behavior decision the building block cannot — *commit on the current branch* vs. *start fresh* — and that decision must happen before grouping and stashing kick in.

**Identify conceptual groups.** Run the shared grouping script:

```bash
python3 ~/.claude/scripts/git_group.py
```

Validate the JSON output against these override signals:

- Two groups share end-to-end intent (handler + model + test) → merge
- One group mixes intents → split
- A `*_test.go` group was separated from its implementation → merge

If multiple groups, present the proposed split and wait for explicit confirmation, then process each sequentially.

**Per group:**

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

**Direct-to-Main (`-m` / `-p`).**

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

**Verify.** Branch mode: PR URL is reachable and state is `OPEN`. Direct-to-main: `git log -1 origin/main --oneline` shows the new commit.

### 3. Dispatch — `sync`

Replicates the prior `/git-sync` skill. Rebases the current branch onto main without merging.

1. **Check state.** `git status` and `git branch --show-current`.
   - **If on `main`/`master`: stop and tell the user to use `/git main` instead.**
   - **If already up to date with `origin/main`: stop — do not create an empty rebase.**

2. **Stash uncommitted changes** if any: `git stash push -m "sync: stash before rebase"`.

3. **Fetch and rebase.**
   ```bash
   git fetch origin
   git rebase origin/main
   ```
   If a `<base>` argument was given, rebase onto that instead. Never `git merge` — always rebase.

4. **Handle conflicts.** Report conflicting files and hunks. Explain what each side changed. **Do not auto-resolve** — present options and wait. After resolution, `git rebase --continue`. On abort: `git rebase --abort`.

5. **Pop the stash if one was created in step 2 — always, even if rebase failed or was aborted.** Conflicts during pop are reported the same way as step 4 conflicts.

6. **Report.** Current branch, commits rebased, stash state, the new base commit.

7. **Run tests if commits were actually applied.** Detect from cwd: `go test ./...` for Go, `pytest` for Python, `make test` if a `Makefile` defines a `test` target. **If no test command matches: stop and ask which command to run.** Report results before exiting.

**Rules for `sync`.** Never force-push unless the user asks (`--force-with-lease` is safer). If `main` does not exist but `master` does, use `master`.

### 4. Dispatch — `main`

Replicates the prior `/git-main` skill. Switch to main and sync.

1. **Check for uncommitted changes.** Run `git status --porcelain`. **If any uncommitted changes are present: stop and ask the user to choose — stash, commit, or abort. Do not switch branches until the choice is made.**
2. `git checkout main` (or `master` if no `main`).
3. `git pull origin main`.
4. If `uv.lock` exists: `uv lock`. Report if it changed; leave it unstaged.
5. **Prune merged local branches in two passes:**
   - **Pass 1 — fast-forward merges:**
     ```bash
     git branch --merged main | grep -v '^\*\|main\|master' | xargs -r git branch -d
     ```
   - **Pass 2 — squash/rebase merges:** for any branch `-d` skipped, run `gh pr list --state merged --head <branch>`. If a merged PR exists, force-delete with `git branch -D`. Otherwise leave the branch and report it.
6. **Report.** Current branch, the pull output, and any deleted branches.

**Rules for `main`.** If `main` doesn't exist but `master` does, use `master`. Omit "no deleted branches" from the report.

### 5. Dispatch — `worktree`

Replicates the prior `/worktree` skill. Create a parallel checkout.

1. **Name.** Use the user's argument or generate `YYYY-MM-DD-descriptor`.
2. **Create:**
   ```bash
   git worktree add .claude/worktrees/$name origin/main
   ```
   On failure (path exists, `origin/main` not fetched), report verbatim and stop. Never force or delete an existing worktree.
3. **Print launch command:**
   ```bash
   cd .claude/worktrees/$name && claude
   ```
4. **Verify** with `git worktree list`. **If the new path is absent: stop and report.**
5. **Print follow-ups:** launch, alternative (`claude -w`), list (`git worktree list`), remove (`git worktree remove .claude/worktrees/$name`).

### 6. Dispatch — `release-notes`

Replicates the prior `/release-notes` skill. Argument is an optional commit range.

1. **Determine the range.**
   - If `$ARGUMENTS` after `release-notes` specifies a range (e.g. `v1.2.0..HEAD`), use it.
   - Else if a last tag exists: `<last-tag>..HEAD`.
   - Else: full history from initial commit — `"$(git rev-list --max-parents=0 HEAD)"..HEAD`.

2. **Run the classifier:**
   ```bash
   python3 ~/.claude/scripts/classify_commits.py <base>..HEAD [--format json|markdown] [--include-chores]
   ```
   The script parses conventional-commit types, detects breaking-change markers, maps types to categories (`feat` → Added or Changed, `fix` → Fixed, `security` → Security, `revert` → Changed), and excludes `refactor`/`perf`/`style`/`test`/`build`/`ci`/`chore` by default.

3. **Refine the Markdown draft.**
   - **Added vs Changed:** move feature entries that modify existing behavior to Changed.
   - **Breaking changes:** expand each one-line subject into a short paragraph naming user-visible impact and migration step.
   - **Drop noise** that is irrelevant for a user-facing changelog.
   - **Security entries:** summarize without leaking CVE-style detail.

4. **Write final notes** in this format:
   ```
   ## [version or date]

   ### Breaking Changes
   - <paragraph per breaking change>

   ### Added
   - <user-visible description>

   ### Fixed
   - <user-visible description>
   ```

5. **Verify.** Every flagged Breaking Change appears; no commit hashes in the final notes; entries grouped under expected headings. **If a section the script populated is missing: stop and explain which commits were dropped and why.**

### 7. Dispatch — `cli`

Reference subcommand. Surfaces a `gh` quick-reference for operations that the workflow subcommands above do not already wrap (CI debugging, PR reviews with inline comments, issue triage, GraphQL queries, `gh api` calls).

Read `~/.claude/skills/git/cli.md` and apply what the user is asking for from its sections:

- Discovery patterns (`--json`, `--limit`, `--web`)
- CI/CD debugging (`gh run list`, `gh run view --log-failed`, `gh run rerun --failed`)
- Reviewing a PR with line-level comments via `gh api repos/{owner}/{repo}/pulls/N/reviews`
- Issue triage (`gh issue list`, `gh issue create`, `gh issue comment`)
- JSON output + jq filtering
- API access (REST and GraphQL)
- Finding your work (`gh pr list --author @me`, `--search "review-requested:@me"`)
- Environment variables and aliases

**This subcommand is read/lookup oriented — do not push, comment, approve, or otherwise mutate remote state without the user explicitly asking for that action.** For routine PR creation use `/open-pr`; for branch → commit → push → PR use `/git ship`; for review with agent feedback use `/code review`.

### 8. Final verification step

For every subcommand, the dispatch block above ends with its own verification gate. Before this skill exits, confirm the gate fired (PR URL reachable, branch pruned report emitted, worktree listed, the requested `gh` command surfaced from the reference, etc.) — if any verification was skipped, re-run it.

## Rules (apply across all subcommands)

- Never `--force` push; never `--no-verify`; never amend a pushed commit.
- Never commit to `main`/`master` except via `ship -m` / `ship -p`.
- If the working tree is unexpectedly clean for `ship`: stop.
- Multi-group flows always branch each group from the latest `main`.
- Always assign PRs to `@me` (handled by `/open-pr`).
