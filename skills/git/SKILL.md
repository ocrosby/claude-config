---
description: Git workflow dispatcher — ship, sync, main, merge, worktree, release-notes, cli, reviewer. The first word of $ARGUMENTS selects the subcommand. Subcommands ship, merge, worktree, and reviewer mutate remote state (push commits, merge PRs, edit PR branches) or parallel checkouts; treat them as human-gated.
argument-hint: "<subcommand> [arguments]"
aliases: git-ship, git-cpr, git-sync, git-main, worktree, release-notes, ship, sync, main, commit-push-pr, gh-cli, reviewer, pr-reviewer
allowed-tools: Bash(git *) Bash(gh *) Bash(uv lock) Read Edit Write
# Human-gated: ship pushes commits, worktree mutates parallel checkouts. Block model auto-invocation; users invoke the slash command explicitly.
disable-model-invocation: true
---

# Git: Workflow Dispatcher

Use this skill for any git-graph or GitHub-CLI operation: shipping a branch (creating it from main or committing onto your existing branch), rebasing, switching to main, creating a parallel worktree, generating release notes, or looking up `gh` commands that the workflow subcommands do not already wrap.

The orchestration delegates to atomic building blocks: `/branch-from-main`, `/conventional-commit-msg`, `/open-pr`, and the shared scripts at `~/.claude/scripts/git_group.py` and `~/.claude/scripts/classify_commits.py`. This skill never re-implements their mechanics.

**Commit messages.** Every commit produced by this skill uses the **Angular Conventional Commits** convention — `<type>(<scope>): <subject>`, lowercase type/scope, imperative-present subject, no trailing period, optional body explaining *why*, optional `BREAKING CHANGE:` footer. Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`. The canonical format lives in `~/.claude/commands/conventional-commit-msg.md`; every commit step below routes through `/conventional-commit-msg` or quotes a header that conforms to it.

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
/git reviewer                         # sweep your open PRs, address reviewer comments and failing CI checks, report which are clean
/git merge <N> [<N> ...]              # merge these open PRs in order, syncing main between each
/git merge --all                      # merge every open PR you authored, ascending PR order
/git merge <N> ... --keep-branch      # keep the remote branch (default deletes it)
/git merge <N> ... --merge|--rebase   # merge method (default: --squash)
```

`/git ship` subsumes the previous `/git cpr` subcommand. If you are already on a feature branch with a prior push, the branch is kept; only pre-flight, commit, push, and PR run. The `--quick` flag skips pre-flight for the same daily-iteration use case.

## Workflow

### 1. Parse the subcommand

Split `$ARGUMENTS` on the first space. The first word is the subcommand; everything after is its argument string.

- If the subcommand is empty or `help`: print the **Usage** block above and stop.
- If the subcommand is `cpr`: print `/git cpr was merged into /git ship — for the daily-iteration ergonomics use /git ship --quick`, then dispatch to `ship` with `--quick` prepended to the remaining argument string. If `--quick` is already present in the remaining argument string, do not prepend a duplicate — treat the argument string as-is.
- If the subcommand is not one of `ship`, `sync`, `main`, `merge`, `worktree`, `release-notes`, `cli`, `reviewer`: stop and print the **Usage** block.
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

### 8. Dispatch — `reviewer`

Sweep every open PR you authored, surface and address reviewer comments (including the minor ones) **and resolve failing GitHub Actions checks**, ending with a summary that says exactly which PRs are clean — so you know when to stop. This subcommand **edits code and pushes to your PR branches**; only ever act on PRs authored by `@me`.

1. **Enumerate your open PRs** in the current repo:
   ```bash
   gh pr list --author @me --state open --json number,title,headRefName,url,isDraft
   ```
   If there are none, print `No open PRs authored by you — nothing to review.` and stop. Resolve `<owner>/<repo>` once with `gh repo view --json owner,name`.

