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
    images = sorted(
        p for p in image_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS
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


def build_interior(
    interiors: list[Path], trim: tuple[float, float], outpath: Path
) -> int:
    """Write a KDP-ready interior PDF with one image per page.

    Each page is sized (trim + 2*bleed) and the image is centered scale-to-fit
    on a white background so the full image is preserved. Pages with content
    extending to the trim edge should have the border already inset slightly
    inside the image (the /image-book border template does this).

    Args:
        interiors: Interior page images, in print order.
        trim: (width_in, height_in) of the final trim.
        outpath: Destination PDF path.

    Returns:
        Page count written.
    """
    assert interiors, "interiors must be non-empty"
    page_w_pt = _in_to_pt(trim[0] + 2 * BLEED_IN)
    page_h_pt = _in_to_pt(trim[1] + 2 * BLEED_IN)
    c = Canvas(str(outpath), pagesize=(page_w_pt, page_h_pt))
    for img in interiors:
        # White background so letterbox strips (if any) blend into the page.
        c.setFillColorRGB(1, 1, 1)
        c.rect(0, 0, page_w_pt, page_h_pt, stroke=0, fill=1)
        _draw_image_fit(c, img, (0, 0, page_w_pt, page_h_pt))
        c.showPage()
    c.save()
    assert outpath.is_file() and outpath.stat().st_size > 0, "interior PDF not written"
    return len(interiors)


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
    c.setFillColor(HexColor(bg_hex))
    c.rect(0, 0, full_w, full_h, stroke=0, fill=1)

    # Back cover text block, inset by 0.5" from the trim edges.
    back_safe_x = _in_to_pt(BLEED_IN + 0.5)
    back_safe_y_top = _in_to_pt(trim_h + BLEED_IN - 0.5)
    back_width_pt = _in_to_pt(trim_w - 1.0)
    description = str(metadata.get("description", "")).strip()
    if description:
        _draw_wrapped_text(
            c,
            description,
            x=back_safe_x,
            y=back_safe_y_top,
            width=back_width_pt,
            font="Helvetica",
            size=11,
            leading=14,
            color_hex=metadata.get("cover_text_color", "#000000"),
        )

    # Spine text: only if spine is wide enough to be legible (≥ 0.125").
    if spine_in >= 0.125:
        spine_x = _in_to_pt(BLEED_IN + trim_w)
        spine_center_x = spine_x + _in_to_pt(spine_in) / 2
        c.saveState()
        c.setFillColor(HexColor(metadata.get("cover_text_color", "#000000")))
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
    page_count = int(metadata.get("page_count") or len(interiors))
    try:
        spine_in = compute_spine(page_count, metadata["paper"])
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    warnings: list[str] = []
    warnings.extend(_preflight_dpi(cover, trim[0] + BLEED_IN, trim[1] + 2 * BLEED_IN))
    for p in interiors:
        warnings.extend(
            _preflight_dpi(p, trim[0] + 2 * BLEED_IN, trim[1] + 2 * BLEED_IN)
        )

    interior_pdf = outdir / "interior.pdf"
    cover_pdf = outdir / "cover.pdf"
    metadata_json = outdir / "metadata.json"

    pages = build_interior(interiors, trim, interior_pdf)
    build_cover(cover, metadata, trim, spine_in, cover_pdf)

    normalized = {
        **metadata,
        "page_count": page_count,
        "spine_width_in": round(spine_in, 4),
        "trim_width_in": trim[0],
        "trim_height_in": trim[1],
        "bleed_in": BLEED_IN,
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
