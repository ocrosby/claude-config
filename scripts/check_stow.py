#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Check that a stow package is fully and cleanly linked into its target.

README structure checks tell you the docs are shaped right; this tells you
the config is actually wired up. It answers three questions `git status`
cannot:

  - Is anything in the package not linked into the target? (a directory
    added months ago that nobody re-stowed)
  - Would a re-stow link something that is not config? (tool caches, which
    self-ignore for git and so never show up in `git status`)
  - Does the target hold a link into the package whose target is gone?

The stow plan is the source of truth, so this shells out to
`stow --simulate -v -R` rather than reimplementing .stow-local-ignore
matching.

Output: Markdown findings grouped by severity (Must Fix / Should Fix /
Consider). Use --json for machine-consumable output.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import cli as _cli  # noqa: E402  # type: ignore[import-not-found]
from _lib import findings as _findings  # noqa: E402  # type: ignore[import-not-found]
from _lib.findings import MUST  # noqa: E402  # type: ignore[import-not-found]

# `stow -R` unlinks everything then relinks it, so an entry that is already
# linked comes back annotated. An unannotated LINK is one that does not
# exist in the target yet.
LINK_RE = re.compile(
    r"^LINK: (?P<name>.+?) => (?P<target>.+?)(?P<revert> \(reverts previous action\))?$"
)

# Names that are build or tool output, never configuration. Matched against
# the top-level entry name only.
JUNK_PATTERNS = (
    re.compile(r"^\..*_cache$"),
    re.compile(r"^__pycache__$"),
    re.compile(r"^node_modules$"),
    re.compile(r"^\.DS_Store$"),
    re.compile(r"^\.(pytest|mypy|ruff|tox)_cache$"),
    re.compile(r"^.*\.egg-info$"),
)

# Timeout for the stow subprocess. A simulate run is fast; anything slower
# than this means stow is wedged, not busy.
STOW_TIMEOUT_SECONDS = 60


def is_junk(name: str) -> bool:
    """True when `name` is tool output rather than configuration."""
    return any(p.match(name) for p in JUNK_PATTERNS)


def stow_plan(
    package_dir: Path, target: Path, package: str
) -> list[tuple[str, str, bool]]:
    """Return [(name, link_target, already_linked)] from `stow --simulate -v -R`.

    Raises RuntimeError when stow is missing or fails.
    """
    if shutil.which("stow") is None:
        raise RuntimeError("GNU Stow is not installed")
    proc = subprocess.run(
        [
            "stow",
            "--simulate",
            "-v",
            "-R",
            "-t",
            str(target),
            "-d",
            str(package_dir),
            package,
        ],
        capture_output=True,
        text=True,
        timeout=STOW_TIMEOUT_SECONDS,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"stow failed: {proc.stderr.strip() or proc.stdout.strip()}")
    plan: list[tuple[str, str, bool]] = []
    # stow writes its plan to stderr on some versions and stdout on others.
    for line in (proc.stderr + "\n" + proc.stdout).splitlines():
        m = LINK_RE.match(line.strip())
        if m:
            plan.append((m["name"], m["target"], bool(m["revert"])))
    return plan


def check_broken_links(
    package_dir: Path, target: Path, package: str
) -> list[tuple[int, str, str, str]]:
    """Find symlinks in `target` that point into the package but dangle."""
    findings: list[tuple[int, str, str, str]] = []
    pkg_root = (package_dir / package).resolve()
    if not target.is_dir():
        return findings
    for entry in sorted(target.iterdir()):
        if not entry.is_symlink():
            continue
        dest = Path(os.path.realpath(entry))
        # Only our own links are our business; the target directory is
        # expected to hold unrelated files and links.
        try:
            inside = dest == pkg_root or pkg_root in dest.parents
        except OSError:
            continue
        if not inside:
            # A dangling link whose text points at the package still counts.
            raw = os.readlink(entry)
            if package not in raw:
                continue
        if not entry.exists():
            findings.append(
                (
                    0,
                    MUST,
                    "stow-broken-link",
                    f"`{entry.name}` in the target is a symlink into the package "
                    f"but its destination no longer exists — re-stow to clear it",
                )
            )
    return findings


