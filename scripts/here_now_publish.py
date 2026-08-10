#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Publish a self-contained HTML file to here.now and print its URL.

Replicates the `/docs research` publish flow: compute size + sha256, POST
a manifest to /api/v1/publish, PUT the file to the returned upload URL,
POST finalize, then verify the site. Uses HERE_NOW_API_KEY (env) for a
permanent publish; without it the link is ephemeral (~24h).

Prints the published site URL to stdout on success. Exit 0 on success,
1 on any failure. `--dry-run` prints the manifest and planned calls
without touching the network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://here.now/api/v1/publish"


def request(
    method: str, url: str, data: bytes | None = None, headers: dict | None = None
) -> tuple[int, bytes]:
    """Issue an HTTP request; return (status, body). Raises on network error."""
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(req) as resp:  # noqa: S310 — fixed https here.now host
        return resp.status, resp.read()


def first_key(obj: object, *keys: str) -> object | None:
    """Return the value of the first present key in obj, else None.

    The publish response's site-URL field name is not pinned by the API
    docs, so we accept the common spellings rather than guess one.
    """
    if isinstance(obj, dict):
        for k in keys:
            if k in obj:
                return obj[k]
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Publish an HTML file to here.now.")
    ap.add_argument("file", help="Path to the self-contained HTML file.")
    ap.add_argument("--title", required=True, help="Viewer title (the topic).")
    ap.add_argument("--description", default="Researched by Claude")
    ap.add_argument(
        "--keep",
        action="store_true",
        help="Require a permanent publish (needs HERE_NOW_API_KEY).",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print size, hash, manifest, and planned calls; do not publish.",
    )
    args = ap.parse_args()

    try:
        with open(args.file, "rb") as f:
            content = f.read()
    except OSError as e:
        print(f"error: cannot read {args.file}: {e}", file=sys.stderr)
        return 1

    size = len(content)
    file_hash = hashlib.sha256(content).hexdigest()
    api_key = os.environ.get("HERE_NOW_API_KEY", "")

    if args.keep and not api_key:
        print("error: --keep requires HERE_NOW_API_KEY to be set", file=sys.stderr)
        return 1

    manifest = {
        "files": [
            {
                "path": "index.html",
                "size": size,
                "contentType": "text/html; charset=utf-8",
                "hash": file_hash,
            }
        ],
        "viewer": {"title": args.title, "description": args.description},
    }

    if args.dry_run:
        print(
            json.dumps(
                {
                    "size": size,
                    "hash": file_hash,
                    "authenticated": bool(api_key),
                    "manifest": manifest,
                    "calls": [
                        f"POST {API}",
                        "PUT <upload_url>",
                        "POST <finalize_url>",
                        "HEAD <site_url>",
                    ],
                },
                indent=2,
            )
        )
        return 0

    headers = {
        "Content-Type": "application/json",
        "X-HereNow-Client": "claude-code/study",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # 1. Create the publication.
    try:
        status, body = request(
            "POST", API, data=json.dumps(manifest).encode(), headers=headers
        )
    except urllib.error.URLError as e:
        print(f"error: publish POST failed: {e}", file=sys.stderr)
        return 1
    try:
        resp = json.loads(body)
    except json.JSONDecodeError:
        print(f"error: publish returned non-JSON: {body[:200]!r}", file=sys.stderr)
        return 1
    if status // 100 != 2 or (isinstance(resp, dict) and resp.get("error")):
        print(f"error: publish failed ({status}): {resp}", file=sys.stderr)
        return 1

    site_url = first_key(resp, "url", "siteUrl", "site_url")
    upload = resp.get("upload", {}) if isinstance(resp, dict) else {}
    uploads = upload.get("uploads") or []
    upload_url = uploads[0].get("url") if uploads else None
    finalize_url = upload.get("finalizeUrl")
    version_id = upload.get("versionId")
    if not (site_url and upload_url and finalize_url and version_id):
        print(
            f"error: publish response missing required fields: {resp}", file=sys.stderr
        )
        return 1

    # 2. Upload the file bytes.
    try:
        up_status, _ = request(
            "PUT",
            upload_url,
            data=content,
            headers={"Content-Type": "text/html; charset=utf-8"},
        )
    except urllib.error.URLError as e:
        print(f"error: upload PUT failed: {e}", file=sys.stderr)
        return 1
    if up_status // 100 != 2:
        print(f"error: upload failed ({up_status})", file=sys.stderr)
        return 1

    # 3. Finalize.
    try:
        fin_status, _ = request(
            "POST",
            finalize_url,
            data=json.dumps({"versionId": version_id}).encode(),
            headers={"Content-Type": "application/json"},
        )
    except urllib.error.URLError as e:
        print(f"error: finalize POST failed: {e}", file=sys.stderr)
        return 1
    if fin_status // 100 != 2:
        print(f"error: finalize failed ({fin_status})", file=sys.stderr)
        return 1

    # 4. Verify (best-effort) and report the URL.
    try:
        v_status, _ = request("HEAD", str(site_url))
        verified = v_status == 200
    except urllib.error.URLError:
        verified = False

    print(site_url)
    if not verified:
        print(
            "note: site not yet reachable (may still be propagating)", file=sys.stderr
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
