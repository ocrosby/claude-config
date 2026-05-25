#!/usr/bin/env bash
# detect_language.sh — emit a single token identifying the primary language
# of the current working directory.
#
# Usage:
#   detect_language.sh                # auto-detect from cwd
#   detect_language.sh <override>     # echo the override verbatim if valid
#
# Output (one of): go py nvim gherkin rest unknown
#
# Detection priority (first match wins):
#   1. explicit $1 override (must be one of the valid tokens)
#   2. go.mod                             -> go
#   3. pyproject.toml or setup.py         -> py
#   4. init.lua or lua/ directory         -> nvim
#   5. *.feature anywhere under cwd       -> gherkin
#   6. openapi.yaml or openapi.json       -> rest
#   7. unknown

set -euo pipefail

VALID="go py nvim gherkin rest unknown"

if [ "${1-}" != "" ]; then
  for t in $VALID; do
    if [ "$1" = "$t" ]; then
      echo "$1"
      exit 0
    fi
  done
  echo "detect_language.sh: invalid override '$1' (must be one of: $VALID)" >&2
  exit 2
fi

if [ -f go.mod ]; then
  echo go
elif [ -f pyproject.toml ] || [ -f setup.py ]; then
  echo py
elif [ -f init.lua ] || [ -d lua ]; then
  echo nvim
elif [ -f openapi.yaml ] || [ -f openapi.yml ] || [ -f openapi.json ]; then
  echo rest
elif find . -maxdepth 4 -name '*.feature' -print -quit 2>/dev/null | grep -q .; then
  echo gherkin
else
  echo unknown
fi
