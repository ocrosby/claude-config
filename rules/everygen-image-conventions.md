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

## Resolution and credit cost per model

Not every model supports every resolution, and credit cost varies by model **and** by resolution. The matrix below is the single source of truth; the table at the top of each column is "credits per image at that resolution" and `—` means the model does not support that resolution. Verify against `list_supported_models` whenever a model is added or Everygen's price list shifts.

| Model | 1K | 2K | 3K | 4K | KDP paperback (8.5×11, 3:4) |
|---|---|---|---|---|---|
| Nano Banana (gemini-2.5-flash-image) | 1 | — | — | — | — too low for print |
| **Nano Banana 2** (default) | 2 | 2 | — | 3 | **4K at 3 credits** (2K ≈ 234 DPI, below 300 floor; no 3K support) |
| Nano Banana Pro | 3 | 3 | — | 4 | 4K at 4 credits — highest-quality fallback |
| Nano Banana 2 Lite | 1 | — | — | — | — too low for print |
| **Seedream 5 Lite** | — | 1 | 1 | 1 | **3K at 1 credit** — cheapest KDP-grade option |
| Seedream 5 Pro | 1 | 2 | — | — | — too low for print |
| Seedream 5 Flash | 1 | 1 | — | — | — too low for print |
| GPT Image 2 | 4 | 4 | — | 4 | 4K at 4 credits |
| GPT Image 2.5 Flare | 4 | 4 | — | 4 | 4K at 4 credits |
| GPT Image 2.5 Sunburst | 4 | 4 | — | 4 | 4K at 4 credits |

**DPI math behind the floor.** 8.5×11 trim + 0.125" bleed on all sides = 8.75×11.25" final page. At 300 DPI the floor is 2,625×3,375 pixels. 2K (≈2,048×2,731) delivers ~234 DPI — below spec. 3K (≈3,072×4,096) delivers ~351 DPI — comfortably over. 4K is always sufficient.

**Choose by signal:**

- **Lowest cost that meets the floor** → Seedream 5 Lite at 3K (1 credit/image). Use when credit budget is the binding constraint and the subject matter is well within Seedream's strengths.
- **Known-good coloring-book line-art style** → Nano Banana 2 at 4K (3 credits/image). Use when the pack requires the clean black-and-white line style the `coloring-book` pack is tuned for.
- **Highest quality** → Nano Banana Pro at 4K (4 credits/image). Reserved for covers where the extra credit buys a visible gain.

