# Publishing printable image books to KDP

End-to-end guide for taking an `/image-book` output directory and turning it into a Kindle Direct Publishing paperback draft. Two subcommands handle the mechanical work; the human handles pricing, categories, and the final Submit for Review click. Nothing in this skill ever publishes without explicit human action — that is a design decision, not an oversight.

Prerequisite: a generated image book under `~/Downloads/image-books/<slug>/`. If you have not generated one, read `docs/image-books.md` first.

## What ships end-to-end

| Component | Purpose | Lives in |
|---|---|---|
| `/kdp compose <image-dir>` | Build `interior.pdf` (trim + 0.125" bleed), `cover.pdf` (back + spine + front spread), and `metadata.json` from the generated images + a `book.yaml` | `skills/kdp/SKILL.md`, `scripts/kdp_compose.py` |
| `/kdp publish --dry-run` | Open a headed Chrome at the KDP bookshelf, verify login works. First-run setup; seeds the persistent profile | same skill, `scripts/kdp_publish.py` |
| `/kdp publish --draft <image-dir>` | Pre-fill a new paperback draft from `metadata.json` + the two PDFs: Details step (text fields, keywords, AI disclosure) and Content step (trim, bleed, uploads). Stops before Submit for Review | same |
| `skills/kdp/book.yaml.example` | Commented template with every supported metadata field | — |
| `rules/everygen-image-conventions.md` | Resolution floor and AI-disclosure mandate for anything destined for `/kdp compose` | `rules/` |

## Prerequisites

Run each of these once. The first two are typically already in place from the generation stage.

| Tool | Check | Install if missing |
|---|---|---|
| Claude Code CLI | `claude --version` | https://claude.com/claude-code |
| Python 3.11+ (via `uv`) | `uv --version` | `brew install uv` (macOS) or https://docs.astral.sh/uv/ |
| Playwright + Chromium (only for `/kdp publish`) | `uv tool install playwright && playwright install chromium` | ~150 MB browser download |
| An active KDP account | https://kdp.amazon.com/ | Includes a one-time tax interview and bank setup — not automatable |

A KDP account needs tax info and a bank account on file *before* any book can be submitted. Do that in the KDP web UI before expecting `/kdp publish` to be useful.

## Quick start — one book, generation to KDP draft

```
/image-book create fairy coloring book         # generates PDF under ~/Downloads/image-books/<slug>/
cp ~/.claude/skills/kdp/book.yaml.example ~/Downloads/image-books/fairy_coloring_book/book.yaml
# edit book.yaml — title, author, description, keywords, categories, AI disclosure
/kdp compose ~/Downloads/image-books/fairy_coloring_book
/kdp publish --dry-run                         # one-time: log in manually in the opened Chrome
/kdp publish --draft ~/Downloads/image-books/fairy_coloring_book
```

After the last command, a Chrome window stays open on the KDP wizard with Details and Content pre-filled. You review each field, fill the per-marketplace categories and pricing by hand, run KDP's previewer, and click **Submit for Review**. The script does not click Submit — that is permanent and reversible only by withdrawing the book, so it stays a human action.

## What `/kdp compose` produces

```
~/Downloads/image-books/fairy_coloring_book/
├── 00-cover.jpg               ← from /image-book
├── 01-fairy-house.jpg
├── ... (interior pages)
├── fairy_coloring_book.pdf    ← bundle PDF from /image-book combine (optional, ignored by KDP)
├── book.yaml                  ← you fill this in
├── interior.pdf               ← ADDED: KDP-ready interior, trim + 0.125" bleed
├── cover.pdf                  ← ADDED: back + spine + front spread with outer bleed
└── metadata.json              ← ADDED: normalized metadata + computed spine width
```

- **Interior PDF.** One image per page sized at trim + 0.125" bleed on all four sides. Images are centered scale-to-fit on a white background; the decorative border from the generation stage sits just inside the trim.
- **Cover PDF.** A single spread sized `(2 × trim_width + spine) × trim_height` plus outer bleed. Back cover gets the description on a solid-color background; spine gets the title if wide enough (≥ 0.125"); front cover is the generated cover image. For a hand-designed cover, replace `cover.pdf` with your own file before uploading — KDP cares only about the file dimensions.
- **metadata.json.** Normalized form of `book.yaml` plus the computed spine width and absolute paths to the two PDFs. Read by `/kdp publish --draft`.

Spine width comes from the KDP cover calculator formula: `page_count × paper_factor`, where `paper_factor` is `0.002252"` for white, `0.0025"` for cream, `0.002252"` for standard color, `0.002347"` for premium color. KDP's own calculator must agree before Submit; if the spread is off the composer and KDP disagree, re-run with the correct `page_count` in `book.yaml`.

## Filling in `book.yaml`

Minimum required fields: `title`, `author`, `trim_size`, `paper`. Everything else has sensible defaults or is downstream-only (categories, pricing — read by phase 2 but entered by hand). The template is self-documenting; a short tour of the most consequential fields:

| Field | Why it matters | Note |
|---|---|---|
| `trim_size` | Determines interior page size and cover spread width | Any value in the aspect-ratio table in `rules/everygen-image-conventions.md`. Match the paper size you picked in `/image-book create` |
| `paper` | Drives spine width and KDP's "print option" radio | `white` (coloring-book default), `cream` (novels), `color-standard`, `color-premium` |
| `page_count` | Overrides the auto-count when you plan to add filler pages (title page, copyright, blank spacers) before upload | KDP minimum is 24 interior pages — a 15-image coloring book needs 9 filler pages or a count override to clear this bar |
| `keywords` | Up to 7 — the publisher reads them for search ranking | Phase 2 fills them in the Details step |
| `categories` | Up to 3 BISAC codes | Phase 2 does **not** fill these — the KDP category picker is a cascading dropdown that drifts; you set them by hand |
| `ai_disclosure.images` | Must be `true` for anything from Everygen | KDP has required disclosure since 2023; false negatives are a ToS violation |
| `price_usd`, `price_gbp`, `price_eur` | Primary + two main territory prices | Phase 2 does **not** fill the Pricing step; you fill it by hand on the Pricing page |

## The two publish modes

### `--dry-run` — first-run setup

```
/kdp publish --dry-run
```

Opens a headed Chrome at `https://kdp.amazon.com/en_US/bookshelf` using a persistent profile at `~/.cache/kdp-automation/chrome-profile/`. On first run you are not logged in; log in manually in that window, complete 2FA, and the profile persists. Subsequent runs reuse the saved cookies — no re-login until KDP expires the session (typically weeks to months).

Exit code 0 = logged in and bookshelf reachable; exit code 2 = window opened but you have not logged in yet. Do not pass `--headless` for first-run setup — 2FA codes need the visible browser.

### `--draft` — pre-fill a new paperback draft

```
/kdp publish --draft ~/Downloads/image-books/<slug>
```

Reads `metadata.json`, `interior.pdf`, `cover.pdf` from the directory. Launches Chrome with the saved profile, clicks **Create → Paperback**, then pre-fills:

- **Details step:** language, title, subtitle, author (split on first space), description, publishing rights = "I own the copyright", up to 7 keywords, AI-images disclosure checkbox.
- **Content step:** ISBN = KDP-provided (free), print option matching `paper`, trim size, bleed = yes, interior PDF upload, cover PDF upload.
- **Pricing step:** not filled. You fill it by hand.
- **Categories:** not filled. The KDP category picker is a cascading dropdown that drifts; you pick by hand.
- **Submit for Review:** not clicked. Ever. The window stays open with the wizard at the step after Content.

## What stays manual, and why

| Thing | Who fills it | Why it's manual |
|---|---|---|
| KDP account tax interview + bank info | You, once | Legal + regulated financial data; not automatable |
| First-run login (2FA) | You, once per profile reset | 2FA codes land on a phone or email, not in the automation |
| BISAC categories | You, per book | The KDP category picker is a cascading dropdown whose structure changes without notice. Automation here breaks weekly |
| Pricing per marketplace | You, per book | 13+ marketplaces × currency conversions × royalty tier choices. Not worth automating until pricing policy is stable per-book |
| KDP previewer approval | You, per book | KDP's previewer runs server-side after upload; waiting for and clicking through it is faster manually than scripting |
| Submit for Review | You, every book | Once submitted, a book goes into KDP's review queue. Pulling it back is a withdraw action with its own tax implications. Human action, always. |

## Tuning when KDP's UI drifts

KDP has no public API; `/kdp publish --draft` drives the live web UI with role/label locators. Amazon ships UI changes without notice. The script's selectors live in exactly one place:

```
scripts/kdp_publish.py  →  SELECTORS = Selectors(...)
```

When a step fails with exit code 3 ("could not reach the paperback wizard") or a specific field is not filled, open the live KDP page in the Chrome window from `--dry-run`, right-click the failing field → Inspect, find a stable `aria-label` or `role` + text, and update the matching `Selectors` field. Re-run `--draft`.

Prefer label and role locators over CSS classes. `page.get_by_label("Book Title")` survives a class-name refactor; `page.locator(".kdp-title-input-field-container input")` does not.

## ToS and account safety

KDP's Terms of Service restrict automated access. This skill is intentionally conservative:

- Headed browser you can watch; no silent background runs.
- Never auto-submits — Submit for Review is always a human click.
- Pauses after each wizard step so you can review before continuing.
- No rapid-fire batching (one book at a time by design).

That said, running `--draft` ten times in an hour on ten different books will look automated. Space them out, especially during the first few weeks on a new account. If KDP flags the account, nothing in this repo recovers it — account support does.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `/kdp compose` emits "page count 15 < KDP minimum 24" | Interior page count is below KDP's floor | Add filler pages (title page, copyright, blank spacers) and set `page_count` in `book.yaml` to the final total, or regenerate with more pages |
| `/kdp compose` emits "effective DPI 234 < 300 target" | Images were generated at 2K instead of 3K | Re-run `/image-book create` with the paper size set correctly — the resolution tier is driven by paper size per `rules/everygen-image-conventions.md` |
| `/kdp publish --dry-run` exits code 2 with "not logged in" | Expected on first run or after session expiry | Log in manually in the open Chrome window; the next invocation reuses the saved cookies |
| `/kdp publish --draft` exits code 3 "could not reach the paperback wizard" | KDP changed the top-level Create → Paperback flow | Update `SELECTORS.bookshelf_create_button` and `SELECTORS.bookshelf_paperback_option` to match the current UI (right-click → Inspect) |
| A specific Details field is empty after `--draft` runs | KDP renamed the field label | Update the matching `Selectors` field (title, subtitle, description, keyword-prefix, AI-images checkbox) |
| Interior or cover upload input not found | KDP changed the file-input selector | Update `SELECTORS.content_interior_upload_input` / `SELECTORS.content_cover_upload_input` (both are CSS, not label — file inputs are rarely labelled) |
| KDP's own cover calculator disagrees with the composed spine | `page_count` in `book.yaml` differs from the final interior page count after filler | Correct `page_count` in `book.yaml`, re-run `/kdp compose`, re-run `/kdp publish --draft` |
| Spread aspect looks wrong in KDP's previewer | Composer used a different trim than you entered in the KDP wizard | Trim size in `book.yaml` must match the trim selected in the Content step; the script sets it, but verify in the open browser |

## Where things live

- Skill: `skills/kdp/SKILL.md`
- Compose script: `scripts/kdp_compose.py`
- Publish script: `scripts/kdp_publish.py`
- Metadata template: `skills/kdp/book.yaml.example`
- Persistent Chrome profile: `~/.cache/kdp-automation/chrome-profile/`
- This doc: `docs/kdp-publishing.md`
- Prior stage: `docs/image-books.md`
- Market signals (niche BSR, pricing math, specificity): `docs/coloring-book-market-signals.md`
