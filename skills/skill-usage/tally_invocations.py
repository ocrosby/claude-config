#!/usr/bin/env python3
"""Tally explicit /command invocations from ~/.claude/history.jsonl.

Cross-references against ~/.claude/skills/ to find unused skills, then
emits a ranked retirement recommendation as the final section.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOME = Path.home()
HISTORY = HOME / ".claude" / "history.jsonl"
SKILLS_DIR = HOME / ".claude" / "skills"

COMMAND_RE = re.compile(r"^/([a-z][a-z0-9-]*)\b")
SINCE_RE = re.compile(r"(\d+)([dh])")
NEW_SKILL_DAYS = 30  # mtime newer than this excludes a skill from "Retire"


def parse_since(arg: str) -> timedelta:
    m = SINCE_RE.fullmatch(arg)
    if not m:
        raise argparse.ArgumentTypeError(f"invalid --since: {arg}")
    n, unit = int(m.group(1)), m.group(2)
    return timedelta(days=n) if unit == "d" else timedelta(hours=n)


def parse_timestamp(record: dict) -> datetime | None:
    for key in ("timestamp", "ts", "time", "created_at"):
        raw = record.get(key)
        if isinstance(raw, str):
            try:
                return datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                continue
        if isinstance(raw, (int, float)):
            # Heuristic: >= 10^12 means milliseconds, otherwise seconds
            seconds = raw / 1000.0 if raw >= 1_000_000_000_000 else float(raw)
            try:
                return datetime.fromtimestamp(seconds, tz=timezone.utc)
            except (ValueError, OSError):
                continue
    return None


def extract_command(record: dict) -> str | None:
    """Return the slash command at the start of the prompt text, or None."""
    for key in ("prompt", "content", "display", "text", "message"):
        text = record.get(key)
        if isinstance(text, str):
            m = COMMAND_RE.match(text.strip())
            if m:
                return m.group(1)
    return None


def read_frontmatter(skill_dir: Path) -> dict:
    """Read YAML frontmatter from SKILL.md as a flat dict (no PyYAML required)."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return {}
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 4)
    if end < 0:
        return {}
    out: dict = {}
    for line in text[4:end].splitlines():
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def days_ago(ts: float, now: datetime) -> int:
    return (now - datetime.fromtimestamp(ts, tz=timezone.utc)).days


