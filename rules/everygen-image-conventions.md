---
description: Conventions for Everygen image generation — aspect-ratio-to-paper-size mapping, resolution-to-use-case, batch sizing math, and reusable style packs (coloring-book line art, cover art) for printable image sets. Referenced by `/image-book`.
---

# Everygen Image Generation Conventions

Printable image sets fail for predictable reasons: wrong aspect ratio for the target paper, resolution picked by vibes instead of print size, repeated single-image calls when a batch would have been one request, prompt text that drifts between pages because it was re-derived each time. This rule names the choices once so every image set in this account looks consistent and the per-generation decision cost drops to zero.

Scope: applies when generating images via the Everygen MCP server (`mcp__claude_ai_Everygen__generate_image*`) for printed or paginated output. Social-only / screen-only generation uses raw aspect ratios and is out of scope.

## Aspect ratio for paper sizes

Pick the aspect-ratio enum closest to the target paper's actual ratio. The right-hand column is what `generate_image_batch`'s `aspectRatio` field accepts.

| Paper size | Orientation | Ratio | `aspectRatio` enum |
|---|---|---|---|
| 8.5×11 (US letter) | Portrait | 0.773 | `3:4` |
| 11×8.5 (US letter) | Landscape | 1.294 | `4:3` |
| 11×17 (ledger / tabloid) | Portrait | 0.647 | `2:3` |
| 17×11 (ledger / tabloid) | Landscape | 1.545 | `3:2` |
| A4 (210×297mm) | Portrait | 0.707 | `3:4` |
| A5 (148×210mm) | Portrait | 0.705 | `3:4` |
| Square card (5×5, 6×6) | — | 1.000 | `1:1` |
| 4×5 / 5×4 print | Portrait / Landscape | 0.800 / 1.250 | `4:5` / `5:4` |

For non-paper outputs (social media, screen, cinematic), the enum choices `9:16`, `16:9`, `21:9` apply directly.

## Resolution

| Resolution | Use case |
|---|---|
| `1K` | Screen preview, social post, inline doc image |
| `2K` | Print quality for US letter / A4 and smaller |
| `3K` | Large-format print (A3, poster) |
| `4K` | Oversize print, archival, high-DPI covers |

Pick the smallest resolution that meets the print target. Higher resolutions cost more credits per image.

## Credit cost per image

| Model | Credits per image |
|---|---|
| Nano Banana 2 (default) | 2 |
| Nano Banana | 1 |
| Nano Banana Pro | 4 |
| GPT Image 2 | 2 |

Credit costs are an Everygen product constant — verify against the Everygen docs when a model is changed or added. Multiply by image count for the per-batch cost; multiply by `N+1` (cover + N interior) for a full image-book cost.

## Batch sizing

`generate_image_batch` takes **2–8** images per call. Plan batches by total count:

| Total images | Batch plan |
|---|---|
| 1 | Single `generate_image` call (batch minimum is 2) |
| 2–8 | One `generate_image_batch` call |
| 9–16 | Two batches of 8 and 1–8 — issue in parallel |
| 17–24 | Three batches, parallel |
| N > 24 | `ceil(N/8)` batches, parallel |

**Never issue 2+ independent `generate_image` calls when one `generate_image_batch` would cover them.** Repeated single calls double round-trip latency with no benefit.

**Parallelism:** when batches do not depend on each other's outputs, issue them in the same message (parallel tool calls). Sequential only when a later batch references an earlier result (e.g. generating variants from a chosen cover).

## Everygen conversational rules

The Everygen MCP server loads its own talk-rules into context when its tools are available: product-not-API phrasing (no "API", "endpoint", "polling", "payload"), never paste raw media URLs in text (the inline result card already shows a download affordance), and prefer `generate_image_batch` over repeated single calls. **Do not restate those rules here or in a skill** — they are already load-time; any restatement is drift.

## Style packs

Each style pack is a prompt-template pair: one for interior pages, one for the cover. Substitute `{PLACEHOLDER}` values; keep every other word unchanged — the exact phrasing (negative prompts, line-art specification, kawaii-cartoon qualifier) is what prevents the model from drifting toward colored output or realistic style.

### `coloring-book` — interior page template (black-and-white line art)

```
Coloring book page for ages {AGE_RANGE}. Black and white line art only, no color, no shading, no grayscale, no gray fills. {INTERIOR_STYLE}. The entire scene is enclosed by a decorative black line-art border frame that spans the full page edges: {BORDER_STYLE}. Scene inside the frame: {SCENE}. Portrait orientation for {SIZE} printing.
```

Substitute `{AGE_RANGE}`, `{INTERIOR_STYLE}`, and `{BORDER_STYLE}` from the age-tier table below. Substitute `{SCENE}` with a one- to two-sentence scene description. Substitute `{SIZE}` with the paper dimensions (e.g. `8.5x11 inch`). **Every generated page must have the border — this is non-optional, do not strip it even if the model would otherwise omit it on an occasional run.**

### `coloring-book` — cover template (full color)

```
Coloring book front cover design for ages {AGE_RANGE}. The entire cover artwork is enclosed by a decorative border frame that spans the full page edges: {BORDER_STYLE}. Title at top inside the frame in {COVER_TYPOGRAPHY}: '{TITLE}'. Scene below the title, inside the frame: {COVER_SCENE}. {COVER_STYLE}. Portrait orientation for {SIZE} printing.
```

