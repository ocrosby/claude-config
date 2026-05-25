---
description: "Compose a Conventional Commits message from staged changes and commit. Building block for /git-ship and /git-cpr; also usable standalone."
---

# Conventional Commit Message

Use this command to commit already-staged changes with a Conventional Commits message. This is the atomic commit step extracted from `/git-ship` and `/git-cpr` — it does **not** stage files, push, or create a branch.

**If nothing is staged: stop and tell the user to stage files first.**

## Steps

1. Run `git diff --cached` to inspect what is staged. If empty, stop and tell the user there is nothing to commit.
2. Determine the conventional commit type from the staged diff:
   - New behavior or public API → `feat`
   - Bug fix → `fix`
   - Docs only → `docs`
   - Code restructure with no behavior change → `refactor`
   - Performance-only change → `perf`
   - Test-only change → `test`
   - Tooling, CI, deps → `chore` or `ci` or `build`
3. Derive a scope from the most prominent affected path (package name, module, or top-level dir). Omit the scope when the change crosses three or more unrelated scopes.
4. Compose the subject line: `<type>(<scope>): <imperative description>`. Lowercase, no trailing period, under 72 characters.
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

## Rules

- Never `git add` from inside this command. The caller stages.
- Never push.
- Never amend.
- Never bypass hooks.
- If the working tree is on `main` or `master` without an explicit override from the caller, stop and tell the user to use `/git-ship -m` for direct-to-main commits.
