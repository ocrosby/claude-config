# Operating notes

Reference material moved out of `CLAUDE.md` to keep the always-loaded surface small. Read only when relevant.

## Working with Plan Mode

- Start every complex task in plan mode (shift+tab to cycle).
- Pour energy into the plan so Claude can 1-shot the implementation.
- When something goes sideways, switch back to plan mode and re-plan. Don't keep pushing.
- Use plan mode for verification steps too, not just for the build.

## Parallel Work

- For tasks that need more compute, use subagents to work in parallel.
- Offload individual tasks to subagents to keep the main context window clean and focused.
- When working in parallel, only one agent should edit a given file at a time.
- For fully parallel workstreams, use git worktrees: `git worktree add .claude/worktrees/<name> origin/main`.

## Session Management

- `/branch` forks a session (or `claude --resume <session-id> --fork-session` from CLI).
- `/btw` answers quick side queries without interrupting the agent's current work.
- `/teleport` continues a cloud session on your local machine.
- `/remote-control` controls a local session from your phone or browser.
- `/voice` (CLI) or the voice button (Desktop) enables voice input.

## Multi-Repo Work

- Use `--add-dir` (or `/add-dir`) to give Claude access to additional repositories.
- Add `"additionalDirectories"` to `settings.json` to always load extra folders on startup (this repo's `settings.json` already has `/tmp` here).
