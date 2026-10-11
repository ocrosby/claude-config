---
description: Use when the user wants to turn an image-book output directory into KDP-ready paperback PDFs (compose), or pre-fill a KDP paperback draft in a headed browser (publish). Never clicks Publish.
when_to_use: "prepare for KDP", "KDP compose", "KDP publish", "upload this book to KDP", "pre-fill the KDP wizard", "turn this book into KDP files".
argument-hint: "<subcommand> [arguments]"
# Side effects outside repo: writes PDFs into the target directory; `publish` opens a Chrome window with a persistent profile at ~/.cache/kdp-automation/.
disable-model-invocation: true
allowed-tools: Read, Write, Bash
---

# KDP: Kindle Direct Publishing Pipeline

Use this skill when the user asks to prepare a generated image book for Kindle Direct Publishing. Two subcommands:

- `compose` — build print-ready `interior.pdf`, `cover.pdf`, and `metadata.json` from an `/image-book` output directory and a `book.yaml`.
- `publish` — open a persistent Chrome, verify login (`--dry-run`) or pre-fill a new paperback draft from `metadata.json` + the PDFs (`--draft`). **Never clicks Publish or Submit for Review** — the human reviews and submits.

**Never upload, commit, or share any generated file.** The `publish` subcommand uploads to KDP as a *draft* only; final publication is a human action in the opened browser window.

## When NOT to use

- The user wants to generate the images themselves — call `/image-book create` first; this skill assumes the images already exist.
- The user wants a Kindle eBook (`.epub`/`.mobi`) rather than a paperback. This skill handles paperback PDFs only.
- The user wants fully automated publishing (click Publish on their behalf). This skill never does that — Submit for Review is always a human action, by design.

## Usage

```
/kdp                                 # show this help
/kdp compose <image-dir>             # build interior.pdf, cover.pdf, metadata.json
/kdp publish <image-dir>             # pre-fill a new KDP paperback draft from the compose output
/kdp publish --dry-run               # open KDP, verify login, exit (first-run setup)
```

## Workflow

### 1. Parse the subcommand

Run:

```bash
sub="${ARGUMENTS%% *}"
rest="${ARGUMENTS#* }"
[ "$rest" = "$sub" ] && rest=""
```

- `sub` empty or `help` → print **Usage** and stop.
- `sub` not `compose` or `publish` → print **Usage** and stop.
- Dispatch to the matching step.

### 2. Dispatch — `compose`

**If `rest` is empty: stop and do not proceed.** Ask the user for the image directory path. Never fabricate a path.

1. **Verify the directory exists.**
   ```bash
   test -d "$rest"
   ```
   **If missing: stop and do not proceed.**

2. **Verify a `book.yaml` is present** (default location is `<image-dir>/book.yaml`).
   ```bash
   test -f "$rest/book.yaml"
   ```
   **If missing:** copy the template, open it for the user, then stop and ask them to fill it in before re-running:
   ```bash
   cp ~/.claude/skills/kdp/book.yaml.example "$rest/book.yaml"
   open "$rest/book.yaml" 2>/dev/null || true
   ```
   Report the path and the required fields (`title`, `author`, `trim_size`, `paper`).

3. **Run the composer.**
   ```bash
   ~/.claude/scripts/kdp_compose.py "$rest"
   ```
   The script writes `interior.pdf`, `cover.pdf`, and `metadata.json` into `<image-dir>` and prints a one-line summary for each. Any DPI preflight advisories or page-count warnings are emitted to stderr — surface them verbatim to the user.

   **If the script exits non-zero: stop and do not proceed.** Report the exact stderr line so the user can fix the metadata or page count.

4. **Open the PDFs for inspection.**
   ```bash
   open "$rest/interior.pdf" "$rest/cover.pdf" 2>/dev/null || true
   ```

5. **Report.** Print the three output paths, the interior page count, and the computed spine width from `metadata.json`. Remind the user that the cover is a plain template — they may replace `cover.pdf` with a hand-designed spread before upload. Suggest `/kdp publish <image-dir>` as the next step once the PDFs look right.

### 3. Dispatch — `publish`

**If `rest` is empty: stop and do not proceed.** Ask the user for the directory path. For `--dry-run` the directory is optional; everything else requires one.

1. **Pre-flight Playwright.**
   ```bash
   python3 -c 'import playwright' 2>/dev/null
   ```
   **If missing:** print `uv tool install playwright && playwright install chromium`, then stop and ask the user to install before re-running.

2. **Decide the mode.** Default is `--dry-run`. If the user said "pre-fill", "fill the wizard", "create the draft", "upload to KDP as a draft", pass `--draft`.

3. **Run the publisher.**
   ```bash
   ~/.claude/scripts/kdp_publish.py --dry-run                   # verify login
   ~/.claude/scripts/kdp_publish.py --draft "$rest"             # pre-fill a new draft
   ```
   The script launches headed Chrome with a persistent profile at `~/.cache/kdp-automation/chrome-profile/`. On first run the user logs in manually (including 2FA); subsequent runs reuse the login.

   **If the script exits non-zero:** surface the exact stderr line. Exit code 2 usually means "not logged in" — re-run with `--dry-run` and complete login. Exit code 3 means "wizard entry selectors drifted" — the user must inspect KDP's current UI and update the `SELECTORS` block in `scripts/kdp_publish.py`.

4. **Report.** State explicitly: `the script stops before Submit for Review. Review every field, upload categories and pricing manually, then click Submit for Review in the opened browser.` Do not claim the book was published.

## Exceptions

- **Page count below KDP minimum (24)** — the composer still writes `interior.pdf` but emits a stderr warning. Surface the warning and advise the user to add filler pages (title page, copyright, blank spacers) before uploading, since KDP will reject the file otherwise.
- **DPI preflight below 300** — the composer warns per image. Pass the warning through; do not re-run. The user generated the images at a lower resolution and must decide whether to regenerate or accept.
- **`publish` with no prior `compose`** — the publisher reads `metadata.json`, `interior.pdf`, and `cover.pdf` from the directory. If any are missing: stop, and tell the user to run `/kdp compose <image-dir>` first.
- **Selectors drifted and `--draft` hits a timeout or exit code 3** — KDP changed the UI. Stop; do not retry the same command. Direct the user to `scripts/kdp_publish.py`'s `SELECTORS` block and ask them to tune the one that failed before re-running.
- **User asks the script to click Publish or Submit for Review** — refuse. Submit for Review is always a human action because KDP ToS restricts automated access and account flags are permanent. Explain this and leave the submission to the user in the opened browser.
