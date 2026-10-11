#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest>=8"]
# ///
"""Tests for kdp_publish.py pure helpers.

The Playwright-driven wizard steps are not unit-tested here — they
require a logged-in KDP session and are exercised by hand against the
live site. These tests cover only the pure helpers (metadata loading,
URL building, keyword normalization) that can run offline.

Run: scripts/test_kdp_publish.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import kdp_publish  # noqa: E402


# --- load_normalized_metadata ----------------------------------------------


def _write_metadata(dirpath: Path, data: dict) -> Path:
    """Write a metadata.json file next to synthetic PDFs and return its path."""
    (dirpath / "interior.pdf").write_bytes(b"%PDF-1.4\n%fake\n")
    (dirpath / "cover.pdf").write_bytes(b"%PDF-1.4\n%fake\n")
    path = dirpath / "metadata.json"
    path.write_text(json.dumps(data))
    return path


def test_load_normalized_metadata_minimal(tmp_path: Path) -> None:
    _write_metadata(
        tmp_path,
        {
            "title": "Test",
            "author": "Me",
            "trim_size": "8.5x11",
            "paper": "white",
            "page_count": 24,
            "interior_pdf": str(tmp_path / "interior.pdf"),
            "cover_pdf": str(tmp_path / "cover.pdf"),
        },
    )
    meta = kdp_publish.load_normalized_metadata(tmp_path)
    assert meta["title"] == "Test"
    assert meta["page_count"] == 24


def test_load_normalized_metadata_rejects_missing_pdfs(tmp_path: Path) -> None:
    (tmp_path / "metadata.json").write_text(
        json.dumps(
            {
                "title": "Test",
                "author": "Me",
                "trim_size": "8.5x11",
                "paper": "white",
                "page_count": 24,
                "interior_pdf": str(tmp_path / "missing.pdf"),
                "cover_pdf": str(tmp_path / "cover.pdf"),
            }
        )
    )
    with pytest.raises(FileNotFoundError, match="interior"):
        kdp_publish.load_normalized_metadata(tmp_path)


def test_load_normalized_metadata_rejects_missing_required(tmp_path: Path) -> None:
    _write_metadata(
        tmp_path,
        {
            "title": "Test",
            # author missing
            "trim_size": "8.5x11",
            "paper": "white",
            "page_count": 24,
            "interior_pdf": str(tmp_path / "interior.pdf"),
            "cover_pdf": str(tmp_path / "cover.pdf"),
        },
    )
    with pytest.raises(ValueError, match="author"):
        kdp_publish.load_normalized_metadata(tmp_path)


def test_load_normalized_metadata_rejects_no_metadata_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="metadata.json"):
        kdp_publish.load_normalized_metadata(tmp_path)


# --- kdp_bookshelf_url -----------------------------------------------------


def test_bookshelf_url_default_us() -> None:
    assert (
        kdp_publish.kdp_bookshelf_url("US") == "https://kdp.amazon.com/en_US/bookshelf"
    )


def test_bookshelf_url_uk() -> None:
    assert (
        kdp_publish.kdp_bookshelf_url("UK") == "https://kdp.amazon.com/en_GB/bookshelf"
    )


def test_bookshelf_url_unknown_marketplace() -> None:
    with pytest.raises(ValueError, match="marketplace"):
        kdp_publish.kdp_bookshelf_url("ZZ")


# --- normalize_keywords ----------------------------------------------------


def test_normalize_keywords_pads_and_truncates() -> None:
    assert kdp_publish.normalize_keywords(["a", "b"]) == ["a", "b"]
    too_many = [f"k{i}" for i in range(10)]
    out = kdp_publish.normalize_keywords(too_many)
    assert len(out) == 7
    assert out == too_many[:7]


def test_normalize_keywords_strips_and_drops_empty() -> None:
    assert kdp_publish.normalize_keywords([" one ", "", "two", "  "]) == ["one", "two"]


def test_normalize_keywords_handles_none() -> None:
    assert kdp_publish.normalize_keywords(None) == []


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
