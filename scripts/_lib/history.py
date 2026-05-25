"""Shared JSONL + timestamp utilities for history-reading scripts.

analyze_history.py and tally_invocations.py both walk ~/.claude/history.jsonl
with identical timestamp coercion, JSONL error handling, and `--since=Nd|Nh`
window parsing. Centralising these keeps the time math consistent — a bug in
one was always silently a bug in the other.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

HISTORY_PATH = Path.home() / ".claude" / "history.jsonl"

_SINCE_RE = re.compile(r"(\d+)([dh])")


def parse_since(arg: str) -> timedelta:
    """Parse a --since argument like `7d` or `12h` into a timedelta.

    Raises argparse.ArgumentTypeError on malformed input so it composes cleanly
    with `parser.add_argument(..., type=parse_since)`.
    """
    m = _SINCE_RE.fullmatch(arg)
    if not m:
        raise argparse.ArgumentTypeError(f"invalid --since: {arg}")
    n, unit = int(m.group(1)), m.group(2)
    return timedelta(days=n) if unit == "d" else timedelta(hours=n)


def parse_timestamp(record: dict) -> datetime | None:
    """Best-effort timestamp coercion across the keys history records actually use.

    Tries ISO-8601 strings (including the `Z` suffix), then unix seconds, then
    unix milliseconds. Returns None when no key parses.
    """
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


def read_jsonl(path: Path) -> Iterator[dict]:
    """Yield one dict per non-empty line; silently skip lines that fail json.loads."""
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue
