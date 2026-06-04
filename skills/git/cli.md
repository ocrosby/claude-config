# GitHub CLI Quick Reference

Reference for `gh` (GitHub's official CLI) covering the operations the rest of `/git` does not already wrap. For the canonical docs see https://cli.github.com/manual.

Source: adapted from [fredrikaverpil/dotfiles](https://github.com/fredrikaverpil/dotfiles/blob/main/stow/shared/.claude/skills/gh-cli/SKILL.md). Cross-references inside `/git`:

- **Routine PR creation** → `/open-pr` (pushes branch + composes structured body + assigns `@me`)
- **Full branch → commit → push → PR flow** → `/git ship`
- **PR review (request feedback from agents)** → `/code review` (delegates to language-reviewer agents)

Use `gh` directly for everything else: CI debugging, issue triage, reviews with line comments, API queries.

## Getting help

```bash
gh --help                    # List all commands
gh <command> --help          # Help for a specific command
gh auth status               # Check authentication
```

## Discovery patterns

```bash
gh <command> --web                  # Open in browser
gh <command> --json FIELDS          # JSON output for scripting
gh <command> <subcommand> -h        # Quick help for any command
gh <command> list --limit N         # Limit results (default: 20-30)
```

**Always use `--limit`** when querying lists (`pr list`, `issue list`, `run list`, etc.) to avoid overwhelming output. Default to a small N (5-10) and increase only if needed.

## CI/CD debugging

```bash
gh run list --limit 5              # Recent runs
gh run list --status failure       # Only failures
gh run view RUN_ID --log-failed    # Logs from failed steps only
gh run rerun RUN_ID --failed       # Rerun only the failed jobs
gh run watch RUN_ID                # Stream live output
```

For the typical "PR is red, what broke?" workflow:

```bash
PR=$(gh pr view --json number -q .number)
RUN=$(gh run list --branch "$(git branch --show-current)" --limit 1 --json databaseId -q '.[0].databaseId')
gh run view "$RUN" --log-failed
```

## Reviewing a PR with line-level comments

`gh pr review` only supports an overall body — not inline comments. For inline review, use `gh api`:

```bash
gh api repos/{owner}/{repo}/pulls/NUMBER/reviews \
  --input - <<'EOF'
{
  "commit_id": "LATEST_COMMIT_SHA",
  "event": "COMMENT",
  "body": "Overall: solid changes with a few suggestions.",
  "comments": [
    {
      "path": "src/example.go",
      "line": 42,
      "side": "RIGHT",
      "body": "This variable is unused."
    },
    {
      "path": "src/example.go",
      "line": 55,
      "side": "RIGHT",
      "body": "Consider using a constant here:\n\n```suggestion\nconst maxRetries = 3\n```"
    }
  ]
}
EOF
```

Set `event` to `COMMENT`, `APPROVE`, or `REQUEST_CHANGES`. Always confirm with the user which one to use — default to `COMMENT` unless explicitly approved or rejected.

**Comment field reference:**

| Field | Description |
|---|---|
| `path` | Relative file path in the repo |
| `line` | Line number in the file (for single-line comments) |
| `side` | `RIGHT` (additions) or `LEFT` (deletions) |
| `start_line` | Starting line (for multi-line comments) |
| `start_side` | Starting side (for multi-line comments) |
| `body` | Comment text (supports markdown and code suggestions) |

**Code suggestions** use GitHub's suggestion syntax inside the body:

````markdown
```suggestion
replacement code here
```
````

For the simple "approve / comment / request changes without inline comments" case:

```bash
gh pr review NUMBER --approve
gh pr review NUMBER --comment -b "feedback"
gh pr review NUMBER --request-changes -b "needs work"
```

## Issue triage

```bash
gh issue list --limit 10
gh issue list --assignee @me
gh issue create --title "Title" --body "Description"
gh issue view NUMBER
gh issue comment NUMBER -b "Comment"
gh issue close NUMBER
```

## JSON output + jq filtering

```bash
# Structured data
gh pr list --json number,title,author --limit 20

# Filter with jq
gh pr list --json number,title --limit 50 | jq '.[] | select(.number > 100)'

# Single-field extraction
gh pr view --json url -q .url
```

## API access

```bash
# Direct REST calls
gh api repos/OWNER/REPO
gh api repos/OWNER/REPO/pulls -f title="PR Title" -f head=branch -f base=main

# GraphQL
gh api graphql -f query='{ viewer { login } }'
```

## Finding your work

```bash
gh pr list --author @me --limit 20
gh issue list --assignee @me --limit 20
gh search prs "author:ocrosby is:open"
gh search issues "assignee:ocrosby is:open"
```

For PRs assigned to you for review:

```bash
gh pr list --search "review-requested:@me"
```

## Environment variables

- `GH_TOKEN` — authentication token (when not using `gh auth login`)
- `GH_REPO` — default repository (OWNER/REPO format)
- `GH_EDITOR` — preferred editor for interactive commands
- `GH_PAGER` — pager for output (e.g., `less`, or empty to disable)

## Aliases

```bash
gh alias set pv 'pr view'
gh alias set co 'pr checkout'
gh alias list
```
