#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pillow>=10",
#   "reportlab>=4",
#   "pyyaml>=6",
# ]
# ///
"""Compose KDP-ready paperback PDFs from an image-book output directory.

Reads a `book.yaml` for metadata, discovers cover + interior images under the
input directory, and emits:

  <outdir>/interior.pdf   -- one image per page, trim + 0.125" bleed on all sides
  <outdir>/cover.pdf       -- back + spine + front spread with outer bleed
  <outdir>/metadata.json  -- normalized metadata + computed spine width

Dimensions follow KDP's paperback submission guidelines:
  https://kdp.amazon.com/en_US/help/topic/G201834180 (cover calculator)
  https://kdp.amazon.com/en_US/help/topic/G201953020 (cover)
  https://kdp.amazon.com/en_US/help/topic/G201857950 (interior)

The script does not upload to KDP. Upload is phase 2 (browser automation).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml
from PIL import Image
from reportlab.lib.colors import HexColor
from reportlab.pdfgen.canvas import Canvas

BLEED_IN = 0.125
DPI = 300
PT_PER_IN = 72.0

MIN_PAGES = 24
MAX_PAGES = 828

# KDP paperback trim sizes (width_in, height_in). Portrait orientations only;
# the script does not currently support landscape layouts.
TRIM_SIZES: dict[str, tuple[float, float]] = {
    "5x8": (5.0, 8.0),
    "5.25x8": (5.25, 8.0),
    "5.5x8.5": (5.5, 8.5),
    "6x9": (6.0, 9.0),
    "6.14x9.21": (6.14, 9.21),
    "6.69x9.61": (6.69, 9.61),
    "7x10": (7.0, 10.0),
    "7.44x9.69": (7.44, 9.69),
    "7.5x9.25": (7.5, 9.25),
    "8x10": (8.0, 10.0),
    "8.25x6": (8.25, 6.0),
    "8.25x8.25": (8.25, 8.25),
    "8.5x8.5": (8.5, 8.5),
    "8.5x11": (8.5, 11.0),
    "8.27x11.69": (8.27, 11.69),  # A4
}

# Inches of spine thickness per interior page, per paper option.
# From the KDP cover calculator reference values.
SPINE_PER_PAGE: dict[str, float] = {
    "white": 0.002252,
    "cream": 0.0025,
    "color-standard": 0.002252,
    "color-premium": 0.002347,
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested)
# ---------------------------------------------------------------------------


def trim_box(name: str) -> tuple[float, float]:
    """Return (width_in, height_in) for a named KDP paperback trim size.

    Args:
        name: Key from TRIM_SIZES, e.g. "8.5x11".

    Returns:
        Trim width and height in inches.

    Raises:
        ValueError: If `name` is not a recognized trim size.
    """
    assert isinstance(name, str) and name, "trim name must be a non-empty string"
    if name not in TRIM_SIZES:
        known = ", ".join(sorted(TRIM_SIZES))
        raise ValueError(f"unknown trim size '{name}' — known: {known}")
    return TRIM_SIZES[name]


def compute_spine(pages: int, paper: str) -> float:
    """Compute spine width in inches for the given interior page count and paper type.

    Args:
        pages: Number of interior pages (not sheets). Must be 24–828 inclusive.
        paper: One of "white", "cream", "color-standard", "color-premium".

    Returns:
        Spine width in inches.

    Raises:
        ValueError: If `pages` is outside KDP's accepted range or `paper` is unknown.
    """
    assert isinstance(pages, int), "pages must be int"
    if pages < MIN_PAGES:
        raise ValueError(f"page count {pages} below KDP minimum of {MIN_PAGES}")
    if pages > MAX_PAGES:
        raise ValueError(f"page count {pages} above KDP maximum of {MAX_PAGES}")
    if paper not in SPINE_PER_PAGE:
        known = ", ".join(sorted(SPINE_PER_PAGE))
        raise ValueError(f"unknown paper '{paper}' — known: {known}")
    return pages * SPINE_PER_PAGE[paper]


def discover_images(image_dir: Path) -> tuple[Path, list[Path]]:
    """Discover cover and interior images in an image-book output directory.

    The /image-book skill writes files with a 2-digit prefix: `00-cover.jpg`
    is the cover; `01-*.jpg`, `02-*.jpg`, ... are interior pages in print order.

    Args:
        image_dir: Directory containing the generated images.

    Returns:
        A tuple of (cover_path, [interior_paths]) sorted lexicographically.

    Raises:
        FileNotFoundError: If no `00-*` cover or no interior pages are present.
    """
    assert image_dir.is_dir(), f"not a directory: {image_dir}"
    # Underscore-prefixed files are reserved for internal/preview artifacts
    # (e.g. a cover.pdf preview PNG rendered next to the book) and must not
    # be treated as content pages.
    images = sorted(
        p
        for p in image_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS and not p.name.startswith("_")
    )
    cover = next((p for p in images if p.stem.startswith("00")), None)
    if cover is None:
        raise FileNotFoundError(
            f"no cover image (expected a file matching '00-*') under {image_dir}"
        )
    interiors = [p for p in images if p is not cover]
    if not interiors:
        raise FileNotFoundError(
            f"no interior images (expected '01-*', '02-*', ...) under {image_dir}"
        )
    return cover, interiors


_REQUIRED_FIELDS = ("title", "author", "trim_size", "paper")
_DEFAULTS: dict[str, Any] = {"language": "English"}


def load_metadata(yaml_path: Path) -> dict[str, Any]:
    """Load, validate, and normalize book metadata from a YAML file.

    Required fields: `title`, `author`, `trim_size`, `paper`. Unknown fields
    are preserved untouched so the downstream upload step can read them.

    Args:
        yaml_path: Path to the metadata YAML file.

    Returns:
        A dict with all required fields present and defaults filled in.

    Raises:
        FileNotFoundError: If `yaml_path` does not exist.
        ValueError: If any required field is missing or has an invalid value.
    """
    if not yaml_path.is_file():
        raise FileNotFoundError(f"metadata not found: {yaml_path}")
    raw = yaml.safe_load(yaml_path.read_text()) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"metadata must be a YAML mapping, got {type(raw).__name__}")
    missing = [f for f in _REQUIRED_FIELDS if f not in raw or raw[f] in (None, "")]
    if missing:
        raise ValueError(f"missing required metadata field(s): {', '.join(missing)}")
    # Validate value spaces that have fixed enumerations.
    trim_box(raw["trim_size"])  # raises ValueError on unknown trim
    if raw["paper"] not in SPINE_PER_PAGE:
        known = ", ".join(sorted(SPINE_PER_PAGE))
        raise ValueError(f"unknown paper '{raw['paper']}' — known: {known}")
    meta = {**_DEFAULTS, **raw}
    return meta


# ---------------------------------------------------------------------------
# PDF builders (integration-tested via CLI invocation)
# ---------------------------------------------------------------------------


def _in_to_pt(x: float) -> float:
    """Convert inches to PDF points (72 pts per inch)."""
    return x * PT_PER_IN


def _draw_image_fit(
    c: Canvas, image_path: Path, box: tuple[float, float, float, float]
) -> None:
    """Draw an image centered inside `box` (x, y, w, h in points), scale-to-fit.

    Preserves aspect ratio; empty strips (if any) are left transparent so the
    page background shows through. The caller is responsible for the background.
    """
    x, y, w, h = box
    assert w > 0 and h > 0, f"box must have positive dimensions: {box}"
    with Image.open(image_path) as im:
        iw, ih = im.size
    scale = min(w / iw, h / ih)
    draw_w, draw_h = iw * scale, ih * scale
    draw_x = x + (w - draw_w) / 2
    draw_y = y + (h - draw_h) / 2
    c.drawImage(
        str(image_path),
        draw_x,
        draw_y,
        width=draw_w,
        height=draw_h,
        preserveAspectRatio=True,
        anchor="c",
        mask="auto",
    )


INNER_SAFE_MARGIN_IN = 0.25

# Default matter page counts when include_matter=True. Front matter:
# title / copyright / belongs-to / intro. Back matter: thanks + review ask.
DEFAULT_FRONT_MATTER_COUNT = 4
DEFAULT_BACK_MATTER_COUNT = 1

DEFAULT_INTRO_TEXT = (
    "This book uses thick, bold lines designed to work with any marker, "
    "pencil, or crayon. Each coloring page is printed single-sided so your "
    "markers won't bleed through to the next design. If you use alcohol "
    "markers or very wet media, place a sheet of scrap paper or cardstock "
    "behind the page as an extra safeguard.\n\n"
    "Take your time — these pages are made for slow, relaxing coloring. "
    "Happy coloring!"
)

DEFAULT_THANKS_TEXT = (
    "Thank you for coloring with us!\n\n"
    "If you enjoyed this book, please take a moment to leave an honest "
    "review on Amazon. Reviews help other colorists discover independent "
    "books like this one, and they mean the world to us.\n\n"
    "Happy coloring!"
)


def physical_page_count(
    *,
    image_count: int,
    single_sided: bool,
    front_matter_count: int = 0,
    back_matter_count: int = 0,
) -> int:
    """Return the number of printed pages for a given image count and layout.

    Args:
        image_count: Number of coloring-image pages (one image per visible page).
        single_sided: When True, a blank backing page is inserted after each
            content page so markers do not bleed through. KDP reports this
            doubled page count on the paperback listing.
        front_matter_count: Content pages at the front (title, copyright,
            belongs-to, intro). Each follows the same single-sided layout
            rule as image pages.
        back_matter_count: Content pages at the back (thanks + review ask).

    Returns:
        The physical page count KDP will see on upload.
    """
    assert image_count > 0, "image_count must be positive"
    assert front_matter_count >= 0 and back_matter_count >= 0, (
        "matter counts must be non-negative"
    )
    total_content = image_count + front_matter_count + back_matter_count
    return total_content * 2 if single_sided else total_content


def _draw_blank_page(c: Canvas, page_w_pt: float, page_h_pt: float) -> None:
    """Draw a plain white page and advance to the next page."""
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, page_w_pt, page_h_pt, stroke=0, fill=1)
    c.showPage()


def _draw_centered_text(
    c: Canvas,
    text: str,
    *,
    cx: float,
    cy: float,
    font: str,
    size: int,
) -> None:
    """Draw a single line of text horizontally centered on (cx, cy)."""
    c.setFont(font, size)
    c.drawCentredString(cx, cy, text)


def _draw_title_page(
    c: Canvas, metadata: dict[str, Any], page: tuple[float, float]
) -> None:
    """Front matter: title + subtitle + author, centered vertically.

    Mirrors the cover's wording but in clean typeset form so the printed
    book has a proper title page behind the cover.
    """
    w, h = page
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, w, h, stroke=0, fill=1)
    c.setFillColorRGB(0.1, 0.1, 0.1)
    cx = w / 2
    _draw_centered_text(
        c, str(metadata["title"]), cx=cx, cy=h * 0.60, font="Helvetica-Bold", size=36
    )
    subtitle = str(metadata.get("subtitle") or "").strip()
    if subtitle:
        _draw_centered_text(c, subtitle, cx=cx, cy=h * 0.54, font="Helvetica", size=16)
    _draw_centered_text(
        c, str(metadata["author"]), cx=cx, cy=h * 0.42, font="Helvetica", size=18
    )
    c.showPage()


def _draw_copyright_page(
    c: Canvas, metadata: dict[str, Any], page: tuple[float, float]
) -> None:
    """Copyright page: © Year Author, rights notice, optional publisher/ISBN."""
    w, h = page
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, w, h, stroke=0, fill=1)
    c.setFillColorRGB(0.1, 0.1, 0.1)
    cx = w / 2
    year = metadata.get("copyright_year") or _current_year()
    lines = [
        (f"Copyright © {year} {metadata['author']}", "Helvetica", 11),
        ("All rights reserved.", "Helvetica", 10),
        ("", "Helvetica", 10),
        (
            "No part of this book may be reproduced, stored in a retrieval system,",
            "Helvetica",
            9,
        ),
        (
            "or transmitted in any form or by any means without prior written",
            "Helvetica",
            9,
        ),
        ("permission from the author.", "Helvetica", 9),
    ]
    if metadata.get("publisher"):
        lines.extend(
            [
                ("", "Helvetica", 10),
                (f"Published by {metadata['publisher']}", "Helvetica", 10),
            ]
        )
    if metadata.get("isbn"):
        lines.extend(
            [
                ("", "Helvetica", 10),
                (f"ISBN: {metadata['isbn']}", "Helvetica", 10),
            ]
        )
    y_cursor = h * 0.55
    for text, font, size in lines:
        if text:
            _draw_centered_text(c, text, cx=cx, cy=y_cursor, font=font, size=size)
        y_cursor -= size + 4
    c.showPage()


def _draw_belongs_to_page(c: Canvas, page: tuple[float, float]) -> None:
    """Belongs-to page: decorative header + two writable lines (name, date)."""
    w, h = page
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, w, h, stroke=0, fill=1)
    c.setFillColorRGB(0.1, 0.1, 0.1)
    cx = w / 2
    _draw_centered_text(
        c, "This book belongs to:", cx=cx, cy=h * 0.70, font="Helvetica-Bold", size=22
    )
    c.setFont("Helvetica", 14)
    label_x = w * 0.25
    line_x_start = w * 0.35
    line_x_end = w * 0.80
    for label, y in (("Name:", h * 0.58), ("Date:", h * 0.48)):
        c.drawString(label_x, y, label)
        c.setLineWidth(0.75)
        c.line(line_x_start, y - 3, line_x_end, y - 3)
    c.showPage()


def _draw_intro_page(
    c: Canvas, metadata: dict[str, Any], page: tuple[float, float]
) -> None:
    """Intro page: how-to text block."""
    w, h = page
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, w, h, stroke=0, fill=1)
    c.setFillColorRGB(0.1, 0.1, 0.1)
    cx = w / 2
    _draw_centered_text(
        c, "How to Color", cx=cx, cy=h * 0.80, font="Helvetica-Bold", size=22
    )
    text = str(metadata.get("intro_text") or DEFAULT_INTRO_TEXT)
    _draw_wrapped_paragraph(
        c,
        text,
        x=w * 0.15,
        y=h * 0.70,
        width=w * 0.70,
        font="Helvetica",
        size=12,
        leading=16,
    )
    c.showPage()


def _draw_thanks_page(
    c: Canvas, metadata: dict[str, Any], page: tuple[float, float]
) -> None:
    """Back matter: thank you + review ask."""
    w, h = page
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, w, h, stroke=0, fill=1)
    c.setFillColorRGB(0.1, 0.1, 0.1)
    cx = w / 2
    _draw_centered_text(
        c, "Thank You!", cx=cx, cy=h * 0.75, font="Helvetica-Bold", size=28
    )
    text = str(metadata.get("thanks_text") or DEFAULT_THANKS_TEXT)
    _draw_wrapped_paragraph(
        c,
        text,
        x=w * 0.15,
        y=h * 0.65,
        width=w * 0.70,
        font="Helvetica",
        size=13,
        leading=18,
    )
    c.showPage()


def _draw_wrapped_paragraph(
    c: Canvas,
    text: str,
    *,
    x: float,
    y: float,
    width: float,
    font: str,
    size: int,
    leading: int,
) -> None:
    """Draw a word-wrapped paragraph with blank-line paragraph breaks."""
    c.setFont(font, size)
    cursor_y = y
    for paragraph in text.split("\n\n"):
        words = paragraph.split()
        line: list[str] = []
        for w in words:
            trial = " ".join([*line, w])
            if c.stringWidth(trial, font, size) <= width:
                line.append(w)
                continue
            c.drawString(x, cursor_y, " ".join(line))
            cursor_y -= leading
            line = [w]
        if line:
            c.drawString(x, cursor_y, " ".join(line))
            cursor_y -= leading
        cursor_y -= leading / 2


def _current_year() -> int:
    """Return the current calendar year — isolated so tests can patch it."""
    from datetime import datetime

    return datetime.now().year


def build_interior(
    interiors: list[Path],
    trim: tuple[float, float],
    outpath: Path,
    *,
    single_sided: bool = True,
    bleed: bool = True,
    metadata: dict[str, Any] | None = None,
    include_matter: bool = False,
) -> int:
    """Write a KDP-ready interior PDF with one image per visible page.

    When `single_sided=True` (the default for coloring books), a blank page is
    inserted after each content page so markers do not bleed through — KDP
    requires this layout for coloring books.

    When `bleed=True`, each page is sized `trim + 2*0.125"` and the image fills
    the full bleed box, so decoration can extend past the trim line. When
    `bleed=False` (the market default for ~95% of adult coloring books), the
    page is sized exactly to trim and the image is inset by a 0.25" safe
    margin so no content is trimmed off at the edge.

    When `include_matter=True`, prepends 4 front-matter pages (title, copyright,
    "this book belongs to", intro) and appends 1 back-matter page (thanks + review
    ask). All matter pages follow the same `single_sided` layout rule as image
    pages. `metadata` is required when `include_matter=True`.

    Args:
        interiors: Interior page images, in print order.
        trim: (width_in, height_in) of the final trim.
        outpath: Destination PDF path.
        single_sided: Insert a blank backing page after each content page.
        bleed: Extend the page by 0.125" on all sides; otherwise inset the image
            by a 0.25" safe margin inside the trim.
        metadata: Book metadata dict. Required when `include_matter=True`.
        include_matter: Prepend front matter + append back matter.

    Returns:
        Physical page count written.

    Raises:
        ValueError: If `include_matter=True` but `metadata` is None.
    """
    assert interiors, "interiors must be non-empty"
    if include_matter and metadata is None:
        raise ValueError("metadata is required when include_matter=True")
    if bleed:
        page_w_pt = _in_to_pt(trim[0] + 2 * BLEED_IN)
        page_h_pt = _in_to_pt(trim[1] + 2 * BLEED_IN)
        image_box = (0.0, 0.0, page_w_pt, page_h_pt)
    else:
        page_w_pt = _in_to_pt(trim[0])
        page_h_pt = _in_to_pt(trim[1])
        margin_pt = _in_to_pt(INNER_SAFE_MARGIN_IN)
        image_box = (
            margin_pt,
            margin_pt,
            page_w_pt - 2 * margin_pt,
            page_h_pt - 2 * margin_pt,
        )
    page_size = (page_w_pt, page_h_pt)
    c = Canvas(str(outpath), pagesize=page_size)

    front_count = DEFAULT_FRONT_MATTER_COUNT if include_matter else 0
    back_count = DEFAULT_BACK_MATTER_COUNT if include_matter else 0

    if include_matter:
        assert metadata is not None  # for the type checker; validated above
        _draw_title_page(c, metadata, page_size)
        if single_sided:
            _draw_blank_page(c, page_w_pt, page_h_pt)
        _draw_copyright_page(c, metadata, page_size)
        if single_sided:
            _draw_blank_page(c, page_w_pt, page_h_pt)
        _draw_belongs_to_page(c, page_size)
        if single_sided:
            _draw_blank_page(c, page_w_pt, page_h_pt)
        _draw_intro_page(c, metadata, page_size)
        if single_sided:
            _draw_blank_page(c, page_w_pt, page_h_pt)

    for img in interiors:
        c.setFillColorRGB(1, 1, 1)
        c.rect(0, 0, page_w_pt, page_h_pt, stroke=0, fill=1)
        _draw_image_fit(c, img, image_box)
        c.showPage()
        if single_sided:
            _draw_blank_page(c, page_w_pt, page_h_pt)

    if include_matter:
        assert metadata is not None
        _draw_thanks_page(c, metadata, page_size)
        if single_sided:
            _draw_blank_page(c, page_w_pt, page_h_pt)

    c.save()
    assert outpath.is_file() and outpath.stat().st_size > 0, "interior PDF not written"
    return physical_page_count(
        image_count=len(interiors),
        single_sided=single_sided,
        front_matter_count=front_count,
        back_matter_count=back_count,
    )


def build_cover(
    cover_image: Path,
    metadata: dict[str, Any],
    trim: tuple[float, float],
    spine_in: float,
    outpath: Path,
) -> None:
    """Write a KDP-ready cover spread PDF.

    Spread layout, left to right:
        [bleed][back_trim][spine][front_trim][bleed]
    with vertical bleed on top and bottom. The front cover image is placed in
    the right-hand region including the outer bleed. The back and spine use a
    solid background color (metadata.cover_bg_color, default white) with the
    title on the spine (only if spine is wide enough) and the description text
    on the back cover within a 0.5" inner safe margin.

    Args:
        cover_image: Front cover image.
        metadata: Normalized metadata dict from load_metadata.
        trim: (width_in, height_in) of the final trim.
        spine_in: Spine width in inches.
        outpath: Destination PDF path.
    """
    assert spine_in >= 0, "spine must be non-negative"
    trim_w, trim_h = trim
    full_w_in = 2 * trim_w + spine_in + 2 * BLEED_IN
    full_h_in = trim_h + 2 * BLEED_IN
    full_w = _in_to_pt(full_w_in)
    full_h = _in_to_pt(full_h_in)

    c = Canvas(str(outpath), pagesize=(full_w, full_h))

    bg_hex = metadata.get("cover_bg_color", "#FFFFFF")
    text_hex = metadata.get("cover_text_color", "#1A1A1A")

    # Background spans the entire spread (bleed to bleed).
    c.setFillColor(HexColor(bg_hex))
    c.rect(0, 0, full_w, full_h, stroke=0, fill=1)

    _draw_back_cover(c, metadata, trim, spine_in, bg_hex, text_hex)

    # Spine text: only if spine is wide enough to be legible (≥ 0.125").
    if spine_in >= 0.125:
        spine_x = _in_to_pt(BLEED_IN + trim_w)
        spine_center_x = spine_x + _in_to_pt(spine_in) / 2
        c.saveState()
        c.setFillColor(HexColor(text_hex))
        c.translate(spine_center_x, full_h / 2)
        c.rotate(90)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(0, -3, str(metadata["title"]))
        c.restoreState()

    # Front cover region: right side including the outer bleed.
    front_x_in = BLEED_IN + trim_w + spine_in
    front_box = (
        _in_to_pt(front_x_in),
        0,
        _in_to_pt(trim_w + BLEED_IN),
        full_h,
    )
    _draw_image_fit(c, cover_image, front_box)

    c.save()
    assert outpath.is_file() and outpath.stat().st_size > 0, "cover PDF not written"


# KDP reserves a 2.0" × 1.2" clear zone in the lower-right of the back cover
# for the auto-added barcode. Draw nothing inside this box.
BARCODE_CLEAR_W_IN = 2.0
BARCODE_CLEAR_H_IN = 1.2
BARCODE_CLEAR_MARGIN_IN = 0.25  # distance from trim edge to the barcode zone


def _draw_back_cover(
    c: Canvas,
    metadata: dict[str, Any],
    trim: tuple[float, float],
    spine_in: float,  # noqa: ARG001  # reserved for future spine-aware layouts
    bg_hex: str,
    text_hex: str,
) -> None:
    """Draw a professional back-cover panel: inset frame, title echo, subtitle,
    divider, description paragraphs, author byline, with the KDP barcode zone
    kept clear.

    Layout coordinates are in PDF points. The back cover occupies the left
    panel of the spread, inset by one bleed from the outer-left edge and
    extending to just before the spine on the inner-right edge.
    """
    trim_w, trim_h = trim
    bleed_pt = _in_to_pt(BLEED_IN)
    panel_x = bleed_pt  # outer-left of the back trim
    panel_y = bleed_pt  # bottom of the trim
    panel_w = _in_to_pt(trim_w)
    panel_h = _in_to_pt(trim_h)

    # Inset inner card — 0.4" cream rectangle inside the solid background,
    # giving the back a framed look that echoes the front cover.
    inner_margin = _in_to_pt(0.4)
    inner_x = panel_x + inner_margin
    inner_y = panel_y + inner_margin
    inner_w = panel_w - 2 * inner_margin
    inner_h = panel_h - 2 * inner_margin
    inner_bg_hex = metadata.get("cover_inner_bg_color", "#FFF8EC")
    c.setFillColor(HexColor(inner_bg_hex))
    c.rect(inner_x, inner_y, inner_w, inner_h, stroke=0, fill=1)

    # A thin accent rule inside the inner panel.
    c.setStrokeColor(HexColor(bg_hex))
    c.setLineWidth(3.0)
    c.rect(inner_x, inner_y, inner_w, inner_h, stroke=1, fill=0)

    # Content layout coordinates within the inner panel.
    text_margin_x = _in_to_pt(0.35)
    content_left = inner_x + text_margin_x
    content_right = inner_x + inner_w - text_margin_x
    content_width = content_right - content_left
    content_cx = (content_left + content_right) / 2
    content_top = inner_y + inner_h - _in_to_pt(0.5)

    c.setFillColor(HexColor(text_hex))

    # Title echo at top-center.
    title = str(metadata["title"])
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(content_cx, content_top, title)

    # Subtitle (if present) under the title.
    cursor_y = content_top - _in_to_pt(0.4)
    subtitle = str(metadata.get("subtitle") or "").strip()
    if subtitle:
        c.setFont("Helvetica-Oblique", 13)
        c.drawCentredString(content_cx, cursor_y, subtitle)
        cursor_y -= _in_to_pt(0.3)

    # Decorative divider rule.
    rule_half = _in_to_pt(1.2)
    c.setStrokeColor(HexColor(bg_hex))
    c.setLineWidth(1.5)
    c.line(content_cx - rule_half, cursor_y, content_cx + rule_half, cursor_y)
    cursor_y -= _in_to_pt(0.35)

    # Description paragraphs — left-aligned, up to one third of the panel.
    description = str(metadata.get("description") or "").strip()
    if description:
        c.setFont("Helvetica", 11)
        _draw_wrapped_paragraph(
            c,
            description,
            x=content_left,
            y=cursor_y,
            width=content_width,
            font="Helvetica",
            size=11,
            leading=15,
        )

    # Author bio + byline near the bottom, above the barcode clear zone.
    byline_y = inner_y + _in_to_pt(BARCODE_CLEAR_H_IN + BARCODE_CLEAR_MARGIN_IN + 0.2)
    author_bio = str(metadata.get("author_bio") or "").strip()
    if author_bio:
        c.setFont("Helvetica", 10)
        _draw_wrapped_paragraph(
            c,
            author_bio,
            x=content_left,
            y=byline_y + _in_to_pt(0.5),
            width=content_width
            - _in_to_pt(BARCODE_CLEAR_W_IN + BARCODE_CLEAR_MARGIN_IN),
            font="Helvetica",
            size=10,
            leading=13,
        )
    c.setFont("Helvetica-Bold", 12)
    c.drawString(content_left, byline_y, f"By {metadata['author']}")

    # Barcode clear zone — leave the lower-right 2.0 x 1.2 inch area of the
    # back trim empty. KDP overlays its auto-generated barcode here on upload.
    # We don't draw anything; we just document the zone and avoid overwriting it.
    # (This function already respected the zone by placing content above and
    # to the left of it.)


def _draw_wrapped_text(
    c: Canvas,
    text: str,
    *,
    x: float,
    y: float,
    width: float,
    font: str,
    size: int,
    leading: int,
    color_hex: str,
) -> None:
    """Draw a plain word-wrapped paragraph starting at (x, y), top-aligned."""
    c.setFillColor(HexColor(color_hex))
    c.setFont(font, size)
    words = text.split()
    line: list[str] = []
    cursor_y = y
    for w in words:
        trial = " ".join([*line, w])
        if c.stringWidth(trial, font, size) <= width:
            line.append(w)
            continue
        c.drawString(x, cursor_y, " ".join(line))
        cursor_y -= leading
        line = [w]
        if cursor_y < 0:
            return
    if line:
        c.drawString(x, cursor_y, " ".join(line))


# ---------------------------------------------------------------------------
# Preflight + CLI
# ---------------------------------------------------------------------------


def _preflight_dpi(
    image_path: Path, target_w_in: float, target_h_in: float
) -> list[str]:
    """Return a list of DPI warning strings for an image placed at target_in size.

    Does not raise — KDP accepts lower-DPI images with a warning, so this
    function surfaces advisories rather than blocking the build.
    """
    warnings: list[str] = []
    with Image.open(image_path) as im:
        iw, ih = im.size
    eff_dpi_w = iw / target_w_in
    eff_dpi_h = ih / target_h_in
    if min(eff_dpi_w, eff_dpi_h) < DPI:
        warnings.append(
            f"{image_path.name}: effective DPI {min(eff_dpi_w, eff_dpi_h):.0f} < {DPI} target"
        )
    return warnings


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    p.add_argument(
        "image_dir", type=Path, help="Directory of generated images (from /image-book)."
    )
    p.add_argument(
        "--metadata",
        type=Path,
        default=None,
        help="Path to book.yaml. Defaults to <image_dir>/book.yaml.",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory for interior.pdf, cover.pdf, metadata.json. Defaults to <image_dir>.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Build interior.pdf, cover.pdf, and metadata.json for a book."""
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    image_dir: Path = args.image_dir
    if not image_dir.is_dir():
        print(f"error: not a directory: {image_dir}", file=sys.stderr)
        return 2

    yaml_path: Path = args.metadata or (image_dir / "book.yaml")
    outdir: Path = args.out or image_dir
    outdir.mkdir(parents=True, exist_ok=True)

    try:
        metadata = load_metadata(yaml_path)
        cover, interiors = discover_images(image_dir)
    except (FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    trim = trim_box(metadata["trim_size"])
    single_sided = bool(metadata.get("single_sided", True))
    bleed = bool(metadata.get("bleed", True))
    include_matter = bool(metadata.get("include_matter", True))
    front_matter_count = DEFAULT_FRONT_MATTER_COUNT if include_matter else 0
    back_matter_count = DEFAULT_BACK_MATTER_COUNT if include_matter else 0
    computed_pages = physical_page_count(
        image_count=len(interiors),
        single_sided=single_sided,
        front_matter_count=front_matter_count,
        back_matter_count=back_matter_count,
    )
    page_count = int(metadata.get("page_count") or computed_pages)
    try:
        spine_in = compute_spine(page_count, metadata["paper"])
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    warnings: list[str] = []
    cover_target_w = trim[0] + BLEED_IN
    cover_target_h = trim[1] + 2 * BLEED_IN
    warnings.extend(_preflight_dpi(cover, cover_target_w, cover_target_h))
    if bleed:
        interior_target_w = trim[0] + 2 * BLEED_IN
        interior_target_h = trim[1] + 2 * BLEED_IN
    else:
        interior_target_w = trim[0] - 2 * INNER_SAFE_MARGIN_IN
        interior_target_h = trim[1] - 2 * INNER_SAFE_MARGIN_IN
    for p in interiors:
        warnings.extend(_preflight_dpi(p, interior_target_w, interior_target_h))

    interior_pdf = outdir / "interior.pdf"
    cover_pdf = outdir / "cover.pdf"
    metadata_json = outdir / "metadata.json"

    pages = build_interior(
        interiors,
        trim,
        interior_pdf,
        single_sided=single_sided,
        bleed=bleed,
        metadata=metadata,
        include_matter=include_matter,
    )
    build_cover(cover, metadata, trim, spine_in, cover_pdf)

    normalized = {
        **metadata,
        "page_count": page_count,
        "image_count": len(interiors),
        "single_sided": single_sided,
        "bleed": bleed,
        "include_matter": include_matter,
        "front_matter_count": front_matter_count,
        "back_matter_count": back_matter_count,
        "spine_width_in": round(spine_in, 4),
        "trim_width_in": trim[0],
        "trim_height_in": trim[1],
        "bleed_in": BLEED_IN if bleed else 0.0,
        "interior_pdf": str(interior_pdf.resolve()),
        "cover_pdf": str(cover_pdf.resolve()),
        "cover_source_image": str(cover.resolve()),
    }
    metadata_json.write_text(json.dumps(normalized, indent=2, sort_keys=True) + "\n")

    print(f"interior: {interior_pdf} ({pages} pages)")
    print(f'cover:    {cover_pdf} (spine {spine_in:.3f}")')
    print(f"metadata: {metadata_json}")
    if page_count < MIN_PAGES:
        print(
            f"warning: page_count {page_count} < KDP minimum {MIN_PAGES} — "
            f"interior PDF will be rejected on upload",
            file=sys.stderr,
        )
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