2. **Collect failing CI checks per PR.** Always sweep checks before reviewer comments — review on top of a red branch wastes effort and re-runs CI for free once a fix lands. List every check and pull failure detail only for the failed ones:
   ```bash
   gh pr checks <N> --json name,state,link,workflow
   ```
   For each check whose `state` is `FAILURE` or `STARTUP_FAILURE`, look up the run for the PR's head branch and grab the failing-step logs:
   ```bash
   RUN=$(gh run list --branch <headRefName> --workflow <workflow> --limit 1 \
           --json databaseId -q '.[0].databaseId')
   gh run view "$RUN" --log-failed
   ```
   Ignore checks in `PENDING`, `QUEUED`, `IN_PROGRESS`, or `SUCCESS`. Classify each failed check before doing anything to it:
   - **Auto-fixable** — deterministic lint/format errors (`ruff format`, `gofmt`, `stylua`, missing newline, trailing whitespace)
   - **Code/test bug** — assertion, type, or compile failure pointing at a specific file/line you can fix
   - **Flaky/transient** — network timeouts, runner provisioning errors, third-party service errors, no signal that the code is wrong
   - **Ambiguous** — anything else (secrets, infra, behavior change of unclear intent)

3. **Resolve failing checks first.** For each PR with failed checks, only on your own PRs, before touching reviewer comments:
   - Require a clean working tree first; if dirty, stop and ask (stash/commit/abort). Prefer a worktree (`/git worktree`) or `gh pr checkout <N>`; restore the user's original branch when done.
   - **Auto-fixable** → apply the formatter/linter fix locally.
   - **Code/test bug** → fix the underlying code or test.
   - **Flaky/transient** → rerun once with `gh run rerun --failed <run-id>`; if it fails again on the same step, reclassify as Ambiguous.
   - **Ambiguous** → surface under "Needs your input" with the failing-step excerpt; do not guess.
   - Run the repo's lint/tests (the `ship` **Pre-flight** table) before pushing; if they fail, fix or stop — never `--no-verify`.
   - Commit with `fix(ci): resolve <check> failure` and push (`git push`; never force unless asked; never amend a pushed commit).
   - **If a PR still has unresolved (Ambiguous) check failures after this step: skip its reviewer-comment pass and report it under "Needs your input" in the summary.** Do not address review comments on a red branch.

4. **Collect reviewer feedback per PR** (only for PRs that are now green or whose only failures were resolved). Gather feedback authored by *someone other than you* — human reviewers **and** review bots (e.g. Copilot, `claude-review`); include their nits/minor notes too — from all three surfaces, keeping only **unresolved / actionable** items:
   - **Inline review threads** with resolution state (skip `isResolved: true`):
     ```bash
     gh api graphql -f query='
       query($owner:String!,$repo:String!,$num:Int!){
         repository(owner:$owner,name:$repo){ pullRequest(number:$num){
           reviewThreads(first:100){ nodes{ isResolved isOutdated
             comments(first:20){ nodes{ author{login} path line body } } } } } } }' \
       -F owner=<owner> -F repo=<repo> -F num=<N>
     ```
   - **Review summaries** with state `CHANGES_REQUESTED` or `COMMENTED` and a non-empty body:
     ```bash
     gh api repos/<owner>/<repo>/pulls/<N>/reviews --jq '.[] | select(.body != "") | {user:.user.login, state, body}'
     ```
   - **PR conversation comments** (general, non-inline):
     ```bash
     gh api repos/<owner>/<repo>/issues/<N>/comments --jq '.[] | {user:.user.login, body}'
     ```
   Exclude comments whose author is the PR author (those are yours, not feedback).

5. **Classify and inform.** For each PR:
   - **No actionable review comments** (and checks resolved in step 3) → record it as clean for the summary.
   - **Otherwise** → list each item as `#<PR> <path>:<line> — <reviewer>: <ask>` (mark nits/minor explicitly) and tell the user what you intend to change *before* editing.

