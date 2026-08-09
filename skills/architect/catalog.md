# Backstage Catalog Registration

Detailed workflow for the `/architect catalog` subcommand. Creates a `catalog-info.yaml` Backstage descriptor for a repo that does not yet have one. **This subcommand commits and pushes to remote.**

## Workflow

1. **Check for an existing descriptor.**
   ```bash
   test -f catalog-info.yaml && echo "EXISTS" || echo "MISSING"
   ```
   **If the file exists: stop and do not proceed.** Show its current contents.

2. **Run the inference script.**
   ```bash
   python3 ~/.claude/scripts/backstage_infer.py
   ```
   Emits JSON with: `slug`, `repo_name`, `branch`, `title`, `description`, `type`, `lifecycle`, `owner_candidates`, `system_candidates`, `errors`. Each candidate carries a `source` field (CODEOWNERS, sibling catalog, name-prefix).

   **If `errors` is non-empty: stop and do not proceed.** Surface the error.

3. **Resolve owner.**
   - All `owner_candidates` agree → use that value, tell user where it came from.
   - Candidates differ → present every candidate and source, ask which to use.
   - Empty → ask: "What Backstage group should own this component? (e.g. `qa-engineering`, `platform-engineering`)". **Do not guess. Do not proceed without confirmed owner.**

4. **Resolve system.**
   - All `system_candidates` agree → propose, wait for explicit confirmation.
   - Multiple or none → ask: "Which Backstage system does this component belong to? (e.g. `weather-infrastructure`)". Wait for explicit answer.

5. **Write the file** using script's values + resolved owner and system:
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

6. **Verify the written file.** `cat catalog-info.yaml`. Confirm every field is present and non-empty:
   - `metadata.name`
   - `metadata.annotations["github.com/project-slug"]` — must be `org/repo` format, no `.git` suffix
   - `spec.type`, `spec.lifecycle`, `spec.owner`, `spec.system`

   **If any field is missing or empty: stop and do not proceed.**

7. **Confirm and commit.** Print the file contents, ask: "Ready to commit this as `chore: add Backstage catalog-info.yaml`? (yes / edit first)".

   - **yes** → stage, commit, push:
     ```bash
     git add catalog-info.yaml
     git commit -m "chore: add Backstage catalog-info.yaml"
     git push
     ```
     **If `git push` fails: stop.** Tell the user the commit is local-only and they must push manually before importing.

   - **edit first** → show the file and wait. Do not commit until confirmed.

8. **Print the import URL** after a successful push:
   ```
   Register this component in Backstage by importing:
   https://github.com/<slug>/blob/<branch>/catalog-info.yaml
   ```
