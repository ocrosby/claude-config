#!/usr/bin/env python3
"""Apply deterministic Write-the-Docs rules to documentation files.

Replaces the inline rule checklists in skills/doc-review/SKILL.md. The script
flags findings; the *fix decisions* and any judgment-required rules (technical
accuracy, missing examples, voice) remain with Claude.

Output: Markdown findings grouped per file by severity (Must Fix / Should Fix
/ Consider). Use --json for machine-consumable output.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Severity tiers
MUST = "Must Fix"
SHOULD = "Should Fix"
CONSIDER = "Consider"

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
                findings.append((i, MUST, "vague-link-text", f"Link text '{m.group(1)}' is vague — describe the destination"))
        for m in RAW_URL_RE.finditer(line):
            # Skip URLs that are inside a Markdown link target — already matched above
            findings.append((i, CONSIDER, "raw-url", f"Raw URL in prose: {m.group(1)[:60]}"))
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
                (i, SHOULD, "heading-hierarchy", f"Heading jumps from H{prev_level} to H{level} (skips a level)")
            )
        # Title case
        if TITLE_CASE_RE.match(text) and level > 1:
            findings.append((i, CONSIDER, "heading-title-case", f"Heading uses title case: '{text}' — prefer sentence case"))
        # FAQ heading
        if FAQ_HEADING_RE.match(line):
            findings.append((i, SHOULD, "faq-section", "FAQ section present — replace with structured content per docs-principles"))
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
                findings.append((i, CONSIDER, "alt-text-long", f"Alt text is more than two sentences: '{alt[:60]}...'"))
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
                (i, CONSIDER, "code-block-no-lang", f"Code block opens without a language hint (`{opener}` — add `{opener}bash` or similar)")
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


def check_readme(text: str) -> list[tuple[int, str, str, str]]:
    """README-specific checks (only run when classified as README)."""
    findings: list[tuple[int, str, str, str]] = []
    body = text.lower()
    if "## install" not in body and "## usage" not in body and "## getting started" not in body:
        findings.append((0, MUST, "readme-no-install", "README has no installation or usage section"))
    if "```" not in body:
        findings.append((0, MUST, "readme-no-example", "README has no code example"))
    if "license" not in body:
        findings.append((0, SHOULD, "readme-no-license", "README does not mention a license"))
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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    p.add_argument("paths", nargs="+", help="Files or globs to check")
    p.add_argument("--json", action="store_true", help="Emit findings as JSON")
    p.add_argument(
        "--severity",
        choices=["must", "should", "consider", "all"],
        default="all",
        help="Filter by severity level",
    )
    return p.parse_args()


def expand_paths(patterns: list[str]) -> list[Path]:
    out: list[Path] = []
    for pattern in patterns:
        p = Path(pattern)
        if p.is_file():
            out.append(p)
            continue
        if "*" in pattern or "?" in pattern:
            for match in Path(".").glob(pattern):
                if match.is_file():
                    out.append(match)
        elif p.is_dir():
            for ext in (".md", ".rst", ".txt", ".adoc"):
                out.extend(q for q in p.rglob(f"*{ext}") if q.is_file())
    return sorted(set(out))


def filter_severity(findings: list[tuple[int, str, str, str]], wanted: str) -> list[tuple[int, str, str, str]]:
    if wanted == "all":
        return findings
    keep = {"must": MUST, "should": SHOULD, "consider": CONSIDER}[wanted]
    return [f for f in findings if f[1] == keep]


def main() -> int:
    args = parse_args()
    files = expand_paths(args.paths)
    if not files:
        print("error: no documentation files matched", file=sys.stderr)
        return 1

    by_file: dict[str, list[tuple[int, str, str, str]]] = {}
    for path in files:
        findings = filter_severity(check_file(path), args.severity)
        if findings:
            by_file[str(path)] = findings

    if args.json:
        payload = {
            str(path): [
                {"line": line, "severity": sev, "rule_id": rule, "message": msg}
                for (line, sev, rule, msg) in findings
            ]
            for path, findings in by_file.items()
        }
        print(json.dumps(payload, indent=2))
        return 0

    total = sum(len(v) for v in by_file.values())
    print(f"# Documentation review\n\nFiles scanned: **{len(files)}** — findings: **{total}**\n")
    if not by_file:
        print("_All files clean._")
        return 0

    for path, findings in sorted(by_file.items()):
        print(f"## `{path}` ({classify(Path(path))})\n")
        for sev in (MUST, SHOULD, CONSIDER):
            tier = [f for f in findings if f[1] == sev]
            if not tier:
                continue
            print(f"### {sev}")
            for line, _, rule, msg in tier:
                line_str = f"line {line}" if line > 0 else "document-level"
                print(f"- `{rule}` ({line_str}) — {msg}")
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
