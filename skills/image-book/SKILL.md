---
description: Use when the user asks for a printable image book (coloring book, workbook, sticker sheet) from a theme — full pipeline from scene design through PDF.
when_to_use: "make a coloring book", "generate a workbook", "create a sticker sheet", "image book about X", or any multi-page printable image set with a cover.
argument-hint: "<subcommand> [arguments]"
# Side effects outside repo: charges credits, writes ~/Downloads, opens desktop app.
disable-model-invocation: true
allowed-tools: Read, Write, Bash, ToolSearch
---

# Image Book: Printable Image Set Pipeline

Use this skill when the user explicitly asks for a multi-page printable image product (coloring book, workbook, sticker sheet) with a cover. Orchestrates scene design → Everygen batch generation → sorted-filename download → PDF combine → open. Style packs, aspect-ratio-for-paper, resolution, credit-cost-per-image, and batching math all live in `rules/everygen-image-conventions.md`; this skill applies them and never restates them.

**Never upload, commit, or share any generated file.** Output stays in `~/Downloads/<slug>` only. The user chooses whether to publish downstream.

## When NOT to use

- The user wants a single image, not a set — call `generate_image` directly; do not invoke this skill.
- The user wants a web-only image (social post, inline doc image) — this skill assumes printable output; use `generate_image` with the raw aspect ratio instead.
- The user already has images and only wants them combined into a PDF — jump to the `combine` subcommand.

## Usage

```
/image-book                                     # show this help
/image-book create <theme>                      # full pipeline: design → generate → download → PDF → open
/image-book combine <folder>                    # combine existing images in <folder> into a PDF and open
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
- `sub` not `create` or `combine` → print **Usage** and stop.
- Dispatch to the matching step.

### 2. Dispatch — `create`

**If `rest` is empty: stop and do not proceed.** Ask the user for a theme via `AskUserQuestion`. Never fabricate a theme.

1. **Normalize the theme into a slug** using the extracted helper:
   ```bash
   slug=$(bash ~/.claude/skills/image-book/slugify.sh "$rest")
   ```

2. **Pre-flight.**
   ```bash
   command -v magick >/dev/null
   ```
   **If ImageMagick is missing: stop and do not proceed.** Install hint: `brew install imagemagick` on macOS, `sudo apt install imagemagick` on Debian/Ubuntu.

   Confirm the Everygen batch tool is loaded. If not, call `ToolSearch` with `select:mcp__claude_ai_Everygen__generate_image_batch`. **If the tool is still unavailable: stop and do not proceed.**

3. **Read `rules/everygen-image-conventions.md` in full.** Extract:
   - The list of available style packs (every `### <pack-name> — ...` heading under the "Style packs" section).
   - The aspect-ratio table (paper size → `aspectRatio` enum).
   - The resolution table (resolution → use case).
   - The credit-cost table (model → credits per image).
   - The batch-sizing table (total images → batch plan).

   **If the file is missing: stop and do not proceed.**

   Compute the maximum interior page count from the batch-sizing table: `max_pages = (max_batch_size × max_sensible_batches) - 1`. The rule's current math is 8 × 6 - 1 = 47; always derive from the current table rather than hardcoding.

4. **Collect parameters via a single `AskUserQuestion` call** with these fields, drawing option lists from step 3:
   - **Interior page count** — default `15`. Valid range: 1 to `max_pages` computed in step 3.
   - **Style pack** — default `coloring-book`. Options are the pack headings extracted in step 3.
   - **Paper size** — default `8.5x11`. Options are the paper sizes in step 3's aspect-ratio table.
   - **Output directory** — default `~/Downloads/<slug>`.

5. **Resolve pack, aspect ratio, resolution, and credit cost** from the tables in step 3. Apply the matching values for the selected paper size and intended-print target. Never hardcode these values in this skill — the rule file is the single source of truth.

6. **Design the scene list.**
   - 1 cover scene — a one- to two-sentence scene featuring the hero elements of the theme. Pick a title based on the theme (e.g. theme `fairy coloring book` → title `My Magical Fairy Coloring Book`).
   - N interior scenes — each a one- to two-sentence scene variation on the theme, no two identical. Keep each scene concrete (name specific objects, actions, and spatial layout) so the model does not drift.

   Substitute each scene into the matching template from the pack extracted in step 3. The cover gets the cover template; interior pages get the interior template.

7. **Show the N+1 scenes to the user and confirm.** Print as a numbered list: `00. Cover — <cover scene>`, `01. <scene 1>`, …, `NN. <scene N>`. Always state the estimated cost: `(N+1) × <credits-per-image> credits = <total> credits`, using the credit-cost value resolved in step 5. **If the user declines: stop and do not proceed.**

8. **Generate using `generate_image_batch`.** Determine the batch plan from the step 3 batch-sizing table. Pass each prompt with the `aspectRatio` and `resolution` resolved in step 5. Never specify `model` — use the default (Nano Banana 2). Issue independent batches in parallel in the same message.

   **If the batch plan produces a final remainder of exactly 1 image:** load `generate_image` via `ToolSearch` and issue a single-image call for that one remainder. **If `generate_image` is also unavailable: stop and do not proceed.** Report the image count and the unavailable tool so the user can re-run with a different page count.

