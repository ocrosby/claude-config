# /study — vault pre-flight (Level 3 resource)

Read this file **only when** `.claude-vault` is `not-configured` in the Environment section of `SKILL.md`. Configures the vault so Step 5 can publish research reports.

## When to read

Loaded on demand by the pre-flight step in `SKILL.md`. If a vault is already configured for the repo (`.claude-vault` present), skip this file entirely.

## Steps

### Step 0 — Ask the user

> No shared vault is configured for this repo (`.claude-vault` not found). Do you want to
> publish this report to a shared Obsidian vault repo? If yes, give me the git URL to use
> (new or existing) — I'll remember it in `.claude-vault` for next time.

**If the user declines or has no vault to use:** skip vault publishing for this session
and go directly to Step 1 in `SKILL.md`. Step 4's local report is unaffected either way.

**If the user provides a URL:** continue to PF1.

### PF1 — Create `.claude-vault`

Write the vault URL the user provided to `<repo_root>/.claude-vault`.

### PF2 — Check whether the file would be gitignored

```bash
git -C "$repo_root" check-ignore -q .claude-vault 2>/dev/null && echo "ignored" || echo "tracked"
```

- If the output is `ignored`: the project has intentionally excluded `.claude-vault` from version control. Use the file silently for this session — do not attempt to commit it. Skip to Step 1 in `SKILL.md`.
- If the output is `tracked`: continue to PF3.

### PF3 — Attempt to commit and push on the current branch

```bash
cd "$repo_root"
git add .claude-vault
git commit -m "chore: add .claude-vault for study skill vault integration"
git push 2>&1
```

- If the push succeeds: inform the user quietly:
  > `.claude-vault` was missing — created and pushed to `<branch>`.

  Then skip to Step 1 in `SKILL.md`.

- If the push fails (non-zero exit, or output contains `rejected` / `protected` / `permission`): proceed to PF4.

### PF4 — PR fallback

The direct push failed. Reset the commit and create a dedicated branch + PR instead:

```bash
cd "$repo_root"
git reset HEAD~1                        # undo the commit, keep the file staged
git stash                               # stash .claude-vault changes
git fetch origin main
git checkout -b chore/add-claude-vault origin/main
git stash pop
git add .claude-vault
git commit -m "chore: add .claude-vault for study skill vault integration"
git push -u origin chore/add-claude-vault 2>&1
```

Then open a PR:

```bash
gh pr create \
  --title "chore: add .claude-vault for study skill vault integration" \
  --body "$(cat <<'EOF'
## Summary

- Adds `.claude-vault` pointing at the shared research vault so the `/study` skill can publish findings to the team Obsidian vault.

## Why

The `/study` skill pre-flight detected that `.claude-vault` was missing. This PR adds it so future sessions can publish directly without prompting.

## Vault

`<vault_url>`
EOF
)" \
  --base main 2>&1
```

Inform the user:
> Could not push `.claude-vault` directly to `<branch>`. Opened a PR instead: `<pr_url>`
>
> Proceeding with vault publishing for this session using the local file.

Then return to Step 1 in `SKILL.md` — the local `.claude-vault` file is present and will be picked up by Step 5 even if the PR has not yet merged.