Multiply by image count for the per-batch cost; multiply by `N+1` (cover + N interior) for a full image-book cost. For a 26-image book: Seedream 5 Lite 3K = 26 credits; Nano Banana 2 4K = 78 credits; Nano Banana Pro 4K = 104 credits.

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
FULL COLOR illustrated book cover for a coloring book, ages {AGE_RANGE}. This is the FRONT COVER, not an interior coloring page — fully painted and colored illustration, NOT black-and-white line art, NOT a coloring page to be filled in. The entire cover artwork is enclosed by a decorative colored border frame that spans the full page edges: {BORDER_STYLE}. Title at top inside the frame in {COVER_TYPOGRAPHY}: '{TITLE}'. Scene below the title, inside the frame, rendered fully in color: {COVER_SCENE}. {COVER_STYLE}. Portrait orientation for {SIZE} printing.
```

Substitute `{AGE_RANGE}`, `{BORDER_STYLE}`, `{COVER_TYPOGRAPHY}`, and `{COVER_STYLE}` from the age-tier table below. Substitute `{TITLE}` with the book title. Substitute `{COVER_SCENE}` with a one- to two-sentence scene featuring the hero elements of the theme. Substitute `{SIZE}` with the paper dimensions.

**The leading "FULL COLOR" assertion and the explicit "NOT black-and-white line art, NOT a coloring page" negation are load-bearing.** Without them, the model anchors on the dominant "coloring book" context from the surrounding interior-page prompts and regresses to grayscale line art for the cover. First documented regression: 2026-10-11 on the "25 Days of Cozy" advent countdown, where the cover came back as line art despite `{COVER_STYLE}` specifying a bright palette — the color instruction was too far down the prompt to overcome the earlier framing. Do not shorten the leading negation.

### Returned-image DPI gotcha

`generate_image_batch` returns images with **72 DPI** metadata embedded in the JPEG; the single `generate_image` call returns images with **300 DPI** metadata embedded. The underlying pixel dimensions are identical, but tools that compute physical page size from `pixels / DPI` (notably ImageMagick's `magick ... pdf` combine) will render the two kinds of pages at wildly different physical sizes in the same PDF — a 4K image at 72 DPI → ~50×67" page; at 300 DPI → ~12×16" page. On a 2-up PDF viewer the batch-image pages appear ~4× larger than any `generate_image` cover added via a separate single call.

**Mandatory behavior when combining mixed-source images into a PDF:** force a uniform DPI with `magick -units pixelsperinch -density 72 "$dir"/*.jpg "$pdf"` (or `mogrify -units pixelsperinch -density 72 "$dir"/<single-image>.jpg` before combining). The `/image-book combine` subcommand does this automatically; manual recombines must do it too.

### `coloring-book` — age tiers

Line weights listed in the `INTERIOR_STYLE` column are the target weight at *print* size (the dominant visible outline, not the finest detail). Nano Banana does not literally render pt values, but phrasing like "5–7 pt extra-thick" vs "1–1.5 pt fine" sharpens the model's interpretation and makes the convention explicit for human review.

| Tier | `AGE_RANGE` | `INTERIOR_STYLE` | `COVER_TYPOGRAPHY` | `COVER_STYLE` | `BORDER_STYLE` |
|---|---|---|---|---|---|
| `toddler` | `2-5` | 5–7 pt extra-thick bold outlines on pure white background. Huge simple shapes with big smiling faces. Minimal detail per page — one or two large hero objects. Kawaii cartoon style, no scary elements | bold chunky playful cartoon letters | Bright primary colors — red, blue, yellow, grass green. Chunky bold outlines, happy smiling faces, extra-simple shapes, cheerful mood | thick single-line rectangular frame with large chunky corner decorations — big simple hearts, stars, suns, or flowers in each corner; bold outer line, nothing fiddly |
| `kid` | `6-9` | 3–4 pt thick bold outlines on pure white background. Cute simple kawaii cartoon style with large shapes and smiling faces. Moderate detail — one scene with 2–4 objects | bold whimsical cartoon letters | Bright pastel colors — soft pink, mint green, lavender, sunny yellow, sky blue. Thick bold outlines, cute kawaii cartoon style, friendly expressions, cheerful, no scary elements | playful rounded rectangular frame with gently curved edges, small flowers, stars, or hearts scattered along the border, cute cartoon flourishes at the corners |
| `tween` | `10-13` | 1.5–2 pt medium outlines on pure white background. Playful illustrated style with moderate detail, pattern accents, and expressive characters. More complex compositions with 3–6 elements per scene | stylized hand-lettered display font | Vibrant color palette with contrasting accents (teal, coral, mustard). Medium outlines, dynamic composition, pattern elements, slightly more mature cartoon style | patterned geometric border with repeating motifs — chevrons, dot bands, triangles, waves — plus medium-detailed ornamental corner pieces |
| `adult` | `14+` | **Bold-and-easy style** (dominant 2026 adult market style). 2–3 pt bold outlines on pure white background. Simple shapes with large open fillable areas, grown-up subject matter — botanical florals, simplified mandalas, cozy scenes, cute animals. Low complexity — one scene with 2–4 clearly separated elements. Marker-friendly: no fine hatching, no cross-hatching, no stippling | clean sans-serif display font (Anton, Poppins, Montserrat) or hand-lettered | Bright cover palette with strong contrast against a white or soft-tinted background. Bold outlines, friendly subject, no juvenile cartoon exaggeration | medium-thick rounded frame with simple leaf, flower, or geometric corner motifs, no fine filigree |
| `adult-intricate` | `14+` niche | 1–1.5 pt fine line art with 0.5 pt detail work on pure white background. Intricate patterns, dense mandalas, geometric decoration, zentangle-inspired fill motifs. Dense but balanced composition — the subject is surrounded by decorative detail. Marketed at experienced colorists; smaller buyer segment than bold-and-easy | elegant serif or script typography | Sophisticated color palette (deep jewel tones, muted earths). Fine linework preview of the interior style, pattern-rich composition | ornate intricate border with zentangle fill, filigree scrollwork along the sides, elaborate mandala or rosette motifs at each corner, fine detailed linework matching the interior density |

The age tier is the `--age` parameter in `/image-book` and surfaces in the skill's `AskUserQuestion`. Each row produces one consistent style across every page of a book — never mix tiers within one book. The border motif stays consistent across every page of a given book so the set reads as a coherent product.

**Why `adult` is now bold-and-easy, not intricate zentangle.** From late 2024 onward "bold and easy" coloring books have been the single biggest growth style on KDP; a 500-book sample found generic mandalas at BSR 287,000 (23 avg reviews) while targeted bold-easy niches cluster at BSR 50,000–65,000 (76–142 avg reviews). The old intricate style is still viable as a niche positioning — use `adult-intricate` for that market — but the default `adult` tier now matches the market's dominant buy signal. See `docs/coloring-book-market-signals.md` for the full data.

### Adding a new style pack

When a new printed-image product is wanted (recipe card, workbook, sticker sheet, worksheet), add a new `###` section here with both templates. The pack name becomes the `--style` value in `/image-book`. Never embed per-pack strings inside skills — this file is the single source of truth.

## Mandatory behaviors

- **Apply the style pack verbatim.** When generating a themed image set, read the template from this file and substitute placeholders. Never re-derive style strings per image — drift between pages is the failure mode.
- **Match aspect ratio to final paper size** using the table above. A page intended for 8.5×11 print must request `3:4`, not `1:1` or `9:16`.
- **Match resolution to print target using the model matrix.** Never pick `4K` for a thumbnail; never pick `1K` for 11×17 print. For any image set destined for `/kdp compose`, the output must meet 300 DPI at trim+bleed. On Nano Banana 2 that means 4K (3 credits/image) because the model does not support 3K and 2K sits at ~234 DPI; on Seedream 5 Lite that means 3K (1 credit/image). 2K with any model for KDP paperback is a Must Fix finding.
- **Pre-flight credit balance before firing a batch.** Compute expected cost from the model-matrix above: `expected = images × credits_per_image_for_resolution`. Call `get_credit_balance` and confirm `remaining >= expected`. **If `remaining < expected`: stop and do not proceed.** Report the shortfall and the two options — top up, or switch to a lower-cost model (e.g. Seedream 5 Lite at 1 credit/image for 3K) if the pack is model-compatible. Failed generations charge 0 credits but waste a user turn and the batch has to be re-fired after the top-up.
- **Set `ai_disclosure.images: true` in `book.yaml`** whenever the set is destined for `/kdp compose`. Every Everygen image is AI-generated; KDP has required disclosure since 2023 and false negatives are a terms-of-service violation.
- **Scene prompts must be specific, not generic.** On KDP, targeted themes average 156 reviews; generic themes average 38. Name 2+ concrete objects, a specific action or arrangement, and spatial layout per scene. "Cat" is a Must Fix; "British shorthair kitten batting a daisy on a sunlit windowsill" is right. "Flowers" is a Must Fix; "cluster of three peonies in a jam jar with a trailing ribbon" is right. The specificity applies to the scene *description* that fills the pack template's `{SCENE}` placeholder — the pack's style (bold outlines, no shading, etc.) stays verbatim.
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