def first_added_timestamp(skill_md: Path) -> float | None:
    """Use `git log` against the resolved real path to find when the file was added.

    Returns None if not in a git repo or the file has no history. Stow symlinks
    in ~/.claude resolve to the real file in the dotfiles repo, so we walk to
    the real path before invoking git.
    """
    real = skill_md.resolve()
    repo_dir = real.parent
    try:
        out = subprocess.run(
            [
                "git",
                "-C",
                str(repo_dir),
                "log",
                "--diff-filter=A",
                "--follow",
                "--format=%at",
                "--",
                real.name,
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    lines = [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]
    if not lines:
        return None
    return float(lines[-1])  # last entry is the original add


def gather_skills(now: datetime) -> dict[str, dict]:
    """Return {name: {age_days, user_only, paths_scoped}} for every skill dir."""
    out: dict[str, dict] = {}
    for p in sorted(SKILLS_DIR.iterdir()):
        if not p.is_dir():
            continue
        skill_md = p / "SKILL.md"
        if not skill_md.exists():
            continue
        fm = read_frontmatter(p)
        added_ts = first_added_timestamp(skill_md)
        if added_ts is None:
            added_ts = skill_md.stat().st_mtime  # fallback if not in a git repo
        out[p.name] = {
            "age_days": days_ago(added_ts, now),
            "user_only": fm.get("disable-model-invocation", "").lower() == "true",
            "paths_scoped": "paths" in fm,
        }
    return out


def tally(since: timedelta | None, known: set[str]) -> tuple[Counter, int, int]:
    counts: Counter = Counter()
    total = 0
    matched = 0
    cutoff = datetime.now(timezone.utc) - since if since else None
    with HISTORY.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            total += 1
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if cutoff:
                ts = parse_timestamp(record)
                if ts is None or ts < cutoff:
                    continue
            cmd = extract_command(record)
            if cmd and cmd in known:
                counts[cmd] += 1
                matched += 1
    return counts, total, matched


def print_bucket(title: str, items: list[tuple[int, str]]) -> None:
    print(f"### {title}")
    if not items:
        print("None.")
    else:
        width = max(len(name) for _, name in items) + 1
        for count, name in items:
            print(f"- /{name:<{width}} {count}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", type=parse_since, default=None)
    args = parser.parse_args()

    if not HISTORY.exists():
        print(f"error: {HISTORY} not found", file=sys.stderr)
        return 1
    if not SKILLS_DIR.exists():
        print(f"error: {SKILLS_DIR} not found", file=sys.stderr)
        return 1

    now = datetime.now(timezone.utc)
    skills = gather_skills(now)
    counts, total_lines, matched = tally(args.since, set(skills))

    window = f"last {args.since.days}d" if args.since else "all time"
    print(f"## Skill usage ({window})")
    print()
    print(f"History records scanned: {total_lines}")
    print(f"Skill invocations matched: {matched}")
    print(f"Skills in catalog: {len(skills)}")
    print()

    sorted_counts = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    heavy = [(c, n) for n, c in sorted_counts if c >= 10]
    moderate = [(c, n) for n, c in sorted_counts if 3 <= c < 10]
    light = [(c, n) for n, c in sorted_counts if 1 <= c < 3]

    print_bucket("Heavily used (>=10)", heavy)
    print_bucket("Moderately used (3-9)", moderate)
    print_bucket("Lightly used (1-2)", light)

    # Zero-invocation skills annotated with age + frontmatter signals
    zero = [name for name in skills if name not in counts]
    zero_with_meta = sorted(
        zero, key=lambda n: -skills[n]["age_days"]  # oldest first
    )

    print("### Zero invocations")
    if not zero_with_meta:
        print("None.")
    else:
        for name in zero_with_meta:
            meta = skills[name]
            tags = []
            if meta["age_days"] < NEW_SKILL_DAYS:
                tags.append("new")
            if meta["user_only"]:
                tags.append("user-invocable only")
            if meta["paths_scoped"]:
                tags.append("paths-scoped")
            tag_str = f" [{', '.join(tags)}]" if tags else ""
            print(f"- /{name}  added {meta['age_days']}d ago{tag_str}")
    print()

    # Retirement recommendation: zero invocations AND not new
    retire = [
        name
        for name in zero_with_meta
        if skills[name]["age_days"] >= NEW_SKILL_DAYS
    ]

    print("### Retire (recommended)")
    if not retire:
        print("None.")
    else:
        print(
            "These skills have zero invocations and have existed for "
            f"{NEW_SKILL_DAYS}+ days. Ordered by strongest signal first "
            "(longest unused)."
        )
        print()
        for i, name in enumerate(retire, 1):
            meta = skills[name]
            reasons = [f"{meta['age_days']}d in catalog"]
            if meta["user_only"]:
                reasons.append("user-invocable only")
            if meta["paths_scoped"]:
                reasons.append("paths-scoped — may fire without explicit /command")
            reasons.append("never invoked")
            print(f"{i}. /{name}  — {', '.join(reasons)}")
    print()

    # "Consider retiring" — low-use skills in the report window
    consider = [(c, n) for n, c in sorted_counts if 1 <= c <= 2]
    print("### Consider retiring")
    if not consider:
        print("None.")
    else:
        print("Low usage (1-2 invocations) — keep if intentional, drop if accidental:")
        print()
        for count, name in consider:
            print(f"- /{name}  ({count} invocation{'s' if count > 1 else ''})")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
