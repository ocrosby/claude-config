# Rapidly generating coloring books

End-to-end guide for producing printable coloring books with the `/image-book` skill. One short command designs the scenes, generates every page, downloads the images into a per-book folder, combines them into a PDF, and opens it. Supports toddler through adult tiers; multiple books stay cleanly separated under one parent directory.

Audience: anyone with the Claude Code CLI, the Everygen MCP server connected, and ImageMagick installed.

## What ships end-to-end

| Component | Purpose | Lives in |
|---|---|---|
| `/image-book create <theme>` | Full pipeline: scene design → Everygen batch generation → sorted-filename download → PDF combine → open | `skills/image-book/SKILL.md` |
| `/image-book combine <folder>` | Just the combine-and-open step for a folder of existing images | same skill |
| `rules/everygen-image-conventions.md` | Single source of truth for paper-size → aspect ratio, resolution, credit cost per model, batch-sizing math, and reusable style packs with age-tier tables | `rules/` |
| `skills/image-book/slugify.sh` | Normalize an arbitrary string to lowercase snake_case for file names | — |
| `skills/image-book/open_and_verify.sh` | OS-aware PDF opener + non-empty verification + page count | — |

See `skills/README.md` under **Standalone primitives** for `/image-book`'s one-line entry.

## Prerequisites

Run each of these once. All of them (except ImageMagick) are typically already in place.

| Tool | Check | Install if missing |
|---|---|---|
| ImageMagick | `command -v magick` | `brew install imagemagick` on macOS, `sudo apt install imagemagick` on Debian/Ubuntu |
| Everygen MCP server | A message mentioning `generate_image_batch` is reachable | Configure via `claude mcp add` per the Everygen docs |
| Claude Code CLI | `claude --version` | https://claude.com/claude-code |

The skill pre-flights ImageMagick and the Everygen tool before any credits are spent. If either is missing it stops with a clear install hint rather than failing midway.

## Quick start — one book end-to-end

```
/image-book create fairy coloring book
```

The skill then asks four short questions:

1. **Interior page count** — default `15`. Max comes from the batch-sizing table in `rules/everygen-image-conventions.md` (currently 47).
2. **Style pack** — default `coloring-book`.
3. **Age tier** — `toddler` (2-5), `kid` (6-9), `tween` (10-13), or `adult` (14+). Default `kid`.
4. **Paper size** — default `8.5x11`.
5. **Output directory** — default `~/Downloads/image-books/<slug>/`.

After the preview of all N+1 scenes and the credit-cost estimate, you confirm and the pipeline runs. Expect under one wall-clock minute for a 16-image book (two 8-image batches in parallel).

The result:

```
~/Downloads/image-books/fairy_coloring_book/
├── 00-cover.jpg
├── 01-fairy-house-toadstool.jpg
├── 02-fairy-on-daisy.jpg
├── 03-three-mushroom-houses.jpg
├── ...
├── 15-magical-fairy-tree.jpg
└── fairy_coloring_book.pdf    ← also opens automatically
```

## Picking the right age tier

The four age tiers produce visibly different pages. Each tier parameterizes line thickness, shape complexity, and tonal maturity. Pick the one that matches your audience; never mix tiers in one book.

| Tier | Ages | Interior | Cover |
|---|---|---|---|
| `toddler` | 2-5 | Very thick outlines, huge simple shapes, 1-2 hero objects, kawaii, no scary elements | Primary colors, chunky bold outlines, happy faces |
| `kid` | 6-9 | Thick bold outlines, large shapes, 2-4 objects per scene, kawaii cartoon | Bright pastels, whimsical cartoon letters |
| `tween` | 10-13 | Medium outlines, moderate detail, pattern accents, 3-6 elements | Vibrant palette with contrasting accents |
| `adult` | 14+ | Fine line art, intricate patterns, mandalas, zentangle fill motifs | Jewel tones, elegant serif/script typography |

The source of truth is the age-tier table inside `rules/everygen-image-conventions.md` — update that file to tune tier definitions globally.

## Running multiple books

Every book lands under `~/Downloads/image-books/<slug>/`. The per-book folder contains both the images and the final PDF, so each book is a single self-contained unit.

