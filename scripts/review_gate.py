#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Gate a PR merge on the review bot's current findings.

Reads a PR's comments and reviews with `gh`, takes only each bot's most recent
completed review (earlier posts are superseded), parses its severity sections
(Critical / Moderate / Minor, or Must Fix / Should Fix / Consider) and reports
whether anything is still open.

Exit codes
  0  clean: every bot's current review has no findings (or no bot reviewed)
  2  open findings: at least one bullet under a severity section
  3  cannot assess: a review is still running, errored, or older than the last
     commit (the bot re-reviews on every push; wait for it)

Never decide to merge on exit 2 or 3. Fix the finding (a new commit triggers a
fresh review) or get the user's explicit decision to decline it, and reply on
the PR with the reason.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime

SEVERITY_ALIASES = {
    "critical": "critical",
    "must fix": "critical",
    "moderate": "moderate",
    "should fix": "moderate",
    "minor": "minor",
    "consider": "minor",
}
HEADING = re.compile(
    r"^\s*(?:#{1,6}\s*)?\**\s*(critical|must fix|moderate|should fix|minor|consider)\b[^\n]*$",
    re.IGNORECASE,
)
STATUS_ONLY = re.compile(
    r"encountered an error|is reviewing|in progress|- \[ \]", re.IGNORECASE
)
NO_FINDINGS = re.compile(
    r"looks good|no issues found|no new issues|all prior findings", re.IGNORECASE
)
REVIEW_SHAPE = re.compile(r"review|issues|looks good", re.IGNORECASE)


def gh(*args: str) -> str:
    out = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    assert out.returncode == 0, f"gh {' '.join(args)} failed: {out.stderr[:200]}"
    return out.stdout


def ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


def parse_findings(body: str) -> dict[str, list[str]]:
    """Bullets under each severity heading; continuation lines are joined."""
    found: dict[str, list[str]] = {"critical": [], "moderate": [], "minor": []}
    current: str | None = None
    for line in body.split("\n"):
        m = HEADING.match(line)
        if m and len(line) < 140 and not line.lstrip().startswith("- "):
            current = SEVERITY_ALIASES[m.group(1).lower()]
            continue
        if line.startswith("## ") or line.strip() == "---":
            if current and not HEADING.match(line):
                current = None
            continue
        if current is None:
            continue
        if re.match(r"^\s*[-*]\s+\S", line):
            found[current].append(re.sub(r"^\s*[-*]\s+", "", line).strip())
        elif line.strip() and found[current] and not line.startswith("<!--"):
            found[current][-1] += " " + line.strip()
    return found


def collect(repo: str, pr: int) -> dict:
    head = json.loads(
        gh("pr", "view", str(pr), "--repo", repo, "--json", "headRefOid,commits,state")
    )
    last_commit = max(ts(c["committedDate"]) for c in head["commits"])
    comments = json.loads(gh("api", "--paginate", f"repos/{repo}/issues/{pr}/comments"))
    reviews = json.loads(gh("api", "--paginate", f"repos/{repo}/pulls/{pr}/reviews"))
    posts = []
    for c in comments:
        if c["user"]["type"] == "Bot":
            posts.append(
                (c["user"]["login"], ts(c["created_at"]), c["id"], c["body"] or "")
            )
    for r in reviews:
        if r["user"]["type"] == "Bot" and (r.get("body") or "").strip():
            posts.append(
                (r["user"]["login"], ts(r["submitted_at"]), r["id"], r["body"])
            )
    bots: dict[str, list] = {}
    for login, created, pid, body in sorted(posts, key=lambda p: p[1]):
        bots.setdefault(login, []).append((created, pid, body))
    report = []
    for login, items in bots.items():
        completed = [
            i
            for i in items
            if not STATUS_ONLY.search(i[2][:400]) and REVIEW_SHAPE.search(i[2][:600])
        ]
        newest = items[-1]
        entry = {"bot": login, "review_id": None, "state": "none"}
        if completed:
            created, pid, body = completed[-1]
            entry.update(review_id=pid, created_at=created.isoformat())
            entry["findings"] = parse_findings(body)
            entry["clean_marker"] = bool(NO_FINDINGS.search(body)) and not any(
                entry["findings"].values()
            )
            if created < last_commit:
                entry["state"] = "stale"
            else:
                entry["state"] = "current"
        if (
            newest is not (completed[-1] if completed else None)
            and (not completed or newest[0] > completed[-1][0])
            and STATUS_ONLY.search(newest[2][:400])
        ):
            entry["state"] = "pending"
        if entry["state"] != "none" or items:
            report.append(entry)
    return {
        "pr": pr,
        "head": head["headRefOid"],
        "last_commit": last_commit.isoformat(),
        "bots": report,
    }


def verdict(data: dict) -> tuple[int, str]:
    reviewers = [b for b in data["bots"] if b["state"] != "none"]
    if not reviewers:
        return 0, "no bot review found (nothing to gate)"
    waiting = [b["bot"] for b in reviewers if b["state"] in ("pending", "stale")]
    if waiting:
        return 3, f"review pending or older than the last commit: {', '.join(waiting)}"
    open_n = sum(len(v) for b in reviewers for v in b.get("findings", {}).values())
    if open_n:
        return 2, f"{open_n} open finding(s) in the current review"
    return 0, "current review has no findings"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pr", type=int)
    ap.add_argument("--repo", help="owner/name (default: current repo)")
    ap.add_argument("--json", action="store_true", help="print JSON only")
    args = ap.parse_args()
    repo = (
        args.repo
        or json.loads(gh("repo", "view", "--json", "nameWithOwner"))["nameWithOwner"]
    )
    data = collect(repo, args.pr)
    code, why = verdict(data)
    data["verdict"] = {0: "CLEAN", 2: "OPEN FINDINGS", 3: "CANNOT ASSESS"}[code]
    data["reason"] = why
    if args.json:
        print(json.dumps(data, indent=1))
        return code
    print(f"PR #{args.pr} {data['verdict']}: {why}")
    for b in data["bots"]:
        print(
            f"  {b['bot']}: {b['state']}"
            + (
                f" (review {b['review_id']} at {b.get('created_at', '')[:16]})"
                if b["review_id"]
                else ""
            )
        )
        for sev in ("critical", "moderate", "minor"):
            for item in b.get("findings", {}).get(sev, []):
                print(f"    [{sev}] {item[:160]}")
    return code


if __name__ == "__main__":
    sys.exit(main())
