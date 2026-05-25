#!/usr/bin/env python3
"""Parse Gherkin .feature files into structured data for documentation generation.

Replaces the inline parsing instructions in skills/gherkin-docs/SKILL.md.
Handles multi-line steps, tags, Background blocks, Scenario Outlines with
Examples tables. Outputs JSON (default) or a one-line-per-feature summary.

Claude consumes the JSON and renders the final Markdown documentation.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import cli as _cli  # noqa: E402  # type: ignore[import-not-found]

TAG_RE = re.compile(r"^\s*(@\S+(?:\s+@\S+)*)\s*$")
KEYWORDS = ("Feature:", "Background:", "Scenario:", "Scenario Outline:", "Example:", "Examples:", "Rule:")
STEP_KEYWORDS = ("Given ", "When ", "Then ", "And ", "But ", "* ")


def parse_feature(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"file": str(path), "error": "could not read"}

    out: dict = {
        "file": str(path),
        "feature_name": "",
        "description": [],
        "tags": [],
        "background_steps": [],
        "scenarios": [],
        "rules": [],
    }
    current_tags: list[str] = []
    current_block: dict | None = None  # active scenario / background / examples
    description_open = True

    lines = text.splitlines()
    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Tags accumulate until the next keyword line
        m = TAG_RE.match(line)
        if m:
            current_tags.extend(m.group(1).split())
            continue

        # Feature header
        if stripped.startswith("Feature:"):
            out["feature_name"] = stripped[len("Feature:"):].strip()
            out["tags"] = current_tags[:]
            current_tags = []
            description_open = True
            current_block = None
            continue

        # Rule (Gherkin 6+)
        if stripped.startswith("Rule:"):
            description_open = False
            rule = {"name": stripped[len("Rule:"):].strip(), "tags": current_tags[:], "scenarios": []}
            out["rules"].append(rule)
            current_tags = []
            current_block = rule  # subsequent scenarios attach here
            continue

        # Background
        if stripped.startswith("Background:"):
            description_open = False
            current_block = {"_kind": "background"}
            current_tags = []
            continue

        # Scenario / Scenario Outline
        for kw in ("Scenario Outline:", "Scenario:", "Example:"):
            if stripped.startswith(kw):
                description_open = False
                scenario = {
                    "name": stripped[len(kw):].strip(),
                    "tags": current_tags[:],
                    "steps": [],
                    "examples": [] if kw == "Scenario Outline:" else None,
                    "outline": kw == "Scenario Outline:",
                }
                # Attach to the most recent rule if present, else the feature
                if out["rules"]:
                    out["rules"][-1]["scenarios"].append(scenario)
                else:
                    out["scenarios"].append(scenario)
                current_block = scenario
                current_tags = []
                break
        else:
            # No keyword match
            pass

        # Examples block (table follows)
        if stripped.startswith("Examples:") or stripped.startswith("Example:"):
            if current_block is not None and current_block.get("outline"):
                # Next lines until blank or new keyword are the table
                current_block["_in_examples"] = True
            continue

        # Step lines
        if any(stripped.startswith(k) for k in STEP_KEYWORDS):
            if current_block is None:
                continue
            if current_block.get("_kind") == "background":
                out["background_steps"].append(stripped)
            else:
                current_block.setdefault("steps", []).append(stripped)
            continue

        # Examples table rows
        if stripped.startswith("|") and current_block is not None and current_block.get("outline"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            current_block.setdefault("examples", []).append(cells)
            continue

        # Description prose lines (only before the first Background/Scenario)
        if description_open and out["feature_name"]:
            out["description"].append(stripped)

    out["description"] = "\n".join(out["description"]).strip()
    return out


def expand(patterns: list[str]) -> list[Path]:
    return _cli.expand_paths(
        patterns,
        dir_globs=("*.feature",),
        recursive=True,
    )


def summarize(features: list[dict]) -> None:
    total_scenarios = sum(len(f["scenarios"]) + sum(len(r["scenarios"]) for r in f["rules"]) for f in features)
    print(f"# Feature summary\n")
    print(f"Files: **{len(features)}** — scenarios: **{total_scenarios}**\n")
    for f in features:
        n = len(f["scenarios"]) + sum(len(r["scenarios"]) for r in f["rules"])
        tags = " ".join(f["tags"]) or "—"
        print(f"- `{f['file']}` — **{f['feature_name'] or '(no name)'}** — {n} scenarios — tags: {tags}")


def main() -> int:
    parser = _cli.make_parser(__doc__)
    parser.add_argument("paths", nargs="+", help="Feature files, directories, or globs")
    parser.add_argument("--summary", action="store_true", help="One-line-per-file summary instead of full JSON")
    args = parser.parse_args()

    files = expand(args.paths)
    if not files:
        return _cli.die("no .feature files matched")

    features = [parse_feature(f) for f in files]
    if args.summary:
        summarize(features)
    else:
        print(json.dumps(features, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
