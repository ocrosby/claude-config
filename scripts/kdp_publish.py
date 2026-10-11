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
              AI disclosure, categories), Content (ISBN, paper, bleed,
              cover finish, cover-choice, AI, interior + cover upload;
              verifies trim size matches book.yaml). Pricing is manual.

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
    # Details step — id-based (KDP form controls have no visible labels on inputs).
    # Verified against the live /title-setup/paperback/new/details page 2026-10-11.
    details_language_dropdown_label: str = "Language"
    details_title_input_id: str = "#data-print-book-title"
    details_subtitle_input_id: str = "#data-print-book-subtitle"
    details_author_first_name_id: str = "#data-print-book-primary-author-first-name"
    details_author_last_name_id: str = "#data-print-book-primary-author-last-name"
    details_description_textarea_id: str = (
        "#data-print-book-description"  # may be contenteditable; verify
    )
    details_publishing_rights_owned_radio_id: str = "#non-public-domain"
    # Description is a CKEditor iframe with title "Rich Text Editor, editor1".
    details_description_iframe_title: str = "Rich Text Editor, editor1"
    # Low-content book checkbox — coloring books ARE low-content; always check.
    details_low_content_checkbox_id: str = "#data-view-is-lcb"
    # Large-print checkbox — enable only for Easy to See style books.
    details_large_print_checkbox_id: str = "#data-print-book-large-print"
    # Adult (sexually explicit) content radio — always No for our catalog.
    details_adult_content_no_radio: str = (
        "input[name='data[print_book][is_adult_content]-radio'][value='false']"
    )
    # Keywords are 0-indexed, data-print-book-keywords-0 through -6.
    details_keyword_input_id_prefix: str = "#data-print-book-keywords-"
    details_ai_images_checkbox_label: str = "AI-generated images"
    details_save_and_continue_button: str = "Save and Continue"

    # Content step — id-based (verified 2026-10 against live /print-setup page).
    content_isbn_free_radio: str = "input[name='isbn-type'][value='NONE']"
    content_paper_white_radio: str = "#ink-paper-BW_WHITE"
    content_paper_cream_radio: str = "#ink-paper-BW_CREAM"
    content_paper_color_standard_radio: str = "#ink-paper-COLOR_WHITE"
    content_paper_color_premium_radio: str = "#ink-paper-COLOR_COLOR"
    content_bleed_no_radio: str = "#bleed-no"
    content_bleed_yes_radio: str = "#bleed-yes"
    content_cover_finish_matte_radio: str = "#cover-finish-MATTE"
    content_cover_finish_glossy_radio: str = "#cover-finish-GLOSSY"
    content_cover_upload_choice_radio: str = (
        "input[name='cover-choice'][value='UPLOAD']"
    )
    content_ai_yes_radio: str = "input[name='has-ai-content'][value='yes']"
    content_ai_no_radio: str = "input[name='has-ai-content'][value='no']"
    # File inputs are hidden behind custom "Upload" buttons. Disambiguate by
    # the `accept` attribute: manuscript accepts many formats (incl. .azw),
    # cover accepts only .pdf. set_input_files() works on hidden inputs.
    content_interior_upload_input: str = "input[type='file'][accept*='.azw']"
    content_cover_upload_input: str = "input[type='file'][accept='.pdf']"
    content_save_and_continue_button: str = "Save and Continue"

    # Pricing step — verified 2026-10-11 against live /pricing page.
    # Royalty tier + expanded distribution + T&C acknowledgement appear
    # only after a USD price is entered; the script leaves those for the
    # human to review after fill, then Publish is a manual click.
    pricing_territories_worldwide_radio: str = "#worldwide-rights"
    pricing_territories_individual_radio: str = "#individual-territories"
    pricing_usd_input: str = "#price-input-usd"
    pricing_gbp_input: str = "#price-input-gbp"
    pricing_cad_input: str = "#price-input-cad"
    pricing_jpy_input: str = "#price-input-jpy"
    pricing_aud_input: str = "#price-input-aud"
    pricing_eur_input: str = "#price-input-eur"
    pricing_pln_input: str = "#price-input-pln"
    pricing_sek_input: str = "#price-input-sek"
    # 13 "Base this price on Amazon.com" buttons — one per non-USD marketplace.
    pricing_base_on_amazon_button: str = "Base this price on Amazon.com"


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
    """Heuristic: logged-in bookshelf URL lands on /bookshelf (not /signin or /ap/).

    URL-based detection is more robust than selector-based: Amazon rebrands the
    "Create" button text and layout periodically, but the sign-in redirect path
    (/ap/signin, /ap/mfa, etc.) is stable. If the URL still contains /bookshelf
    after the initial navigation + a short settle, we're authenticated.
    """
    try:
        # Give any sign-in redirect a moment to settle before reading the URL.
        page.wait_for_load_state("domcontentloaded", timeout=5000)
    except Exception:
        pass
    url = page.url or ""
    if "/ap/" in url or "/signin" in url:
        return False
    return "bookshelf" in url


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
_PAPER_TO_PAPER_RADIO: dict[str, str] = {
    "white": SELECTORS.content_paper_white_radio,
    "cream": SELECTORS.content_paper_cream_radio,
    "color-standard": SELECTORS.content_paper_color_standard_radio,
    "color-premium": SELECTORS.content_paper_color_premium_radio,
}


