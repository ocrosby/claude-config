#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Apply deterministic Write-the-Docs rules to documentation files.

Replaces the inline rule checklists in skills/doc-review/SKILL.md. The script
flags findings; the *fix decisions* and any judgment-required rules (technical
accuracy, missing examples, voice) remain with Claude.

Output: Markdown findings grouped per file by severity (Must Fix / Should Fix
/ Consider). Use --json for machine-consumable output.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import cli as _cli  # noqa: E402  # type: ignore[import-not-found]
from _lib import findings as _findings  # noqa: E402  # type: ignore[import-not-found]
from _lib.findings import MUST, SHOULD, CONSIDER  # noqa: E402  # type: ignore[import-not-found]

VAGUE_LINK_TEXTS = {"click here", "here", "this link", "this page", "read more"}
CODE_FENCE_RE = re.compile(r"^(\`{3,}|~{3,})(\w*)\s*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
RAW_URL_RE = re.compile(r"(?<![\(<\"])(https?://\S+)(?![\)>\"])")
TITLE_CASE_RE = re.compile(r"^([A-Z][a-z]+)(\s+[A-Z][a-z]+){2,}\b")
FAQ_HEADING_RE = re.compile(r"^#{1,6}\s+.*\bf\.?a\.?q\b", re.IGNORECASE)


def in_code_block(lines: list[str], target: int) -> bool:
    """Return True if line at index `target` is inside a fenced code block."""
    inside = False
    for i, line in enumerate(lines):
        if i == target:
            return inside
        if CODE_FENCE_RE.match(line):
            inside = not inside
    return inside


def check_links(lines: list[str]) -> list[tuple[int, str, str, str]]:
    """Find vague link texts and raw URLs."""
    findings: list[tuple[int, str, str, str]] = []
    for i, line in enumerate(lines, 1):
        if in_code_block(lines, i - 1):
            continue
        for m in LINK_RE.finditer(line):
            text = m.group(1).strip().lower()
            if text in VAGUE_LINK_TEXTS:
                findings.append(
                    (
                        i,
                        MUST,
                        "vague-link-text",
                        f"Link text '{m.group(1)}' is vague — describe the destination",
                    )
                )
        for m in RAW_URL_RE.finditer(line):
            # Skip URLs that are inside a Markdown link target — already matched above
            findings.append(
                (i, CONSIDER, "raw-url", f"Raw URL in prose: {m.group(1)[:60]}")
            )
    return findings


def check_headings(lines: list[str]) -> list[tuple[int, str, str, str]]:
    findings: list[tuple[int, str, str, str]] = []
    prev_level = 0
    heading_count = 0
    for i, line in enumerate(lines, 1):
        if in_code_block(lines, i - 1):
            continue
        m = HEADING_RE.match(line)
        if not m:
            continue
        heading_count += 1
        level = len(m.group(1))
        text = m.group(2)
        # Hierarchy: jumping more than one level deeper is broken
        if prev_level > 0 and level > prev_level + 1:
            findings.append(
                (
                    i,
                    SHOULD,
                    "heading-hierarchy",
                    f"Heading jumps from H{prev_level} to H{level} (skips a level)",
                )
            )
        # Title case
        if TITLE_CASE_RE.match(text) and level > 1:
            findings.append(
                (
                    i,
                    CONSIDER,
                    "heading-title-case",
                    f"Heading uses title case: '{text}' — prefer sentence case",
                )
            )
        # FAQ heading
        if FAQ_HEADING_RE.match(line):
            findings.append(
                (
                    i,
                    SHOULD,
                    "faq-section",
                    "FAQ section present — replace with structured content per docs-principles",
                )
            )
        prev_level = level
    return findings


def check_images(lines: list[str]) -> list[tuple[int, str, str, str]]:
    findings: list[tuple[int, str, str, str]] = []
    for i, line in enumerate(lines, 1):
        if in_code_block(lines, i - 1):
            continue
        for m in IMAGE_RE.finditer(line):
            alt = m.group(1).strip()
            if not alt:
                findings.append((i, MUST, "image-no-alt", "Image has no alt text"))
            elif alt.count(".") > 2:
                findings.append(
                    (
                        i,
                        CONSIDER,
                        "alt-text-long",
                        f"Alt text is more than two sentences: '{alt[:60]}...'",
                    )
                )
    return findings


def check_code_blocks(lines: list[str]) -> list[tuple[int, str, str, str]]:
    findings: list[tuple[int, str, str, str]] = []
    for i, line in enumerate(lines, 1):
        m = CODE_FENCE_RE.match(line)
        if not m:
            continue
        opener = m.group(1)
        lang = m.group(2)
        # Only flag opening fences (heuristic: same fence char re-opens after content)
        # An unlabelled fence is the opener if the *previous* line is not inside a block
        if not in_code_block(lines, i - 2) and not lang:
            findings.append(
                (
                    i,
                    CONSIDER,
                    "code-block-no-lang",
                    f"Code block opens without a language hint (`{opener}` — add `{opener}bash` or similar)",
                )
            )
    return findings


def classify(path: Path) -> str:
    name = path.name.lower()
    if name.startswith("readme"):
        return "README"
    if name.startswith("changelog") or name.startswith("history"):
        return "Changelog"
    if name.startswith("contributing"):
        return "Guide"
    if "tutorial" in name or "getting-started" in name:
        return "Tutorial"
    return "Document"


# Canonical H2 sections from rules/readme-standard.md, in required order.
# Each maps to the aliases a real README plausibly uses for it. Aliases
# match the whole heading or a leading whole word ("Installation" also
# matches "## Installation & Setup").
README_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Overview", ("overview", "about", "introduction", "what is")),
    ("Features", ("features", "capabilities", "highlights")),
    ("Requirements", ("requirements", "prerequisites", "dependencies")),
    ("Installation", ("installation", "install", "getting started", "setup")),
    ("Usage", ("usage", "use", "quick start", "quickstart")),
    ("Examples", ("examples", "example")),
    ("Configuration", ("configuration", "config", "options", "settings")),
    ("Development", ("development", "developing", "contributing and development")),
    ("Contributing", ("contributing", "contribute")),
    ("License", ("license", "licence", "licensing")),
)

