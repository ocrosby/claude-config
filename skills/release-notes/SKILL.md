---
name: release-notes
description: Generate a changelog or release notes for a version, tag range, or branch. Use when the user asks to write a changelog, generate release notes, summarize changes since a tag or version, or invokes /release-notes.
disable-model-invocation: true
allowed-tools: Bash, Read
---

Generate release notes for: `$ARGUMENTS`

If no arguments are provided, generate notes since the last tag; if the repository has no tags, generate notes from the initial commit.

## Current state

- Last tag: !`git describe --tags --abbrev=0 2>/dev/null || echo "(no tags yet)"`
- Commits since last tag or initial commit: !`git log "$(git describe --tags --abbrev=0 2>/dev/null || git rev-list --max-parents=0 HEAD)"..HEAD --oneline`

## Instructions

1. Determine the commit range:
   - If `$ARGUMENTS` specifies a range (e.g. `v1.2.0..HEAD` or `v1.1.0..v1.2.0`), use it directly.
   - Otherwise:
     - If a last tag exists, use it as the base: `git log <last-tag>..HEAD`
     - If there are no tags (Last tag is `(no tags yet)`), use the full history from the initial commit, e.g. `git log "$(git rev-list --max-parents=0 HEAD)"..HEAD` or simply `git log --oneline`

2. Run `git diff <base>...HEAD --stat` to understand the scope of changes

3. Group commits by type:
   - **Added** — new features, new endpoints, new commands
   - **Changed** — modified behavior, updated dependencies, refactors that affect users
   - **Fixed** — bug fixes
   - **Removed** — deleted features, deprecated API removal
   - **Security** — vulnerability fixes, auth changes

4. Write for a human reader — describe what changed from a user/consumer perspective, not a git log dump. Skip obvious internal chores (lint fixes, formatting) unless they affect users.

5. Note breaking changes explicitly at the top under **Breaking Changes**.

## Output format

```
## [version or date]

### Breaking Changes

- ...

### Added

- ...

### Fixed

- ...
```

Keep entries concise — one line per change unless context genuinely requires more.
