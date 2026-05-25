---
description: Create a new git worktree under .claude/worktrees/ for running a parallel Claude Code session.
argument-hint: "[name]"
# Human gate: this skill mutates the filesystem and spawns parallel sessions. Block model auto-invocation.
disable-model-invocation: true
---

# Worktree: Parallel Session Setup

Use this skill when you want to spin up a git worktree so a parallel Claude Code session can run on the same repo without disturbing the main checkout.

## Workflow

### 1. Determine the worktree name

If the user passed a name argument, use it. Otherwise, generate one from today's date plus a short descriptor based on the current intent (e.g. `2026-02-03-feature`).

### 2. Create the worktree

```bash
git worktree add .claude/worktrees/$name origin/main
```

If the command fails (e.g. the path already exists or `origin/main` is not fetched), report the failure verbatim and stop. Do not force or delete an existing worktree.

### 3. Confirm and print the launch command

Confirm the worktree was created. Then print the launch command for the user to copy:

```bash
cd .claude/worktrees/$name && claude
```

### 4. Verify

Run `git worktree list` and confirm the new worktree appears in the output. **If the new path is absent: stop and report the failure.**

### 5. Print follow-up commands

Print these literal commands so the user can act on the new worktree:

- Launch: `cd .claude/worktrees/$name && claude`
- Alternative entry point: `claude -w` starts a new session directly in a worktree without this skill
- List: `git worktree list`
- Remove: `git worktree remove .claude/worktrees/$name`