# Examples is required "unless a single Usage example fully demonstrates the
# surface" — a judgment the script cannot make, so its absence is Should Fix
# while every other section's absence is Must Fix.
README_CONDITIONAL = frozenset({"Examples"})

TOC_ALIASES = ("table of contents", "contents", "toc")

# rules/readme-standard.md: a TOC is required once the README exceeds four
# sections.
TOC_SECTION_THRESHOLD = 4


def _normalize_heading(text: str) -> str:
    """Lowercase, drop non-alphanumerics, collapse whitespace."""
    kept = "".join(c if (c.isalnum() or c.isspace()) else " " for c in text.lower())
    return " ".join(kept.split())


def _matches(normalized: str, aliases: tuple[str, ...]) -> bool:
    return any(
        normalized == alias or normalized.startswith(alias + " ") for alias in aliases
    )


def h2_sections(lines: list[str]) -> list[tuple[int, str]]:
    """Return (line_number, heading_text) for every H2 outside a code fence.

    Single pass — the module's in_code_block() helper is O(n) per call and
    would make this O(n^2) over the file.
    """
    sections: list[tuple[int, str]] = []
    inside = False
    for i, line in enumerate(lines, 1):
        if CODE_FENCE_RE.match(line):
            inside = not inside
            continue
        if inside:
            continue
        m = HEADING_RE.match(line)
        if m and len(m.group(1)) == 2:
            sections.append((i, m.group(2).strip()))
    return sections