FIELD_TIMEOUT_MS = 5000  # cap per-field waits so misses fail fast on UI drift


def _try_fill_selector(page: Any, selector: str, value: str) -> bool:
    """Fill an input matched by a CSS selector with a short timeout."""
    try:
        page.locator(selector).first.fill(value, timeout=FIELD_TIMEOUT_MS)
        return True
    except Exception:
        return False


def _try_check_selector(page: Any, selector: str) -> bool:
    """Check a radio/checkbox matched by a CSS selector with a short timeout."""
    try:
        page.locator(selector).first.check(timeout=FIELD_TIMEOUT_MS)
        return True
    except Exception:
        return False


def _try_check_label(page: Any, label: str) -> bool:
    """Check by visible label text (useful for AI disclosure, bleed radios)."""
    try:
        page.get_by_label(label, exact=False).first.check(timeout=FIELD_TIMEOUT_MS)
        return True
    except Exception:
        return False


def _fill_rich_text_iframe(page: Any, iframe_title: str, value: str) -> bool:
    """Fill a CKEditor-style rich-text editor hosted inside an iframe.

    KDP's description field is a CKEditor rendered as an iframe with
    title="Rich Text Editor, editor1". The editable area is the <body> inside
    that iframe. CKEditor doesn't recognize Playwright's `fill()` as a real
    edit (its change-detection fires on keystrokes), so we try two strategies:

    1. Direct CKEditor JS API — `CKEDITOR.instances['editor1'].setData(...)` is
       the most reliable path if CKEditor exposes a global instance.
    2. Fallback: click the body and type the value as keystrokes via
       `press_sequentially`, which CKEditor treats as real input.
    """
    # Extract editor name from title ("Rich Text Editor, editor1" -> "editor1").
    editor_name = (
        iframe_title.rsplit(",", 1)[-1].strip() if "," in iframe_title else "editor1"
    )

    # Strategy 1: CKEditor JS API.
    try:
        ok = page.evaluate(
            """([name, text]) => {
                if (window.CKEDITOR && window.CKEDITOR.instances && window.CKEDITOR.instances[name]) {
                    window.CKEDITOR.instances[name].setData(text);
                    return true;
                }
                return false;
            }""",
            [editor_name, value],
        )
        if ok:
            return True
    except Exception:
        pass

    # Strategy 2: keystroke-level typing into the iframe body.
    try:
        frame = page.frame_locator(f'iframe[title="{iframe_title}"]')
        body = frame.locator("body")
        body.click(timeout=FIELD_TIMEOUT_MS)
        body.press("Control+a", timeout=FIELD_TIMEOUT_MS)
        body.press("Delete", timeout=FIELD_TIMEOUT_MS)
        body.press_sequentially(value, delay=5)
        return True
    except Exception:
        return False


