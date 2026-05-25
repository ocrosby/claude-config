#!/usr/bin/env python3
"""Deterministic checks for GitHub Actions workflow files (.github/workflows/*.yml).

Replaces the inline checklist in skills/code-review/SKILL.md. Same shape as
check_action_yml.py and the rest of the script catalog — severity tiers,
file:line + rule_id + message, --json + --severity flags, standard library
only.

Some rules need access to repo-level state (go.work existence, .golangci.yml
version) — the script accepts --repo-root for that. Defaults to cwd.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

MUST = "Must Fix"
SHOULD = "Should Fix"
CONSIDER = "Consider"

USES_GOLANGCI_RE = re.compile(r"^\s*-?\s*uses:\s*golangci/golangci-lint-action@v(\d+)")
USES_LATEST_RE = re.compile(r"^\s*-?\s*uses:\s*[^@\s]+@latest\s*$")
GO_TEST_ROOT_RE = re.compile(r"\bgo\s+test\s+(?:-[^\s]+\s+)*\./\.\.\.")
GOLANGCI_RUN_ROOT_RE = re.compile(r"\bgolangci-lint\s+run\s+(?:-[^\s]+\s+)*\./\.\.\.")
MATRIX_BLOCK_RE = re.compile(r"^\s*matrix:\s*$")
FAIL_FAST_RE = re.compile(r"^\s*fail-fast:\s*(true|false)")
PERMISSIONS_BLOCK_RE = re.compile(r"^\s*permissions:\s*$")
CONTENTS_READ_RE = re.compile(r"^\s*contents:\s*(read|write)")
ACTIONS_CHECKOUT_RE = re.compile(r"^\s*-?\s*uses:\s*actions/checkout@")
CONCURRENCY_BLOCK_RE = re.compile(r"^\s*concurrency:\s*")
CANCEL_IN_PROGRESS_FALSE_RE = re.compile(r"cancel-in-progress:\s*false")
GO_VERSION_RE = re.compile(r"\bgo-version:\s*['\"]?([0-9][0-9.]+)['\"]?")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    p.add_argument("paths", nargs="+", help="Workflow files or globs (.github/workflows/*.yml)")
    p.add_argument("--repo-root", default=".", help="Repo root (for go.work / .golangci.yml lookups)")
    p.add_argument("--json", action="store_true", help="Emit findings as JSON")
    p.add_argument(
        "--severity",
        choices=["must", "should", "consider", "all"],
        default="all",
    )
    return p.parse_args()


def expand_paths(patterns: list[str]) -> list[Path]:
    out: list[Path] = []
    for pattern in patterns:
        p = Path(pattern)
        if p.is_file() and p.suffix in (".yml", ".yaml"):
            out.append(p)
            continue
        if p.is_dir():
            out.extend(q for q in p.glob("*.yml") if q.is_file())
            out.extend(q for q in p.glob("*.yaml") if q.is_file())
            continue
        # Skip glob fallback for absolute paths (Pathlib disallows it) — the
        # path was neither a file nor a directory, so nothing to match.
        if Path(pattern).is_absolute():
            continue
        for match in Path(".").glob(pattern):
            if match.is_file() and match.suffix in (".yml", ".yaml"):
                out.append(match)
    return sorted(set(out))


def detect_repo_state(repo_root: Path) -> dict:
    """Pre-compute repo-level facts used by multiple checks."""
    state = {
        "has_go_work": (repo_root / "go.work").exists(),
        "golangci_yaml_version": None,
        "has_golangci_yaml": False,
    }
    for name in (".golangci.yml", ".golangci.yaml"):
        cfg = repo_root / name
        if cfg.exists():
            state["has_golangci_yaml"] = True
            try:
                text = cfg.read_text(encoding="utf-8", errors="replace")
            except OSError:
                break
            m = re.search(r"^\s*version:\s*['\"]?(\d+)['\"]?", text, re.MULTILINE)
            state["golangci_yaml_version"] = m.group(1) if m else None
            break
    return state


def check_go_workspace_root(lines: list[str], state: dict) -> list[tuple[int, str, str, str]]:
    findings: list[tuple[int, str, str, str]] = []
    if not state["has_go_work"]:
        return findings
    for i, line in enumerate(lines, 1):
        if GO_TEST_ROOT_RE.search(line) or GOLANGCI_RUN_ROOT_RE.search(line):
            findings.append((i, SHOULD, "workflow-go-workspace-mismatch", "repo has go.work but command runs from root with ./... — iterate per-module instead"))
    return findings


def check_golangci_action_version(lines: list[str]) -> list[tuple[int, str, str, str]]:
    findings: list[tuple[int, str, str, str]] = []
    for i, line in enumerate(lines, 1):
        m = USES_GOLANGCI_RE.search(line)
        if m and int(m.group(1)) < 9:
            findings.append((i, SHOULD, "workflow-golangci-lint-version", f"golangci-lint-action@v{m.group(1)} caps at golangci-lint v1 (built with Go 1.24) — use @v9 for Go 1.26+ modules"))
    return findings


def check_golangci_config_v1(state: dict) -> list[tuple[int, str, str, str]]:
    findings: list[tuple[int, str, str, str]] = []
    if state["has_golangci_yaml"] and state["golangci_yaml_version"] != "2":
        findings.append((0, SHOULD, "workflow-golangci-config-v1", ".golangci.yml lacks `version: \"2\"` — v1 config is silently rejected by golangci-lint v2"))
    return findings


def check_matrix_fail_fast(lines: list[str]) -> list[tuple[int, str, str, str]]:
    findings: list[tuple[int, str, str, str]] = []
    matrix_lines: list[int] = []
    for i, line in enumerate(lines, 1):
        if MATRIX_BLOCK_RE.match(line):
            matrix_lines.append(i)
    if not matrix_lines:
        return findings
    # Walk the file; if a matrix block exists but no explicit fail-fast: false is found nearby, flag.
    has_explicit_false = any(FAIL_FAST_RE.search(line) and "false" in line for line in lines)
    if not has_explicit_false:
        findings.append((matrix_lines[0], CONSIDER, "workflow-matrix-fail-fast", "matrix block found without explicit `fail-fast: false` — default `true` cascades cancellations across independent jobs"))
    return findings


def check_permissions(lines: list[str]) -> list[tuple[int, str, str, str]]:
    findings: list[tuple[int, str, str, str]] = []
    uses_checkout = any(ACTIONS_CHECKOUT_RE.search(line) for line in lines)
    if not uses_checkout:
        return findings
    has_permissions_block = any(PERMISSIONS_BLOCK_RE.match(line) for line in lines)
    if not has_permissions_block:
        # Find the checkout line for the finding location
        for i, line in enumerate(lines, 1):
            if ACTIONS_CHECKOUT_RE.search(line):
                findings.append((i, MUST, "workflow-missing-permissions", "actions/checkout used without a permissions: block declaring contents: read"))
                break
    return findings


def check_release_concurrency(path: Path, lines: list[str], text: str) -> list[tuple[int, str, str, str]]:
    findings: list[tuple[int, str, str, str]] = []
    is_release = "release" in path.stem.lower() or re.search(r"^name:\s*['\"]?[^\n]*release", text, re.MULTILINE | re.IGNORECASE)
    if not is_release:
        return findings
    has_concurrency = any(CONCURRENCY_BLOCK_RE.search(line) for line in lines)
    has_cancel_false = bool(CANCEL_IN_PROGRESS_FALSE_RE.search(text))
    if not has_concurrency or not has_cancel_false:
        # Find a reasonable location to point at
        for i, line in enumerate(lines, 1):
            if line.startswith("name:") or line.startswith("on:"):
                findings.append((i, SHOULD, "workflow-release-no-concurrency", "release workflow should set `concurrency: { group: release, cancel-in-progress: false }` to prevent parallel releases"))
                return findings
        findings.append((0, SHOULD, "workflow-release-no-concurrency", "release workflow should set `concurrency: { group: release, cancel-in-progress: false }` to prevent parallel releases"))
    return findings


def check_pinned_versions(lines: list[str]) -> list[tuple[int, str, str, str]]:
    findings: list[tuple[int, str, str, str]] = []
    for i, line in enumerate(lines, 1):
        if USES_LATEST_RE.search(line):
            findings.append((i, SHOULD, "workflow-action-pinned-latest", "action pinned to @latest — pin to a major version (@v4, @v9) to avoid unexpected breakage"))
    return findings


def check_go_version_drift(lines: list[str]) -> list[tuple[int, str, str, str]]:
    findings: list[tuple[int, str, str, str]] = []
    versions: list[tuple[int, str]] = []
    for i, line in enumerate(lines, 1):
        m = GO_VERSION_RE.search(line)
        if m:
            versions.append((i, m.group(1)))
    distinct = {v for _, v in versions}
    if len(distinct) > 1:
        # Flag every occurrence after the first
        first_value = versions[0][1]
        for i, v in versions:
            if v != first_value:
                findings.append((i, MUST, "workflow-go-version-drift", f"go-version: {v} disagrees with earlier go-version: {first_value} in the same file"))
    return findings


def check_file(path: Path, state: dict) -> list[tuple[int, str, str, str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines = text.splitlines()
    findings: list[tuple[int, str, str, str]] = []
    findings.extend(check_go_workspace_root(lines, state))
    findings.extend(check_golangci_action_version(lines))
    findings.extend(check_golangci_config_v1(state))
    findings.extend(check_matrix_fail_fast(lines))
    findings.extend(check_permissions(lines))
    findings.extend(check_release_concurrency(path, lines, text))
    findings.extend(check_pinned_versions(lines))
    findings.extend(check_go_version_drift(lines))
    return sorted(findings, key=lambda f: (f[0], f[1]))


def filter_severity(findings, wanted: str):
    if wanted == "all":
        return findings
    keep = {"must": MUST, "should": SHOULD, "consider": CONSIDER}[wanted]
    return [f for f in findings if f[1] == keep]


def main() -> int:
    args = parse_args()
    files = expand_paths(args.paths)
    if not files:
        print("error: no workflow files matched", file=sys.stderr)
        return 1
    state = detect_repo_state(Path(args.repo_root).resolve())

    by_file: dict[str, list[tuple[int, str, str, str]]] = {}
    for path in files:
        findings = filter_severity(check_file(path, state), args.severity)
        if findings:
            by_file[str(path)] = findings

    if args.json:
        payload = {
            str(path): [
                {"line": line, "severity": sev, "rule_id": rule, "message": msg}
                for (line, sev, rule, msg) in findings
            ]
            for path, findings in by_file.items()
        }
        print(json.dumps(payload, indent=2))
        return 0

    total = sum(len(v) for v in by_file.values())
    print(f"# GitHub Actions workflow checks\n\nFiles scanned: **{len(files)}** — findings: **{total}**\n")
    if state["has_go_work"]:
        print("_Repo has go.work — workspace-mode rules active._\n")
    if not by_file:
        print("_No mechanical violations detected._")
        return 0

    for path, findings in sorted(by_file.items()):
        print(f"## `{path}`\n")
        for sev in (MUST, SHOULD, CONSIDER):
            tier = [f for f in findings if f[1] == sev]
            if not tier:
                continue
            print(f"### {sev}")
            for line, _, rule, msg in tier:
                line_str = f"line {line}" if line > 0 else "document-level"
                print(f"- `{rule}` ({line_str}) — {msg}")
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
