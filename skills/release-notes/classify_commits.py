#!/usr/bin/env python3
"""Classify conventional commits into release-notes categories.

Replaces the inline category mapping in skills/release-notes/SKILL.md. The
script handles the deterministic work (parse conventional-commit type, detect
breaking-change markers, group into Added/Changed/Fixed/Removed/Security/Other).
Range derivation and prose synthesis stay in the skill body because they
require conditional logic and judgment.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

CONV_RE = re.compile(
    r"^(?P<type>feat|fix|docs|style|refactor|perf|test|build|ci|chore|security|revert)"
    r"(?:\((?P<scope>[^)]+)\))?"
    r"(?P<bang>!)?"
    r":\s*(?P<subject>.+)$",
    re.IGNORECASE,
)

# Map conventional-commit type → release-notes category.
TYPE_TO_CATEGORY = {
    "feat": "Added",          # default for feat; "Changed" is a possibility but the user picks
    "fix": "Fixed",
    "security": "Security",
    "revert": "Changed",
    # The rest are excluded by default
}

EXCLUDED_TYPES = {"docs", "style", "refactor", "perf", "test", "build", "ci", "chore"}

# Heuristic: a feat commit that uses "update" / "change" / "modify" / "rename" in the subject is "Changed", not "Added"
CHANGED_HINTS = re.compile(r"\b(update|change|modify|rename|tweak|adjust|improve|enhance|expand)\b", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    p.add_argument(
        "range",
        help="Commit range (e.g. v1.0.0..HEAD, HEAD~20..HEAD). Use '..' to separate base..head.",
    )
    p.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    p.add_argument(
        "--include-chores",
        action="store_true",
        help="Include refactor/perf/test/build/ci/chore commits in the 'Changed' section",
    )
    return p.parse_args()


def git_log(rng: str) -> list[dict]:
    """Read commits in the range. Each entry: {hash, subject, body}."""
    sep = "\x1e"
    fmt = f"%H%x1f%s%x1f%b{sep}"
    out = subprocess.run(
        ["git", "log", "--format=" + fmt, rng],
        capture_output=True,
        text=True,
    )
    if out.returncode != 0:
        print(f"error: git log failed: {out.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    commits: list[dict] = []
    for raw in out.stdout.split(sep):
        raw = raw.strip()
        if not raw:
            continue
        parts = raw.split("\x1f", 2)
        if len(parts) < 2:
            continue
        h, subject, *rest = parts
        body = rest[0] if rest else ""
        commits.append({"hash": h, "subject": subject, "body": body})
    return commits


def classify(commit: dict, include_chores: bool) -> dict:
    """Return {commit, type, scope, breaking, category, excluded}."""
    subject = commit["subject"]
    body = commit["body"]
    m = CONV_RE.match(subject)
    out = {
        "hash": commit["hash"][:10],
        "subject": subject,
        "type": None,
        "scope": None,
        "breaking": False,
        "category": None,
        "excluded": False,
    }
    breaking_footer = "BREAKING CHANGE:" in body or "BREAKING-CHANGE:" in body
    if not m:
        out["category"] = "Other"
        return out
    out["type"] = m.group("type").lower()
    out["scope"] = m.group("scope")
    bang = bool(m.group("bang"))
    out["breaking"] = bang or breaking_footer

    if out["type"] in EXCLUDED_TYPES and not include_chores:
        out["excluded"] = True
        return out

    if out["type"] == "feat":
        out["category"] = "Changed" if CHANGED_HINTS.search(m.group("subject")) else "Added"
    elif out["type"] in EXCLUDED_TYPES and include_chores:
        out["category"] = "Changed"
    else:
        out["category"] = TYPE_TO_CATEGORY.get(out["type"], "Other")
    return out


def format_markdown(classified: list[dict]) -> str:
    breaking = [c for c in classified if c["breaking"]]
    excluded = sum(1 for c in classified if c["excluded"])
    sections: dict[str, list[dict]] = {"Added": [], "Changed": [], "Fixed": [], "Removed": [], "Security": [], "Other": []}
    for c in classified:
        if c["excluded"]:
            continue
        sections.setdefault(c["category"], []).append(c)
    lines: list[str] = ["## Release notes (draft)\n"]
    if breaking:
        lines.append("### Breaking changes\n")
        for c in breaking:
            lines.append(f"- {c['subject']} ({c['hash']})")
        lines.append("")
    for name in ("Added", "Changed", "Fixed", "Removed", "Security", "Other"):
        if not sections[name]:
            continue
        lines.append(f"### {name}\n")
        for c in sections[name]:
            lines.append(f"- {c['subject']} ({c['hash']})")
        lines.append("")
    if excluded:
        lines.append(f"_Excluded: {excluded} chore/refactor/style/test/build/ci commits. Use --include-chores to surface them._")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    commits = git_log(args.range)
    if not commits:
        print("error: no commits in range", file=sys.stderr)
        return 1
    classified = [classify(c, args.include_chores) for c in commits]
    if args.format == "json":
        sections: dict[str, list[dict]] = {}
        for c in classified:
            if c["excluded"]:
                continue
            sections.setdefault(c["category"], []).append(c)
        print(json.dumps({
            "categories": sections,
            "breaking": [c for c in classified if c["breaking"]],
            "excluded_count": sum(1 for c in classified if c["excluded"]),
            "total": len(classified),
        }, indent=2))
    else:
        print(format_markdown(classified))
    return 0


if __name__ == "__main__":
    sys.exit(main())