Substitute `{AGE_RANGE}`, `{BORDER_STYLE}`, `{COVER_TYPOGRAPHY}`, and `{COVER_STYLE}` from the age-tier table below. Substitute `{TITLE}` with the book title. Substitute `{COVER_SCENE}` with a one- to two-sentence scene featuring the hero elements of the theme. Substitute `{SIZE}` with the paper dimensions.

### `coloring-book` — age tiers

| Tier | `AGE_RANGE` | `INTERIOR_STYLE` | `COVER_TYPOGRAPHY` | `COVER_STYLE` | `BORDER_STYLE` |
|---|---|---|---|---|---|
| `toddler` | `2-5` | Very thick bold outlines on pure white background. Huge simple shapes with big smiling faces. Minimal detail per page — one or two large hero objects. Kawaii cartoon style, no scary elements | bold chunky playful cartoon letters | Bright primary colors — red, blue, yellow, grass green. Chunky bold outlines, happy smiling faces, extra-simple shapes, cheerful mood | thick single-line rectangular frame with large chunky corner decorations — big simple hearts, stars, suns, or flowers in each corner; bold outer line, nothing fiddly |
| `kid` | `6-9` | Thick bold outlines on pure white background. Cute simple kawaii cartoon style with large shapes and smiling faces. Moderate detail — one scene with 2–4 objects | bold whimsical cartoon letters | Bright pastel colors — soft pink, mint green, lavender, sunny yellow, sky blue. Thick bold outlines, cute kawaii cartoon style, friendly expressions, cheerful, no scary elements | playful rounded rectangular frame with gently curved edges, small flowers, stars, or hearts scattered along the border, cute cartoon flourishes at the corners |
| `tween` | `10-13` | Medium outlines on pure white background. Playful illustrated style with moderate detail, pattern accents, and expressive characters. More complex compositions with 3–6 elements per scene | stylized hand-lettered display font | Vibrant color palette with contrasting accents (teal, coral, mustard). Medium outlines, dynamic composition, pattern elements, slightly more mature cartoon style | patterned geometric border with repeating motifs — chevrons, dot bands, triangles, waves — plus medium-detailed ornamental corner pieces |
| `adult` | `14+` | Fine detailed line art on pure white background. Intricate patterns, mandalas, geometric decoration, zentangle-inspired fill motifs. Dense but balanced composition — the subject is recognizable but surrounded by decorative detail | elegant serif or script typography | Sophisticated color palette (deep jewel tones, muted earths). Fine linework preview of the interior style, pattern-rich composition, no juvenile cartoon elements | ornate intricate border with zentangle fill, filigree scrollwork along the sides, elaborate mandala or rosette motifs at each corner, fine detailed linework matching the interior density |

The age tier is the `--age` parameter in `/image-book` and surfaces in the skill's `AskUserQuestion`. Each row produces one consistent style across every page of a book — never mix tiers within one book. The border motif stays consistent across every page of a given book so the set reads as a coherent product.

### Adding a new style pack

When a new printed-image product is wanted (recipe card, workbook, sticker sheet, worksheet), add a new `###` section here with both templates. The pack name becomes the `--style` value in `/image-book`. Never embed per-pack strings inside skills — this file is the single source of truth.

## Mandatory behaviors

- **Apply the style pack verbatim.** When generating a themed image set, read the template from this file and substitute placeholders. Never re-derive style strings per image — drift between pages is the failure mode.
- **Match aspect ratio to final paper size** using the table above. A page intended for 8.5×11 print must request `3:4`, not `1:1` or `9:16`.
- **Match resolution to print target** using the table above. Never pick `4K` for a thumbnail; never pick `1K` for 11×17 print.
- **Batch when the count is ≥2 and the images are independent.** Repeated `generate_image` calls on independent prompts are a Must Fix finding during review.
- **Issue independent batches in parallel.** Serial-only when a later batch inputs a prior batch's output.
- **Follow Everygen MCP talk-rules exactly.** Do not restate them; obey them.

## Pragmatism Guard

Do not apply this rule when:

- **Single-image one-off previews** (one image, ≤A6 size, thrown away immediately) — pick aspect ratio by hand; the table-lookup round-trip is more cost than value.
- **Non-printable screen-only outputs** (social post, inline doc image, UI mockup) — ignore the paper-size table; use `9:16`, `16:9`, or `1:1` directly.
- **Reference-image edits** where the output's aspect is determined by the reference, not the paper target.

## Anti-patterns to avoid

- **Re-deriving the coloring-book line-art spec each session.** The exact "no color, no shading, no grayscale, no gray fills, thick bold black outlines on pure white background" phrasing is load-bearing. Shortening it (e.g. "line art, no color") produces pages the model fills with shading. Copy the template verbatim.
- **Choosing aspect ratio from the enum list in isolation.** `9:16` looks tall; it is tall for *video*, not for 8.5×11 paper. Always route through the paper-size table.
- **Mixing style packs within one image set.** If 15 pages are `coloring-book` interior and 1 cover is `coloring-book` cover, that is one pack. If one page is `workbook` and the others are `coloring-book`, the output is incoherent — pick one pack per set.
- **Issuing 10 single `generate_image` calls when `generate_image_batch` would take 2 calls of 5 each.** Each round-trip is extra latency; batching keeps the total under one wall-clock minute.
