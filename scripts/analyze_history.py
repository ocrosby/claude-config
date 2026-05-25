#!/usr/bin/env python3
"""Tally slash-command invocations and freeform natural-language phrases from
~/.claude/history.jsonl. Replaces the inline Python heredoc in
skills/skill-gaps/SKILL.md so the parsing logic stays out of context.

The script outputs frequencies; the *gap interpretation* (which patterns are
real gaps vs already covered by an existing skill) remains the user's job
because it requires reading the current skill catalog.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

HISTORY = Path.home() / ".claude" / "history.jsonl"
SINCE_RE = re.compile(r"(\d+)([dh])")


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


def extract_display(record: dict) -> str:
    for key in ("display", "prompt", "content", "text", "message"):
        v = record.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--since", type=parse_since, default=None)
    parser.add_argument("--min-count", type=int, default=2, help="Minimum repetition to surface (default: 2)")
    parser.add_argument("--top", type=int, default=30, help="How many entries to show per section")
    parser.add_argument("--phrase-words", type=int, default=8, help="Number of leading words to use as the phrase key")
    args = parser.parse_args()

    if not HISTORY.exists():
        print(f"error: {HISTORY} not found", file=sys.stderr)
        return 1

    cutoff = datetime.now(timezone.utc) - args.since if args.since else None
    slash_counts: Counter = Counter()
    phrase_counts: Counter = Counter()
    total = 0
    in_window = 0

    with HISTORY.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            total += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if cutoff:
                ts = parse_timestamp(record)
                if ts is None or ts < cutoff:
                    continue
            in_window += 1
            text = extract_display(record)
            if not text or text == "exit":
                continue
            if text.startswith("/"):
                cmd = text.split()[0]
                slash_counts[cmd] += 1
            elif len(text) > 10:
                words = text.split()[: args.phrase_words]
                phrase = " ".join(words).lower()
                phrase_counts[phrase] += 1

    window = f"last {args.since.days}d" if args.since else "all time"
    print(f"# Skill gap analysis ({window})")
    print()
    print(f"History records scanned: {total}")
    if cutoff:
        print(f"Records in window: {in_window}")
    print()

    print(f"## Top slash-command invocations (skills currently in use)")
    print()
    if slash_counts:
        for cmd, count in slash_counts.most_common(args.top):
            print(f"- `{cmd[:60]}` — {count}")
    else:
        print("_No slash-command invocations in window._")
    print()

    print(f"## Repeating natural-language phrases (potential skill gaps)")
    print()
    print(f"Phrases typed ≥{args.min_count} times, top {args.top}:")
    print()
    matches = [(p, c) for p, c in phrase_counts.most_common() if c >= args.min_count]
    if matches:
        for phrase, count in matches[: args.top]:
            print(f"- {count:>3}× `{phrase[:80]}`")
    else:
        print(f"_No phrases meeting the ≥{args.min_count} threshold._")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
