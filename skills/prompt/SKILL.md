---
description: Use when adding a new reusable prompt to the `prompts/` directory. Scaffolds `prompts/<slug>.md` from a template and inserts an index bullet into `prompts/README.md`.
when_to_use: User says "add a prompt", "create a new prompt", "scaffold a prompt file", "add a reusable prompt", or asks to put a prompt body under `prompts/` for later paste-in.
argument-hint: "new <slug>"
allowed-tools: Read, Edit, Write, Bash
---

# Prompt: Reusable-Prompt Scaffolder

Use this skill when the user asks to add a new reusable prompt to the `prompts/` library so the file scaffold and the README index entry stay consistent across prompts.

## When NOT to use

- The user wants to run a prompt, not create one → paste the prompt body directly; this skill writes files, it does not execute them.
- The repo has no top-level `prompts/` directory → this skill is specific to repos that keep a reusable prompt library there (e.g. `ocrosby/claude-config`). Stop and tell the user.
- Editing an existing prompt → use `Edit` on the file directly. This skill creates new files only.

## Usage

```
/prompt                             # show this help
/prompt new <slug>                  # scaffold prompts/<slug>.md + update prompts/README.md
```

`<slug>` must be lowercase, snake_case, no `.md` suffix — e.g. `fairy_coloring_book`, `personal_data_removal`. The scaffold matches the shape of existing files in `prompts/`.

## Workflow

### 1. Parse the subcommand

Run:

```bash
sub="${ARGUMENTS%% *}"
rest="${ARGUMENTS#* }"
```

- `sub` empty or `help` → print **Usage** and stop.
- `sub` not `new` → print **Usage** and stop.
- `sub` is `new` and `rest` is empty or equals `$sub` → stop and ask the user for a slug via `AskUserQuestion`. Do not fabricate a slug.
- Otherwise `slug="$rest"` and dispatch to **Dispatch — `new`**.

### 2. Dispatch — `new`

1. **Normalize the slug.** Lowercase; replace spaces, hyphens, and dots with underscores:

   ```bash
   slug=$(echo "$slug" | tr '[:upper:] -.' '[:lower:]___' | sed 's/_\{2,\}/_/g;s/^_//;s/_$//')
   ```

   **If the normalized slug differs from the input: tell the user both forms before continuing.** The user then confirms or supplies a different slug.

2. **Verify the repo shape.**
   ```bash
   test -d prompts && test -f prompts/README.md
   ```
   **If either is missing: stop and do not proceed.** Tell the user this repo has no `prompts/` library.

3. **Verify the target does not already exist.**
   ```bash
   test ! -e "prompts/${slug}.md"
   ```
   **If the file already exists: stop and do not proceed.** Report the path. Never overwrite.

4. **Read `prompts/README.md`** and extract existing section headers (lines matching `^## `). These are the valid section choices.

5. **Collect metadata via `AskUserQuestion`:**
   - **Title** — the H1 for the new file (human-readable, title-case).
   - **Lede** — one sentence describing what the prompt does, used both as the file's lede paragraph and the README bullet description.
   - **Section** — pick an existing section from step 4, or type a new section name. Default position for a new section is append-to-end-of-file. Never ask the user for section position unless the user explicitly requests non-default placement.

   **If the user does not provide Title, Lede, or Section: stop and do not proceed.** Never fabricate titles, ledes, or section names.

6. **Collect the body via a separate `AskUserQuestion` call.** Prompt text:

   > Paste the prompt body — the exact text that gets pasted into a session when the prompt is used.

   **If the body is empty: stop and do not proceed.**

7. **Write `prompts/<slug>.md`** by reading the template at `skills/prompt/assets/prompt_template.md` and substituting the placeholders `<Title>`, `<Lede>`, and `<Body>` with the user-supplied values. Never apply typo correction or reformatting to the body. Preserve the user's body verbatim.

8. **Update `prompts/README.md`** using the templates at `skills/prompt/assets/readme_entries.md`:
   - Section exists → insert the "existing section" bullet after the last bullet under that `## <Section>` heading, before the next `## ` heading (or EOF).
   - Section is new → append the "new section" block at EOF.

   Substitute `<Title>`, `<Section>`, `<slug>`, and `<Lede>` with the user-supplied values exactly as entered.

9. **Verify.** Read both files back and confirm:
   - `prompts/<slug>.md` exists and contains the title, lede, and body.
   - `prompts/README.md` contains exactly one new bullet pointing at `<slug>.md`.
   - If a new section was added, exactly one new `## <Section>` heading is present.

   **If any check fails: stop and do not proceed.** Report which check failed. Never retry — tell the user so they can decide.

10. **Report.** Print the two file paths and a one-line summary. Never commit — committing is the user's call via `/git ship` or an explicit instruction.

## Exceptions

- **Non-canonical slug input** — if the user supplies `fairy-coloring-book`, `Fairy Coloring Book`, `fairy.coloring.book`, or `FairyColoringBook`, normalize to `fairy_coloring_book` (per step 2.1) and tell the user both forms. Existing files in `prompts/` use snake_case uniformly.
- **Lede punctuation** — preserve exactly as the user wrote it. Never normalize trailing periods, dashes, or case.
