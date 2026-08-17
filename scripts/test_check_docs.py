#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest>=8"]
# ///
"""Tests for check_docs.py README section checks.

Run: scripts/test_check_docs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import check_docs  # noqa: E402


REQUIRED = [
    "Overview",
    "Features",
    "Requirements",
    "Installation",
    "Usage",
    "Configuration",
    "Development",
    "Contributing",
    "License",
]


def build_readme(sections: list[str], toc: bool = True) -> str:
    """Assemble a minimal README with the given H2 sections, in order."""
    parts = ["# my-project", "", "One-sentence description.", ""]
    if toc:
        parts += ["## Table of Contents", "", "- [Overview](#overview)", ""]
    for name in sections:
        parts += [f"## {name}", "", "Body text.", "", "```bash", "echo hi", "```", ""]
    return "\n".join(parts)


def codes(findings) -> list[str]:
    return [f[2] for f in findings]


def by_code(findings, code):
    return [f for f in findings if f[2] == code]


def write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "README.md"
    p.write_text(text, encoding="utf-8")
    return p


# --- section presence ---------------------------------------------------


def test_complete_readme_reports_no_section_findings(tmp_path):
    findings = check_docs.check_file(write(tmp_path, build_readme(REQUIRED)))
    assert "readme-missing-section" not in codes(findings)
    assert "readme-section-order" not in codes(findings)


def test_missing_required_section_is_must_fix(tmp_path):
    without_dev = [s for s in REQUIRED if s != "Development"]
    findings = check_docs.check_file(write(tmp_path, build_readme(without_dev)))
    missing = by_code(findings, "readme-missing-section")
    assert len(missing) == 1
    assert missing[0][1] == check_docs.MUST
    assert "Development" in missing[0][3]


def test_each_missing_section_reported_separately(tmp_path):
    sparse = ["Installation", "Usage", "License"]
    findings = check_docs.check_file(write(tmp_path, build_readme(sparse)))
    missing = by_code(findings, "readme-missing-section")
    reported = " ".join(f[3] for f in missing)
    for name in ["Overview", "Features", "Requirements", "Configuration"]:
        assert name in reported, f"{name} not reported missing"


def test_section_present_with_na_body_counts_as_present(tmp_path):
    text = build_readme(REQUIRED).replace(
        "## Configuration\n\nBody text.", "## Configuration\n\nN/A"
    )
    findings = check_docs.check_file(write(tmp_path, text))
    reported = " ".join(f[3] for f in by_code(findings, "readme-missing-section"))
    assert "Configuration" not in reported


def test_heading_inside_code_fence_does_not_count_as_section(tmp_path):
    without_usage = [s for s in REQUIRED if s != "Usage"]
    text = build_readme(without_usage) + "\n```markdown\n## Usage\n```\n"
    findings = check_docs.check_file(write(tmp_path, text))
    reported = " ".join(f[3] for f in by_code(findings, "readme-missing-section"))
    assert "Usage" in reported


# --- section ordering ---------------------------------------------------


def test_out_of_order_sections_are_should_fix(tmp_path):
    swapped = REQUIRED[:]
    i, j = swapped.index("Installation"), swapped.index("Usage")
    swapped[i], swapped[j] = swapped[j], swapped[i]
    findings = check_docs.check_file(write(tmp_path, build_readme(swapped)))
    order = by_code(findings, "readme-section-order")
    assert order, "expected an ordering finding"
    assert order[0][1] == check_docs.SHOULD


def test_extra_sections_do_not_trigger_ordering(tmp_path):
    with_extra = REQUIRED[:2] + ["Architecture"] + REQUIRED[2:]
    findings = check_docs.check_file(write(tmp_path, build_readme(with_extra)))
    assert "readme-section-order" not in codes(findings)


# --- table of contents --------------------------------------------------


def test_missing_toc_with_many_sections_is_should_fix(tmp_path):
    findings = check_docs.check_file(write(tmp_path, build_readme(REQUIRED, toc=False)))
    toc = by_code(findings, "readme-no-toc")
    assert len(toc) == 1
    assert toc[0][1] == check_docs.SHOULD


def test_missing_toc_with_few_sections_is_not_flagged(tmp_path):
    findings = check_docs.check_file(
        write(tmp_path, build_readme(["Overview", "Usage", "License"], toc=False))
    )
    assert "readme-no-toc" not in codes(findings)


# --- non-README files unaffected ----------------------------------------


def test_non_readme_file_gets_no_readme_findings(tmp_path):
    p = tmp_path / "GUIDE.md"
    p.write_text("# Guide\n\nSome prose.\n", encoding="utf-8")
    found = codes(check_docs.check_file(p))
    assert not [c for c in found if c.startswith("readme-")]


# --- pre-existing checks still hold -------------------------------------


def test_readme_without_license_still_flagged(tmp_path):
    text = build_readme([s for s in REQUIRED if s != "License"])
    findings = check_docs.check_file(write(tmp_path, text))
    assert "readme-no-license" in codes(findings)


def test_readme_without_code_example_still_flagged(tmp_path):
    text = "# p\n\nDesc.\n\n" + "\n".join(f"## {s}\n\nBody.\n" for s in REQUIRED)
    findings = check_docs.check_file(write(tmp_path, text))
    assert "readme-no-example" in codes(findings)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