def _tick_placement_checkboxes(page: Any, names: list[str]) -> bool:
    """Tick at least one Placement checkbox in the open Choose Categories modal.

    After a full category path is picked, KDP shows a list of Placement
    checkboxes to the right (e.g. "Animals", "Mandalas & Patterns", "General"
    for the Coloring Books for Grown-Ups leaf). At least one must be ticked
    for the "Add another category" commit button to actually persist the
    category. Returns True if at least one checkbox was successfully ticked.

    Strategy:
      1. If `names` is non-empty, try each by label text (first-match wins
         per name; multiple names are ticked if present).
      2. Else try "General" as a safe default (exists on most leaves).
      3. Else tick the first visible checkbox inside the dialog.
    """
    import time as _time

    def _try_tick_by_label(label: str) -> bool:
        """Try multiple strategies to tick a placement checkbox by label text.

        The checkboxes have no name/id/aria-label — only surrounding label
        text, which Playwright's role-name match can't resolve.
        """
        dialog = page.locator("[role='dialog']")
        # Strategy A: click the visible text (if wrapped in <label>, toggles box)
        try:
            dialog.get_by_text(label, exact=True).first.click(timeout=FIELD_TIMEOUT_MS)
            _time.sleep(0.4)
            return True
        except Exception:
            pass
        # Strategy B: iterate all checkboxes, match by parent inner_text
        try:
            for cb in dialog.locator("input[type='checkbox']").all():
                try:
                    if not cb.is_visible():
                        continue
                    parent_txt = cb.locator("xpath=..").inner_text().strip()
                    if label.lower() in parent_txt.lower():
                        cb.check(timeout=FIELD_TIMEOUT_MS)
                        _time.sleep(0.4)
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    ticked_any = False
    if names:
        for name in names:
            if _try_tick_by_label(name):
                ticked_any = True
        if ticked_any:
            return True

    # Fallback 1: "General" placement
    if _try_tick_by_label("General"):
        return True

    # Fallback 2: first visible checkbox in the dialog
    try:
        checks = page.locator("[role='dialog'] input[type='checkbox']").all()
        for c in checks:
            try:
                if c.is_visible():
                    c.check(timeout=FIELD_TIMEOUT_MS)
                    _time.sleep(0.4)
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def _pick_categories(
    page: Any,
    paths: list[list[str]],
    placements: list[list[str]] | None = None,
) -> int:
    """Open the Choose Categories modal and walk up to 3 cascading paths.

    Each path is a list of strings navigating from top-level to leaf
    (e.g. ["Crafts, Hobbies & Home", "Crafts & Hobbies"]). KDP's modal uses
    native `<select class="a-native-dropdown">` elements per slot — one more
    appears each time a parent is picked, until a leaf is reached. We walk
    the chain by targeting the deepest unselected `<select>` within the
    slot's `.dd-{slot_idx}` container.

    Returns the number of paths that completed cleanly (walked all levels
    without a missing option).
    """
    import time as _time

    if not paths:
        return 0

    # Open the modal.
    try:
        btn = page.locator("#categories-modal-button")
        btn.scroll_into_view_if_needed()
        btn.click(timeout=FIELD_TIMEOUT_MS)
    except Exception as e:
        _log("categories button missing", f"modal may be disabled; {e}")
        return 0
    _time.sleep(2.5)

    # Important: "Add another category" is the COMMIT action for the currently-
    # staged dropdown selection, not just a slot-spawner. KDP's modal stages
    # a path through the dropdowns but only persists it when the user clicks
    # "Add another category" (which also creates the next slot). So the flow
    # per slot is: fill dropdowns → click Add another category → repeat.
    # After the last slot, we click Add another category one more time to
    # commit it (leaves a stray empty slot which Save ignores), then Save.
    picked = 0
    for slot_idx, path in enumerate(paths[:3]):
        slot_complete = True
        for level, label in enumerate(path):
            try:
                # KDP wraps each <select> in a visible Amazon dropdown facade
                # (.a-dropdown-container). The facade has its own React state
                # that counts "placements selected" — the hidden <select>'s
                # value is downstream of that state, not upstream. Driving the
                # native select directly (even with React's native-value-setter
                # trick) updates the DOM but leaves the facade's counter at 0,
                # so KDP shows no categories after Save. The correct path is
                # to open the facade and click the <a role='option'> item.
                try:
                    containers = page.locator(
                        f"div.dd-{slot_idx} .a-dropdown-container"
                    ).all()
                    if not containers:
                        _log(
                            f"no dropdown facade in slot {slot_idx}",
                            "structure drifted",
                        )
                        slot_complete = False
                        break
                    # Deepest facade = the one most recently added (newest level).
                    containers[-1].click(timeout=FIELD_TIMEOUT_MS)
                    _time.sleep(0.6)  # wait for popup to render
                    # Click the option in the open popup. The popup renders
                    # <a class="a-dropdown-link" role="option">; using
                    # get_by_role("option") also matches the hidden <option>
                    # elements inside the native <select>, so filter by the
                    # a-dropdown-link class and require exact text match.
                    page.locator("a.a-dropdown-link").filter(has_text=label).filter(
                        has=page.locator(f'text="{label}"')
                    ).first.click(timeout=FIELD_TIMEOUT_MS)
                except Exception as e:
                    _log(
                        f"could not pick '{label}' at level {level} in slot {slot_idx}",
                        f"{e}",
                    )
                    slot_complete = False
                    break
                _time.sleep(1.5)  # wait for next level to render
            except Exception as e:
                _log(
                    f"could not pick '{label}' at level {level} in slot {slot_idx}",
                    f"{e}",
                )
                slot_complete = False
                break
        if slot_complete:
            # Tick at least one Placement checkbox — KDP shows them to the
            # right of the dropdown chain once a leaf is picked. Each
            # category + placement combo counts as one "category placement"
            # (the modal's "N out of 3 category placements selected" counter).
            # Pick from book.yaml's kdp_placements[slot_idx] if provided,
            # else default to "General" if present, else the first visible
            # checkbox.
            slot_placements = (
                placements[slot_idx]
                if placements and slot_idx < len(placements)
                else []
            )
            if not _tick_placement_checkboxes(page, slot_placements):
                _log(
                    f"could not tick placement for slot {slot_idx}",
                    "Add another category will not commit without one; manual tick required",
                )
                break

            # Click "Add another category" to COMMIT this slot's selection.
            # This is non-obvious: the button name suggests "add a new slot"
            # but it's also what persists the current selection. Without this,
            # the dropdown values stay staged and Save discards them.
            try:
                page.get_by_role(
                    "button", name="Add another category", exact=False
                ).first.click(timeout=FIELD_TIMEOUT_MS)
                _time.sleep(1.5)
                picked += 1
            except Exception as e:
                _log(
                    f"could not commit slot {slot_idx}",
                    f"Add another category click failed: {e}",
                )
                break
        else:
            # Incomplete slot — break out rather than commit a partial pick.
            _log(
                "category slot aborted",
                f"slot {slot_idx} incomplete; stopping",
            )
            break

    # Save — scope to the dialog so we hit the right button (not any Save
    # elsewhere on the page). Longer sleep after save to let KDP's AJAX
    # update the Details page's category display.
    try:
        page.locator("[role='dialog']").get_by_role(
            "button", name="Save categories", exact=False
        ).first.click(timeout=FIELD_TIMEOUT_MS)
        _time.sleep(3)
    except Exception as e:
        _log("Save categories button not found", f"click manually; {e}")

    return picked


