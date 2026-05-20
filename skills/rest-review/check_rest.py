#!/usr/bin/env python3
"""Deterministic REST convention checks against HTTP handler files.

Acts as a fast pre-check before /rest-review delegates to the rest-reviewer
agent. Catches mechanical violations (verb-in-URI, wrong status code for the
HTTP method, missing Location header on POST creating) so the agent can focus
on judgment-required concerns (auth flow, pagination shape, HATEOAS).

Mirrors skills/doc-review/check_docs.py: same severity tiers, same finding
shape, same flags.
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

# Verbs commonly mis-used in URI paths (each becomes part of the verb-in-URI regex).
URI_VERBS = (
    "get", "create", "update", "delete", "remove", "add", "fetch", "list",
    "find", "search", "edit", "modify", "save", "load", "submit", "send",
    "cancel", "approve", "reject", "process", "execute", "run",
)

# Route registration patterns per language. Each match captures HTTP method + path literal.
ROUTE_PATTERNS: dict[str, list[re.Pattern]] = {
    ".go": [
        re.compile(r'\b(?:r|router|mux|app)\.(?P<method>GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s*\(\s*"(?P<path>[^"]+)"'),
        re.compile(r'\bhttp\.HandleFunc\s*\(\s*"(?P<path>[^"]+)"'),
    ],
    ".py": [
        re.compile(r'@(?:app|router)\.(?P<method>get|post|put|patch|delete|head|options)\s*\(\s*["\'](?P<path>[^"\']+)["\']'),
        re.compile(r'@(?:app|router)\.route\s*\(\s*["\'](?P<path>[^"\']+)["\']'),
        re.compile(r'\b(?:app|router)\.(?P<method>get|post|put|patch|delete)\s*\(\s*["\'](?P<path>[^"\']+)["\']'),
    ],
    ".ts": [
        re.compile(r'\b(?:app|router)\.(?P<method>get|post|put|patch|delete|head|options)\s*\(\s*[`"\'](?P<path>[^`"\']+)[`"\']'),
    ],
    ".js": [
        re.compile(r'\b(?:app|router)\.(?P<method>get|post|put|patch|delete|head|options)\s*\(\s*[`"\'](?P<path>[^`"\']+)[`"\']'),
    ],
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    p.add_argument("paths", nargs="+", help="Handler files, directories, or globs")
    p.add_argument("--json", action="store_true", help="Emit findings as JSON")
    p.add_argument(
        "--severity",
        choices=["must", "should", "consider", "all"],
        default="all",
    )
    return p.parse_args()


def expand_paths(patterns: list[str]) -> list[Path]:
    out: list[Path] = []
    extensions = set(ROUTE_PATTERNS)
    for pattern in patterns:
        p = Path(pattern)
        if p.is_file():
            out.append(p)
            continue
        if p.is_dir():
            for ext in extensions:
                out.extend(q for q in p.rglob(f"*{ext}") if q.is_file())
            continue
        for match in Path(".").glob(pattern):
            if match.is_file():
                out.append(match)
    return sorted(set(out))


def detect_routes(path: Path, lines: list[str]) -> list[tuple[int, str, str]]:
    """Return list of (line_no, method_upper, route_path) per detected route."""
    ext = path.suffix
    patterns = ROUTE_PATTERNS.get(ext, [])
    routes: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(lines, 1):
        for pat in patterns:
            m = pat.search(line)
            if not m:
                continue
            method = (m.groupdict().get("method") or "").upper()
            route_path = m.group("path")
            if not method:
                # http.HandleFunc has no method — emit empty so URI checks still run
                method = ""
            routes.append((lineno, method, route_path))
    return routes


def check_uri(line_no: int, route_path: str) -> list[tuple[int, str, str, str]]:
    """URI-shape checks. Return findings as (line, severity, rule_id, message)."""
    findings: list[tuple[int, str, str, str]] = []

    # Strip path-parameter braces so {userId} doesn't trip the casing checks
    bare = re.sub(r"\{[^}]+\}|:\w+", "", route_path)

    # Verb in URI — must fix
    segments = [s for s in bare.split("/") if s and not s.startswith(":") and not s.startswith("{")]
    for seg in segments:
        # Lowercase the segment for matching, but strip suffixes that aren't verbs.
        # A segment "getUsers" matches "get"; "/users/get" matches "get"; "/v2/users" doesn't.
        seg_lower = seg.lower()
        for verb in URI_VERBS:
            # Match "getUsers", "createOrder", or a bare verb segment.
            if seg_lower == verb or seg_lower.startswith(verb) and len(seg_lower) > len(verb) and not seg_lower[len(verb)].isdigit():
                # Avoid false positives like 'addressBook' (starts with 'add' but 'r' continues)
                # We only flag if the character after the verb is uppercase in the original (camelCase)
                # OR the segment IS the verb exactly.
                rest_orig = seg[len(verb):] if len(seg) >= len(verb) else ""
                if seg_lower == verb or (rest_orig and rest_orig[0].isupper()):
                    findings.append((line_no, MUST, "uri-has-verb", f"URI path '{route_path}' contains the verb '{verb}' — use a noun and let the HTTP method express the verb"))
                    break

    # Uppercase letters in URI segments
    for seg in segments:
        if any(c.isupper() for c in seg):
            findings.append((line_no, SHOULD, "uri-uppercase", f"URI path '{route_path}' contains uppercase letters — use lowercase"))
            break

    # snake_case in URI segments
    for seg in segments:
        if "_" in seg:
            findings.append((line_no, SHOULD, "uri-snake-case", f"URI path '{route_path}' uses snake_case — use kebab-case (hyphens)"))
            break

    # Trailing slash (excluding root)
    if route_path != "/" and route_path.endswith("/"):
        findings.append((line_no, CONSIDER, "uri-trailing-slash", f"URI path '{route_path}' has a trailing slash — be consistent across the API"))

    return findings


def find_handler_block(lines: list[str], start: int) -> str:
    """Return the next ~30 lines after a route registration — enough to inspect the handler body."""
    return "\n".join(lines[start:start + 30])


def check_handler(line_no: int, method: str, route_path: str, lines: list[str]) -> list[tuple[int, str, str, str]]:
    """Handler-body checks. Look at the next ~30 lines after the route registration."""
    findings: list[tuple[int, str, str, str]] = []
    body = find_handler_block(lines, line_no - 1)
    lower_body = body.lower()

    if method == "POST":
        # POST creating: should return 201 + Location header
        # Heuristic: if the body returns 200 explicitly, flag. If it returns 201 without setting Location, flag.
        if re.search(r"\b201\b", body):
            if "location" not in lower_body and "set" not in lower_body:
                findings.append((line_no, SHOULD, "post-no-location", f"POST {route_path} returns 201 but does not set a Location header"))
        elif re.search(r"\b200\b", body) and "list" not in route_path.lower():
            findings.append((line_no, SHOULD, "post-no-201", f"POST {route_path} returns 200 — use 201 + Location header when creating a resource"))

    if method == "GET":
        # GET should not read the request body
        if re.search(r"\b(?:request|req|r)\.(?:Body|body|json|get_json)\b", body) and "decode" in lower_body:
            findings.append((line_no, MUST, "get-with-body", f"GET {route_path} appears to read from the request body — GETs must be safe and idempotent"))
        # GET cache headers
        if not re.search(r"\b(?:Cache-Control|ETag|cache_control|etag)\b", body, re.IGNORECASE):
            findings.append((line_no, CONSIDER, "get-no-cache-headers", f"GET {route_path} omits Cache-Control / ETag headers"))

    if method == "DELETE":
        # DELETE typically returns 204; if it returns 200, the response body should be absent
        if re.search(r"\b200\b", body) and re.search(r"\breturn\b.*(?:json|jsonify|c\.JSON|response)", body, re.IGNORECASE):
            findings.append((line_no, SHOULD, "delete-with-body", f"DELETE {route_path} returns a response body with 200 — use 204 No Content"))

    # 405 without Allow header
    if re.search(r"\b405\b", body):
        if "allow" not in lower_body:
            findings.append((line_no, SHOULD, "405-no-allow", f"{method or 'Handler'} for {route_path} returns 405 but does not set an Allow header"))

    return findings


def check_file(path: Path) -> list[tuple[int, str, str, str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines = text.splitlines()
    findings: list[tuple[int, str, str, str]] = []
    routes = detect_routes(path, lines)
    for line_no, method, route_path in routes:
        findings.extend(check_uri(line_no, route_path))
        if method:
            findings.extend(check_handler(line_no, method, route_path, lines))
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
        print("error: no HTTP handler files matched", file=sys.stderr)
        return 1

    by_file: dict[str, list[tuple[int, str, str, str]]] = {}
    for path in files:
        findings = filter_severity(check_file(path), args.severity)
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
    print(f"# REST convention pre-check\n\nFiles scanned: **{len(files)}** — findings: **{total}**\n")
    if not by_file:
        print("_No mechanical REST violations detected. The /rest-review skill will still delegate to the rest-reviewer agent for cross-cutting concerns._")
        return 0

    for path, findings in sorted(by_file.items()):
        print(f"## `{path}`\n")
        for sev in (MUST, SHOULD, CONSIDER):
            tier = [f for f in findings if f[1] == sev]
            if not tier:
                continue
            print(f"### {sev}")
            for line, _, rule, msg in tier:
                print(f"- `{rule}` (line {line}) — {msg}")
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
