#!/usr/bin/env python3
"""Build the deterministic skeleton of a knowledge-base wiki index from a raw/ tree.

Walks a `raw/` directory and emits a Markdown table of contents that links every
asset with its type and size, grouped by top-level subfolder. The semantic
one-line summary of each asset is left as a placeholder for the model to fill in
(the `/knowledge-base` skill does that) — this script only produces the stable,
regenerable structure so the skill body carries no directory-walking logic.

Output is Markdown to stdout; exit 0 on success, 1 on a bad path.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import cli as _cli  # noqa: E402  # type: ignore[import-not-found]

# Assets larger than this are still indexed; the size column simply flags them.
_SIZE_UNITS = ("B", "KB", "MB", "GB", "TB")
# Placeholder the model replaces with a real one-line summary during reindex.
SUMMARY_PLACEHOLDER = "_summary pending — fill in from the asset_"
BANNER = "<!-- AI-GENERATED — do not hand-edit; regenerate via /knowledge-base -->"


def human_size(num_bytes: int) -> str:
    """Return a compact human-readable size like `12 KB` for a byte count."""
    size = float(num_bytes)
    for unit in _SIZE_UNITS:
        if size < 1024 or unit == _SIZE_UNITS[-1]:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} {_SIZE_UNITS[-1]}"


def collect(raw_root: Path) -> dict[str, list[Path]]:
    """Group every file under `raw_root` by its top-level subfolder name.

    Files sitting directly in `raw/` are grouped under the key "" (rendered as a
    top-level section). Hidden files and directories (dot-prefixed) are skipped.
    Returns an insertion-ordered dict of group name -> sorted file paths.
    """
    groups: dict[str, list[Path]] = {}
    # rglob once, then bucket — single pass over the tree (O(n) in file count).
    for path in sorted(raw_root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(raw_root)
        if any(part.startswith(".") for part in rel.parts):
            continue
        group = rel.parts[0] if len(rel.parts) > 1 else ""
        groups.setdefault(group, []).append(path)
    return groups


def render(raw_root: Path, groups: dict[str, list[Path]]) -> str:
    """Render the grouped assets as a Markdown index linking back into raw/."""
    lines = [
        BANNER,
        "",
        "# Knowledge Base — Index",
        "",
        f"Index of `{raw_root.name}/`. Regenerate with `/knowledge-base` — never hand-edit.",
        "",
    ]
    total = sum(len(files) for files in groups.values())
    if total == 0:
        lines.append("_No assets yet. Add files under `raw/`, then reindex._")
        return "\n".join(lines) + "\n"

    # Loose files first (group ""), then named subfolders alphabetically.
    for group in sorted(groups, key=lambda g: (g != "", g)):
        heading = group if group else "Top level"
        lines.append(f"## {heading}")
        lines.append("")
        lines.append("| Asset | Type | Size | Summary |")
        lines.append("|---|---|---|---|")
        for path in groups[group]:
            rel = path.relative_to(raw_root.parent)  # link relative to KB root (wiki/ sibling of raw/)
            ext = path.suffix.lstrip(".").lower() or "—"
            size = human_size(path.stat().st_size)
            lines.append(f"| [{path.name}](../{rel.as_posix()}) | {ext} | {size} | {SUMMARY_PLACEHOLDER} |")
        lines.append("")
    lines.append(f"_Total: {total} asset(s)._")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = _cli.make_parser(__doc__)
    parser.add_argument("raw", help="Path to the knowledge base's raw/ directory")
    args = parser.parse_args(argv)

    raw_root = Path(args.raw).expanduser()
    if not raw_root.is_dir():
        return _cli.die(f"not a directory: {raw_root}")
    if raw_root.name != "raw":
        # Guard against pointing the walker at the wrong tree — the KB contract is raw/.
        return _cli.die(f"expected a directory named 'raw', got '{raw_root.name}'")

    print(render(raw_root, collect(raw_root)), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