def _fill_details(page: Any, meta: dict[str, Any]) -> None:
    """Pre-fill the Details step. Fields filled: title, subtitle, author, description,
    keywords, publishing-rights = owned, AI-content disclosure. Categories, series,
    edition, and primary audience are left for the human to fill.

    Uses id-based CSS selectors (verified against the live /title-setup/paperback/
    new/details page) rather than labels — KDP's inputs have no visible label
    elements. Each field has a 5-second cap; a missed field logs and the human
    fills it in the open browser.
    """
    _log("details step", "filling text fields")
    if not _try_fill_selector(
        page, SELECTORS.details_title_input_id, str(meta["title"])
    ):
        _log("title field not found", "fill manually in the browser")
    if meta.get("subtitle") and not _try_fill_selector(
        page, SELECTORS.details_subtitle_input_id, str(meta["subtitle"])
    ):
        _log("subtitle field not found", "fill manually in the browser")

    author = str(meta["author"]).strip()
    first, _, last = author.partition(" ")
    if not _try_fill_selector(page, SELECTORS.details_author_first_name_id, first):
        _log("author first-name field not found", "fill manually in the browser")
    if last and not _try_fill_selector(
        page, SELECTORS.details_author_last_name_id, last
    ):
        _log("author last-name field not found", "fill manually in the browser")

    if meta.get("description"):
        if not _fill_rich_text_iframe(
            page, SELECTORS.details_description_iframe_title, str(meta["description"])
        ):
            _log("description iframe not found", "fill manually in the browser")

    # Publishing rights — "I own the copyright and I hold necessary publishing rights".
    if not _try_check_selector(
        page, SELECTORS.details_publishing_rights_owned_radio_id
    ):
        _log("publishing-rights radio not found", "select manually in the browser")

    # Low-content book — coloring books ARE low-content; always check.
    if not _try_check_selector(page, SELECTORS.details_low_content_checkbox_id):
        _log("low-content checkbox not found", "tick manually in the browser")

    # Large-print book — enable when the title or subtitle suggests it.
    title_sub = (
        str(meta.get("title", "")) + " " + str(meta.get("subtitle", ""))
    ).lower()
    if any(
        hint in title_sub
        for hint in ("large print", "large-print", "easy to see", "extra-large")
    ):
        if not _try_check_selector(page, SELECTORS.details_large_print_checkbox_id):
            _log("large-print checkbox not found", "tick manually in the browser")

    # Adult (sexually explicit) content — always No for our catalog.
    if not _try_check_selector(page, SELECTORS.details_adult_content_no_radio):
        _log("adult-content No radio not found", "select manually in the browser")

    # Keywords — 0-indexed (keywords-0 through keywords-6), 7 slots total.
    for i, kw in enumerate(normalize_keywords(meta.get("keywords") or [])):
        selector = f"{SELECTORS.details_keyword_input_id_prefix}{i}"
        if not _try_fill_selector(page, selector, kw):
            _log("keyword slot not found", f"{selector} (stopping fill)")
            break

    # Categories — walk up to 3 cascading dropdown paths from book.yaml via
    # the facade-click flow. Each path requires: pick dropdowns → tick ≥1
    # Placement checkbox → click "Add another category" (which is actually
    # the commit button) → repeat. Save Categories at the end persists all
    # committed placements.
    kdp_cats = meta.get("kdp_categories") or []
    kdp_placements = meta.get("kdp_placements") or []
    if kdp_cats:
        picked = _pick_categories(page, kdp_cats, kdp_placements)
        _log("categories", f"picked {picked} of {len(kdp_cats)} paths")
    else:
        _log("categories", "no kdp_categories in book.yaml; pick manually")

    # AI disclosure — not on Details step on current KDP UI (2026-10). May appear
    # on Content or Pricing step, or at Submit for Review. Probe + patch per-step
    # as encountered. For now, no attempt here (no false failure log).

    _log(
        "details step",
        "auto-fill done; still manual in browser: Primary Audience "
        "and any AI disclosure prompts on later steps",
    )


