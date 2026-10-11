#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest>=8", "pyyaml>=6", "pillow>=10", "reportlab>=4"]
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


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
