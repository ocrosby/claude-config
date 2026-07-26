# /git reviewer (Level 3 resource)

Read this file when `SKILL.md` step 1 dispatches to `reviewer`. Sweeps every open PR you authored, addresses reviewer comments and failing CI, and ends with a summary that names exactly which PRs are clean.

**This subcommand edits code and pushes to your PR branches**; only ever act on PRs authored by `@me`.

The workflow runs **one sub-agent per PR in parallel, each in its own isolated `git worktree`**. The exact sub-agent input prompt and JSON return schema live in `skills/git/reviewer-subagent.md` — that is the authoritative contract. Do not paraphrase it inline; the orchestrator substitutes its placeholders and passes the result to `Agent()`.

## Workflow

1. **Enumerate your open PRs** in the current repo:
   ```bash
   gh pr list --author @me --state open --json number,title,headRefName,url,isDraft
   ```
   **If there are none: print `No open PRs authored by you — nothing to review.` and stop.**
   Resolve `<owner>/<repo>` once with `gh repo view --json owner,name`. Record `<original_cwd>` as the user's starting directory — sub-agents receive it for cleanup.

2. **Pre-flight — always run, in this order:**
   ```bash
   run_id=$(uuidgen | tr -d - | head -c8)
   git worktree prune -v
   # sweep pr-* worktrees older than 24h — orphans from prior crashed runs
   find .claude/worktrees -maxdepth 1 -type d -name 'pr-*' -mmin +1440 2>/dev/null | \
     while read -r d; do
       git worktree remove --force "$d" 2>/dev/null || rm -rf "$d"
     done
   ```
   The `run_id` becomes the per-invocation suffix on every worktree path this run creates (`.claude/worktrees/pr-<N>-<run_id>`), so this invocation's paths cannot collide with a prior run's leftovers.

3. **Pre-collect the per-PR work list** in the main-agent context. Sub-agents receive it as fixed input and must not re-fetch. For every PR:
   - **Failed checks** — `gh pr checks <N> --json name,state,link,workflow`. For each `FAILURE` or `STARTUP_FAILURE`, grab the failing-step log:
     ```bash
     RUN=$(gh run list --branch <headRefName> --workflow <workflow> --limit 1 \
             --json databaseId -q '.[0].databaseId')
     gh run view "$RUN" --log-failed
     ```
     Ignore `PENDING`, `QUEUED`, `IN_PROGRESS`, `SUCCESS`. Classify each failed check:
     - **auto-fixable** — deterministic lint/format errors (`ruff format`, `gofmt`, `stylua`, trailing whitespace)
     - **bug** — assertion, type, or compile failure pointing at a specific file/line
     - **flaky** — network timeouts, runner provisioning errors, third-party service errors, no signal that the code is wrong
     - **ambiguous** — anything else (secrets, infra, unclear behavior change)
   - **Unresolved reviewer feedback** from all three surfaces. Keep only unresolved, actionable items; exclude comments authored by the PR author. Include both human reviewers and review bots (Copilot, `claude-review`, etc.).
     ```bash
     # Inline threads (skip isResolved: true)
     gh api graphql -f query='
       query($owner:String!,$repo:String!,$num:Int!){
         repository(owner:$owner,name:$repo){ pullRequest(number:$num){
           reviewThreads(first:100){ nodes{ isResolved isOutdated
             comments(first:20){ nodes{ author{login} path line body } } } } } } }' \
       -F owner=<owner> -F repo=<repo> -F num=<N>
     # Review summaries with a non-empty body
     gh api repos/<owner>/<repo>/pulls/<N>/reviews \
       --jq '.[] | select(.body != "") | {user:.user.login, state, body}'
     # PR conversation comments
     gh api repos/<owner>/<repo>/issues/<N>/comments \
       --jq '.[] | {user:.user.login, body}'
     ```

4. **Print the plan and wait for confirmation.** Group by PR:
   ```
   #<N> <title>
     Checks to fix:      <count> (auto-fixable=<n>, bug=<n>, flaky=<n>, ambiguous=<n>)
     Comments to address: <count>
   ```
   **If the user does not confirm: stop. Do not create worktrees. Do not fanout.**

5. **Create one worktree per PR** at its assigned path:
   ```bash
   git worktree add .claude/worktrees/pr-<N>-<run_id> origin/<headRefName>
   ```
   **If any `git worktree add` fails: stop.** Remove every worktree already created earlier in this batch (`git worktree remove --force`), print the failure, and do not fanout a partial batch.

6. **Fanout — dispatch one sub-agent per PR concurrently.** For each PR, compose the sub-agent prompt by substituting the placeholders in `skills/git/reviewer-subagent.md` (`<N>`, `<owner>/<repo>`, `<worktree_path>`, `<headRefName>`, `<run_id>`, `<original_cwd>`, `<failed_checks_block>`, `<review_comments_block>`). Invoke every `Agent()` in a **single response** so they run in parallel. **Cap at 8 concurrent sub-agents per batch**; process any additional PRs in a second batch after the first completes. **The main agent must never `cd` into a sub-agent's worktree** — paths flow through the sub-agent prompts.

7. **Collect returns.** Each sub-agent returns the JSON specified in `skills/git/reviewer-subagent.md`. Malformed, missing, or non-JSON output is treated as `outcome: "failed"` with the raw text captured in the PR's `needs_input` array.

8. **Cleanup verification — always run, regardless of sub-agent outcomes.** For each dispatched `worktree_path`:
   ```bash
   git worktree list --porcelain | grep -F "<worktree_path>" && \
     git worktree remove --force "<worktree_path>"
   ```
   **If a worktree still exists after force-remove: mark it as `leaked` in the summary.** Never delete the parent `.claude/worktrees/` directory — future runs depend on it.

9. **Summary — always print this last**, covering every open PR so the stop condition is unambiguous:
   - **Clean (no work needed, checks green):** list `#<PR> <title>`.
   - **Addressed:** list each PR, its checks fixed and comments resolved, the pushed commit SHAs, and the PR URL.
   - **Needs your input:** every `needs_input` entry from every sub-agent, verbatim, with its PR number and `kind`.
   - **Worktrees:** `<N> removed, <M> leaked` — name the leaked paths if any.

   If every open PR falls in **Clean**, say so plainly — e.g. `All N open PRs are free of unaddressed review comments and have all checks green — nothing left to do.` — so you know to stop.

## Rules

Only push to PRs authored by `@me`. Never resolve or dismiss a reviewer thread without a real change. Never `gh run rerun` a check whose log shows a clear code-level failure — fix the code instead. Surface ambiguous or behavior-changing feedback (or unclear CI failures) as `needs_input` rather than guessing. The main agent must never `cd` into a sub-agent's worktree; every path passes through the sub-agent prompt. Sub-agent count is capped at 8 concurrent per batch to keep GH API polling under rate limits (`--interval 60` on `gh pr checks --watch` gives roughly 480 calls/hour at full concurrency, well below the 5000/hour cap).
