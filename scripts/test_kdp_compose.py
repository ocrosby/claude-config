#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest>=8", "pyyaml>=6", "pillow>=10", "reportlab>=4", "pypdf>=5"]
# ///
"""Tests for kdp_compose.py pure helpers.

Black-box: tests exercise discover_images, load_metadata, trim_box, and
compute_spine through their public call signatures with real filesystem
input. The PDF-building functions are integration-tested by invoking the
script end-to-end against a fixture directory.

Run: scripts/test_kdp_compose.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import kdp_compose  # noqa: E402


# --- compute_spine ---------------------------------------------------------


def test_compute_spine_white_paper() -> None:
    assert kdp_compose.compute_spine(100, "white") == pytest.approx(0.2252)


def test_compute_spine_cream_paper() -> None:
    assert kdp_compose.compute_spine(100, "cream") == pytest.approx(0.25)


def test_compute_spine_color_premium() -> None:
    assert kdp_compose.compute_spine(100, "color-premium") == pytest.approx(0.2347)


def test_compute_spine_rejects_below_minimum() -> None:
    with pytest.raises(ValueError, match="minimum"):
        kdp_compose.compute_spine(23, "white")


def test_compute_spine_rejects_above_maximum() -> None:
    with pytest.raises(ValueError, match="maximum"):
        kdp_compose.compute_spine(829, "white")


def test_compute_spine_rejects_unknown_paper() -> None:
    with pytest.raises(ValueError, match="paper"):
        kdp_compose.compute_spine(100, "parchment")


# --- trim_box --------------------------------------------------------------


def test_trim_box_8_5x11() -> None:
    assert kdp_compose.trim_box("8.5x11") == (8.5, 11.0)


def test_trim_box_6x9() -> None:
    assert kdp_compose.trim_box("6x9") == (6.0, 9.0)


def test_trim_box_unknown() -> None:
    with pytest.raises(ValueError, match="trim"):
        kdp_compose.trim_box("99x99")


# --- discover_images -------------------------------------------------------


def test_discover_images_separates_cover(tmp_path: Path) -> None:
    (tmp_path / "00-cover.jpg").touch()
    (tmp_path / "01-page.jpg").touch()
    (tmp_path / "02-page.jpg").touch()
    cover, interiors = kdp_compose.discover_images(tmp_path)
    assert cover.name == "00-cover.jpg"
    assert [p.name for p in interiors] == ["01-page.jpg", "02-page.jpg"]


def test_discover_images_sorts_by_prefix(tmp_path: Path) -> None:
    (tmp_path / "00-cover.jpg").touch()
    (tmp_path / "10-ten.jpg").touch()
    (tmp_path / "02-two.jpg").touch()
    (tmp_path / "01-one.jpg").touch()
    _, interiors = kdp_compose.discover_images(tmp_path)
    assert [p.name for p in interiors] == ["01-one.jpg", "02-two.jpg", "10-ten.jpg"]


def test_discover_images_mixed_jpg_png(tmp_path: Path) -> None:
    (tmp_path / "00-cover.png").touch()
    (tmp_path / "01-a.jpg").touch()
    (tmp_path / "02-b.png").touch()
    cover, interiors = kdp_compose.discover_images(tmp_path)
    assert cover.suffix == ".png"
    assert len(interiors) == 2


def test_discover_images_requires_cover(tmp_path: Path) -> None:
    (tmp_path / "01-page.jpg").touch()
    with pytest.raises(FileNotFoundError, match="cover"):
        kdp_compose.discover_images(tmp_path)


def test_discover_images_requires_interiors(tmp_path: Path) -> None:
    (tmp_path / "00-cover.jpg").touch()
    with pytest.raises(FileNotFoundError, match="interior"):
        kdp_compose.discover_images(tmp_path)


def test_discover_images_ignores_pdfs_and_yaml(tmp_path: Path) -> None:
    (tmp_path / "00-cover.jpg").touch()
    (tmp_path / "01-page.jpg").touch()
    (tmp_path / "book.yaml").touch()
    (tmp_path / "existing.pdf").touch()
    _, interiors = kdp_compose.discover_images(tmp_path)
    assert len(interiors) == 1


def test_discover_images_ignores_underscore_prefixed(tmp_path: Path) -> None:
    # Underscore-prefixed images (e.g. a preview render of cover.pdf saved
    # alongside the book) must not be treated as interior pages.
    (tmp_path / "00-cover.jpg").touch()
    (tmp_path / "01-page.jpg").touch()
    (tmp_path / "_cover_preview.png").touch()
    (tmp_path / "_scratch.jpg").touch()
    _, interiors = kdp_compose.discover_images(tmp_path)
    assert [p.name for p in interiors] == ["01-page.jpg"]


# --- load_metadata ---------------------------------------------------------


def _write_yaml(path: Path, body: str) -> Path:
    path.write_text(dedent(body).lstrip())
    return path


def test_load_metadata_minimal(tmp_path: Path) -> None:
    p = _write_yaml(
        tmp_path / "book.yaml",
        """
        title: Test Book
        author: Jane Doe
        trim_size: 8.5x11
        paper: white
        """,
    )
    meta = kdp_compose.load_metadata(p)
    assert meta["title"] == "Test Book"
    assert meta["author"] == "Jane Doe"
    assert meta["trim_size"] == "8.5x11"
    assert meta["paper"] == "white"
    assert meta["language"] == "English"


def test_load_metadata_rejects_missing_title(tmp_path: Path) -> None:
    p = _write_yaml(
        tmp_path / "book.yaml",
        """
        author: Jane Doe
        trim_size: 8.5x11
        paper: white
        """,
    )
    with pytest.raises(ValueError, match="title"):
        kdp_compose.load_metadata(p)


def test_load_metadata_rejects_missing_author(tmp_path: Path) -> None:
    p = _write_yaml(
        tmp_path / "book.yaml",
        """
        title: Test
        trim_size: 8.5x11
        paper: white
        """,
    )
    with pytest.raises(ValueError, match="author"):
        kdp_compose.load_metadata(p)


def test_load_metadata_rejects_unknown_trim(tmp_path: Path) -> None:
    p = _write_yaml(
        tmp_path / "book.yaml",
        """
        title: Test
        author: Me
        trim_size: 99x99
        paper: white
        """,
    )
    with pytest.raises(ValueError, match="trim"):
        kdp_compose.load_metadata(p)


def test_load_metadata_rejects_unknown_paper(tmp_path: Path) -> None:
    p = _write_yaml(
        tmp_path / "book.yaml",
        """
        title: Test
        author: Me
        trim_size: 8.5x11
        paper: parchment
        """,
    )
    with pytest.raises(ValueError, match="paper"):
        kdp_compose.load_metadata(p)


def test_load_metadata_preserves_optional_fields(tmp_path: Path) -> None:
    p = _write_yaml(
        tmp_path / "book.yaml",
        """
        title: Test
        author: Me
        trim_size: 8.5x11
        paper: white
        subtitle: A Subtitle
        description: One line.
        keywords: [fairy, kids]
        price_usd: 7.99
        ai_disclosure:
          text: true
          images: true
          translation: false
        """,
    )
    meta = kdp_compose.load_metadata(p)
    assert meta["subtitle"] == "A Subtitle"
    assert meta["keywords"] == ["fairy", "kids"]
    assert meta["price_usd"] == 7.99
    assert meta["ai_disclosure"]["images"] is True


# --- build_interior: single_sided and bleed ---------------------------------


def _make_image(path: Path, size: tuple[int, int] = (2625, 3375)) -> Path:
    """Write a minimal RGB JPEG at `size` to `path` and return the path."""
    from PIL import Image

    Image.new("RGB", size, (255, 255, 255)).save(path, "JPEG", quality=70)
    return path


def _pdf_page_count(path: Path) -> int:
    """Return the number of pages in `path`."""
    from pypdf import PdfReader

    return len(PdfReader(str(path)).pages)


def _pdf_first_page_size_pt(path: Path) -> tuple[float, float]:
    """Return (width_pt, height_pt) of page 1."""
    from pypdf import PdfReader

    box = PdfReader(str(path)).pages[0].mediabox
    return float(box.width), float(box.height)


def test_build_interior_single_sided_inserts_blank_backs(tmp_path: Path) -> None:
    imgs = [_make_image(tmp_path / f"{i:02d}-p.jpg") for i in range(1, 4)]
    outp = tmp_path / "interior.pdf"
    pages = kdp_compose.build_interior(
        imgs, trim=(8.5, 11.0), outpath=outp, single_sided=True
    )
    assert pages == 6
    assert _pdf_page_count(outp) == 6


def test_build_interior_two_sided_matches_image_count(tmp_path: Path) -> None:
    imgs = [_make_image(tmp_path / f"{i:02d}-p.jpg") for i in range(1, 4)]
    outp = tmp_path / "interior.pdf"
    pages = kdp_compose.build_interior(
        imgs, trim=(8.5, 11.0), outpath=outp, single_sided=False
    )
    assert pages == 3
    assert _pdf_page_count(outp) == 3


def test_build_interior_with_bleed_sizes_page_including_bleed(tmp_path: Path) -> None:
    img = _make_image(tmp_path / "01-p.jpg")
    outp = tmp_path / "interior.pdf"
    kdp_compose.build_interior(
        [img], trim=(8.5, 11.0), outpath=outp, single_sided=False, bleed=True
    )
    w_pt, h_pt = _pdf_first_page_size_pt(outp)
    assert w_pt == pytest.approx((8.5 + 0.25) * 72, abs=0.5)
    assert h_pt == pytest.approx((11.0 + 0.25) * 72, abs=0.5)


def test_build_interior_without_bleed_sizes_page_to_trim(tmp_path: Path) -> None:
    img = _make_image(tmp_path / "01-p.jpg")
    outp = tmp_path / "interior.pdf"
    kdp_compose.build_interior(
        [img], trim=(8.5, 11.0), outpath=outp, single_sided=False, bleed=False
    )
    w_pt, h_pt = _pdf_first_page_size_pt(outp)
    assert w_pt == pytest.approx(8.5 * 72, abs=0.5)
    assert h_pt == pytest.approx(11.0 * 72, abs=0.5)


# --- inner_margin_in: KDP requires non-bleed content ≥ 0.375" from trim -----


def test_build_interior_default_inner_margin_is_half_inch() -> None:
    # The module default must stay ≥ 0.5" so a book created without an
    # inner_margin override meets KDP's safe-for-all margin recommendation.
    assert kdp_compose.INNER_SAFE_MARGIN_IN >= 0.5


def test_build_interior_rejects_inner_margin_below_kdp_minimum(tmp_path: Path) -> None:
    img = _make_image(tmp_path / "01-p.jpg")
    outp = tmp_path / "interior.pdf"
    with pytest.raises(ValueError, match="0.375"):
        kdp_compose.build_interior(
            [img],
            trim=(8.5, 11.0),
            outpath=outp,
            single_sided=False,
            bleed=False,
            inner_margin_in=0.25,
        )


def test_build_interior_accepts_inner_margin_override(tmp_path: Path) -> None:
    img = _make_image(tmp_path / "01-p.jpg")
    outp = tmp_path / "interior.pdf"
    kdp_compose.build_interior(
        [img],
        trim=(8.5, 11.0),
        outpath=outp,
        single_sided=False,
        bleed=False,
        inner_margin_in=0.75,
    )
    assert outp.is_file()


# --- Font embedding: KDP rejects PDFs with un-embedded fonts ---------------


def _embedded_fonts(path: Path) -> set[tuple[str, bool]]:
    """Return the set of (BaseFont, is_embedded) tuples across all pages."""
    from pypdf import PdfReader

    seen: set[tuple[str, bool]] = set()
    for pg in PdfReader(str(path)).pages:
        res = pg.get("/Resources")
        if res is None:
            continue
        fdict = res.get("/Font")
        if fdict is None:
            continue
        for _, fref in fdict.items():
            fobj = fref.get_object()
            name = str(fobj.get("/BaseFont"))
            desc = fobj.get("/FontDescriptor")
            embedded = False
            if desc is not None:
                d = desc.get_object()
                embedded = any(
                    k in d for k in ("/FontFile", "/FontFile2", "/FontFile3")
                )
            seen.add((name, embedded))
    return seen


def test_build_interior_embeds_all_fonts(tmp_path: Path) -> None:
    imgs = [_make_image(tmp_path / f"{i:02d}-p.jpg") for i in range(1, 3)]
    outp = tmp_path / "interior.pdf"
    kdp_compose.build_interior(
        imgs,
        trim=(8.5, 11.0),
        outpath=outp,
        single_sided=False,
        bleed=False,
        metadata=_META,
        include_matter=True,
    )
    fonts = _embedded_fonts(outp)
    assert fonts, "interior PDF should reference at least one font"
    unembedded = [name for name, emb in fonts if not emb]
    assert not unembedded, (
        f"KDP rejects un-embedded fonts; found: {unembedded}. "
        f"All fonts referenced in interior.pdf must have a /FontFile*."
    )


def test_build_cover_embeds_all_fonts(tmp_path: Path) -> None:
    cover_img = _make_image(tmp_path / "00-cover.jpg")
    outp = tmp_path / "cover.pdf"
    kdp_compose.build_cover(
        cover_img, _META, trim=(8.5, 11.0), spine_in=0.15, outpath=outp
    )
    fonts = _embedded_fonts(outp)
    assert fonts, "cover PDF should reference at least one font"
    unembedded = [name for name, emb in fonts if not emb]
    assert not unembedded, (
        f"KDP rejects un-embedded fonts; found: {unembedded}. "
        f"All fonts referenced in cover.pdf must have a /FontFile*."
    )


# --- physical_page_count ----------------------------------------------------


def test_physical_page_count_single_sided() -> None:
    assert kdp_compose.physical_page_count(image_count=20, single_sided=True) == 40


def test_physical_page_count_two_sided() -> None:
    assert kdp_compose.physical_page_count(image_count=20, single_sided=False) == 20


# --- rename_image_book_preview ---------------------------------------------


def test_rename_image_book_preview_renames_slug_pdf(tmp_path: Path) -> None:
    bundle = tmp_path / f"{tmp_path.name}.pdf"
    bundle.write_bytes(b"%PDF-1.4\n")
    result = kdp_compose.rename_image_book_preview(tmp_path)
    assert result is not None
    assert result.name == "_preview.pdf"
    assert not bundle.exists()
    assert (tmp_path / "_preview.pdf").is_file()


def test_rename_image_book_preview_no_slug_pdf_is_noop(tmp_path: Path) -> None:
    assert kdp_compose.rename_image_book_preview(tmp_path) is None


def test_rename_image_book_preview_overwrites_existing_target(tmp_path: Path) -> None:
    bundle = tmp_path / f"{tmp_path.name}.pdf"
    bundle.write_bytes(b"NEW")
    (tmp_path / "_preview.pdf").write_bytes(b"OLD")
    kdp_compose.rename_image_book_preview(tmp_path)
    assert (tmp_path / "_preview.pdf").read_bytes() == b"NEW"
    assert not bundle.exists()


def test_rename_image_book_preview_leaves_interior_and_cover_alone(
    tmp_path: Path,
) -> None:
    (tmp_path / "interior.pdf").write_bytes(b"I")
    (tmp_path / "cover.pdf").write_bytes(b"C")
    assert kdp_compose.rename_image_book_preview(tmp_path) is None
    assert (tmp_path / "interior.pdf").read_bytes() == b"I"
    assert (tmp_path / "cover.pdf").read_bytes() == b"C"


def test_physical_page_count_with_matter_single_sided() -> None:
    # 20 images + 4 front + 1 back = 25 image-equivalent, x2 single-sided = 50
    assert (
        kdp_compose.physical_page_count(
            image_count=20,
            single_sided=True,
            front_matter_count=4,
            back_matter_count=1,
        )
        == 50
    )


def test_physical_page_count_with_matter_two_sided() -> None:
    assert (
        kdp_compose.physical_page_count(
            image_count=20,
            single_sided=False,
            front_matter_count=4,
            back_matter_count=1,
        )
        == 25
    )


# --- build_interior: matter pages ------------------------------------------


_META = {
    "title": "Test Book",
    "author": "Jane Doe",
    "copyright_year": 2026,
    "publisher": "Test Press",
}


def test_build_interior_with_matter_single_sided_counts_pages(tmp_path: Path) -> None:
    imgs = [_make_image(tmp_path / f"{i:02d}-p.jpg") for i in range(1, 4)]
    outp = tmp_path / "interior.pdf"
    pages = kdp_compose.build_interior(
        imgs,
        trim=(8.5, 11.0),
        outpath=outp,
        single_sided=True,
        bleed=False,
        metadata=_META,
        include_matter=True,
    )
    # 4 front matter + 3 image + 1 back matter = 8 content pages, x2 single-sided = 16
    assert pages == 16
    assert _pdf_page_count(outp) == 16


def test_build_interior_with_matter_two_sided_counts_pages(tmp_path: Path) -> None:
    imgs = [_make_image(tmp_path / f"{i:02d}-p.jpg") for i in range(1, 4)]
    outp = tmp_path / "interior.pdf"
    pages = kdp_compose.build_interior(
        imgs,
        trim=(8.5, 11.0),
        outpath=outp,
        single_sided=False,
        bleed=False,
        metadata=_META,
        include_matter=True,
    )
    # 4 front + 3 image + 1 back = 8 pages, no backing
    assert pages == 8
    assert _pdf_page_count(outp) == 8


def test_build_interior_include_matter_false_omits_matter(tmp_path: Path) -> None:
    imgs = [_make_image(tmp_path / f"{i:02d}-p.jpg") for i in range(1, 4)]
    outp = tmp_path / "interior.pdf"
    pages = kdp_compose.build_interior(
        imgs,
        trim=(8.5, 11.0),
        outpath=outp,
        single_sided=True,
        bleed=False,
        metadata=_META,
        include_matter=False,
    )
    # 3 images x2 single-sided = 6; no matter
    assert pages == 6


def test_build_interior_matter_requires_metadata(tmp_path: Path) -> None:
    imgs = [_make_image(tmp_path / f"{i:02d}-p.jpg") for i in range(1, 4)]
    outp = tmp_path / "interior.pdf"
    # include_matter=True but metadata=None → raise, since title/author are needed
    with pytest.raises(ValueError, match="metadata"):
        kdp_compose.build_interior(
            imgs,
            trim=(8.5, 11.0),
            outpath=outp,
            single_sided=True,
            bleed=False,
            metadata=None,
            include_matter=True,
        )


# --- build_review_pdf -------------------------------------------------------


def _write_interior_fixture(tmp_path: Path, image_count: int = 3) -> Path:
    """Build a minimal interior.pdf by running build_interior on synthetic images."""
    imgs = [_make_image(tmp_path / f"{i:02d}-p.jpg") for i in range(1, image_count + 1)]
    outp = tmp_path / "interior.pdf"
    kdp_compose.build_interior(
        imgs, trim=(8.5, 11.0), outpath=outp, single_sided=False, bleed=False
    )
    return outp


def test_build_review_pdf_page_count_no_matter(tmp_path: Path) -> None:
    cover_img = _make_image(tmp_path / "00-cover.jpg")
    interiors = [_make_image(tmp_path / f"{i:02d}-p.jpg") for i in range(1, 4)]
    out = tmp_path / "review.pdf"
    pages = kdp_compose.build_review_pdf(
        cover_image=cover_img,
        interiors=interiors,
        metadata=_META,
        trim=(8.5, 11.0),
        outpath=out,
        single_sided=False,
        include_matter=False,
    )
    # 1 front cover + 3 interior pages + 1 back cover = 5
    assert pages == 5
    assert _pdf_page_count(out) == 5


def test_build_review_pdf_page_count_single_sided_with_matter(tmp_path: Path) -> None:
    cover_img = _make_image(tmp_path / "00-cover.jpg")
    interiors = [_make_image(tmp_path / f"{i:02d}-p.jpg") for i in range(1, 4)]
    out = tmp_path / "review.pdf"
    pages = kdp_compose.build_review_pdf(
        cover_image=cover_img,
        interiors=interiors,
        metadata=_META,
        trim=(8.5, 11.0),
        outpath=out,
        single_sided=True,
        include_matter=True,
    )
    # 1 front + (4 matter + 3 images + 1 back-matter) * 2 single-sided + 1 back = 18
    assert pages == 1 + 16 + 1 == 18
    assert _pdf_page_count(out) == 18


def test_build_review_pdf_pages_all_trim_sized(tmp_path: Path) -> None:
    cover_img = _make_image(tmp_path / "00-cover.jpg")
    interiors = [_make_image(tmp_path / f"{i:02d}-p.jpg") for i in range(1, 3)]
    out = tmp_path / "review.pdf"
    kdp_compose.build_review_pdf(
        cover_image=cover_img,
        interiors=interiors,
        metadata=_META,
        trim=(8.5, 11.0),
        outpath=out,
        single_sided=False,
        include_matter=False,
    )
    from pypdf import PdfReader

    sizes = {
        (round(float(p.mediabox.width), 1), round(float(p.mediabox.height), 1))
        for p in PdfReader(str(out)).pages
    }
    expected = (round(8.5 * 72, 1), round(11.0 * 72, 1))
    assert sizes == {expected}


def test_build_review_pdf_target_dpi_reduces_file_size(tmp_path: Path) -> None:
    # 4K source images (big); low target_dpi should produce a notably smaller PDF
    cover_img = _make_image(tmp_path / "00-cover.jpg", size=(3584, 4800))
    interiors = [
        _make_image(tmp_path / f"{i:02d}-p.jpg", size=(3584, 4800)) for i in range(1, 4)
    ]
    full = tmp_path / "review_full.pdf"
    small = tmp_path / "review_small.pdf"
    kdp_compose.build_review_pdf(
        cover_image=cover_img,
        interiors=interiors,
        metadata=_META,
        trim=(8.5, 11.0),
        outpath=full,
        single_sided=False,
        include_matter=False,
        target_dpi=None,  # no downsampling → embed source images
    )
    kdp_compose.build_review_pdf(
        cover_image=cover_img,
        interiors=interiors,
        metadata=_META,
        trim=(8.5, 11.0),
        outpath=small,
        single_sided=False,
        include_matter=False,
        target_dpi=150,
    )
    assert small.stat().st_size < full.stat().st_size * 0.5, (
        f"target_dpi=150 should produce a notably smaller PDF than full-res; "
        f"got {small.stat().st_size} vs {full.stat().st_size}"
    )


def test_build_review_pdf_requires_cover_image(tmp_path: Path) -> None:
    out = tmp_path / "review.pdf"
    with pytest.raises(FileNotFoundError, match="cover"):
        kdp_compose.build_review_pdf(
            cover_image=tmp_path / "missing.jpg",
            interiors=[_make_image(tmp_path / "01-p.jpg")],
            metadata=_META,
            trim=(8.5, 11.0),
            outpath=out,
            single_sided=False,
            include_matter=False,
        )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