def _verify_trim_size_display(page: Any, expected_trim: str) -> None:
    """Read the Content page's Trim Size display and log whether it matches.

    KDP's new-paperback Content step shows the trim as read-only text in a
    sibling of the "Trim Size" h3 heading (`div.css-1h2ruwl`, verified
    2026-10-11 against the live /print-setup page). There is no change
    button, no radio group, and no picker modal — the trim is fixed at the
    draft's creation and defaults to 8.5 x 11. Our catalog is 100% 8.5x11,
    so this helper only verifies and warns on drift.

    Args:
        page: Playwright page already on the Content step.
        expected_trim: Expected trim string from book.yaml (e.g. "8.5x11").
    """
    assert expected_trim, "expected_trim must be a non-empty string"
    try:
        displayed = (
            page.locator("div.css-1h2ruwl").first.inner_text(timeout=FIELD_TIMEOUT_MS)
        ).strip()
    except Exception as e:
        _log(
            "trim size",
            f"display not found; verify manually: expected '{expected_trim}' ({e})",
        )
        return

    # Normalize both sides for the match: drop spaces, "in", "cm", punctuation.
    def _norm(s: str) -> str:
        return "".join(c for c in s.lower() if c.isdigit() or c == ".")

    want = _norm(expected_trim)
    got_prefix = _norm(displayed.split("(")[0])  # ignore the cm block in parens
    if want and want in got_prefix:
        _log("trim size", f"ok: displayed '{displayed}' matches '{expected_trim}'")
    else:
        _log(
            "trim size",
            f"MISMATCH: displayed '{displayed}' != expected '{expected_trim}'; "
            "trim is set at draft creation and cannot be changed on Content page",
        )


