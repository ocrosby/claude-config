#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Aggregate git history into a structured JSON health report.

Covers the git-only dimensions of `/audit repo` — churn, ownership /
bus-factor, bug hotspots, momentum, and firefighting. GitHub enrichments
(gh issues/PRs/releases) stay in the skill; this script is git-only so it
runs on any clone. Emits JSON to stdout; exit 0 on success, 1 if the path
is not a git repository.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path


def git(args: list[str], cwd: Path) -> str:
    """Run a git command; return stdout as text ('' on any failure)."""
    try:
        out = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
        )
        return out.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def churn(cwd: Path, since: str, top: int) -> list[dict]:
    out = git(["log", "--format=format:", "--name-only", f"--since={since}"], cwd)
    counts = Counter(ln.strip() for ln in out.splitlines() if ln.strip())
    return [{"file": f, "changes": n} for f, n in counts.most_common(top)]


def author_commits(cwd: Path, since: str | None = None) -> Counter:
    args = ["log", "--no-merges", "--format=%aN"]
    if since:
        args.append(f"--since={since}")
    return Counter(a for a in git(args, cwd).splitlines() if a)


def lines_by_author(cwd: Path, authors: list[str]) -> list[dict]:
    result = []
    for a in authors:
        out = git(
            ["log", f"--author={a}", "--numstat", "--no-merges", "--format="], cwd
        )
        add = dele = 0
        for ln in out.splitlines():
            parts = ln.split("\t")
            # numstat rows are "added<TAB>deleted<TAB>path"; binaries show "-".
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                add += int(parts[0])
                dele += int(parts[1])
        result.append({"author": a, "insertions": add, "deletions": dele})
    return result


def top_level_dirs(cwd: Path) -> list[str]:
    dirs = {
        ln.split("/", 1)[0] for ln in git(["ls-files"], cwd).splitlines() if "/" in ln
    }
    return sorted(dirs)


def subsystem_owners(cwd: Path, dirs: list[str], top: int = 3) -> list[dict]:
    result = []
    for d in dirs:
        counts = Counter(
            a
            for a in git(
                ["log", "--no-merges", "--format=%aN", "--", d], cwd
            ).splitlines()
            if a
        )
        result.append(
            {
                "dir": d,
                "top_contributors": [
                    {"author": k, "commits": v} for k, v in counts.most_common(top)
                ],
            }
        )
    return result


def recent_commits(cwd: Path, authors: list[str], n: int = 5) -> list[dict]:
    result = []
    for a in authors:
        out = git(["log", f"--author={a}", "--no-merges", "--oneline", f"-{n}"], cwd)
        result.append({"author": a, "commits": [ln for ln in out.splitlines() if ln]})
    return result


def bug_hotspots(cwd: Path, top: int) -> list[dict]:
    out = git(
        ["log", "-i", "-E", "--grep=fix|bug|broken", "--name-only", "--format="], cwd
    )
    counts = Counter(ln.strip() for ln in out.splitlines() if ln.strip())
    return [{"file": f, "changes": n} for f, n in counts.most_common(top)]


def momentum(cwd: Path) -> list[dict]:
    counts = Counter(
        m
        for m in git(["log", "--format=%ad", "--date=format:%Y-%m"], cwd).splitlines()
        if m
    )
    return [{"month": m, "commits": counts[m]} for m in sorted(counts)]


def firefighting(cwd: Path, since: str) -> dict:
    out = git(["log", "--oneline", f"--since={since}"], cwd)
    needles = ("revert", "hotfix", "emergency", "rollback")
    hits = [ln for ln in out.splitlines() if any(p in ln.lower() for p in needles)]
    return {"count": len(hits), "commits": hits}


def main() -> int:
    ap = argparse.ArgumentParser(description="Git history health report as JSON.")
    ap.add_argument("--repo", default=".", help="Repository path (default: cwd).")
    ap.add_argument(
        "--since", default="1 year ago", help="Window for churn/firefighting."
    )
    ap.add_argument(
        "--top", type=int, default=20, help="Top-N files for churn/hotspots."
    )
    ap.add_argument(
        "--json", action="store_true", help="Emit JSON (default and only mode)."
    )
    args = ap.parse_args()
    assert args.top > 0, "--top must be positive"

    cwd = Path(args.repo).resolve()
    if not git(["rev-parse", "--git-dir"], cwd).strip():
        print(f"error: not a git repository: {cwd}", file=sys.stderr)
        return 1

    all_time = author_commits(cwd)
    recent = author_commits(cwd, since="6 months ago")
    top5 = [a for a, _ in all_time.most_common(5)]
    top3 = [a for a, _ in all_time.most_common(3)]

    report = {
        "churn": churn(cwd, args.since, args.top),
        "ownership": {
            "commits_all_time": [
                {"author": k, "commits": v} for k, v in all_time.most_common(20)
            ],
            "commits_recent_6mo": [
                {"author": k, "commits": v} for k, v in recent.most_common(20)
            ],
            "lines_by_author": lines_by_author(cwd, top5),
            "subsystems": subsystem_owners(cwd, top_level_dirs(cwd)),
            "recent_commits": recent_commits(cwd, top3),
        },
        "bug_hotspots": bug_hotspots(cwd, args.top),
        "momentum": momentum(cwd),
        "firefighting": firefighting(cwd, args.since),
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
