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
   - **Unresolved reviewer feedback**, split by who wrote it. Exclude comments authored by the PR author.

     **Human reviewers** — every unresolved, actionable item, from all three surfaces (same as before):
     ```bash
     # Inline threads (skip isResolved: true)
     gh api graphql -f query='
       query($owner:String!,$repo:String!,$num:Int!){
         repository(owner:$owner,name:$repo){ pullRequest(number:$num){
           reviewThreads(first:100){ nodes{ isResolved isOutdated
             comments(first:20){ nodes{ author{login __typename} path line body
               pullRequestReview{ databaseId } } } } } } } }' \
       -F owner=<owner> -F repo=<repo> -F num=<N>
     # Review summaries with a non-empty body
     gh api repos/<owner>/<repo>/pulls/<N>/reviews \
       --jq '.[] | select(.body != "") | {id, user:.user.login, type:.user.type, state, body, commit_id, submitted_at}'
     # PR conversation comments
     gh api repos/<owner>/<repo>/issues/<N>/comments \
       --jq '.[] | {id, user:.user.login, type:.user.type, body, created_at}'
     ```

     **Review bots** (author `type == "Bot"` / GraphQL `__typename == "Bot"`, for example `twc-mercury-reviewer[bot]`, Copilot, `claude-review`) — take **only the single most recent completed review per bot** and ignore everything that bot posted earlier. Bots re-review on every push and repeat or supersede their earlier findings, so reading the whole history re-does work that is already done. Per bot login:
     1. Collect that bot's comments across all three surfaces and sort by timestamp.
     2. **Drop status-only posts**: bodies containing `encountered an error`, or a progress checklist with unchecked boxes (`- [ ]`), or "is reviewing" / "in progress". They are not reviews. Also drop bots whose latest body has no actionable findings (coverage reports, badge updates, "all prior findings resolved") and treat that bot as having **no open feedback**.
     3. The **most recent remaining post** is the bot's current review. **If a status-only post (an in-progress review) is newer than it, the current review is still running**: take nothing from that bot, record `review pending: <bot>` against the PR, and tell the user to re-run once it finishes. A bot whose newest post is only an `encountered an error` notice with no completed review after it is reported the same way (pending or failed); the user decides whether to re-trigger it. Do not fall back to its older findings.
     4. Take that review's findings **in full**, including any it explicitly carries over from earlier rounds ("still unaddressed"), and nothing from older posts. Keep only items under its issue sections (`Must Fix` / `Moderate` / `Minor` / `Should Fix` / `Consider`, or the bot's equivalent). Ignore its "resolved", "no new issues" and score or marker lines.
     5. Inline threads by that bot count only if unresolved, not outdated, and part of the same review (`pullRequestReview.databaseId` equals the current review's id, when it has one).
     6. Record the review's reviewed commit if it carries one (for example `<!-- reviewed-commit: <sha> -->`, or the review's `commit_id`) and the PR's current head SHA. The sub-agent uses the gap to check whether fixes already landed.

     Print, per bot, which review was used and how many older posts were ignored.

4. **Print the plan and wait for confirmation.** Group by PR:
   ```
   #<N> <title>
     Checks to fix:      <count> (auto-fixable=<n>, bug=<n>, flaky=<n>, ambiguous=<n>)
     Comments to address: <count> (humans=<n>, bots=<n>)
     Bot review used:    <bot> at <timestamp>, reviewed <sha> (head <sha>); <n> older posts ignored
     Review pending:     <bot>   (only when an in-progress review is newer; nothing taken from that bot)
   ```
   **If the user does not confirm: stop. Do not create worktrees. Do not fanout.**

5. **Create one worktree per PR** at its assigned path:
   ```bash
   git worktree add .claude/worktrees/pr-<N>-<run_id> origin/<headRefName>
   ```
   **If any `git worktree add` fails: stop.** Remove every worktree already created earlier in this batch (`git worktree remove --force`), print the failure, and do not fanout a partial batch.

6. **Fanout — dispatch one sub-agent per PR concurrently.** For each PR, compose the sub-agent prompt by substituting the placeholders in `skills/git/reviewer-subagent.md` (`<N>`, `<owner>/<repo>`, `<worktree_path>`, `<headRefName>`, `<run_id>`, `<original_cwd>`, `<failed_checks_block>`, `<review_comments_block>`). Invoke every `Agent()` in a **single response** so they run in parallel, **and pass `model: "haiku"` on every `Agent()` call in this fanout** — the sub-agent work (lint auto-fixes, addressing individual review comments, replying to threads, JSON return) is well within Haiku's range and the fanout is where cost and latency compound. **Cap at 8 concurrent sub-agents per batch**; process any additional PRs in a second batch after the first completes. **The main agent must never `cd` into a sub-agent's worktree** — paths flow through the sub-agent prompts.

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
   - **Already addressed:** `comments_already_addressed` entries (current review findings the sub-agent found already fixed in the code).
   - **Review pending:** PRs where a bot review is still running, so nothing was taken from that bot. Re-run once it finishes.
   - **Needs your input:** every `needs_input` entry from every sub-agent, verbatim, with its PR number and `kind`.
   - **Worktrees:** `<N> removed, <M> leaked` — name the leaked paths if any.

   If every open PR falls in **Clean**, say so plainly — e.g. `All N open PRs are free of unaddressed review comments and have all checks green — nothing left to do.` — so you know to stop.

## Rules

Only push to PRs authored by `@me`. Never resolve or dismiss a reviewer thread without a real change. Never act on a bot's older reviews: only its most recent completed review counts, so an earlier finding that the latest review no longer raises stays untouched. Never `gh run rerun` a check whose log shows a clear code-level failure — fix the code instead. Surface ambiguous or behavior-changing feedback (or unclear CI failures) as `needs_input` rather than guessing. The main agent must never `cd` into a sub-agent's worktree; every path passes through the sub-agent prompt. Sub-agent count is capped at 8 concurrent per batch to keep GH API polling under rate limits (`--interval 60` on `gh pr checks --watch` gives roughly 480 calls/hour at full concurrency, well below the 5000/hour cap).