def _fill_content_and_upload(
    page: Any,
    meta: dict[str, Any],
    interior_pdf: Path,
    cover_pdf: Path,
) -> None:
    """Pre-fill the Content step: ISBN, paper, bleed, cover finish, AI, uploads.

    Trim size is read-only on this page (set at draft creation, defaults to
    8.5x11); the helper only verifies that the displayed trim matches
    book.yaml and logs a warning on drift. Both file inputs are hidden
    behind custom upload buttons but `set_input_files` works on hidden
    inputs so no click is needed.
    """
    _log("content step", "filling radios")

    # ISBN — use the free KDP ISBN (don't bring your own).
    if not _try_check_selector(page, SELECTORS.content_isbn_free_radio):
        _log("isbn free radio not found", "pick manually")

    # Paper type → ink-paper radio.
    paper = meta.get("paper", "white")
    paper_radio = _PAPER_TO_PAPER_RADIO.get(paper)
    if paper_radio and not _try_check_selector(page, paper_radio):
        _log(f"paper radio '{paper_radio}' not found", "pick manually")

    # Bleed — book.yaml governs; default to no-bleed (market standard).
    bleed = bool(meta.get("bleed", False))
    bleed_radio = (
        SELECTORS.content_bleed_yes_radio if bleed else SELECTORS.content_bleed_no_radio
    )
    if not _try_check_selector(page, bleed_radio):
        _log(f"bleed radio '{bleed_radio}' not found", "pick manually")

    # Cover finish — matte is the market default for coloring books.
    if not _try_check_selector(page, SELECTORS.content_cover_finish_matte_radio):
        _log("cover finish Matte radio not found", "pick manually")

    # Cover choice — we have a pre-made cover.pdf; pick Upload.
    if not _try_check_selector(page, SELECTORS.content_cover_upload_choice_radio):
        _log("cover-choice Upload radio not found", "pick manually")

    # AI content disclosure — moved to Content step. Images are always AI.
    ai = meta.get("ai_disclosure") or {}
    ai_radio = (
        SELECTORS.content_ai_yes_radio
        if ai.get("images")
        else SELECTORS.content_ai_no_radio
    )
    if not _try_check_selector(page, ai_radio):
        _log(f"AI content radio '{ai_radio}' not found", "pick manually")

    # Trim size — KDP paperback defaults to 8.5 x 11 on new drafts. The
    # Content page displays the trim as read-only text (div.css-1h2ruwl)
    # alongside the "Trim Size" h3 — there is no adjacent change button or
    # radio group. Verified against live page 2026-10-11: the display shows
    # "8.5 x 11 in ( 21.59 x 27.94 cm )" with no clickable siblings. If the
    # book requires a non-default trim, that choice must be made at book
    # creation time (not on the Content page), so this step only verifies.
    _verify_trim_size_display(page, meta.get("trim_size", "8.5x11"))

    # File uploads — the file inputs are hidden behind custom buttons.
    # Playwright's set_input_files() works on hidden inputs; no need to click
    # the visible button.
    try:
        page.locator(SELECTORS.content_interior_upload_input).first.set_input_files(
            str(interior_pdf), timeout=FIELD_TIMEOUT_MS
        )
        _log(
            "upload",
            f"interior.pdf set ({interior_pdf.stat().st_size // (1024 * 1024)} MB)",
        )
    except Exception as e:
        _log("interior upload input not found", f"upload manually: {e}")

    try:
        page.locator(SELECTORS.content_cover_upload_input).first.set_input_files(
            str(cover_pdf), timeout=FIELD_TIMEOUT_MS
        )
        _log(
            "upload", f"cover.pdf set ({cover_pdf.stat().st_size // (1024 * 1024)} MB)"
        )
    except Exception as e:
        _log("cover upload input not found", f"upload manually: {e}")

    _log(
        "content step",
        "radios + uploads auto-filled; wait for KDP to process uploads before launching previewer",
    )