9. **Download each result to the output directory in a loop.**
   ```bash
   OUTDIR="${HOME}/Downloads/${slug}"   # or whatever step 4 produced
   mkdir -p "$OUTDIR"

   # Scenes and urls are two parallel arrays built from step 8's results,
   # index 0 is the cover, 1..N are interior pages.
   for i in "${!urls[@]}"; do
     scene_slug=$(bash ~/.claude/skills/image-book/slugify.sh "$(echo "${scenes[$i]}" | cut -d' ' -f1-4)")
     [ $i -eq 0 ] && scene_slug="cover"
     printf -v idx "%02d" "$i"
     curl -sS -o "$OUTDIR/${idx}-${scene_slug}.jpg" "${urls[$i]}"
   done
   ```
   The 2-digit prefix guarantees `*.jpg` globs expand in cover-first page order.

10. **Verify all N+1 downloads completed, counting only image files.**
    ```bash
    count=$(ls "$OUTDIR"/*.jpg "$OUTDIR"/*.png 2>/dev/null | wc -l | tr -d ' ')
    ```
    **If `count` does not equal N+1: stop and do not proceed.** Report which indices are missing (compare `ls $OUTDIR/*.jpg` against expected `00..NN`). Never proceed to combine with a short set — a partial PDF silently loses pages.

11. **Combine into a PDF alongside the output directory.** Detect which image types are present:
    ```bash
    has_jpg=$(ls "$OUTDIR"/*.jpg 2>/dev/null | head -1)
    has_png=$(ls "$OUTDIR"/*.png 2>/dev/null | head -1)
    ```
    Combine with a globally sorted file list so the 2-digit prefix order is preserved across mixed formats. Use an array (not an unquoted string) to survive filenames containing spaces:
    ```bash
    if [ -n "$has_jpg" ] && [ -n "$has_png" ]; then
      mapfile -t files < <(ls "$OUTDIR"/*.jpg "$OUTDIR"/*.png 2>/dev/null | sort)
      magick "${files[@]}" "${OUTDIR}.pdf"
    elif [ -n "$has_jpg" ]; then
      magick "$OUTDIR"/*.jpg "${OUTDIR}.pdf"
    else
      magick "$OUTDIR"/*.png "${OUTDIR}.pdf"
    fi
    ```

12. **Open and verify the PDF** via the extracted helper:
    ```bash
    bash ~/.claude/skills/image-book/open_and_verify.sh "${OUTDIR}.pdf"
    ```
    The helper exits non-zero if the file is missing, empty, or if `magick` is unavailable. **If it exits non-zero: stop and do not proceed.**

13. **Report.** Print the PDF path, image count, output directory, and total credits used.

### 3. Dispatch — `combine`

**If `rest` is empty: stop and do not proceed.** Ask the user for a folder path.

1. **Pre-flight ImageMagick.**
   ```bash
   command -v magick >/dev/null
   ```
   **If missing: stop and do not proceed.** Install hint: `brew install imagemagick` on macOS, `sudo apt install imagemagick` on Debian/Ubuntu.

2. **Verify the folder exists.**
   ```bash
   test -d "$rest"
   ```
   **If missing: stop and do not proceed.**

3. **Detect which image types are present.**
   ```bash
   has_jpg=$(ls "$rest"/*.jpg 2>/dev/null | head -1)
   has_png=$(ls "$rest"/*.png 2>/dev/null | head -1)
   ```
   **If both are empty: stop and do not proceed.** Report the empty folder.

4. **Derive the output PDF path alongside the folder.**
   ```bash
   base=$(basename "$rest")
   parent=$(dirname "$rest")
   out="${parent}/${base}.pdf"
   ```

5. **Combine with a globally sorted file list** so numeric prefixes order correctly across mixed formats. Use an array (not an unquoted string) to survive filenames containing spaces:
   ```bash
   if [ -n "$has_jpg" ] && [ -n "$has_png" ]; then
     mapfile -t files < <(ls "$rest"/*.jpg "$rest"/*.png 2>/dev/null | sort)
     magick "${files[@]}" "$out"
   elif [ -n "$has_jpg" ]; then
     magick "$rest"/*.jpg "$out"
   else
     magick "$rest"/*.png "$out"
   fi
   ```

6. **Open and verify** via the extracted helper:
   ```bash
   bash ~/.claude/skills/image-book/open_and_verify.sh "$out"
   ```
   **If it exits non-zero: stop and do not proceed.**

7. **Report.** Echo the helper's `OK:` line (contains the PDF path and page count).

## Exceptions

- **Theme that reads like a flag string** — if the user types `/image-book create generate a workbook for 2nd grade math with 20 pages`, treat the whole string after `create` as the theme and derive page count from the `AskUserQuestion` in step 4, not from the typed string. Never parse flags inside the theme — all parameters go through step 4.
- **Odd page count giving a 1-image final batch** — e.g. 17 total images (cover + 16 pages) produces batches of 8, 8, 1. The 1-image final batch cannot use `generate_image_batch` (minimum is 2, per `rules/everygen-image-conventions.md`). Fall back to a single `generate_image` call for that one remainder. **If `generate_image` is also unavailable: stop and do not proceed.** State this transition explicitly before step 8 runs.
- **Pack not in the rule file** — e.g. the user picks `space-adventure` and `rules/everygen-image-conventions.md` only defines `coloring-book`. Step 3 enumerates available packs; step 4's option list is drawn from that enumeration. **If the user's chosen pack is not present after step 3: stop and do not proceed.** Report the available packs and ask the user to either pick one or extend the rule file first.
