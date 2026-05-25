---
description: Creates a catalog-info.yaml Backstage component descriptor for a repo that does not already have one. Infers name, type, lifecycle, and GitHub slug from the repo; prompts for owner and system when they cannot be determined automatically.
aliases: backstage-init
# Human gate: this skill commits and pushes to remote. Block model auto-invocation.
disable-model-invocation: true
---

# Backstage Catalog Init

Use this skill when a repository does not yet have a `catalog-info.yaml` and needs to be registered in the Backstage software catalog for the first time. Deterministic inference (CODEOWNERS, pyproject, sibling catalogs) lives in `scripts/backstage_infer.py`; this skill orchestrates.

## When NOT to use

- The repo already has a `catalog-info.yaml` — edit the existing file instead.
- The repo registers more than one `kind: Component` — this skill creates a single descriptor.

## Workflow

### 1. Check for an existing descriptor

```bash
test -f catalog-info.yaml && echo "EXISTS" || echo "MISSING"
```

**If the file exists: stop and do not proceed.** Show its current contents with `cat catalog-info.yaml`.

### 2. Run the inference script

```bash
python3 ~/.claude/scripts/backstage_infer.py
```

The script emits JSON with: `slug`, `repo_name`, `branch`, `title`, `description`, `type`, `lifecycle`, `owner_candidates`, `system_candidates`, and `errors`. Owner and system candidates each carry a `source` field explaining where the suggestion came from (CODEOWNERS, sibling catalog, name-prefix).

**If `errors` contains "no origin remote configured" or any other non-empty entry: stop and do not proceed.** Surface the error to the user before continuing.

### 3. Resolve owner

- If `owner_candidates` is non-empty and all entries agree on a value: use that value and tell the user where it came from (e.g. "owner inferred from `.github/CODEOWNERS`").
- If `owner_candidates` is non-empty but values differ: present every candidate and its source, then ask which one to use. Wait for an explicit answer.
- If `owner_candidates` is empty: ask the user, "What Backstage group should own this component? (e.g. `qa-engineering`, `platform-engineering`)". **Do not guess. Do not proceed without a confirmed owner.**

### 4. Resolve system

- If `system_candidates` is non-empty and all entries agree on a value: propose it and wait for explicit confirmation.
- If multiple candidates exist or none does: ask the user, "Which Backstage system does this component belong to? (e.g. `weather-infrastructure`)". Wait for an explicit answer.

### 5. Write the file

Construct `catalog-info.yaml` using the script's `slug`, `repo_name`, `branch`, `title`, `description`, `type`, `lifecycle`, plus the resolved owner and system from steps 3–4. Write to the repo root:

```yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: <repo_name>
  title: <title>
  description: <description>
  annotations:
    github.com/project-slug: <slug>
    backstage.io/managed-by-location: url:https://github.com/<slug>/blob/<branch>/catalog-info.yaml
    backstage.io/managed-by-origin-location: url:https://github.com/<slug>/blob/<branch>/catalog-info.yaml
spec:
  type: <type>
  lifecycle: <lifecycle>
  owner: <owner>
  system: <system>
```

### 6. Verify the written file

Run `cat catalog-info.yaml` and confirm every field is present and non-empty:

- `metadata.name`
- `metadata.annotations["github.com/project-slug"]` — must be `org/repo` format, no `.git` suffix
- `spec.type`, `spec.lifecycle`, `spec.owner`, `spec.system`

**If any field is missing or empty: stop and do not proceed.** Correct the value before continuing.

### 7. Confirm and commit

Print the file contents and ask: "Ready to commit this as `chore: add Backstage catalog-info.yaml`? (yes / edit first)".

- **yes**: stage, commit, push:

  ```bash
  git add catalog-info.yaml
  git commit -m "chore: add Backstage catalog-info.yaml"
  git push
  ```

  **If `git push` fails: stop.** Tell the user the commit was created locally and they must push manually before importing the catalog URL.

- **edit first**: show the file and wait for the user to confirm. Do not commit until they say so.

### 8. Print the import URL

After a successful push:

```
Register this component in Backstage by importing:
https://github.com/<slug>/blob/<branch>/catalog-info.yaml
```

## Rules

- Never guess the owner or system. If the script cannot determine them, ask.
- Never overwrite an existing `catalog-info.yaml` — step 1 stops the skill.
- Never push a commit if the local commit succeeded but `git push` failed. Tell the user to push manually.
