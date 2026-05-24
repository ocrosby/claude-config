#!/usr/bin/env python3
"""Classify the working tree's changed files into conceptual commit groups.

Shared by both /git-cpr and /git-ship. Lives in `scripts/` (not under either
skill) because both consume it equally. Emits JSON so Claude can consume the
suggestions and make the final call on splits, branch names, and commit text.

A 'group' is a set of files that share a single conventional-commit (type,
scope) pair. The script heuristically assigns each file to one group; Claude
overrides when the heuristic is wrong.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

# Type inference by path. First match wins.
TYPE_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^\.github/workflows/"), "ci"),
    (re.compile(r"^(\.gitlab-ci|\.circleci|\.buildkite|\.travis)"), "ci"),
    (re.compile(r"^(Dockerfile|docker-compose\.|\.dockerignore)"), "build"),
    (re.compile(r"^(go\.mod|go\.sum|package\.json|package-lock\.json|pyproject\.toml|uv\.lock|requirements.*\.txt|Pipfile|Cargo\.toml|Cargo\.lock)$"), "build"),
    (re.compile(r"^Makefile$|^makefile$"), "build"),
    (re.compile(r"^(README|CHANGELOG|CONTRIBUTING|LICENSE|AUTHORS|HISTORY)"), "docs"),
    (re.compile(r"^docs?/"), "docs"),
    (re.compile(r"\.md$|\.rst$|\.adoc$"), "docs"),
    (re.compile(r".*_test\.go$|.*\.test\.[jt]sx?$|^tests?/"), "test"),
    (re.compile(r".*_spec\.rb$|.*\.spec\.[jt]sx?$"), "test"),
    (re.compile(r"\.css$|\.scss$|\.sass$|\.less$"), "style"),
]

# Scope inference: pull a meaningful subdirectory name.
SCOPE_PREFIXES = ("internal/", "pkg/", "cmd/", "src/", "app/", "apps/", "lib/", "skills/", "rules/", "agents/", "hooks/", "commands/")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    p.add_argument(
        "--include-untracked",
        action="store_true",
        default=True,
        help="Include untracked files in the analysis (default: on)",
    )
    p.add_argument(
        "--no-untracked",
        dest="include_untracked",
        action="store_false",
        help="Exclude untracked files",
    )
    p.add_argument(
        "--from",
        dest="from_ref",
        default=None,
        help="Compare against a ref instead of working tree (e.g. main, HEAD~3)",
    )
    return p.parse_args()


def run(cmd: list[str]) -> str:
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        return ""
    return out.stdout


def current_branch() -> str:
    return run(["git", "branch", "--show-current"]).strip()


def changed_files(include_untracked: bool, from_ref: str | None) -> list[tuple[str, str]]:
    """Return (status_code, path) pairs for changed files."""
    if from_ref:
        # Compare against a ref — only show files that differ
        raw = run(["git", "diff", "--name-status", from_ref])
        return [(line.split(maxsplit=1)[0], line.split(maxsplit=1)[1]) for line in raw.splitlines() if line.strip()]
    raw = run(["git", "status", "--porcelain"])
    pairs: list[tuple[str, str]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        # Porcelain format: XY <path>
        code = line[:2].strip()
        path = line[3:].strip()
        if "->" in path:  # rename
            path = path.split("->")[1].strip()
        if code == "??" and not include_untracked:
            continue
        pairs.append((code, path))
    return pairs


def infer_type(path: str) -> str:
    for pattern, t in TYPE_RULES:
        if pattern.search(path):
            return t
    return "feat"  # default for code


def infer_scope(path: str) -> str:
    """Pick a single-word scope from the path."""
    # Strip a known prefix and take the next path segment
    for prefix in SCOPE_PREFIXES:
        if path.startswith(prefix):
            remainder = path[len(prefix):]
            first = remainder.split("/", 1)[0]
            # If 'first' is itself a file, drop the extension and use top-level prefix
            if "." in first:
                return prefix.rstrip("/")
            return first
    # Top-level files: use the top dir, or the stem for root files
    if "/" in path:
        return path.split("/", 1)[0]
    return Path(path).stem.split("-")[0].split("_")[0]


def derive_branch(commit_type: str, scope: str) -> str:
    """Suggest a branch name. type 'feat' → feature/, 'fix' → hotfix/, others → feature/<type>-..."""
    if commit_type == "feat":
        prefix = "feature/"
        name_hint = scope or "changes"
    elif commit_type == "fix":
        prefix = "hotfix/"
        name_hint = scope or "fix"
    else:
        prefix = "feature/"
        name_hint = f"{commit_type}-{scope}" if scope else commit_type
    # Sanitize
    name_hint = re.sub(r"[^a-z0-9-]+", "-", name_hint.lower()).strip("-") or "changes"
    return f"{prefix}{name_hint}"


def group_files(pairs: list[tuple[str, str]]) -> list[dict]:
    """Bin files by (type, scope), preserving 'pair test files with their target' heuristic."""
    bins: dict[tuple[str, str], list[str]] = defaultdict(list)
    for _code, path in pairs:
        t = infer_type(path)
        s = infer_scope(path)
        # Test files inherit the scope of their counterpart but keep type=test
        # — Claude can decide to merge with the implementation group post-hoc.
        bins[(t, s)].append(path)
    groups = []
    for (t, s), files in sorted(bins.items()):
        groups.append(
            {
                "type": t,
                "scope": s,
                "files": sorted(files),
                "suggested_branch": derive_branch(t, s),
            }
        )
    return groups


def main() -> int:
    args = parse_args()
    branch = current_branch()
    if not branch:
        print(json.dumps({"error": "not in a git repository"}), file=sys.stderr)
        return 1
    pairs = changed_files(args.include_untracked, args.from_ref)
    if not pairs:
        print(json.dumps({"branch": branch, "is_main": branch in ("main", "master"), "groups": [], "untracked_only": False}, indent=2))
        return 0
    has_untracked = any(code == "??" for code, _ in pairs)
    groups = group_files(pairs)
    print(
        json.dumps(
            {
                "branch": branch,
                "is_main": branch in ("main", "master"),
                "from_ref": args.from_ref,
                "untracked_included": args.include_untracked,
                "has_untracked": has_untracked,
                "groups": groups,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