6. **Address review comments**, one PR at a time, only on your own PRs:
   - Require a clean working tree (or stay in the worktree/`gh pr checkout` from step 3); restore the user's original branch when done.
   - Implement **every** comment, including minor ones (naming, formatting, nits, comment wording). For an ambiguous, subjective, or behavior-changing comment, **do not guess** — surface it under "Needs your input" and move on.
   - Run the repo's lint/tests (the `ship` **Pre-flight** table) before pushing; if they fail, fix or stop — never `--no-verify`.
   - Commit with `fix(review): address review feedback on <area>` and push to update the PR (`git push`; never force unless the user asks; never amend a pushed commit).
   - Optionally reply on each thread so the reviewer sees it was handled — but never resolve a thread you did not actually address:
     ```bash
     gh api repos/<owner>/<repo>/pulls/<N>/comments/<comment_id>/replies -f body='Addressed in <sha>.'
     ```

7. **Summary message — always print this last**, covering every open PR so the stop condition is unambiguous:
   - **Clean (no review comments, all checks green):** list `#<PR> <title>` for each — these need nothing.
   - **Addressed:** list each PR, the comments resolved and checks fixed, and the pushed commit/URL.
   - **Needs your input:** any comment or check failure you could not safely auto-address, with the question or failing-step excerpt.

   If every open PR falls in **Clean**, say so plainly — e.g. `All N open PRs are free of unaddressed review comments and have all checks green — nothing left to do.` — so you know to stop.

**Rules for `reviewer`.** Only push to PRs authored by `@me`. Never resolve or dismiss a reviewer thread without a real change. Never `gh run rerun` a check whose log shows a clear code-level failure — fix the code instead. Surface ambiguous or behavior-changing feedback (or unclear CI failures) as a question rather than guessing. Restore the user's original branch (or use worktrees) when finished.

### 9. Dispatch — `merge`

Merge a set of open PRs **in the order given**, refreshing local `main` between each so every PR
merges against the latest base. This is a single operation with one job: land a queue of PRs
sequentially. It does not review, rebase-for-cleanliness, or trigger follow-on builds — for
review-then-merge use `/git reviewer` first; for the "wait for a release, then bump and un-skip"
playbook use the dedicated orchestration, not this subcommand. **Merging is a remote mutation —
only ever run this on explicit `/git merge` invocation, and only merge PRs that are green and
conflict-free.**

**Flag and argument parsing.** Inspect the argument string first:

- `--all` — target every open PR authored by `@me` in the current repo, in ascending PR-number
  order. Mutually exclusive with an explicit number list. **If both `--all` and one or more bare
  integers are present: stop and ask which the user meant.**
- Bare integers (`30 31 32`) — the exact PRs to merge, **in the order written**. Order matters;
  never reorder them.
- `--keep-branch` — keep the remote head branch. Default is to delete it after a successful merge.
- `--merge` / `--rebase` — merge method. Default is `--squash`. `--merge`, `--rebase`, and
  `--squash` are mutually exclusive; **if more than one is present: stop and ask.**

Resolve the PR list:

- `--all`:
  ```bash
  gh pr list --author @me --state open --json number,title,headRefName --jq 'sort_by(.number)[]'
  ```
  If none, print `No open PRs authored by you — nothing to merge.` and stop. `headRefName` is
  fetched so the confirmation step can name the branches that deletion will remove.
- Explicit numbers: use them verbatim in the given order.

**Confirm before mutating.** Print the ordered list as `#<N> <title> (<headRefName>)` and the
resolved options (method, and — when deletion is on — the exact branches that will be removed).
For `--all`, or any list of more than one PR, **wait for explicit confirmation** before merging
anything — the order and set are the user's decision.

**Per PR, in order:**

