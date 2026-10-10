#!/usr/bin/env bash
# slugify.sh — normalize an arbitrary string to lowercase snake_case for use as a
# filename or output-directory name. Collapses runs of underscores and trims
# leading/trailing underscores.
#
# Usage: slugify.sh "Fairy Coloring Book"
# Output: fairy_coloring_book

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "usage: slugify.sh <string>" >&2
    exit 1
fi

echo "$1" \
    | tr '[:upper:] -.' '[:lower:]___' \
    | sed 's/_\{2,\}/_/g;s/^_//;s/_$//'
