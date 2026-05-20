---
name: release-notes
description: Generate a changelog or release notes for a version, tag range, or branch. Use when the user asks to write a changelog, generate release notes, summarize changes since a tag or version, or invokes /release-notes.
disable-model-invocation: true
allowed-tools: Bash, Read
---

Generate release notes for: `$ARGUMENTS`

If no arguments are provided, generate notes since the last tag; if the repository has no tags, generate notes from the initial commit. The deterministic work (parsing each commit's conventional-commit type, detecting breaking-change markers, grouping into Added/Changed/Fixed/Removed/Security) lives in the bundled `classify_commits.py` script. Range derivation, "Added vs Changed" disambiguation, and human-readable prose synthesis stay here because they require conditional logic and judgment.

## Current state

- Last tag: !`git describe --tags --abbrev=0 2>/dev/null || echo "(no tags yet)"`
- Commits since last tag or initial commit: !`git log "$(git describe --tags --abbrev=0 2>/dev/null || git rev-list --max-parents=0 HEAD)"..HEAD --oneline`

## Workflow

### 1. Determine the commit range

- If `$ARGUMENTS` specifies a range (e.g. `v1.2.0..HEAD` or `v1.1.0..v1.2.0`), use it directly
- Otherwise:
  - If a last tag exists, use it as the base: `<last-tag>..HEAD`
  - If there are no tags, use the full history from the initial commit: `"$(git rev-list --max-parents=0 HEAD)"..HEAD`

### 2. Run the classifier

```bash
python3 ~/.claude/skills/release-notes/classify_commits.py <base>..HEAD [--format json|markdown] [--include-chores]
```

The script:

- Reads `git log` for the range
- Parses each commit subject for conventional-commit type and `!` breaking-change marker
- Inspects the commit body for `BREAKING CHANGE:` footers
- Maps types to categories: `feat` → Added (or Changed if the subject contains "update/change/modify/rename"), `fix` → Fixed, `security` → Security, `revert` → Changed
- Excludes `refactor`, `perf`, `style`, `test`, `build`, `ci`, `chore` by default (surface with `--include-chores`)
- Emits a Markdown draft (default) or JSON

### 3. Refine the Markdown draft

Read the script's output and apply judgment:

- **Added vs Changed**: The script defaults `feat` to Added. Move entries to Changed when the feature modifies existing behavior rather than introducing a net-new capability. The script's `change` heuristic catches obvious wording cues but not all of them.
- **Breaking changes write-up**: For each entry in the `### Breaking changes` section, expand the one-line subject into a short paragraph naming the user-visible impact and the migration step
- **Drop noise**: Even commits the script kept can be irrelevant for a user-facing changelog (typo fixes in internal docs, test-only changes that slipped through). Remove them
- **Group security entries**: If the script surfaced multiple Security entries, summarize what was vulnerable and what's fixed without leaking CVE-style detail

### 4. Write the final notes

Use this format:

```
## [version or date]

### Breaking Changes

- <one-paragraph write-up per breaking change>

### Added

- <user-visible description, not commit-log dump>

### Fixed

- <user-visible description>
```

Keep entries concise — one line per change unless context genuinely requires more. Write from the user/consumer perspective, not a git log dump.

### 5. Verify

Confirm the final notes:

- Include every Breaking Change the script flagged (do not silently drop)
- Do not list commit hashes (the script's draft has them as anchors; the final notes should not)
- Group entries under the expected section headings

**If a section the script populated is missing from the final notes: stop and explain which commits were dropped and why.**
