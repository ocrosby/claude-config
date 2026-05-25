#!/usr/bin/env python3
"""Scan a codebase for deprecated patterns per language and emit a Markdown report.

Replaces the inline pattern tables in skills/migrate/SKILL.md. The detected
patterns and their modern replacements are encoded as a structured dict per
language so the SKILL.md body stays small while the rule catalog can grow.

The scan is mechanical (regex per pattern); the *replacement* is the user's
job because most modernizations require context-aware edits.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import cli as _cli  # noqa: E402  # type: ignore[import-not-found]

# Per-language pattern catalog. Each entry: regex, deprecated_form, modern_form, category.
PATTERNS: dict[str, list[dict]] = {
    "go": [
        {"category": "stdlib", "regex": r"\bioutil\.ReadAll\b", "deprecated": "ioutil.ReadAll", "modern": "io.ReadAll (Go 1.16+)"},
        {"category": "stdlib", "regex": r"\bioutil\.ReadFile\b", "deprecated": "ioutil.ReadFile", "modern": "os.ReadFile (Go 1.16+)"},
        {"category": "stdlib", "regex": r"\bioutil\.WriteFile\b", "deprecated": "ioutil.WriteFile", "modern": "os.WriteFile (Go 1.16+)"},
        {"category": "stdlib", "regex": r"\bioutil\.TempDir\b", "deprecated": "ioutil.TempDir", "modern": "os.MkdirTemp (Go 1.16+)"},
        {"category": "stdlib", "regex": r"\bioutil\.TempFile\b", "deprecated": "ioutil.TempFile", "modern": "os.CreateTemp (Go 1.16+)"},
        {"category": "stdlib", "regex": r"\bioutil\.ReadDir\b", "deprecated": "ioutil.ReadDir", "modern": "os.ReadDir (Go 1.16+)"},
        {"category": "stdlib", "regex": r"\blog\.Printf\b|\blog\.Println\b", "deprecated": "log.Printf / log.Println", "modern": "log/slog structured logging (Go 1.21+)"},
        {"category": "generics", "regex": r"interface\{\}", "deprecated": "interface{}", "modern": "any (Go 1.18+) or type parameters"},
        {"category": "generics", "regex": r"\bsort\.Slice\b", "deprecated": "sort.Slice", "modern": "slices.SortFunc (Go 1.21+)"},
        {"category": "errors", "regex": r'fmt\.Errorf\([^)]*%s",\s*err', "deprecated": "fmt.Errorf with %s + err", "modern": 'fmt.Errorf("...: %w", err) for wrapping'},
        {"category": "context", "regex": r"\bcontext\.TODO\(\)", "deprecated": "context.TODO()", "modern": "Pass context.Context from the caller"},
        {"category": "testing", "regex": r"\bioutil\.TempDir\b.*\btesting\b", "deprecated": "ioutil.TempDir in tests", "modern": "t.TempDir()"},
    ],
    "py": [
        {"category": "typing", "regex": r"from\s+typing\s+import[^\n]*\b(List|Dict|Tuple|Set|FrozenSet|Type)\b", "deprecated": "typing.List/Dict/Tuple/Set (Python <3.9)", "modern": "Built-in generics: list[T], dict[K, V] (Python 3.9+)"},
        {"category": "typing", "regex": r"\btyping\.Optional\b", "deprecated": "typing.Optional[T]", "modern": "T | None (Python 3.10+)"},
        {"category": "typing", "regex": r"\btyping\.Union\b", "deprecated": "typing.Union[A, B]", "modern": "A | B (Python 3.10+)"},
        {"category": "testing", "regex": r"\bunittest\.TestCase\b", "deprecated": "unittest.TestCase", "modern": "Plain pytest functions"},
        {"category": "testing", "regex": r"self\.assertEqual\b|self\.assertTrue\b|self\.assertFalse\b|self\.assertRaises\b", "deprecated": "self.assert* methods", "modern": "Plain assert / pytest.raises"},
        {"category": "packaging", "regex": r"^\s*from\s+setuptools\s+import|^setup\(", "deprecated": "setup.py / setup.cfg", "modern": "pyproject.toml + uv"},
        {"category": "fastapi", "regex": r'@app\.on_event\(["\'](startup|shutdown)["\']\)', "deprecated": "@app.on_event(startup|shutdown)", "modern": "lifespan context manager"},
        {"category": "general", "regex": r"\bos\.path\.join\b", "deprecated": "os.path.join", "modern": "pathlib.Path / operator"},
        {"category": "general", "regex": r'"[^"\n]*"\s*%\s*\(', "deprecated": '"... %s" % (...) formatting', "modern": "f-strings"},
        {"category": "general", "regex": r"\.format\(", "deprecated": '"...".format(...)', "modern": "f-strings"},
        {"category": "general", "regex": r"\btype\(\s*\w+\s*\)\s*==\s*", "deprecated": "type(x) == SomeType", "modern": "isinstance(x, SomeType)"},
    ],
    "lua": [
        {"category": "keymaps", "regex": r"\bnvim_set_keymap\b|\bnvim_buf_set_keymap\b", "deprecated": "nvim_set_keymap / nvim_buf_set_keymap", "modern": "vim.keymap.set"},
        {"category": "options", "regex": r"\bnvim_set_option\b|\bnvim_buf_set_option\b|\bnvim_win_set_option\b", "deprecated": "nvim_set_option / nvim_buf_set_option", "modern": "vim.o / vim.bo[buf] / vim.wo[win]"},
        {"category": "autocmd", "regex": r'vim\.cmd\(\s*"\s*au\b', "deprecated": 'vim.cmd("autocmd ...")', "modern": "vim.api.nvim_create_autocmd"},
        {"category": "highlight", "regex": r'vim\.cmd\(\s*"\s*hi(?:ghlight)?\b', "deprecated": 'vim.cmd("highlight ...")', "modern": "vim.api.nvim_set_hl"},
        {"category": "command", "regex": r'vim\.cmd\(\s*"\s*command!', "deprecated": 'vim.cmd("command! ...")', "modern": "vim.api.nvim_create_user_command"},
        {"category": "lsp", "regex": r"\bvim\.lsp\.buf_get_clients\b", "deprecated": "vim.lsp.buf_get_clients", "modern": "vim.lsp.get_clients({ buffer = bufnr })"},
    ],
    "gherkin": [
        {"category": "imperative", "regex": r'^\s*(When|And)\s+I\s+(click|type|navigate to|press|select|fill in)\b', "deprecated": "Imperative UI step (click/type/navigate)", "modern": "Declarative step describing user intent"},
        {"category": "imperative", "regex": r'^\s*(When|And)\s+I\s+(open the browser|go to)\b', "deprecated": "Imperative browser step", "modern": "Given I am on <page>"},
        {"category": "coupling", "regex": r"^\s*(sleep|wait)\(", "deprecated": "sleep/wait in step definitions", "modern": "Polling assertions or explicit synchronization"},
    ],
}

EXTENSIONS = {"go": [".go"], "py": [".py"], "lua": [".lua"], "gherkin": [".feature"]}
IGNORE_DIRS = {".git", "node_modules", ".venv", "venv", "vendor", "third_party", ".tox", "__pycache__", "target", "dist", "build"}


def parse_args():
    p = _cli.make_parser(__doc__)
    p.add_argument(
        "--language",
        choices=["go", "py", "lua", "gherkin", "all"],
        default="all",
        help="Language to scan (default: all)",
    )
    p.add_argument("--root", default=".", help="Codebase root to scan (default: cwd)")
    _cli.add_json_flag(p, help_text="Emit findings as JSON instead of Markdown")
    return p.parse_args()


def iter_files(root: Path, exts: list[str]):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        if path.suffix in exts:
            yield path


def scan_language(root: Path, lang: str) -> list[dict]:
    findings: list[dict] = []
    compiled = [(re.compile(p["regex"]), p) for p in PATTERNS[lang]]
    for path in iter_files(root, EXTENSIONS[lang]):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for regex, p in compiled:
                if regex.search(line):
                    findings.append(
                        {
                            "language": lang,
                            "file": str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
                            "line": lineno,
                            "category": p["category"],
                            "deprecated": p["deprecated"],
                            "modern": p["modern"],
                            "snippet": line.strip()[:120],
                        }
                    )
    return findings


def print_markdown(by_language: dict[str, list[dict]]) -> None:
    total = sum(len(v) for v in by_language.values())
    print(f"# Deprecation scan")
    print()
    print(f"Total findings: **{total}**")
    print()
    for lang, findings in by_language.items():
        if not findings:
            continue
        print(f"## {lang.upper()} ({len(findings)} findings)")
        print()
        print("| File | Line | Category | Deprecated → Modern |")
        print("|---|---|---|---|")
        for f in findings:
            arrow = f"`{f['deprecated']}` → {f['modern']}"
            print(f"| `{f['file']}` | {f['line']} | {f['category']} | {arrow} |")
        print()
    if total == 0:
        print("_No deprecated patterns found._")


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir():
        return _cli.die(f"root not found: {root}")

    languages = list(PATTERNS) if args.language == "all" else [args.language]
    by_language: dict[str, list[dict]] = {}
    for lang in languages:
        by_language[lang] = scan_language(root, lang)

    if args.json:
        print(json.dumps({"root": str(root), "findings": by_language}, indent=2))
    else:
        print_markdown(by_language)
    return 0


if __name__ == "__main__":
    sys.exit(main())
