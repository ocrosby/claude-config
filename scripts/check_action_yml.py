#!/usr/bin/env python3
"""Deterministic checks for GitHub Action definition files (action.yml / action.yaml).

Replaces the inline checklist in skills/code-review/SKILL.md so the rules
fire automatically when /code-review touches a GitHub Action definition.
Same shape as check_docs.py / check_rest.py — severity tiers, file:line +
rule_id + message lines, --json + --severity flags.

The checks are regex-based against line content so no third-party YAML
parser is required (consistent with the rest of the script catalog).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import cli as _cli  # noqa: E402  # type: ignore[import-not-found]
from _lib import findings as _findings  # noqa: E402  # type: ignore[import-not-found]
from _lib.findings import MUST, SHOULD  # noqa: E402  # type: ignore[import-not-found]

NAME_RE = re.compile(r"^name:\s*['\"]?([^'\"\n]+)['\"]?\s*$")
DESC_RE = re.compile(r"^description:\s*['\"]?(.+?)['\"]?\s*$")
USING_COMPOSITE_RE = re.compile(r"^\s*using:\s*['\"]?composite['\"]?\s*$")
RUN_RE = re.compile(r"^(\s*)run:\s*")
SHELL_RE = re.compile(r"^\s*shell:\s*")
SECRETS_REF_RE = re.compile(r"\$\{\{\s*secrets\.\w+\s*\}\}")
ENV_BLOCK_RE = re.compile(r"^(\s*)env:\s*$")
INPUTS_BLOCK_RE = re.compile(r"^inputs:\s*$")
INPUT_KEY_RE = re.compile(r"^  ([a-zA-Z_][\w-]*):\s*$")
INPUT_DESCRIPTION_RE = re.compile(r"^    description:\s*")
BRANDING_BLOCK_RE = re.compile(r"^branding:\s*$")
BRANDING_FIELD_RE = re.compile(r"^  (icon|color):\s*")


def parse_args():
    p = _cli.make_parser(__doc__)
    p.add_argument("paths", nargs="+", help="action.yml / action.yaml files")
    _cli.add_json_flag(p)
    _cli.add_severity_flag(p)
    return p.parse_args()


_ACTION_NAMES = ("action.yml", "action.yaml")


def expand_paths(patterns: list[str]) -> list[Path]:
    return _cli.expand_paths(
        patterns,
        accept_file=lambda q: q.name in _ACTION_NAMES,
        dir_globs=_ACTION_NAMES,
        recursive=False,
    )


def check_name(lines: list[str]) -> list[tuple[int, str, str, str]]:
    findings: list[tuple[int, str, str, str]] = []
    for i, line in enumerate(lines, 1):
        m = NAME_RE.match(line)
        if m:
            name = m.group(1).strip()
            if not name.endswith("by Jedi Knights"):
                findings.append((i, SHOULD, "action-name-suffix", f"name '{name}' should end with 'by Jedi Knights' for marketplace consistency"))
            break  # only the first top-level name: counts
    return findings


def check_description(lines: list[str]) -> list[tuple[int, str, str, str]]:
    findings: list[tuple[int, str, str, str]] = []
    for i, line in enumerate(lines, 1):
        m = DESC_RE.match(line)
        if m:
            desc = m.group(1).strip()
            if len(desc) >= 125:
                findings.append((i, MUST, "action-description-too-long", f"description is {len(desc)} chars — GitHub truncates at 125 on the marketplace"))
            break  # only top-level description matters here
    return findings


def check_branding(lines: list[str], text: str) -> list[tuple[int, str, str, str]]:
    findings: list[tuple[int, str, str, str]] = []
    if not BRANDING_BLOCK_RE.search(text):
        # No branding at all
        findings.append((0, SHOULD, "action-no-branding", "no branding: block — add branding.icon and branding.color for marketplace presentation"))
        return findings
    # Find branding block index, then check its children
    block_start = None
    for i, line in enumerate(lines):
        if BRANDING_BLOCK_RE.match(line):
            block_start = i
            break
    if block_start is None:
        return findings
    fields_found: set[str] = set()
    for line in lines[block_start + 1:]:
        if line and not line[0].isspace():
            break  # left the block
        m = BRANDING_FIELD_RE.match(line)
        if m:
            fields_found.add(m.group(1))
    for required in ("icon", "color"):
        if required not in fields_found:
            findings.append((block_start + 1, SHOULD, "action-no-branding", f"branding: block missing '{required}' field"))
    return findings


def check_inputs(lines: list[str]) -> list[tuple[int, str, str, str]]:
    findings: list[tuple[int, str, str, str]] = []
    in_inputs = False
    pending_input: tuple[int, str] | None = None  # (line_no, key_name)
    has_description = False
    for i, line in enumerate(lines, 1):
        if INPUTS_BLOCK_RE.match(line):
            in_inputs = True
            continue
        if in_inputs:
            # End the block when a new top-level key appears (no leading space, contains ":")
            if line and not line[0].isspace() and ":" in line and not line.startswith("inputs"):
                # Emit pending input if it never got a description
                if pending_input and not has_description:
                    findings.append((pending_input[0], MUST, "action-input-no-description", f"input '{pending_input[1]}' has no description"))
                pending_input = None
                in_inputs = False
                continue
            m = INPUT_KEY_RE.match(line)
            if m:
                # Close out previous input
                if pending_input and not has_description:
                    findings.append((pending_input[0], MUST, "action-input-no-description", f"input '{pending_input[1]}' has no description"))
                pending_input = (i, m.group(1))
                has_description = False
                continue
            if pending_input and INPUT_DESCRIPTION_RE.match(line):
                has_description = True
    # Close out final pending input
    if pending_input and not has_description:
        findings.append((pending_input[0], MUST, "action-input-no-description", f"input '{pending_input[1]}' has no description"))
    return findings


def check_composite_steps(lines: list[str]) -> list[tuple[int, str, str, str]]:
    """For composite actions, every step that uses 'run:' must have 'shell:'."""
    findings: list[tuple[int, str, str, str]] = []
    is_composite = any(USING_COMPOSITE_RE.match(line) for line in lines)
    if not is_composite:
        return findings
    # Find each step block (steps: → entries beginning with "  - ")
    in_steps = False
    step_start_line: int | None = None
    step_block_indent: int | None = None
    step_lines: list[str] = []

    def flush_step():
        if step_start_line is None or not step_lines:
            return
        has_run = any(RUN_RE.match(ln) for ln in step_lines)
        has_shell = any(SHELL_RE.match(ln) for ln in step_lines)
        if has_run and not has_shell:
            findings.append((step_start_line, MUST, "action-composite-missing-shell", "composite step uses 'run:' without 'shell:' — every composite run step must declare a shell"))

    for i, line in enumerate(lines, 1):
        if re.match(r"^\s*steps:\s*$", line):
            in_steps = True
            continue
        if in_steps:
            # New step starts with a dash at consistent indent: "  - name:" or "  - uses:" or "  - run:"
            m = re.match(r"^(\s+)-\s", line)
            if m:
                flush_step()
                step_lines = [line]
                step_start_line = i
                step_block_indent = len(m.group(1))
                continue
            if step_block_indent is not None and line and not line.startswith(" "):
                # Left the steps block entirely
                flush_step()
                step_lines = []
                step_start_line = None
                in_steps = False
                continue
            if step_lines:
                step_lines.append(line)
    flush_step()
    return findings


def check_secrets_in_composite_env(lines: list[str]) -> list[tuple[int, str, str, str]]:
    """Inside a composite step's run block, secrets.* in env: is forbidden."""
    findings: list[tuple[int, str, str, str]] = []
    is_composite = any(USING_COMPOSITE_RE.match(line) for line in lines)
    if not is_composite:
        return findings
    in_env_block = False
    env_block_indent: int | None = None
    for i, line in enumerate(lines, 1):
        if not in_env_block:
            m = ENV_BLOCK_RE.match(line)
            if m:
                in_env_block = True
                env_block_indent = len(m.group(1))
                continue
        else:
            stripped = line.rstrip()
            if stripped and len(stripped) - len(stripped.lstrip()) <= (env_block_indent or 0):
                in_env_block = False
                env_block_indent = None
                continue
            if SECRETS_REF_RE.search(line):
                findings.append((i, MUST, "action-secrets-in-env", "secrets.* used directly in env: inside a composite step — pass via inputs: only"))
    return findings


def check_file(path: Path) -> list[tuple[int, str, str, str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines = text.splitlines()
    findings: list[tuple[int, str, str, str]] = []
    findings.extend(check_name(lines))
    findings.extend(check_description(lines))
    findings.extend(check_branding(lines, text))
    findings.extend(check_inputs(lines))
    findings.extend(check_composite_steps(lines))
    findings.extend(check_secrets_in_composite_env(lines))
    return sorted(findings, key=lambda f: (f[0], f[1]))


def main() -> int:
    args = parse_args()
    files = expand_paths(args.paths)
    if not files:
        return _cli.die("no action.yml/action.yaml files matched")

    by_file: dict[str, list[tuple[int, str, str, str]]] = {}
    for path in files:
        findings = _findings.filter_by_severity(check_file(path), args.severity)
        if findings:
            by_file[str(path)] = findings

    if args.json:
        print(_findings.format_json(by_file))
        return 0

    total = sum(len(v) for v in by_file.values())
    print(f"# GitHub Action definition checks\n\nFiles scanned: **{len(files)}** — findings: **{total}**\n")
    if not by_file:
        print("_No mechanical violations detected._")
        return 0

    _findings.print_markdown(by_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
