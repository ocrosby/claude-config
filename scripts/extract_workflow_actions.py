#!/usr/bin/env python3
"""Extract unique third-party `uses:` action references from GitHub Actions
workflow files (.github/workflows/*.yml).

Feeds `/audit actions`, which checks each extracted (repo, ref) pair against
the action's actual `action.yml` to catch Node-version deprecation (see
https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/).
That live check needs network access, so it stays out of this script — this
script only does the deterministic part: parse and dedupe. Same shape as the
rest of the script catalog — standard library only, --json flag.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import cli as _cli  # noqa: E402  # type: ignore[import-not-found]

USES_RE = re.compile(r"^\s*-?\s*uses:\s*['\"]?([^\s'\"#]+)")


def parse_args():
    p = _cli.make_parser(__doc__)
    p.add_argument("paths", nargs="+", help="Workflow files or globs (.github/workflows/*.yml)")
    _cli.add_json_flag(p)
    return p.parse_args()


def expand_paths(patterns: list[str]) -> list[Path]:
    return _cli.expand_paths(
        patterns,
        accept_file=lambda q: q.suffix in (".yml", ".yaml"),
        dir_globs=("*.yml", "*.yaml"),
        recursive=False,
        skip_absolute_glob=True,
    )


def is_third_party_action(ref: str) -> bool:
    """True for `owner/repo[@ref]` refs. False for local (`./x`) and docker (`docker://x`) uses:."""
    return "@" in ref and not ref.startswith((".", "docker://"))


def extract_refs(path: Path) -> list[tuple[int, str, str]]:
    """Return (line_no, repo, ref) for every third-party `uses:` in `path`."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    out: list[tuple[int, str, str]] = []
    for i, line in enumerate(lines, 1):
        m = USES_RE.search(line)
        if not m:
            continue
        raw = m.group(1)
        if not is_third_party_action(raw):
            continue
        repo, _, ref = raw.rpartition("@")
        out.append((i, repo, ref))
    return out


def main() -> int:
    args = parse_args()
    files = expand_paths(args.paths)
    if not files:
        return _cli.die("no workflow files matched")

    # repo@ref -> {"repo": ..., "ref": ..., "locations": ["file:line", ...]}
    by_key: dict[str, dict] = {}
    for path in files:
        for line_no, repo, ref in extract_refs(path):
            key = f"{repo}@{ref}"
            entry = by_key.setdefault(key, {"repo": repo, "ref": ref, "locations": []})
            entry["locations"].append(f"{path}:{line_no}")

    unique = sorted(by_key.values(), key=lambda e: (e["repo"], e["ref"]))

    if args.json:
        print(json.dumps(unique, indent=2))
        return 0

    print(f"# Third-party action references\n\nFiles scanned: **{len(files)}** — unique actions: **{len(unique)}**\n")
    if not unique:
        print("_No third-party `uses:` references found._")
        return 0
    for entry in unique:
        locs = ", ".join(entry["locations"])
        print(f"- `{entry['repo']}@{entry['ref']}` — {locs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
