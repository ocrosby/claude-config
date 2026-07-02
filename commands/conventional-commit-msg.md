---
description: "Compose an Angular Conventional Commits message from staged changes and commit. Building block for /git ship."
user-invocable: false
---

# Conventional Commit Message

Use this command to commit already-staged changes with an **Angular Conventional Commits** message. This is the atomic commit step extracted from `/git ship` — it does **not** stage files, push, or create a branch.

The Angular convention is the canonical format used everywhere in this repo:

- Header: `<type>(<scope>): <subject>` — type and scope lowercase, subject in imperative present tense ("change" not "changed" or "changes"), no trailing period.
- Optional body separated by a blank line, explaining **why** not what, wrapped at 72 columns.
- Optional footers — `BREAKING CHANGE: …` and issue references like `Closes #123`.

Reference: https://www.conventionalcommits.org/ and https://github.com/angular/angular/blob/main/contributing.md.

**If nothing is staged: stop and tell the user to stage files first.**

## Steps

1. Run `git diff --cached` to inspect what is staged. If empty, stop and tell the user there is nothing to commit.
2. Determine the Angular conventional commit type from the staged diff:
   - New behavior or public API → `feat`
   - Bug fix → `fix`
   - Docs only → `docs`
   - Formatting / whitespace / style only, no logic change → `style`
   - Code restructure with no behavior change → `refactor`
   - Performance-only change → `perf`
   - Test-only change → `test`
   - Reverting a previous commit → `revert`
   - Tooling, CI, deps → `chore` or `ci` or `build`

   The canonical type list lives in `CLAUDE.md` — if it ever diverges from this list, `CLAUDE.md` wins.
3. Derive a scope from the most prominent affected path (package name, module, or top-level dir). Omit the scope when the change crosses three or more unrelated scopes.
4. Compose the subject line: `<type>(<scope>): <imperative description>`. Type and scope lowercase, subject in imperative present tense, no trailing period, under 72 characters. Omit the scope (and its parens) when the change crosses three or more unrelated scopes.
5. Compose the body (optional, only when the subject is insufficient): explain **why**, not what. Wrap at 72 columns.
6. Commit with a HEREDOC to preserve formatting:

   ```bash
   git commit -m "$(cat <<'EOF'
   <subject>

   <body>
   EOF
   )"
   ```

7. If the commit succeeds, print the new commit hash and short message. If it fails (pre-commit hook, etc.), report the failure verbatim and stop — do not retry, do not `--no-verify`.

## Breaking changes

When the staged diff removes, renames, or alters a public API in a way that requires callers to change, mark the commit as breaking. Both forms are valid; use both for maximum visibility on a true breaking change:

- **Subject suffix:** add `!` immediately after the type/scope — `feat(api)!: remove deprecated /v1/users endpoint`
- **Footer:** add a `BREAKING CHANGE:` paragraph at the end of the body explaining the impact and migration path

Example:

```
feat(api)!: remove deprecated /v1/users endpoint

The /v1/users routes have been replaced by /v2/users with cursor pagination.

BREAKING CHANGE: callers of /v1/users must migrate to /v2/users — the response
envelope and pagination shape are different. See docs/migrations/v2-users.md.
```

Surface breaking changes in `/git ship` reports so the user can confirm before pushing — a breaking commit on `main` skips PR review entirely under `-m`.

## Rules

- Never `git add` from inside this command. The caller stages.
- Never push.
- Never amend.
- Never bypass hooks.
- If the working tree is on `main` or `master` without an explicit override from the caller, stop and tell the user to use `/git ship -m` for direct-to-main commits.
