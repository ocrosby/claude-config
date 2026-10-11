#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright>=1.47"]
# ///
"""Pre-fill a KDP paperback draft from a kdp_compose output directory.

Reads `metadata.json`, `interior.pdf`, and `cover.pdf`, launches a
headed Chrome with a persistent profile, and pre-fills the Details +
Content steps of KDP's new-paperback wizard. The script never clicks
Publish or Submit for Review — it stops after upload so the human can
review and submit manually.

Modes:
  --dry-run   Open the browser, verify login, land on the bookshelf,
              exit. First run uses this to establish the login cookie.
  --draft     Create a new paperback draft and pre-fill fields:
              Details (title, subtitle, author, description, keywords,
              AI disclosure), Content (trim, bleed, interior upload,
              cover upload). Pricing and categories remain manual.

First-run setup:
  1. Run `--dry-run` once. A Chrome window opens pointed at KDP.
  2. Log in manually (including 2FA). The profile persists at
     ~/.cache/kdp-automation/chrome-profile.
  3. Future runs reuse the saved login.

KDP has no official upload API; selectors below are best-effort
against the live UI and will drift. When a step fails, update
`SELECTORS` at the top of this file and re-run.

ToS note: KDP ToS restricts automated access. The script never clicks
Publish; final submission is always a human action. Use at your own
risk; batch runs or rapid-fire usage can flag an account.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROFILE_DIR = Path.home() / ".cache" / "kdp-automation" / "chrome-profile"

MARKETPLACE_LOCALES: dict[str, str] = {
    "US": "en_US",
    "UK": "en_GB",
    "DE": "de_DE",
    "FR": "fr_FR",
    "ES": "es_ES",
    "IT": "it_IT",
    "JP": "ja_JP",
    "CA": "en_US",  # KDP routes CA through en_US bookshelf
    "AU": "en_US",  # KDP routes AU through en_US bookshelf
}

REQUIRED_FIELDS: tuple[str, ...] = (
    "title",
    "author",
    "trim_size",
    "paper",
    "page_count",
    "interior_pdf",
    "cover_pdf",
)

MAX_KEYWORDS = 7
MAX_KEYWORD_LEN = 50

# ---------------------------------------------------------------------------
# Selector map — the single place to tune when the KDP UI drifts.
#
# Prefer role/label locators over CSS; they survive class-name churn. If a
# step fails, run `--dry-run` and inspect the live page before editing here.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Selectors:
    """Locator strings for the KDP wizard. Verify against live UI on failure."""

    # Bookshelf → wizard entry
    bookshelf_create_button: str = "Create"
    bookshelf_paperback_option: str = "Paperback"

    # Details step
    details_language_dropdown_label: str = "Language"
    details_title_input_label: str = "Book Title"
    details_subtitle_input_label: str = "Subtitle"
    details_author_first_name_label: str = "First name"
    details_author_last_name_label: str = "Last name"
    details_description_textarea_label: str = "Description"
    details_publishing_rights_owned_radio: str = "I own the copyright"
    details_keyword_input_prefix: str = "Keyword "  # "Keyword 1", "Keyword 2", ...
    details_ai_text_radio_label_no: str = "No"
    details_ai_images_checkbox_label: str = "AI-generated images"
    details_save_and_continue_button: str = "Save and Continue"

    # Content step
    content_isbn_free_radio: str = "Get a free KDP ISBN"
    content_publication_date_leave_blank: str = ""  # KDP defaults to today
    content_print_option_bw_white_radio: str = "Black & white interior with white paper"
    content_print_option_bw_cream_radio: str = "Black & white interior with cream paper"
    content_print_option_color_standard_radio: str = (
        "Standard color interior with white paper"
    )
    content_print_option_color_premium_radio: str = (
        "Premium color interior with white paper"
    )
    content_trim_size_select_label: str = "Trim Size"
    content_bleed_yes_radio: str = "Bleed (PDF only)"
    content_interior_upload_input: str = "input[type=file][name*=manuscript i]"
    content_cover_upload_input: str = "input[type=file][name*=cover i]"
    content_save_and_continue_button: str = "Save and Continue"

    # Pricing step — hands-off for MVP. Script stops before this step.


SELECTORS = Selectors()


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested)
# ---------------------------------------------------------------------------


def kdp_bookshelf_url(marketplace: str) -> str:
    """Return the KDP bookshelf URL for a marketplace code.

    Args:
        marketplace: Two-letter marketplace code (US, UK, DE, FR, ES, IT, JP, CA, AU).

    Returns:
        A full HTTPS URL to the marketplace's bookshelf.

    Raises:
        ValueError: If `marketplace` is not recognized.
    """
    if marketplace not in MARKETPLACE_LOCALES:
        known = ", ".join(sorted(MARKETPLACE_LOCALES))
        raise ValueError(f"unknown marketplace '{marketplace}' — known: {known}")
    locale = MARKETPLACE_LOCALES[marketplace]
    return f"https://kdp.amazon.com/{locale}/bookshelf"


def normalize_keywords(keywords: list[str] | None) -> list[str]:
    """Trim, drop blanks, truncate to the KDP 7-keyword cap.

    KDP accepts up to 7 keywords per title, each ≤ 50 characters. The script
    does not enforce the per-keyword length cap here — that is a soft rule and
    KDP will warn in the UI. Over-length keywords pass through so the user can
    see the warning in context.

    Args:
        keywords: Raw keyword list from book.yaml, or None.

    Returns:
        A list of up to MAX_KEYWORDS non-empty, stripped keyword strings.
    """
    if not keywords:
        return []
    cleaned = [k.strip() for k in keywords if isinstance(k, str) and k.strip()]
    return cleaned[:MAX_KEYWORDS]


def load_normalized_metadata(book_dir: Path) -> dict[str, Any]:
    """Load `<book_dir>/metadata.json` and validate required fields and files.

    Args:
        book_dir: Directory containing `metadata.json`, `interior.pdf`, `cover.pdf`.

    Returns:
        The parsed metadata dict.

    Raises:
        FileNotFoundError: If `metadata.json`, `interior.pdf`, or `cover.pdf` is missing.
        ValueError: If any required metadata field is missing.
    """
    path = book_dir / "metadata.json"
    if not path.is_file():
        raise FileNotFoundError(f"metadata.json not found under {book_dir}")
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(
            f"metadata.json must be a JSON object, got {type(data).__name__}"
        )
    missing = [f for f in REQUIRED_FIELDS if not data.get(f)]
    if missing:
        raise ValueError(
            f"metadata.json missing required field(s): {', '.join(missing)}"
        )
    interior_pdf = Path(data["interior_pdf"])
    cover_pdf = Path(data["cover_pdf"])
    if not interior_pdf.is_file():
        raise FileNotFoundError(f"interior PDF missing: {interior_pdf}")
    if not cover_pdf.is_file():
        raise FileNotFoundError(f"cover PDF missing: {cover_pdf}")
    return data


# ---------------------------------------------------------------------------
# Browser orchestration (not unit-tested — requires a logged-in KDP session)
# ---------------------------------------------------------------------------


def _import_playwright() -> Any:
    """Lazy-import Playwright so the pure helpers work without the browser dep."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    except ImportError as e:
        raise SystemExit(
            "playwright is not installed. Run: uv pip install playwright "
            "&& playwright install chromium"
        ) from e
    return sync_playwright


