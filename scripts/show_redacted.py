#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Print a config file with secret values masked, so it can be read without leaking a credential.

Use this instead of Read/cat on files that may hold secrets (settings.local.json, .env,
~/.zshrc.private, ~/.claude.json, *.tfvars). Supports JSON, and KEY=VALUE / `export KEY=VALUE` lines.
A value is masked when its key name matches SECRET_KEY, or the value itself looks like a token.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SECRET_KEY = re.compile(r"token|secret|password|passwd|key|auth|credential|cookie|private|bearer", re.I)
SECRET_VALUE = re.compile(r"^(sk-|ghp_|gho_|github_pat_|xox[abp]-|AKIA|eyJ)[\w.\-]{8,}|^[A-Za-z0-9+/=_\-]{32,}$")
MASK = "***"


def _mask_json(node: object, key: str = "") -> object:
    """Return a copy of a parsed JSON value with secret-looking leaves masked."""
    if isinstance(node, dict):
        return {k: _mask_json(v, k) for k, v in node.items()}
    if isinstance(node, list):
        return [_mask_json(v, key) for v in node]
    if isinstance(node, str) and (SECRET_KEY.search(key) or SECRET_VALUE.search(node)):
        return MASK
    return node


def _mask_line(line: str) -> str:
    """Mask the value of a KEY=VALUE line when the key or the value looks secret."""
    m = re.match(r"^(\s*(?:export\s+)?)([A-Za-z_][\w.\-]*)(\s*[=:]\s*)(.*)$", line)
    if not m:
        return line
    head, key, sep, value = m.groups()
    if value and (SECRET_KEY.search(key) or SECRET_VALUE.search(value.strip("'\" "))):
        return f"{head}{key}{sep}{MASK}"
    return line


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: show_redacted.py <file>", file=sys.stderr)
        return 2
    path = Path(argv[1]).expanduser()
    assert path.is_file(), f"not a file: {path}"
    text = path.read_text()
    try:
        print(json.dumps(_mask_json(json.loads(text)), indent=2))
    except json.JSONDecodeError:
        print("\n".join(_mask_line(line) for line in text.splitlines()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