def _fill_pricing(page: Any, meta: dict[str, Any]) -> None:
    """Pre-fill the Pricing step: territories = worldwide, prices from book.yaml.

    Fills explicit USD/GBP/EUR prices from `book.yaml`. For every other
    marketplace (CAD, JPY, AUD, PLN, SEK), clicks "Base this price on
    Amazon.com" so KDP auto-converts from the USD price. The 7 EUR inputs
    share one id (`#price-input-eur`) because EUR covers DE/FR/ES/IT/NL/PL BE/IE;
    each one is filled individually so KDP accepts the explicit value instead
    of inferring from Amazon.com.

    Royalty tier, expanded distribution, and T&C acknowledgement render only
    after a price is entered — those remain a human-review step. The script
    never clicks Publish Your Paperback Book.

    Args:
        page: Playwright page already on the Pricing step.
        meta: Loaded metadata dict with `price_usd`, `price_gbp`, `price_eur`.
    """
    assert meta, "meta must be a non-empty dict"
    _log("pricing step", "filling territories + prices")

    price_usd = meta.get("price_usd")
    assert price_usd, (
        "price_usd missing from book.yaml — refusing to publish without an explicit price"
    )
    price_gbp = meta.get("price_gbp")
    price_eur = meta.get("price_eur")

    # Territories — worldwide rights (the default for self-published coloring books).
    if not _try_check_selector(page, SELECTORS.pricing_territories_worldwide_radio):
        _log("worldwide-rights radio not found", "pick manually")

    # USD must be filled first — KDP uses it as the FX anchor for "Base on Amazon.com".
    if not _try_fill_selector(page, SELECTORS.pricing_usd_input, f"{price_usd:.2f}"):
        _log("USD price input not found", "fill manually")
        return

    # Click every "Base this price on Amazon.com" button so KDP auto-converts
    # the 5 marketplaces we don't explicitly price (CAD, JPY, AUD, PLN, SEK)
    # plus the GBP and EUR fields we will then overwrite with book.yaml values.
    try:
        buttons = page.get_by_role(
            "link", name=SELECTORS.pricing_base_on_amazon_button, exact=False
        ).all()
        clicked = 0
        for btn in buttons:
            try:
                if btn.is_visible():
                    btn.click(timeout=FIELD_TIMEOUT_MS)
                    clicked += 1
            except Exception:
                continue
        _log("pricing", f"clicked {clicked} 'Base on Amazon.com' buttons")
    except Exception as e:
        _log("Base on Amazon.com buttons not found", str(e))

    # Overwrite GBP + EUR with explicit book.yaml values (if provided).
    if price_gbp and not _try_fill_selector(
        page, SELECTORS.pricing_gbp_input, f"{price_gbp:.2f}"
    ):
        _log("GBP price input not found", "fill manually")

    if price_eur:
        # 7 EUR inputs share one id — fill each via .all().
        try:
            eur_inputs = page.locator(SELECTORS.pricing_eur_input).all()
            filled = 0
            for inp in eur_inputs:
                try:
                    if inp.is_visible():
                        inp.fill(f"{price_eur:.2f}", timeout=FIELD_TIMEOUT_MS)
                        filled += 1
                except Exception:
                    continue
            _log("pricing", f"filled {filled} EUR inputs with {price_eur:.2f}")
        except Exception as e:
            _log("EUR price inputs not found", str(e))

    _log(
        "pricing step",
        "prices filled; royalty tier + T&C + Publish are manual review steps",
    )


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
            # Create is an <a href> link ("+ Create new title or series"), not a button.
            # Clicking it navigates to /en_US/create — a chooser page with three
            # format buttons: "Create eBook", "Create paperback", "Create hardcover".
            page.locator('a[href*="dualbookshelf.createnew"]').first.click(
                timeout=10000
            )
            page.wait_for_url("**/create**", timeout=10000)
            # Click the "Create paperback" button (lowercase "paperback" — exact match
            # from the live KDP /create page as of 2026-10).
            page.get_by_role(
                "button", name="Create paperback", exact=False
            ).first.click(timeout=10000)
            # Wait for the Details page to load — URL typically contains /title-setup/paperback.
            page.wait_for_url("**/title-setup/paperback/**", timeout=15000)
        except Exception as e:
            _log(
                "could not reach the paperback wizard",
                f"update SELECTORS and retry; last error: {e}",
            )
            ctx.close()
            return 3

        page.wait_for_load_state("domcontentloaded")
        import time as _time

        _time.sleep(3)  # let the Details form render fully
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
            "paused on Content step. Verify uploads + launch previewer, then "
            "click 'Save and Continue' to proceed to Pricing — the script will "
            "fill prices automatically when the page lands.",
            file=sys.stderr,
        )
        try:
            page.wait_for_url("**/pricing**", timeout=0)
        except Exception:
            ctx.close()
            return 0
        page.wait_for_load_state("domcontentloaded")
        import time as _time2

        _time2.sleep(4)  # let the Pricing form render fully
        _fill_pricing(page, meta)
        print(
            "paused on Pricing step. Review royalty tier, expanded distribution, "
            "and T&C acknowledgement, then click 'Publish Your Paperback Book' "
            "manually. The script never clicks Publish.",
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