1. **Inspect state.**
   ```bash
   gh pr view <N> --json number,title,state,isDraft,mergeable,mergeStateStatus,headRefName
   ```
   - `state != OPEN` → skip with a note (already merged/closed); continue to the next PR.
   - `isDraft: true` → **stop the run** and report; do not merge a draft.
   - `mergeable == CONFLICTING` → **stop the run**, name the conflict, and do not force. The user
     resolves conflicts (via `/git sync` on that branch) before re-running.
   - `mergeStateStatus == BLOCKED` (required reviews outstanding, an unmet branch-protection rule,
     etc.) → **stop the run** and report the blocking reason. Do not attempt the merge — `gh pr
     merge` will fail. This is a distinct fourth stop condition, not a conflict or a red check.
2. **Require green checks.**
   ```bash
   gh pr checks <N>
   ```
   If any required check is failing or still pending → **stop the run** and report which check.
   Never merge a red or in-flight PR.
3. **Merge.** Build the command from the parsed flags — do not hardcode `--squash`/`--delete-branch`:
   - Method token: `--squash` (default), or `--merge` / `--rebase` when the user passed one.
   - Branch flag: include `--delete-branch` **unless** `--keep-branch` was passed; omit it when it was.
   ```bash
   gh pr merge <N> <--squash|--merge|--rebase> [--delete-branch]
   ```
   Example — default flags: `gh pr merge 31 --squash --delete-branch`. With `--rebase --keep-branch`:
   `gh pr merge 31 --rebase`.
4. **Sync `main` between PRs.** Dispatch to the `main` subcommand (Section 4) to checkout `main`,
   pull, and prune the merged branch. This is the "sync main between" step. **Note:** Section 4
   prunes *every* local branch fully merged into `main`, not only the branches in this merge set —
   so an unrelated, already-merged local branch (even one you were sitting on before the run) can
   be cleaned up here. This is harmless (`git branch -d` refuses unmerged branches, so nothing
   with unmerged work is ever deleted), but do not assume the only branch removed is the one just
   merged.
5. **Bring the next PR up to date.** If more PRs remain, run `gh pr update-branch` on the next one
   — it is idempotent (a no-op when the branch is already current), so run it unconditionally
   rather than guessing whether branch protection requires it:
   ```bash
   gh pr update-branch <next-N>
   ```
   If the output reports the branch is already up to date, continue immediately. **If it updates
   the branch, its checks are now pending — stop the run and tell the user checks are re-running
   on `#<next-N>`; do not proceed until they re-invoke `/git merge` after checks pass.** (Do not
   poll or block waiting for CI.)

**Stop semantics.** On the first draft / conflict / BLOCKED / red-check PR, stop the whole run —
do not skip ahead to later PRs, because a queue is usually ordered for a reason (a later PR may
depend on an earlier one). Report exactly which PRs merged and which remain untouched.

**Verify.** For each PR that was merged:
```bash
gh pr view <N> --json state --jq .state    # expect MERGED
```
Confirm local `main` is at the latest (`git log -1 origin/main --oneline`). Print a summary table:

| PR | Title | Result | Branch |
|----|-------|--------|--------|

with Result one of `merged` / `skipped (not open)` / `stopped (<reason>)` and Branch `deleted` /
`kept`.

**Rules for `merge`.** Never merge a PR with failing/pending checks or a conflict. Never force.
Never reorder the requested PR list. Confirm the set and order before merging when more than one
PR is targeted. Only merge PRs in the current repo; for `--all`, only PRs authored by `@me`.

### 10. Final verification step

For every subcommand, the dispatch block above ends with its own verification gate. Before this skill exits, confirm the gate fired (PR URL reachable, branch pruned report emitted, worktree listed, the requested `gh` command surfaced from the reference, the `reviewer` per-PR summary printed, the `merge` summary table printed with every merged PR showing MERGED, etc.) — if any verification was skipped, re-run it.

## Rules (apply across all subcommands)

- Never `--force` push; never `--no-verify`; never amend a pushed commit.
- Never commit to `main`/`master` except via `ship -m` / `ship -p`.
- If the working tree is unexpectedly clean for `ship`: stop.
- Multi-group flows always branch each group from the latest `main`.
- Always assign PRs to `@me` (handled by `/open-pr`).