def check_readme_sections(lines: list[str]) -> list[tuple[int, str, str, str]]:
    """Check required-section presence, ordering, and TOC per readme-standard."""
    findings: list[tuple[int, str, str, str]] = []
    sections = h2_sections(lines)
    normalized = [(line_no, _normalize_heading(text)) for line_no, text in sections]

    # Map each canonical section to the first heading that satisfies it.
    found: dict[str, int] = {}
    for canonical, aliases in README_SECTIONS:
        for line_no, norm in normalized:
            if canonical not in found and _matches(norm, aliases):
                found[canonical] = line_no

    for canonical, _ in README_SECTIONS:
        if canonical in found:
            continue
        if canonical in README_CONDITIONAL:
            findings.append(
                (
                    0,
                    SHOULD,
                    "readme-no-examples",
                    f"README has no {canonical} section — required unless the Usage "
                    "example fully demonstrates the surface",
                )
            )
        else:
            findings.append(
                (
                    0,
                    MUST,
                    "readme-missing-section",
                    f"README is missing the required '{canonical}' section "
                    "(write 'N/A' under the heading if genuinely not applicable)",
                )
            )

    # Ordering: the canonical sections that are present must appear in the
    # standard's order. Non-canonical sections may be interleaved freely.
    present = [(found[c], c) for c, _ in README_SECTIONS if c in found]
    in_document_order = sorted(present)
    if [c for _, c in present] != [c for _, c in in_document_order]:
        expected = [c for _, c in present]
        actual = [c for _, c in in_document_order]
        first_bad = next(
            (a for e, a in zip(expected, actual) if e != a),
            actual[0] if actual else "",
        )
        findings.append(
            (
                found.get(first_bad, 0),
                SHOULD,
                "readme-section-order",
                f"README sections are out of order — expected {' → '.join(expected)}, "
                f"found {' → '.join(actual)}",
            )
        )

    has_toc = any(_matches(norm, TOC_ALIASES) for _, norm in normalized)
    body_sections = [1 for _, norm in normalized if not _matches(norm, TOC_ALIASES)]
    if not has_toc and len(body_sections) > TOC_SECTION_THRESHOLD:
        findings.append(
            (
                0,
                SHOULD,
                "readme-no-toc",
                f"README has {len(body_sections)} sections and no Table of Contents "
                f"(required above {TOC_SECTION_THRESHOLD})",
            )
        )

    return findings


def check_readme(text: str) -> list[tuple[int, str, str, str]]:
    """README-specific checks (only run when classified as README)."""
    findings: list[tuple[int, str, str, str]] = []
    body = text.lower()
    findings.extend(check_readme_sections(text.splitlines()))
    if "```" not in body:
        findings.append((0, MUST, "readme-no-example", "README has no code example"))
    if "license" not in body:
        findings.append(
            (0, SHOULD, "readme-no-license", "README does not mention a license")
        )
    return findings


def check_file(path: Path) -> list[tuple[int, str, str, str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines = text.splitlines()
    findings: list[tuple[int, str, str, str]] = []
    findings.extend(check_links(lines))
    findings.extend(check_headings(lines))
    findings.extend(check_images(lines))
    findings.extend(check_code_blocks(lines))
    if classify(path) == "README":
        findings.extend(check_readme(text))
    return sorted(findings, key=lambda f: (f[0], f[1]))


EXAMPLES = """\
Examples:
  check_docs.py README.md CHANGELOG.md   # Markdown findings across multiple files
  check_docs.py docs/ --json             # JSON for tooling
  check_docs.py docs/ --fail-on=must     # CI gate on Must Fix findings
"""


def parse_args():
    p = _cli.make_parser(__doc__, examples=EXAMPLES)
    p.add_argument("paths", nargs="+", help="Files or globs to check")
    _cli.add_json_flag(p)
    _cli.add_severity_flag(p, help_text="Filter by severity level")
    _cli.add_fail_on_flag(p)
    return p.parse_args()


def expand_paths(patterns: list[str]) -> list[Path]:
    return _cli.expand_paths(
        patterns,
        dir_globs=("*.md", "*.rst", "*.txt", "*.adoc"),
        recursive=True,
    )


def main() -> int:
    args = parse_args()
    files = expand_paths(args.paths)
    if not files:
        return _cli.die("no documentation files matched")

    raw_by_file: dict[str, list[tuple[int, str, str, str]]] = {}
    by_file: dict[str, list[tuple[int, str, str, str]]] = {}
    for path in files:
        raw = check_file(path)
        if not raw:
            continue
        raw_by_file[str(path)] = raw
        filtered = _findings.filter_by_severity(raw, args.severity)
        if filtered:
            by_file[str(path)] = filtered

    if args.json:
        print(_findings.format_json(by_file))
    else:
        total = sum(len(v) for v in by_file.values())
        print(
            f"# Documentation review\n\nFiles scanned: **{len(files)}** — findings: **{total}**\n"
        )
        if not by_file:
            print("_All files clean._")
        else:
            _findings.print_markdown(
                by_file,
                path_label=lambda p: f"`{p}` ({classify(Path(p))})",
            )

    all_raw = [f for lst in raw_by_file.values() for f in lst]
    if _findings.triggers_fail(all_raw, args.fail_on):
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
