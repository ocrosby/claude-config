"""Shared argparse helpers for the scripts/ CLIs.

Every Python script in scripts/ constructs its ArgumentParser the same way:
description taken from the first line of the module docstring. Severity and
--json flags repeat across the check_* scripts with identical choices. Path
expansion follows one of a handful of conventions (file / dir-with-globs /
relative-glob fallback). Centralising these keeps the CLI surface consistent
and prevents drift when a new script is added.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable


def make_parser(module_doc: str | None) -> argparse.ArgumentParser:
    """Build an ArgumentParser whose description is the first line of `module_doc`.

    Pass the caller's `__doc__` directly. Falls back to an empty description if
    the module has no docstring.
    """
    description = (module_doc or "").splitlines()[0] if module_doc else ""
    return argparse.ArgumentParser(description=description)


def add_severity_flag(parser: argparse.ArgumentParser, help_text: str | None = None) -> None:
    """Add `--severity {must,should,consider,all}` with default `all`.

    `help_text` is passed straight to argparse — leave it None to omit the
    help string entirely (matches the per-script defaults of check_rest,
    check_action_yml, and check_workflows).
    """
    kwargs: dict = {"choices": ["must", "should", "consider", "all"], "default": "all"}
    if help_text is not None:
        kwargs["help"] = help_text
    parser.add_argument("--severity", **kwargs)


def add_json_flag(parser: argparse.ArgumentParser, help_text: str = "Emit findings as JSON") -> None:
    """Add the standard `--json` boolean flag."""
    parser.add_argument("--json", action="store_true", help=help_text)


def expand_paths(
    patterns: list[str],
    *,
    accept_file: Callable[[Path], bool] = lambda _: True,
    dir_globs: tuple[str, ...] = (),
    recursive: bool = True,
    skip_absolute_glob: bool = False,
) -> list[Path]:
    """Resolve a mix of files, directories, and globs into a sorted unique file list.

    For each input pattern:
      - if it points at a file, include it when `accept_file(file)` is True.
      - if it points at a directory, walk it with each entry in `dir_globs`
        (using `rglob` when `recursive=True`, else `glob`). Each matched file
        must still pass `accept_file`.
      - otherwise fall back to a `Path('.').glob(pattern)` match. Absolute
        patterns can be skipped with `skip_absolute_glob=True` because Pathlib
        cannot glob absolute strings.

    `accept_file` lets each caller pin its own acceptance rule (by extension,
    by filename, etc.) without forking the loop body.
    """
    out: list[Path] = []
    for pattern in patterns:
        p = Path(pattern)
        if p.is_file():
            if accept_file(p):
                out.append(p)
            continue
        if p.is_dir():
            glob_method = "rglob" if recursive else "glob"
            for g in dir_globs:
                out.extend(
                    q for q in getattr(p, glob_method)(g)
                    if q.is_file() and accept_file(q)
                )
            continue
        if skip_absolute_glob and Path(pattern).is_absolute():
            continue
        for match in Path(".").glob(pattern):
            if match.is_file() and accept_file(match):
                out.append(match)
    return sorted(set(out))


def die(msg: str, code: int = 1) -> int:
    """Print `error: <msg>` to stderr and return `code` for use as the script's exit status."""
    print(f"error: {msg}", file=sys.stderr)
    return code
