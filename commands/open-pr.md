---
description: "Push the current branch and open a PR with a structured body, or update the existing PR. Building block for /git ship and /git cpr."
user-invocable: false
---

# Open PR

Use this command to push the current branch upstream and open a pull request against `main` (or update the existing PR if one already exists for the branch). Composes a structured body from the most recent commit(s) on the branch.

**If the current branch is `main` or `master`: stop and tell the caller to use `/git ship -m` for direct-to-main commits.**

## Steps

1. Capture the current branch:

   ```bash
   BRANCH=$(git branch --show-current)
   ```

   If `BRANCH` is empty, stop (detached HEAD).

2. Push to remote with `-u` (idempotent — safe whether the upstream is set or not):

   ```bash
   git push -u origin "$BRANCH"
   ```

   Never `--force` or `--force-with-lease`. If the push is rejected because the remote is ahead, stop and tell the caller to rebase via `/git sync`.

3. Check whether a PR already exists for this branch:

   ```bash
   gh pr view --json url --jq .url 2>/dev/null
   ```

   - **PR exists:** the push in step 2 already updated it. Print the URL and stop.
   - **No PR exists:** continue to step 4.

4. Read the most recent commit on the branch to derive the PR title and body context:

   ```bash
   git log -1 --pretty=format:"%s%n%n%b"
   ```

5. Determine the PR label from the commit type:

   | Commit type | Label |
   |---|---|
   | `feat` | `enhancement` |
   | `fix` | `bug` |
   | `docs` | `documentation` |
   | anything else | omit `--label` |

6. Open the PR with `gh pr create` using the commit subject as the title (under 70 characters) and a structured body:

   ```bash
   gh pr create --assignee @me --label <label> --title "<conventional title>" --body "$(cat <<'EOF'
   ## Summary
   - <bullet 1>
   - <bullet 2>

   ## Motivation
   <why — business context, bug impact, technical debt>

   ## Test Plan
   - [ ] <test step 1>
   - [ ] <test step 2>
   EOF
   )"
   ```

   Derive bullets and motivation from the commit body and the diff against `main`. Use a `Depends on #<PR>` line in the body if the caller indicated a cross-PR dependency.

7. Run `gh pr view --json url,state --jq '"\(.state) \(.url)"'` and print the result. Confirm the state is `OPEN`.

## Rules

- Never `--force` or `--force-with-lease` push.
- Never open a duplicate PR — if one exists, the push has already updated it.
- Always assign the PR to `@me`.
- Never bypass the title length limit (70 characters) — abbreviate the scope or description instead.
- PR title must follow Conventional Commits format and match the commit type used on the branch.
