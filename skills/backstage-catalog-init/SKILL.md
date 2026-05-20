---
description: Creates a catalog-info.yaml Backstage component descriptor for a repo that does not already have one. Infers name, type, lifecycle, and GitHub slug from the repo; prompts for owner and system when they cannot be determined automatically.
triggers:
  - /backstage-catalog-init
  - /backstage-init
---

# Backstage Catalog Init

## When to use

Invoke `/backstage-catalog-init` when a repository does not yet have a `catalog-info.yaml` and needs to be registered in the Backstage software catalog for the first time.

## When NOT to use

- The repo already has a `catalog-info.yaml` — edit the existing file instead.
- You need to register a multi-component repo with more than one `kind: Component` — this skill creates a single descriptor; extend it manually after running.

---

## Workflow

### 1. Check for an existing descriptor

```bash
test -f catalog-info.yaml && echo "EXISTS" || echo "MISSING"
```

If the file exists, **stop and do not proceed.** Tell the user the file already exists and show its current contents with `cat catalog-info.yaml`.

---

### 2. Gather repo identity

Run all of these in parallel:

```bash
# GitHub slug (org/repo)
git remote get-url origin \
  | sed 's|.*github\.com[:/]\(.*\)\.git|\1|; s|.*github\.com[:/]\(.*\)|\1|'

# Repo name only (last path segment, no .git)
basename "$(git rev-parse --show-toplevel)"

# Default branch
git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null \
  | sed 's|.*/||'
```

If `git remote get-url origin` fails, **stop and do not proceed.** Tell the user the repo must have a GitHub remote configured before this skill can run.

Store:
- `SLUG` — the `org/repo` string (e.g. `TheWeatherCompany/sun-ms-gateway-acceptance-tests`)
- `REPO_NAME` — the bare repo name (e.g. `sun-ms-gateway-acceptance-tests`)
- `BRANCH` — default branch; fall back to `main` if the command produces no output

---

### 3. Infer description

Always check these sources in order; use the first non-empty result:

1. `description` field in `pyproject.toml`:
   ```bash
   python3 -c "
   import tomllib, pathlib
   p = pathlib.Path('pyproject.toml')
   if p.exists():
       d = tomllib.loads(p.read_text())
       print(d.get('project', {}).get('description', ''))
   "
   ```
2. First non-empty paragraph after the `# <title>` heading in `README.md` (read the file, extract lines 2–10).
3. If neither yields a description, derive one from the repo name using this exact rule: strip a leading `sun-ms-` or `sun-` prefix, expand remaining hyphens to spaces, capitalize the first word, and append a period. Then frame it as a sentence. For example: `sun-ms-gateway-acceptance-tests` → strip `sun-ms-` → `gateway acceptance tests` → `"Acceptance tests for the gateway service."`. For `sun-qa-python-tools` → strip `sun-` → `qa python tools` → `"QA Python tools library."`

---

### 4. Infer component type

Always examine the repo layout using the table below to determine `type`. Apply the first row whose signal matches:

| Signal | `type` value |
|---|---|
| `features/` directory with `.feature` files, OR `tests/bdd/`, OR `pytest.ini` with `bdd` marker | `test-suite` |
| `src/` with `main.py` importing FastAPI / FastMCP, OR `cmd/` directory with a `main.go` | `service` |
| Primary entrypoint is a CLI (`click`, `cobra`, `argparse`), OR repo name contains `-cli` or `-tool` | `tool` |
| `charts/` directory with Helm charts, OR repo is purely infrastructure config | `infrastructure` |
| None of the above | `service` |

---

### 5. Infer lifecycle

| Signal | `lifecycle` |
|---|---|
| Repo name contains `-experimental`, `-poc`, `-spike`, `-demo`, or `-sandbox` | `experimental` |
| `pyproject.toml` classifier `"Development Status :: 5 - Production/Stable"` is present | `production` |
| Default branch is `main` or `master` and none of the experimental signals apply | `production` |
| Otherwise | `experimental` |

---

### 6. Determine owner

Always check these sources in order:

1. `CODEOWNERS` file (`.github/CODEOWNERS` or `CODEOWNERS`):
   ```bash
   cat .github/CODEOWNERS 2>/dev/null || cat CODEOWNERS 2>/dev/null
   ```
   If a `*` catch-all line exists, extract the team slug (e.g. `@TheWeatherCompany/qa-engineering` → `qa-engineering`).

2. Existing `catalog-info.yaml` files in sibling repos under the same parent directory:
   ```bash
   grep -r "owner:" ../*/catalog-info.yaml 2>/dev/null | head -5
   ```
   If a consistent owner appears, propose it to the user and wait for confirmation before using it.

3. If neither source yields an owner, ask the user:
   > "What Backstage group should own this component? (e.g. `qa-engineering`, `platform-engineering`)"

   Never guess. **Stop and do not proceed** without a confirmed owner.

---

### 7. Determine system

Always check these sources in order:

1. Existing `catalog-info.yaml` files in sibling repos:
   ```bash
   grep -r "system:" ../*/catalog-info.yaml 2>/dev/null | head -5
   ```
   If a consistent system appears, propose it to the user and wait for confirmation.

2. Infer from the repo name prefix:
   - `sun-ms-*` or `sun-*` → propose `weather-infrastructure`
   - No recognizable prefix → ask the user

3. If inference is ambiguous, ask:
   > "Which Backstage system does this component belong to? (e.g. `weather-infrastructure`)"

---

### 8. Write the file

Construct `catalog-info.yaml` using the gathered values and write it to the repo root:

```yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: <REPO_NAME>
  title: <human-readable title — expand hyphens, title-case each word>
  description: <description from step 3>
  annotations:
    github.com/project-slug: <SLUG>
    backstage.io/managed-by-location: url:https://github.com/<SLUG>/blob/<BRANCH>/catalog-info.yaml
    backstage.io/managed-by-origin-location: url:https://github.com/<SLUG>/blob/<BRANCH>/catalog-info.yaml
spec:
  type: <type from step 4>
  lifecycle: <lifecycle from step 5>
  owner: <owner from step 6>
  system: <system from step 7>
```

---

### 9. Verify the written file

Run `cat catalog-info.yaml` and confirm all of the following fields are present and non-empty:

- `metadata.name`
- `metadata.annotations["github.com/project-slug"]` — must be `org/repo` format, no `.git` suffix
- `spec.type`
- `spec.lifecycle`
- `spec.owner`
- `spec.system`

If any field is missing or empty, **stop and do not proceed.** Correct the value before continuing.

---

### 10. Confirm and commit

Print the file contents. Then ask the user:

> "Ready to commit this as `chore: add Backstage catalog-info.yaml`? (yes / edit first)"

- If the user confirms: stage and commit:
  ```bash
  git add catalog-info.yaml
  git commit -m "chore: add Backstage catalog-info.yaml"
  git push
  ```
  If the push fails, **stop.** Tell the user: "The commit was created locally but the push failed. Run `git push` manually and verify before importing the catalog URL."
- If the user wants to edit: show the file and wait. Do not commit until they confirm.

---

### 11. Print the import URL

After a successful push, output:

```
Register this component in Backstage by importing:
https://github.com/<SLUG>/blob/<BRANCH>/catalog-info.yaml
```
