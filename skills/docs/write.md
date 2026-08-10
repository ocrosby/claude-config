# /docs write (Level 3 resource)

Read this file when `SKILL.md` step 1 dispatches to `write`. Detects the language and routes to the matching per-language workflow so only the relevant one loads.

## Entry point

Run the language detector. The second token of `$ARGUMENTS` (after `write`) is an explicit override:

```bash
bash ~/.claude/scripts/detect_language.sh "${2-}"
```

Returns `go`, `py`, `nvim`, `gherkin`, `rest`, or `unknown`.

- `unknown` → stop and ask the user which language.
- `rest` → not supported by `write`; recommend `/architect spec` instead.
- Otherwise read the matching file below and follow its workflow. Each ends with its own verification gate — confirm it fired before exiting.

| Detected | Read and apply |
|---|---|
| `go` | `~/.claude/skills/docs/write-go.md` |
| `py` | `~/.claude/skills/docs/write-py.md` |
| `nvim` | `~/.claude/skills/docs/write-nvim.md` |
| `gherkin` | `~/.claude/skills/docs/write-gherkin.md` |