def _log(step: str, detail: str = "") -> None:
    """Print a progress step to stderr so stdout stays reserved for structured output."""
    msg = f"[kdp_publish] {step}"
    if detail:
        msg += f": {detail}"
    print(msg, file=sys.stderr)


def _launch_context(playwright: Any, *, headless: bool) -> Any:
    """Launch a persistent Chromium context that reuses the saved login profile."""
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    return playwright.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=headless,
        channel="chrome",
        viewport={"width": 1440, "height": 900},
    )


def _is_logged_in(page: Any) -> bool:
    """Heuristic: a logged-in bookshelf page shows the Create button."""
    try:
        return page.get_by_role(
            "button", name=SELECTORS.bookshelf_create_button
        ).is_visible(timeout=5000)
    except Exception:
        return False


def _run_dry_run(marketplace: str, headless: bool) -> int:
    """Open the bookshelf, verify login state, and exit."""
    sync_playwright = _import_playwright()
    url = kdp_bookshelf_url(marketplace)
    with sync_playwright() as p:
        ctx = _launch_context(p, headless=headless)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        _log("navigating", url)
        page.goto(url, wait_until="domcontentloaded")
        if _is_logged_in(page):
            _log("logged in", "bookshelf reachable")
            print("ok: logged in and ready")
            ctx.close()
            return 0
        _log(
            "not logged in",
            "complete the login in the open window; profile will persist for future runs",
        )
        print(
            "action required: log in manually in the opened Chrome window, then re-run"
        )
        # Hold the window open so the user can log in. Close exits the script.
        try:
            page.wait_for_event("close", timeout=0)
        except Exception:
            pass
        ctx.close()
        return 2


