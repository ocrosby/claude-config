#!/usr/bin/env bash
# open_and_verify.sh — open a PDF with the OS-appropriate opener and verify the
# file exists and is non-empty. Prints the page count on success.
#
# Usage: open_and_verify.sh <pdf-path>
# Exits 0 on success, non-zero on any check failure.

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "usage: open_and_verify.sh <pdf-path>" >&2
    exit 1
fi

command -v magick >/dev/null 2>&1 || {
    echo "FAIL: magick not found (brew install imagemagick / sudo apt install imagemagick)" >&2
    exit 3
}

pdf="$1"

if [ ! -s "$pdf" ]; then
    echo "FAIL: $pdf does not exist or is empty" >&2
    exit 2
fi

if [[ "$OSTYPE" == "darwin"* ]]; then
    open "$pdf"
else
    xdg-open "$pdf" >/dev/null 2>&1 &
fi

pages=$(magick identify -format "%n\n" "$pdf" 2>/dev/null | tail -1)
echo "OK: $pdf ($pages pages)"
