#!/bin/sh
set -eu

if [ "$#" -ne 1 ] || [ ! -f "$1/src/cachetools/__init__.py" ]; then
    echo "usage: oracle/run.sh <tree>" >&2
    exit 2
fi

tree=$(cd "$1" && pwd)
oracle_dir=$(cd "$(dirname "$0")" && pwd)
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT HUP INT TERM
cd "$scratch"
PYTHONPATH="$tree/src" PYTHONDONTWRITEBYTECODE=1 python -B "$oracle_dir/check.py"
