#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Render a consolidated git status display: branch, tracking, tree state, stash, recent commits, and open PR.

Consumed by /git status. Centralizes the plumbing git_group.py and
classify_commits.py already wrap individually (branch, remote tracking,
porcelain parsing) into one read-only snapshot, so the display is
byte-identical between runs instead of being re-derived from raw `git status`
output turn by turn.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import cli as _cli  # noqa: E402  # type: ignore[import-not-found]
from _lib import git as _git  # noqa: E402  # type: ignore[import-not-found]

STATUS_LABELS = {
    "M": "modified",
    "A": "added",
    "D": "deleted",
    "R": "renamed",
    "C": "copied",
    "U": "unmerged",
}


def branch_info() -> dict:
    """Current branch (or short SHA if detached), upstream, and ahead/behind counts."""
    branch = _git.run(["branch", "--show-current"]).strip()
    detached = not branch
    if detached:
        branch = _git.run(["rev-parse", "--short", "HEAD"]).strip()
    upstream = _git.run(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"]).strip()
    ahead = behind = 0
    if upstream:
        counts = _git.run(["rev-list", "--left-right", "--count", f"{upstream}...HEAD"]).strip()
        if counts:
            behind_str, ahead_str = counts.split()
            behind, ahead = int(behind_str), int(ahead_str)
    assert ahead >= 0 and behind >= 0, f"negative ahead/behind count: {ahead}/{behind}"
    return {
        "branch": branch,
        "detached": detached,
        "upstream": upstream or None,
        "ahead": ahead,
        "behind": behind,
    }


def porcelain_entries() -> list[dict]:
    """Parse `git status --porcelain=v1 -z` into structured entries, handling rename's extra NUL field."""
    out = _git.run(["status", "--porcelain=v1", "-z"])
    parts = [p for p in out.split("\0") if p != ""] if out else []
    entries: list[dict] = []
    i = 0
    while i < len(parts):
        part = parts[i]
        code, path = part[:2], part[3:]
        assert len(code) == 2, f"malformed porcelain status code: {part!r}"
        if "R" in code or "C" in code:
            i += 1
            old_path = parts[i] if i < len(parts) else ""
            entries.append({"code": code, "path": path, "old_path": old_path})
        else:
            entries.append({"code": code, "path": path, "old_path": None})
        i += 1
    return entries


def stash_list() -> list[str]:
    out = _git.run(["stash", "list"])
    return [line for line in out.splitlines() if line]


def recent_commits(n: int = 5) -> list[str]:
    out = _git.run(["log", f"-{n}", "--pretty=format:%h %s"])
    return [line for line in out.splitlines() if line]


def pr_info(branch: str) -> dict | None:
    """Look up the open PR for `branch` via `gh`. Returns None on any failure — a missing PR is not an error."""
    if not branch or branch in ("main", "master"):
        return None
    try:
        proc = subprocess.run(
            [
                "gh",
                "pr",
                "view",
                branch,
                "--json",
                "number,title,state,url,isDraft,statusCheckRollup",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,  # returncode inspected explicitly below; a missing PR is not an error
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    checks = data.get("statusCheckRollup") or []
    failing = sum(1 for c in checks if c.get("conclusion") in ("FAILURE", "CANCELLED", "TIMED_OUT"))
    passing = sum(1 for c in checks if c.get("conclusion") == "SUCCESS")
    return {
        "number": data.get("number"),
        "title": data.get("title"),
        "state": data.get("state"),
        "url": data.get("url"),
        "draft": bool(data.get("isDraft")),
        "checks": {"passing": passing, "failing": failing, "total": len(checks)},
    }


def render(data: dict) -> str:
    b = data["branch_info"]
    lines = ["Branch: " + b["branch"] + (" (detached HEAD)" if b["detached"] else "")]
    if b["upstream"]:
        tracking = f"Tracking: {b['upstream']}"
        if b["ahead"] or b["behind"]:
            parts = []
            if b["ahead"]:
                parts.append(f"{b['ahead']} ahead")
            if b["behind"]:
                parts.append(f"{b['behind']} behind")
            tracking += " (" + ", ".join(parts) + ")"
        else:
            tracking += " (up to date)"
        lines.append(tracking)
    else:
        lines.append("Tracking: none")

    entries = data["entries"]
    staged = [e for e in entries if e["code"][0] not in (" ", "?")]
    unstaged = [e for e in entries if e["code"][1] not in (" ", "?")]
    untracked = [e for e in entries if e["code"] == "??"]

    lines.append("")
    if not entries:
        lines.append("Working tree: clean")
    else:
        if staged:
            lines.append(f"Staged ({len(staged)}):")
            lines += [f"  {STATUS_LABELS.get(e['code'][0], e['code'][0])}: {e['path']}" for e in staged]
        if unstaged:
            lines.append(f"Unstaged ({len(unstaged)}):")
            lines += [f"  {STATUS_LABELS.get(e['code'][1], e['code'][1])}: {e['path']}" for e in unstaged]
        if untracked:
            lines.append(f"Untracked ({len(untracked)}):")
            lines += [f"  {e['path']}" for e in untracked]

    stash = data["stash"]
    lines.append("")
    lines.append(f"Stash: {len(stash)} entr{'y' if len(stash) == 1 else 'ies'}")
    lines += [f"  {s}" for s in stash[:5]]

    lines.append("")
    lines.append("Recent commits:")
    lines += [f"  {c}" for c in data["commits"]] or ["  (none)"]

    pr = data.get("pr")
    lines.append("")
    if pr:
        state = "DRAFT" if pr["draft"] else pr["state"]
        checks = pr["checks"]
        summary = f"{checks['passing']}/{checks['total']} checks passing" if checks["total"] else "no checks reported"
        if checks["failing"]:
            summary += f", {checks['failing']} failing"
        lines.append(f"PR #{pr['number']} [{state}]: {pr['title']}")
        lines.append(f"  {summary}")
        lines.append(f"  {pr['url']}")
    elif not b["detached"] and b["branch"] not in ("main", "master"):
        lines.append("PR: none open for this branch")

    result = "\n".join(lines)
    assert result, "render produced empty output"
    return result


def main() -> int:
    parser = _cli.make_parser(__doc__)
    _cli.add_json_flag(parser, "Emit raw data as JSON instead of the rendered display")
    parser.add_argument(
        "--no-pr",
        action="store_true",
        help="Skip the gh pr view lookup (faster, no network)",
    )
    args = parser.parse_args()

    info = branch_info()
    data = {
        "branch_info": info,
        "entries": porcelain_entries(),
        "stash": stash_list(),
        "commits": recent_commits(),
        "pr": None if args.no_pr else pr_info(info["branch"]),
    }

    print(json.dumps(data, indent=2) if args.json else render(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