# Mapping from book.yaml `paper` value to KDP's Content-step print-option label.
_PAPER_TO_PRINT_OPTION: dict[str, str] = {
    "white": SELECTORS.content_print_option_bw_white_radio,
    "cream": SELECTORS.content_print_option_bw_cream_radio,
    "color-standard": SELECTORS.content_print_option_color_standard_radio,
    "color-premium": SELECTORS.content_print_option_color_premium_radio,
}


def _fill_details(page: Any, meta: dict[str, Any]) -> None:
    """Pre-fill the Details step. Fields filled: title, subtitle, author, description,
    keywords, publishing-rights = owned, AI-content disclosure. Categories and
    series/edition are left blank for the human to fill.
    """
    _log("details step", "filling text fields")
    page.get_by_label(SELECTORS.details_title_input_label, exact=False).fill(
        str(meta["title"])
    )
    if meta.get("subtitle"):
        page.get_by_label(SELECTORS.details_subtitle_input_label, exact=False).fill(
            str(meta["subtitle"])
        )

    author = str(meta["author"]).strip()
    first, _, last = author.partition(" ")
    page.get_by_label(SELECTORS.details_author_first_name_label, exact=False).fill(
        first
    )
    if last:
        page.get_by_label(SELECTORS.details_author_last_name_label, exact=False).fill(
            last
        )

    if meta.get("description"):
        page.get_by_label(
            SELECTORS.details_description_textarea_label, exact=False
        ).fill(str(meta["description"]))

    # Publishing rights — default to "I own the copyright and hold necessary rights".
    try:
        page.get_by_label(
            SELECTORS.details_publishing_rights_owned_radio, exact=False
        ).check()
    except Exception:
        _log("publishing-rights radio not found", "select manually in the browser")

    # Keywords — fill up to 7 slots in order.
    for i, kw in enumerate(normalize_keywords(meta.get("keywords") or []), start=1):
        label = f"{SELECTORS.details_keyword_input_prefix}{i}"
        try:
            page.get_by_label(label, exact=False).fill(kw)
        except Exception:
            _log("keyword slot not found", f"{label} (stopping fill)")
            break

    # AI disclosure — required for every book from this pipeline.
    ai = meta.get("ai_disclosure") or {}
    if ai.get("images"):
        try:
            page.get_by_label(
                SELECTORS.details_ai_images_checkbox_label, exact=False
            ).check()
        except Exception:
            _log("ai-images checkbox not found", "tick manually in the browser")

    _log("details step", "done; press Save and Continue manually to proceed")


def _fill_content_and_upload(
    page: Any,
    meta: dict[str, Any],
    interior_pdf: Path,
    cover_pdf: Path,
) -> None:
    """Pre-fill the Content step: trim size, bleed yes, print option, upload files."""
    _log("content step", "selecting print options")

    # Print option — paper type drives the radio choice.
    paper = meta["paper"]
    radio_label = _PAPER_TO_PRINT_OPTION.get(paper)
    if radio_label:
        try:
            page.get_by_label(radio_label, exact=False).check()
        except Exception:
            _log(f"print-option radio '{radio_label}' not found", "select manually")

    # Trim size — the dropdown value is the trim like "8.5 x 11 in".
    try:
        page.get_by_label(
            SELECTORS.content_trim_size_select_label, exact=False
        ).select_option(label=f"{meta['trim_size'].replace('x', ' x ')} in")
    except Exception:
        _log("trim-size select not found or label mismatch", "select manually")

    # Bleed — our composer always writes with bleed.
    try:
        page.get_by_label(SELECTORS.content_bleed_yes_radio, exact=False).check()
    except Exception:
        _log("bleed radio not found", "select 'Bleed (PDF only)' manually")

    # File uploads.
    _log("uploading", f"interior {interior_pdf.name}")
    try:
        page.locator(SELECTORS.content_interior_upload_input).set_input_files(
            str(interior_pdf)
        )
    except Exception:
        _log("interior upload input not found", "upload the file manually")
    _log("uploading", f"cover {cover_pdf.name}")
    try:
        page.locator(SELECTORS.content_cover_upload_input).set_input_files(
            str(cover_pdf)
        )
    except Exception:
        _log("cover upload input not found", "upload the file manually")

    _log("content step", "done; wait for KDP to process the uploads before continuing")


