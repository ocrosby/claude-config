# GitHub Actions Node-Version Deprecation Audit

Check every third-party action referenced in `.github/workflows/*.yml` for the Node-20-on-GitHub-Actions-runners deprecation (https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/) and propose version bumps for the ones a newer release already fixes.

This is distinct from `check_workflows.py` (wired into `/code review`), which checks this repo's own Go-flavored workflow authoring conventions, and from `check_action_yml.py`, which checks `action.yml` files this repo publishes. Neither touches the Node runtime of *consumed* third-party actions — that is what this subcommand covers, in any repository.

## Workflow

### 1. Extract every third-party action reference

```bash
python3 ~/.claude/scripts/extract_workflow_actions.py .github/workflows --json
```

If no workflow files exist: report "no `.github/workflows/*.yml` found" and stop.

### 2. Check each unique action's Node runtime

For each `{repo, ref, locations}` entry from step 1:

1. Fetch the pinned version's action definition: `https://raw.githubusercontent.com/<repo>/<ref>/action.yml` (fall back to `action.yaml` on 404).
2. Read the `runs.using` field.
   - `composite` or `docker` → not affected. Skip this entry, no finding.
   - `node16` or `node20` → deprecated. Continue to step 3.
   - `node24` (or later) → already fixed. Skip this entry, no finding.
3. Fetch the action's latest release tag (`gh api repos/<repo>/releases/latest --jq .tag_name` if `gh` is available, otherwise `https://api.github.com/repos/<repo>/releases/latest`), then fetch that tag's `action.yml` the same way as step 1 to read its `runs.using`.

### 3. Classify each deprecated entry

Per `rules/findings-format.md`:

- **Should Fix** — pinned ref uses `node16`/`node20` AND the latest release uses `node24` (or is composite/docker). The action is already fixed upstream; only the pin is stale. **Fix:** bump every location's `@<ref>` to the latest release tag.
- **Consider** — pinned ref uses `node16`/`node20` AND the latest release still does too. No upstream fix exists yet. **Fix:** none available; note the action's repo so it can be watched, and list an alternative action if one is known.

Do not emit a finding for entries already on `node24`, composite, or docker — that is correct as-is, not something to report.

### 4. Report

Group findings by bucket, most-impactful first, using the shape from `rules/findings-format.md`. Each finding's location is every `file:line` in that entry's `locations` list.

### 5. Apply fixes

**If the user does not confirm applying fixes: stop and do not proceed past step 4.**

For each **Should Fix** finding, edit every listed location to replace `@<old-ref>` with `@<latest-tag>`. Do not touch **Consider** entries — there is no fix to apply.

### 6. Verify

Confirm every `{repo, ref}` entry returned by step 1 is accounted for in the final report — either as a Should Fix or Consider finding, or explicitly resolved as already on `node24`, composite, or docker. If fixes were applied in step 5, re-run step 1's extraction script and confirm none of the old, bumped refs still appear.

## Rules

- Never guess an action's Node runtime from its name or popularity — always read the actual `action.yml`.
- Never bump a version pin without having verified via step 2 that the target tag actually declares a newer `runs.using`.
- If `action.yml` cannot be fetched (private repo, network unavailable, action deleted), report the entry as **Consider** with "could not verify — check manually" rather than guessing.
