---
description: Use when the user wants to turn an image-book output directory into KDP-ready paperback PDFs (interior.pdf + cover spread + normalized metadata).
when_to_use: "prepare for KDP", "KDP compose", "turn this book into KDP files", "make the interior PDF", "build the cover spread".
argument-hint: "<subcommand> [arguments]"
# Side effects outside repo: writes PDFs into the target directory.
disable-model-invocation: true
allowed-tools: Read, Write, Bash
---

# KDP: Kindle Direct Publishing Pipeline

Use this skill when the user asks to prepare a generated image book for Kindle Direct Publishing. Current scope is phase 1: compose print-ready `interior.pdf`, `cover.pdf`, and `metadata.json` from an `/image-book` output directory and a `book.yaml`. Phase 2 (browser-driven KDP upload) is **not yet implemented** — this skill never pushes to KDP.

**Never upload, commit, or share any generated file.** Output stays in the target directory only. The user is responsible for the final Publish click on KDP.

## When NOT to use

- The user wants to generate the images themselves — call `/image-book create` first; this skill assumes the images already exist.
- The user wants a Kindle eBook (`.epub`/`.mobi`) rather than a paperback. This skill handles paperback PDFs only.
- The user wants to upload to KDP automatically. Phase 2 is not shipped — stop and tell the user.

## Usage

```
/kdp                                 # show this help
/kdp compose <image-dir>             # build interior.pdf, cover.pdf, metadata.json
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
- `sub` not `compose` → print **Usage** and stop.
- `sub` = `compose` → continue to step 2.

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

5. **Report.** Print the three output paths, the interior page count, and the computed spine width from `metadata.json`. Remind the user that the cover is a plain template — they may replace `cover.pdf` with a hand-designed spread before upload. Phase 2 (KDP upload automation) is not yet implemented; the user must upload manually.

## Exceptions

- **Page count below KDP minimum (24)** — the composer still writes `interior.pdf` but emits a stderr warning. Surface the warning and advise the user to add filler pages (title page, copyright, blank spacers) before uploading, since KDP will reject the file otherwise.
- **DPI preflight below 300** — the composer warns per image. Pass the warning through; do not re-run. The user generated the images at a lower resolution and must decide whether to regenerate or accept.
- **User asks to upload to KDP after compose completes** — phase 2 is not shipped. Stop and tell the user: `KDP upload automation is phase 2 and not yet implemented. Upload interior.pdf and cover.pdf manually via https://kdp.amazon.com/ for now.` Do not attempt to script the upload with ad-hoc Playwright or other automation.
