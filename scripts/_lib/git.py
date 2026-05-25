"""Shared `git` subprocess wrapper for scripts that shell out to git.

backstage_infer.py and git_group.py both swallow non-zero exit codes and
return empty strings; classify_commits.py and tally_invocations.py need the
returncode to distinguish "no commits" from "git failed". `run` matches the
former; `run_checked` matches the latter.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


def run(args: list[str], *, cwd: Path | None = None, timeout: float | None = None) -> str:
    """Run `git <args>` and return stdout.

    Returns an empty string on any non-zero exit code or subprocess failure —
    matches the error-swallowing semantics that backstage_infer.py and
    git_group.py share. For callers that need to react to failure, use
    `run_checked`.
    """
    try:
        out = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    if out.returncode != 0:
        return ""
    return out.stdout


def run_checked(args: list[str], *, cwd: Path | None = None, timeout: float | None = None) -> subprocess.CompletedProcess:
    """Run `git <args>` and return the full CompletedProcess.

    Use when the caller needs to distinguish failure modes (e.g. non-zero exit
    vs missing binary) or to read stderr.
    """
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=timeout,
    )
