# Codebase Audit (Repository History)

Analyze the current git repository's history to produce a structured health report covering churn, ownership, bugs, momentum, and firefighting patterns.

Source: adapted from [fredrikaverpil/dotfiles](https://github.com/fredrikaverpil/dotfiles/blob/main/stow/shared/.claude/skills/codebase-audit/SKILL.md), which credits [piechowski.io/post/git-commands-before-reading-code](https://piechowski.io/post/git-commands-before-reading-code/) for the underlying technique.

## Goal

Produce a structured markdown report with one section per dimension, including raw data (top files/contributors) and observations, to help the reader orient in an unfamiliar codebase and identify risk areas before reading code.

## Steps

### 0. Detect GitHub availability

```bash
gh repo view --json nameWithOwner 2>/dev/null
```

If this succeeds, the GitHub enrichments in step 2 are available. If it fails (not a GitHub repo, or `gh` not authenticated), skip them and rely on the git-only data. Do not warn or apologize — just use what's available.

### 1. Gather git-only metrics

```bash
python3 ~/.claude/scripts/audit_repo.py --json
```

The script emits JSON with five dimensions, each bounded to top-N:

- `churn` — top 20 files by change count in the past year (the clearest signal of codebase drag).
- `ownership` — `commits_all_time` and `commits_recent_6mo` (per-author counts), `lines_by_author` (insertions/deletions for the top-5 committers — distinguishes high-volume from high-frequency contributors), `subsystems` (top-3 contributors per top-level directory), and `recent_commits` (5 recent subjects for the top-3 committers, for qualitative characterization).
- `bug_hotspots` — top 20 files touched in `fix|bug|broken` commits.
- `momentum` — monthly commit counts across all history.
- `firefighting` — count + list of `revert|hotfix|emergency|rollback` commits in the past year.

Flags: `--since "<window>"` (churn/firefighting window, default `1 year ago`), `--top N` (default 20). **If the script exits non-zero (not a git repository): stop and report.**

### 2. GitHub enrichments (only if step 0 succeeded)

Run to cross-validate and enrich the git data. Skip any that error.

- **Contributor stats** — pre-aggregated additions/deletions per author; cross-check against `ownership.lines_by_author`:
  ```bash
  gh api repos/{owner}/{repo}/stats/contributors
  ```
- **PR review patterns** — review silos and bottlenecks (a knowledge-concentration risk):
  ```bash
  gh pr list --state merged --limit 100 --json author,reviews
  ```
- **Bug issues** — user-facing bugs, vs the commit-grep hotspots:
  ```bash
  gh issue list --label bug --state all --limit 50 --json title,assignees,url,closedAt
  ```
- **PR merge cadence** — often a better velocity signal than raw commits in squash workflows; group by month and compare to `momentum`:
  ```bash
  gh pr list --state merged --limit 200 --json mergedAt
  ```
- **Release cadence** — regular releases indicate a healthy delivery rhythm:
  ```bash
  gh release list --limit 20
  ```
- **Reverted PRs** — squash-merged reverts don't always show in `git log`:
  ```bash
  gh pr list --state merged --search "revert OR hotfix OR emergency" --limit 50 --json title,mergedAt,url
  ```

### 3. Synthesize the report

Combine the script's JSON (and any GitHub enrichments) into a structured markdown report:

1. **High-Churn Files** — table + observations; flag any file appearing disproportionately often.
2. **Team Ownership** — all-time / recent tables + a nuanced bus-factor assessment. A contributor with few commits but large line changes in critical subsystems matters more than commit count suggests; concentrated subsystem ownership is a bus-factor risk even when overall counts look balanced; mostly-formatting/config churn carries less risk.
3. **Bug Hotspots** — table + overlay against churn to find the highest-risk code (changes frequently AND attracts bug fixes).
4. **Project Momentum** — monthly timeline + trend (steady rhythm / growth / decline); flag sudden drops.
5. **Firefighting Patterns** — count + list + observations; frequent reverts indicate deploy instability and test-reliability issues.
6. **Key Takeaways** — 3–5 bullets summarizing the most important findings.

If GitHub data was available, note that at the top of the report. If not, mention the analysis is git-only and could be enriched by running against a GitHub-hosted repo with `gh` authenticated.

**Success criteria**: A single, coherent markdown report covering all 5 dimensions with actionable observations is returned to the user.
