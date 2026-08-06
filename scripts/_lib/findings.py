"""Shared finding model and output rendering for the check_* scripts.

A "finding" is a `(line, severity, rule_id, message)` tuple. Severities are
the three Write-the-Docs tiers used throughout rules/docs-principles.md.

Each `check_*` script builds a `by_file: dict[str, list[Finding]]` mapping
and renders it either as JSON (machine-consumable) or Markdown
(severity-grouped per file). Both shapes are produced here so the per-file
loop, the line/path labels, and the JSON schema stay consistent.
"""

from __future__ import annotations

import json
import sys
from typing import Callable, TextIO

MUST = "Must Fix"
SHOULD = "Should Fix"
CONSIDER = "Consider"

Finding = tuple[int, str, str, str]


def filter_by_severity(findings: list[Finding], wanted: str) -> list[Finding]:
    """Keep only findings whose severity matches `wanted` ('must'/'should'/'consider'/'all')."""
    if wanted == "all":
        return findings
    keep = {"must": MUST, "should": SHOULD, "consider": CONSIDER}[wanted]
    return [f for f in findings if f[1] == keep]


# Severity rank — higher = more severe. Used by `triggers_fail` to decide when
# `--fail-on=<severity>` should push the process exit code to 3.
_SEVERITY_RANK = {MUST: 3, SHOULD: 2, CONSIDER: 1}
_THRESHOLD = {"must": 3, "should": 2, "consider": 1}


def triggers_fail(findings: list[Finding], fail_on: str) -> bool:
    """True when any finding meets or exceeds the `fail_on` threshold.

    `fail_on` is one of 'must', 'should', 'consider', or 'none' (never triggers).
    Callers pass the *unfiltered* finding list — `--severity` is a display filter,
    the gate should not be affected by what the user asked to see.
    """
    if fail_on == "none":
        return False
    threshold = _THRESHOLD[fail_on]
    return any(_SEVERITY_RANK.get(f[1], 0) >= threshold for f in findings)


def format_json(by_file: dict[str, list[Finding]]) -> str:
    """Render findings as the canonical {path: [{line, severity, rule_id, message}, ...]} JSON."""
    payload = {
        str(path): [
            {"line": line, "severity": sev, "rule_id": rule, "message": msg}
            for (line, sev, rule, msg) in findings
        ]
        for path, findings in by_file.items()
    }
    return json.dumps(payload, indent=2)


def _default_line_label(n: int) -> str:
    return f"line {n}" if n > 0 else "document-level"


def print_markdown(
    by_file: dict[str, list[Finding]],
    *,
    path_label: Callable[[str], str] = lambda p: f"`{p}`",
    line_label: Callable[[int], str] = _default_line_label,
    severities: tuple[str, ...] = (MUST, SHOULD, CONSIDER),
    file: TextIO | None = None,
) -> None:
    """Print per-file findings grouped by severity.

    `path_label` controls the H2 heading content (e.g. add a classification suffix).
    `line_label` formats the line number for each bullet — default falls back to
    "document-level" for line == 0.
    """
    out = file if file is not None else sys.stdout
    for path, findings in sorted(by_file.items()):
        print(f"## {path_label(path)}\n", file=out)
        for sev in severities:
            tier = [f for f in findings if f[1] == sev]
            if not tier:
                continue
            print(f"### {sev}", file=out)
            for line, _, rule, msg in tier:
                print(f"- `{rule}` ({line_label(line)}) — {msg}", file=out)
            print(file=out)