```
~/Downloads/image-books/
├── fairy_coloring_book/
│   ├── 00-cover.jpg
│   ├── 01-fairy-house-toadstool.jpg
│   ├── ...
│   └── fairy_coloring_book.pdf
├── dinosaur_coloring_book_adult/
│   ├── 00-cover.jpg
│   ├── 01-anatomical-triceratops.jpg
│   ├── ...
│   └── dinosaur_coloring_book_adult.pdf
└── space_adventure_tween/
    ├── 00-cover.jpg
    ├── ...
    └── space_adventure_tween.pdf
```

A slug suffix like `_adult` or `_tween` is a useful convention when you plan to produce the same theme across tiers — the skill will not add tier suffixes automatically, so include the tier in the theme string if you want it reflected in the folder name.

## Iterating on a single page

If one page comes back wrong (wrong composition, too busy, drifted into color), regenerate just that image and re-combine:

1. **Regenerate the single image** using the Everygen `generate_image` tool with the same style-pack template substituted, plus a tightened scene description.
2. **Overwrite the file at the same path** (e.g. `~/Downloads/image-books/fairy_coloring_book/07-ladybug-on-daisy.jpg`).
3. **Re-combine via the `combine` subcommand:**
   ```
   /image-book combine ~/Downloads/image-books/fairy_coloring_book
   ```
   This re-reads every image file in the folder (sorted by filename, so the 2-digit prefix preserves page order), rebuilds the PDF *in place*, and opens it. The pre-existing PDF is overwritten.

The 2-digit prefix is why this works — as long as every file keeps its `NN-...` prefix, the sort order remains correct regardless of how many pages you regenerated.

## Adding a new style pack

Coloring books aren't the only output shape. The skill is pack-driven, so adding a workbook, a sticker sheet, or a recipe card is additive and requires zero skill changes.

1. Open `rules/everygen-image-conventions.md`.
2. Under the **Style packs** section, add a new `### <pack-name> — ...` subsection with both an interior template and a cover template (or a single template if the product has no cover). Follow the exact phrasing conventions of the existing packs — the negative prompts (`no color`, `no shading`) are load-bearing against the model's defaults.
3. If the pack needs age tiers, add an age-tier table analogous to the `coloring-book` one, keyed on the same `AGE_RANGE` / `INTERIOR_STYLE` placeholders.
4. The skill's step 3 will auto-discover the new pack headings; step 4's `AskUserQuestion` offers it as a style-pack choice.

No code change required — the pack is a prompt template, and the skill is a template consumer.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Skill stops at step 2 with "ImageMagick is missing" | `magick` not on `PATH` | `brew install imagemagick` (macOS) or `sudo apt install imagemagick` (Debian/Ubuntu) |
| Skill stops at step 2 with "Everygen tool unavailable" | MCP server not loaded in this session | Reconnect via `claude mcp` or restart Claude Code |
| Pages come back with color despite "coloring book" style | Likely the style-pack template was shortened or paraphrased | Verify the exact pack prompt in `rules/everygen-image-conventions.md` — the "no color, no shading, no grayscale, no gray fills" phrasing is load-bearing |
| Pages drift away from the age tier (e.g. toddler-tier scene has fine detail) | The AGE_RANGE / INTERIOR_STYLE substitution did not apply | Check the age-tier row the skill resolved; the tier table in the rule file is authoritative |
| Count check fails after download: "N+1 expected, got fewer" | A `curl` request errored silently | Re-run `/image-book create <same theme>`; the failed URL will be re-fetched. The pre-combine count check is what prevents a short PDF from being produced |
| Book comes out upside-down or sideways | Wrong aspect ratio for the paper | Check `rules/everygen-image-conventions.md` paper-size table; 8.5×11 portrait is `3:4`, not `9:16` |

## Costs and limits

Per the current rate card in `rules/everygen-image-conventions.md`:

- Nano Banana 2 (default) — 2 credits per image.
- A standard 16-image book (cover + 15 pages) at 2K portrait costs 32 credits and completes in two 8-image parallel batches.
- Hard upper bound: 48 total images per invocation (6 batches of 8). For larger books, run the skill twice and merge the resulting folders before `combine`.

The skill always prints an estimated credit total before any generation call and waits for your confirmation.

## Where things live

- Skill: `skills/image-book/SKILL.md`
- Rule / style packs / age tiers: `rules/everygen-image-conventions.md`
- Helpers: `skills/image-book/slugify.sh`, `skills/image-book/open_and_verify.sh`
- Default output root: `~/Downloads/image-books/`
- This doc: `docs/coloring-books.md`
