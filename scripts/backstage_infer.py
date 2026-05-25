#!/usr/bin/env python3
"""Infer Backstage catalog-info.yaml fields from the current repo.

Used by skills/backstage-catalog-init. Replaces ~100 lines of inlined shell
heuristics in the SKILL.md. Emits JSON so the skill orchestrator can present
the candidates, prompt the user for any missing values, and write the file.

Output schema (all fields always present; values may be empty strings or
empty lists when inference fails):

  {
    "slug": "<org/repo>",
    "repo_name": "<bare-name>",
    "branch": "<default-branch>",
    "title": "<human-readable-title>",
    "description": "<inferred-description>",
    "type": "<service|tool|test-suite|infrastructure>",
    "lifecycle": "<production|experimental>",
    "owner_candidates": [{"value": "...", "source": "..."}],
    "system_candidates": [{"value": "...", "source": "..."}],
    "errors": ["..."]
  }

Sources are reported so the skill can explain to the user why each value
was proposed. Errors are non-fatal hints (e.g. "no GitHub remote") that
the skill must surface before writing the file.
"""
from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import cli as _cli  # noqa: E402  # type: ignore[import-not-found]
from _lib import git as _git  # noqa: E402  # type: ignore[import-not-found]


def _git_out(*args: str) -> str:
    """Shorthand wrapper preserving the original `.strip()` behavior of this script."""
    return _git.run(list(args)).strip()


def github_slug() -> tuple[str, str]:
    url = _git_out("remote", "get-url", "origin")
    if not url:
        return "", "no origin remote configured"
    m = re.search(r"github\.com[:/]([^/]+/[^/\s]+?)(\.git)?$", url)
    if not m:
        return "", f"origin remote is not a GitHub URL: {url}"
    return m.group(1), ""


def repo_root() -> Path:
    out = _git_out("rev-parse", "--show-toplevel")
    return Path(out) if out else Path.cwd()


def default_branch() -> str:
    ref = _git_out("symbolic-ref", "refs/remotes/origin/HEAD")
    if ref:
        return ref.rsplit("/", 1)[-1]
    return "main"


def infer_description(root: Path, repo_name: str) -> str:
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            data = tomllib.loads(pyproject.read_text())
            desc = data.get("project", {}).get("description", "").strip()
            if desc:
                return desc
        except Exception:
            pass
    readme = root / "README.md"
    if readme.exists():
        lines = readme.read_text().splitlines()
        for i, line in enumerate(lines[:20]):
            if line.startswith("# "):
                for follow in lines[i + 1 : i + 11]:
                    if follow.strip() and not follow.startswith("#") and not follow.startswith("!["):
                        return follow.strip()
                break
    bare = re.sub(r"^sun-ms-|^sun-", "", repo_name)
    bare = bare.replace("-", " ").strip()
    if bare:
        return bare[0].upper() + bare[1:] + "."
    return ""


def infer_title(repo_name: str) -> str:
    parts = re.split(r"[-_]", repo_name)
    return " ".join(p[:1].upper() + p[1:] for p in parts if p)


def infer_type(root: Path, repo_name: str) -> str:
    if (root / "features").exists() and any(p.suffix == ".feature" for p in (root / "features").rglob("*.feature")):
        return "test-suite"
    if (root / "tests" / "bdd").exists():
        return "test-suite"
    pytest_ini = root / "pytest.ini"
    if pytest_ini.exists() and "bdd" in pytest_ini.read_text().lower():
        return "test-suite"
    if (root / "charts").exists():
        return "infrastructure"
    if (root / "cmd").exists() and any((root / "cmd").glob("*/main.go")):
        return "service"
    src = root / "src"
    if src.exists():
        for f in src.rglob("main.py"):
            text = f.read_text(errors="ignore")
            if "FastAPI" in text or "FastMCP" in text or "fastapi" in text or "fastmcp" in text:
                return "service"
    if "-cli" in repo_name or "-tool" in repo_name or repo_name.endswith("-tools"):
        return "tool"
    if (root / "pyproject.toml").exists():
        try:
            data = tomllib.loads((root / "pyproject.toml").read_text())
            scripts = data.get("project", {}).get("scripts", {})
            if scripts:
                return "tool"
        except Exception:
            pass
    return "service"


def infer_lifecycle(root: Path, repo_name: str, branch: str) -> str:
    experimental_markers = ("-experimental", "-poc", "-spike", "-demo", "-sandbox")
    if any(m in repo_name for m in experimental_markers):
        return "experimental"
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            data = tomllib.loads(pyproject.read_text())
            classifiers = data.get("project", {}).get("classifiers", [])
            for c in classifiers:
                if "Development Status :: 5" in c:
                    return "production"
        except Exception:
            pass
    if branch in ("main", "master"):
        return "production"
    return "experimental"


def find_codeowners(root: Path) -> list[dict]:
    candidates: list[dict] = []
    for path in (root / ".github" / "CODEOWNERS", root / "CODEOWNERS"):
        if path.exists():
            for line in path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if parts and parts[0] == "*":
                    for owner in parts[1:]:
                        if owner.startswith("@"):
                            slug = owner.lstrip("@").split("/", 1)[-1]
                            candidates.append({"value": slug, "source": f"CODEOWNERS:{path.name}"})
                    break
    return candidates


def scan_sibling_catalogs(root: Path, field: str) -> list[dict]:
    parent = root.parent
    if not parent.exists():
        return []
    out: list[dict] = []
    seen: set[str] = set()
    for sibling in parent.iterdir():
        if not sibling.is_dir() or sibling == root:
            continue
        catalog = sibling / "catalog-info.yaml"
        if not catalog.exists():
            continue
        for line in catalog.read_text().splitlines():
            line = line.strip()
            if line.startswith(f"{field}:"):
                value = line.split(":", 1)[1].strip()
                if value and value not in seen:
                    out.append({"value": value, "source": f"sibling:{sibling.name}"})
                    seen.add(value)
                break
    return out


def main() -> int:
    parser = _cli.make_parser(__doc__)
    parser.add_argument("--root", default=None, help="Override repo root (default: derived from git)")
    args = parser.parse_args()

    root = Path(args.root) if args.root else repo_root()
    errors: list[str] = []

    slug, slug_err = github_slug()
    if slug_err:
        errors.append(slug_err)

    if slug:
        repo_name = slug.split("/", 1)[-1]
    else:
        repo_name = root.name

    branch = default_branch()
    title = infer_title(repo_name)
    description = infer_description(root, repo_name)
    component_type = infer_type(root, repo_name)
    lifecycle = infer_lifecycle(root, repo_name, branch)
    owner_candidates = find_codeowners(root) + scan_sibling_catalogs(root, "owner")
    system_candidates = scan_sibling_catalogs(root, "system")

    if not system_candidates and repo_name.startswith(("sun-ms-", "sun-")):
        system_candidates.append({"value": "weather-infrastructure", "source": "name-prefix"})

    result = {
        "slug": slug,
        "repo_name": repo_name,
        "branch": branch,
        "title": title,
        "description": description,
        "type": component_type,
        "lifecycle": lifecycle,
        "owner_candidates": owner_candidates,
        "system_candidates": system_candidates,
        "errors": errors,
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