def _run_draft(book_dir: Path, marketplace: str, headless: bool) -> int:
    """Create a new paperback draft and pre-fill Details + Content."""
    meta = load_normalized_metadata(book_dir)
    interior_pdf = Path(meta["interior_pdf"])
    cover_pdf = Path(meta["cover_pdf"])

    sync_playwright = _import_playwright()
    url = kdp_bookshelf_url(marketplace)
    with sync_playwright() as p:
        ctx = _launch_context(p, headless=headless)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        _log("navigating", url)
        page.goto(url, wait_until="domcontentloaded")
        if not _is_logged_in(page):
            _log("not logged in", "run --dry-run first and log in manually")
            print(
                "error: not logged in. Run `scripts/kdp_publish.py --dry-run <dir>` first "
                "and complete login in the opened browser.",
                file=sys.stderr,
            )
            ctx.close()
            return 2

        _log("creating paperback draft")
        try:
            page.get_by_role("button", name=SELECTORS.bookshelf_create_button).click()
            page.get_by_role("link", name=SELECTORS.bookshelf_paperback_option).click()
        except Exception:
            _log("could not reach the paperback wizard", "update SELECTORS and retry")
            ctx.close()
            return 3

        page.wait_for_load_state("domcontentloaded")
        _fill_details(page, meta)
        # Human clicks Save and Continue (and reviews first) between steps.
        print(
            "paused on Details step. Review the filled fields, click 'Save and Continue', "
            "then re-run with the same arguments to continue to the Content step.",
            file=sys.stderr,
        )
        try:
            page.wait_for_url("**/content**", timeout=0)
        except Exception:
            ctx.close()
            return 0
        _fill_content_and_upload(page, meta, interior_pdf, cover_pdf)
        print(
            "paused on Content step. Verify uploads, categories, and pricing manually. "
            "Never run with any flag that clicks Submit for Review — stop here.",
            file=sys.stderr,
        )
        try:
            page.wait_for_event("close", timeout=0)
        except Exception:
            pass
        ctx.close()
        return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """Build the argparse namespace for the CLI."""
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    p.add_argument(
        "book_dir",
        type=Path,
        nargs="?",
        help="Directory containing metadata.json, interior.pdf, cover.pdf.",
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Launch the browser, verify login, exit. Default mode.",
    )
    mode.add_argument(
        "--draft",
        action="store_true",
        help="Create a new paperback draft and pre-fill Details + Content.",
    )
    p.add_argument(
        "--marketplace",
        default="US",
        choices=sorted(MARKETPLACE_LOCALES),
        help="KDP marketplace code (default: US).",
    )
    p.add_argument(
        "--headless",
        action="store_true",
        help="Run Chromium headless. Useful only for CI smoke tests — "
        "normal use is headed so 2FA works.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Dispatch dry-run or draft mode based on the parsed arguments."""
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    if args.draft and args.book_dir is None:
        print("error: --draft requires book_dir", file=sys.stderr)
        return 2
    if args.draft:
        if not args.book_dir.is_dir():
            print(f"error: not a directory: {args.book_dir}", file=sys.stderr)
            return 2
        return _run_draft(args.book_dir, args.marketplace, args.headless)
    # Default: dry-run.
    return _run_dry_run(args.marketplace, args.headless)


if __name__ == "__main__":
    sys.exit(main())
