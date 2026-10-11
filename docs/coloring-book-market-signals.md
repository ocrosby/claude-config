# Coloring book market signals (KDP, 2026)

Reference data behind the defaults in `rules/everygen-image-conventions.md`, `skills/image-book/SKILL.md`, and `skills/kdp/book.yaml.example`. Pulled from a 500-book sample analyzed in 2026 plus corroborating KDP niche studies — see Sources at the bottom. Treat the numbers as directional, not authoritative; re-run the research if a strategy depends on specific thresholds.

## Niche performance (BSR = Best Sellers Rank; lower is better)

| Niche shape | Avg BSR | Avg reviews | Price point |
|---|---:|---:|---:|
| Anxiety relief / mindfulness | 47,300 | 142 | $9.99 |
| Profession-specific (nurses, teachers, EMTs, truckers) | 52,100 | 134 | $8.99 |
| Breed-specific pets ("golden retrievers", not "dogs") | 58,700 | 98 | $8.99 |
| Seasonal micro-niches (advent, Halloween-week, Mother's Day) | 61,200 | 87 | $7.99 |
| Cultural / heritage themes | 64,800 | 76 | $9.99 |
| **Avoid**: generic mandalas | 287,000 | 23 | mixed |
| **Avoid**: simple flowers | 298,000 | 21 | mixed |
| **Avoid**: broad animals | 312,000 | 19 | mixed |

The specificity gap is enormous: targeted themes averaged 156 reviews; generic titles averaged 38. The same book-making effort directed at "coloring book for ER nurses" outperforms "coloring book for nurses" by ~4×, which in turn beats "coloring book" by another ~4×.

## Style signal — "bold and easy" is dominant

Since late 2024, bold-and-easy has been the single biggest growth style on KDP. Characteristics:

- 2–3 pt bold outlines at print size (adult tier).
- Simple shapes with large open fillable areas.
- Grown-up subject matter — botanical florals, simplified mandalas, cozy scenes, cute animals.
- 2–4 clearly separated elements per scene; no fine hatching, cross-hatching, or stippling.
- Marker-friendly: works with cheap crayons and alcohol markers alike.

The intricate zentangle style still has a buyer segment but is now the niche positioning, not the default. The `adult` age tier in `rules/everygen-image-conventions.md` points at bold-and-easy; the `adult-intricate` tier preserves the detailed-line variant for that niche.

## Trim size

| Size | Share of top-selling adult coloring books |
|---|---:|
| 8.5×11 | 60–65% |
| 8.5×8.5 | ~25% |
| 8×10 | ~8% |

8.5×11 is the default in both skills and in `book.yaml.example` because buyer expectation and reviewer bias both favor it. Avoid 6×9 for coloring content — "too cramped" is a recurring 1-star review theme.

## Interior page count

| Range | Market role |
|---|---|
| < 24 physical pages | **Rejected by KDP** (paperback minimum) |
| 24–39 | Thin, undersells perceived value; low-review segment |
| **40–60** | **Sweet spot** — 118 avg reviews at $8.99 (highest "reviews per dollar") |
| 60–100 | Common for children's; viable for adults if theme supports it |
| > 100 | Printing cost eats royalty margin without lifting conversion |

Physical page count = `image_count × 2` when `single_sided: true` (standard for coloring books because markers bleed through). So 20–30 images with single-sided layout → 40–60 physical pages → bestseller sweet spot. The `/image-book` default of 40 images already sits inside this range.

## Pricing

Royalty tiers (as of June 2025):

- List price below $9.99 → 50% royalty.
- List price ≥ $9.99 → 60% royalty.

Going from $7.99 to $9.99 raises per-sale profit by ~53% on a 50-page coloring book. Default to **$9.99 USD** in `book.yaml`; three-marketplace ladder: $9.99 USD / £7.99 GBP / €8.99 EUR.

**Launch tactic**: price at $7.99 for the first ~4 weeks to accumulate reviews and improve BSR, then raise to $9.99 once you have 10+ reviews. Raise again to $11.99 only if BSR holds under 100,000 after 60 days.

## Cover design (what converts)

- Big bold sans-serif title typography — Anton, Poppins, Montserrat, or clean hand-lettering.
- Strong contrast between title and background. White or soft-tinted background outperforms busy decorative frames at thumbnail size.
- One clear hero subject below the title. Avoid "collage of 6 small subjects" — reads as noise in search results.
- Series branding: use a consistent border + typography across your titles so repeat buyers recognize you.

## Interior design (bleed-through, margins, orientation)

- **Single-sided** is the strong default. Markers bleed through standard KDP paper. One image on the right page, blank behind. `/kdp compose` inserts the blank page automatically when `single_sided: true` (the default).
- **No bleed** is used by ~95% of adult coloring books. Content sits inside the trim with a 0.25" inner safe margin so colorists can grip the book without smudging their work. `/kdp compose` honors `bleed: false` (the recommended default) by sizing pages to trim and insetting the image. Set `bleed: true` only when you intentionally want designs to extend to the trim edge.
- **Portrait orientation**. Landscape coloring books exist but underperform portrait in reviews ("uncomfortable to hold open").

## Keywords and categories

- KDP accepts up to **7 keywords** (filled by `/kdp publish --draft` from `book.yaml`) and up to **3 categories** (picked in the browser — the picker is a cascading dropdown that drifts, so automation isn't worth the maintenance).
- Keyword phrasing matters: `coloring book for seniors` beats `senior coloring`; `anxiety relief coloring` beats `coloring for anxiety`. Match the search-box phrasing an actual buyer would type.
- Some categories auto-attach from keywords. Example: including "stress relief" in your keywords often attaches the Humor → Coping / Mindfulness category without a manual pick.

## When to re-run this research

- When a new year's data is available (yearly cadence is enough).
- When Amazon changes its royalty structure (June 2025 was the last; monitor for shifts).
- When the dominant style trend visibly rotates (bold-and-easy has held since late 2024, but trends do turn — if a new style is clearly outranking it in BSR, update the `adult` tier definition in `rules/everygen-image-conventions.md`).

## Sources

- [500 Coloring Books Analyzed: Top KDP Niches 2026](https://inkchamps.com/blog/500-coloring-books-analyzed-top-kdp-niches-2026/)
- [KDP Coloring Book Pricing: $9.99 vs $7.99 Profit Math](https://www.kdpeasy.com/blog/kdp-coloring-book-pricing)
- [How many pages should a KDP coloring book have?](https://bookillustrationai.com/blog/how-many-pages-should-a-kdp-coloring-book-have)
- [KDP coloring book trim size, bleed, and rejections](https://bookillustrationai.com/blog/kdp-coloring-book-format-trim-size-bleed-rejections)
- [Coloring book line weight and complexity by age](https://bookillustrationai.com/blog/coloring-book-line-weight-complexity-by-age)
- [KDP coloring book categories: the 3-pick rule](https://bookillustrationai.com/blog/kdp-coloring-book-categories)
- [Best Coloring Book Niches for Amazon KDP 2026](https://inkchamps.com/blog/best-niches-for-coloring-books-amazon-kdp-2026/)
- [Coloring Book Trends 2026](https://www.kdpeasy.com/guides/coloring-book-trends-2026)
