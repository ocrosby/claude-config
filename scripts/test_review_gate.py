#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest>=8"]
# ///
"""Tests for review_gate.py's severity parsing.

Black-box: each test feeds a real review body — the shapes the bots actually
post — to parse_findings and asserts on the buckets it returns. No network and
no `gh`; the parser is pure, so the body is the whole input.

The emoji-heading and numbered-bullet cases are regressions. A review on
sun-qa-wiremock#66 reported one Minor finding that the gate scored as clean,
because the heading was "#### <warning> Minor" and the finding was "1. item" —
the heading regex allowed only asterisks before the severity word, and bullets
matched only "-" and "*". The gate said CLEAN on a PR with an open finding.

Run: scripts/test_review_gate.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import review_gate  # noqa: E402


def total(body: str) -> int:
    return sum(len(v) for v in review_gate.parse_findings(body).values())


# --- the regression that prompted these tests ----------------------------


def test_emoji_decorated_heading_still_opens_the_section() -> None:
    body = "#### ⚠️ Minor\n\n1. **sed unescaped** (line 237): would break on a slash.\n"
    assert review_gate.parse_findings(body)["minor"] == [
        "**sed unescaped** (line 237): would break on a slash."
    ]


def test_numbered_findings_are_counted() -> None:
    body = "### Must Fix\n\n1. first problem\n2. second problem\n"
    assert review_gate.parse_findings(body)["critical"] == [
        "first problem",
        "second problem",
    ]


def test_a_praise_section_after_findings_is_not_counted() -> None:
    """A non-severity heading must close the open section.

    Scoping the reset to "## " alone let "#### Strengths" inherit an earlier
    severity bucket, so compliments were scored as findings.
    """
    body = (
        "#### ⚠️ Minor\n\n1. the one real finding\n\n"
        "#### ✅ Strengths\n\n1. nice error handling\n2. good fallback\n"
    )
    found = review_gate.parse_findings(body)
    assert found["minor"] == ["the one real finding"]
    assert total(body) == 1


def test_praise_before_findings_is_not_counted() -> None:
    body = (
        "#### ✅ Strengths\n\n1. clean migration\n2. clear errors\n\n"
        "#### ⚠️ Minor\n\n1. the one real finding\n"
    )
    assert total(body) == 1


# --- shapes that already worked, pinned so the fix did not widen them -----


@pytest.mark.parametrize(
    "heading,bucket",
    [
        ("## Critical", "critical"),
        ("**Must Fix**", "critical"),
        ("### Moderate", "moderate"),
        ("#### Should Fix", "moderate"),
        ("## Minor", "minor"),
        ("### Consider", "minor"),
    ],
)
def test_severity_aliases_map_to_buckets(heading: str, bucket: str) -> None:
    found = review_gate.parse_findings(f"{heading}\n\n- a finding\n")
    assert found[bucket] == ["a finding"]


def test_dash_and_star_bullets_both_count() -> None:
    body = "## Minor\n\n- dash item\n* star item\n"
    assert total(body) == 2


def test_continuation_lines_join_the_preceding_bullet() -> None:
    body = "## Minor\n\n- first line\n  wrapped onto a second\n"
    assert review_gate.parse_findings(body)["minor"] == [
        "first line wrapped onto a second"
    ]


def test_a_clean_review_yields_nothing() -> None:
    body = (
        "## Code Review\n\n### Overview\nLooks good to me.\n\n"
        "No issues found. Nice work.\n"
    )
    assert total(body) == 0


def test_prose_mentioning_a_severity_word_opens_nothing() -> None:
    """The word alone must not open a section, or ordinary prose leaks in."""
    body = "## Summary\n\nNo critical issues were found here.\n\n- just a list item\n"
    assert total(body) == 0


def test_horizontal_rule_closes_the_section() -> None:
    body = "## Minor\n\n- counted\n\n---\n\n- not counted\n"
    assert review_gate.parse_findings(body)["minor"] == ["counted"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