def check(
    package_dir: Path, target: Path, package: str
) -> list[tuple[int, str, str, str]]:
    """Return findings for one package/target pair, most severe first."""
    findings: list[tuple[int, str, str, str]] = []
    plan = stow_plan(package_dir, target, package)

    # If nothing at all is linked, the package was never stowed here — or
    # this is the wrong target. Either way, reporting every entry as
    # individually "unlinked" buries the one fact that matters under a wall
    # of noise. Say it once, and stop.
    #
    # Seen for real: pointing this at a Neovim plugin repo that a plugin
    # manager *clones* rather than links produced ten Must Fix findings,
    # every one of them false.
    if plan and not any(already_linked for _n, _d, already_linked in plan):
        return [
            (
                0,
                MUST,
                "stow-nothing-linked",
                f"the target holds no links into `{package}` — it was never "
                f"stowed there, or this is the wrong target. No other checks "
                f"were run ({len(plan)} package entries would be linked by a stow)",
            )
        ]

    for name, _dest, already_linked in plan:
        if is_junk(name):
            findings.append(
                (
                    0,
                    MUST,
                    "stow-junk-linked",
                    f"`{name}` is tool output, not configuration, but a re-stow "
                    f"would link it into the target — add it to .stow-local-ignore",
                )
            )
        elif not already_linked:
            findings.append(
                (
                    0,
                    MUST,
                    "stow-unlinked",
                    f"`{name}` is in the package but not linked into the target — "
                    f"re-stow so it takes effect",
                )
            )
    findings.extend(check_broken_links(package_dir, target, package))
    return sorted(findings, key=lambda f: (f[1] != MUST, f[2], f[3]))


EXAMPLES = """\
Examples:
  check_stow.py                                  # this repo -> ~/.claude
  check_stow.py --target ~/.config/nvim          # a different target
  check_stow.py --fail-on=must                   # CI gate
  check_stow.py --json                           # machine-consumable
"""


def parse_args():
    p = _cli.make_parser(__doc__, examples=EXAMPLES)
    p.add_argument(
        "--package-dir",
        default=None,
        help="Directory containing the stow package (default: the repo's parent)",
    )
    p.add_argument(
        "--package",
        default=None,
        help="Package name (default: the repo directory's name)",
    )
    p.add_argument(
        "--target",
        default="~/.claude",
        help="Where the package is stowed (default: ~/.claude)",
    )
    _cli.add_json_flag(p)
    _cli.add_severity_flag(p, help_text="Filter by severity level")
    _cli.add_fail_on_flag(p)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(__file__).resolve().parent.parent
    package_dir = (
        Path(args.package_dir).expanduser() if args.package_dir else repo.parent
    )
    package = args.package or repo.name
    target = Path(args.target).expanduser()

    if not (package_dir / package).is_dir():
        return _cli.die(f"package not found: {package_dir / package}")
    if not target.is_dir():
        return _cli.die(f"target is not a directory: {target}")

    try:
        raw = check(package_dir, target, package)
    except RuntimeError as exc:
        return _cli.die(str(exc))

    label = f"{package} -> {target}"
    filtered = _findings.filter_by_severity(raw, args.severity)
    by_file = {label: filtered} if filtered else {}

    if args.json:
        print(_findings.format_json(by_file))
    else:
        print(
            f"# Stow link check\n\nPackage: **{label}** — findings: **{len(filtered)}**\n"
        )
        if not by_file:
            print("_Package is fully and cleanly linked._")
        else:
            # print_markdown parenthesises the label itself — return it bare.
            _findings.print_markdown(by_file, line_label=lambda n: "package-level")

    if _findings.triggers_fail(raw, args.fail_on):
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
