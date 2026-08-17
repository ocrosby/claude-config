#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest>=8"]
# ///
"""Tests for check_stow.py.

Black-box: each test builds a real package directory and a real target
directory, runs the real `stow`, and asserts on the findings. The
filesystem and stow are the system edge, so they are used rather than
mocked.

Run: scripts/test_check_stow.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import check_stow  # noqa: E402

pytestmark = pytest.mark.skipif(
    shutil.which("stow") is None, reason="GNU Stow is not installed"
)


def make_package(tmp_path: Path, entries: dict[str, str], ignore: str | None = None):
    """Create <tmp>/pkgdir/pkg with `entries` and an empty target dir.

    Keys ending in "/" become directories holding a single file.
    """
    root = tmp_path / "pkgdir"
    pkg = root / "pkg"
    pkg.mkdir(parents=True)
    for name, content in entries.items():
        if name.endswith("/"):
            d = pkg / name.rstrip("/")
            d.mkdir(parents=True)
            (d / "file.txt").write_text(content, encoding="utf-8")
        else:
            (pkg / name).write_text(content, encoding="utf-8")
    if ignore is not None:
        (pkg / ".stow-local-ignore").write_text(ignore, encoding="utf-8")
    target = tmp_path / "target"
    target.mkdir()
    return root, pkg, target


def stow(root: Path, target: Path):
    subprocess.run(
        ["stow", "-t", str(target), "-d", str(root), "pkg"], check=True, timeout=60
    )


def codes(findings):
    return [f[2] for f in findings]


def by_code(findings, code):
    return [f for f in findings if f[2] == code]


# --- fully stowed --------------------------------------------------------


def test_fully_stowed_package_is_clean(tmp_path):
    root, _, target = make_package(tmp_path, {"rules/": "x", "CLAUDE.md": "y"})
    stow(root, target)
    assert check_stow.check(root, target, "pkg") == []


# --- unlinked entries ----------------------------------------------------


def test_entry_added_after_stow_is_reported(tmp_path):
    root, pkg, target = make_package(tmp_path, {"rules/": "x"})
    stow(root, target)
    (pkg / "docs").mkdir()
    (pkg / "docs" / "GUIDE.md").write_text("g", encoding="utf-8")
    found = check_stow.check(root, target, "pkg")
    missing = by_code(found, "stow-unlinked")
    assert len(missing) == 1
    assert missing[0][1] == check_stow.MUST
    assert "docs" in missing[0][3]


def test_multiple_unlinked_entries_reported_separately(tmp_path):
    root, pkg, target = make_package(tmp_path, {"rules/": "x"})
    stow(root, target)
    for name in ("docs", "prompts"):
        (pkg / name).mkdir()
        (pkg / name / "f.md").write_text("f", encoding="utf-8")
    reported = " ".join(
        f[3] for f in by_code(check_stow.check(root, target, "pkg"), "stow-unlinked")
    )
    assert "docs" in reported and "prompts" in reported


def test_ignored_entry_is_not_reported_as_unlinked(tmp_path):
    root, pkg, target = make_package(tmp_path, {"rules/": "x"}, ignore="^/README.*\n")
    stow(root, target)
    (pkg / "README.md").write_text("readme", encoding="utf-8")
    assert "stow-unlinked" not in codes(check_stow.check(root, target, "pkg"))


# --- junk that would be linked -------------------------------------------


def test_tool_cache_that_would_be_linked_is_reported(tmp_path):
    root, pkg, target = make_package(tmp_path, {"rules/": "x"})
    stow(root, target)
    (pkg / ".pytest_cache").mkdir()
    (pkg / ".pytest_cache" / "v").write_text("c", encoding="utf-8")
    found = check_stow.check(root, target, "pkg")
    junk = by_code(found, "stow-junk-linked")
    assert len(junk) == 1
    assert junk[0][1] == check_stow.MUST
    assert ".pytest_cache" in junk[0][3]


def test_tool_cache_excluded_by_ignore_is_not_reported(tmp_path):
    root, pkg, target = make_package(
        tmp_path, {"rules/": "x"}, ignore="^/\\.pytest_cache\n"
    )
    stow(root, target)
    (pkg / ".pytest_cache").mkdir()
    (pkg / ".pytest_cache" / "v").write_text("c", encoding="utf-8")
    found = check_stow.check(root, target, "pkg")
    assert "stow-junk-linked" not in codes(found)
    assert "stow-unlinked" not in codes(found)


# --- broken links --------------------------------------------------------


def test_broken_link_into_package_is_reported(tmp_path):
    root, pkg, target = make_package(tmp_path, {"rules/": "x", "gone.md": "g"})
    stow(root, target)
    (pkg / "gone.md").unlink()
    found = check_stow.check(root, target, "pkg")
    broken = by_code(found, "stow-broken-link")
    assert len(broken) == 1
    assert broken[0][1] == check_stow.MUST
    assert "gone.md" in broken[0][3]


def test_foreign_symlink_in_target_is_ignored(tmp_path):
    root, _, target = make_package(tmp_path, {"rules/": "x"})
    stow(root, target)
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (target / "other").symlink_to(outside)
    assert check_stow.check(root, target, "pkg") == []


def test_unrelated_real_directory_in_target_is_ignored(tmp_path):
    root, _, target = make_package(tmp_path, {"rules/": "x"})
    stow(root, target)
    (target / "sessions").mkdir()
    (target / "sessions" / "a.json").write_text("{}", encoding="utf-8")
    assert check_stow.check(root, target, "pkg") == []


# --- output rendering ----------------------------------------------------


def test_markdown_label_is_not_double_parenthesised(tmp_path):
    root, pkg, target = make_package(tmp_path, {"rules/": "x"})
    stow(root, target)
    (pkg / "docs").mkdir()
    (pkg / "docs" / "f.md").write_text("f", encoding="utf-8")
    out = subprocess.run(
        [
            str(Path(__file__).parent / "check_stow.py"),
            "--package-dir", str(root), "--package", "pkg", "--target", str(target),
        ],
        capture_output=True, text=True, timeout=120,
    ).stdout
    assert "(package-level)" in out
    assert "((package-level))" not in out


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
