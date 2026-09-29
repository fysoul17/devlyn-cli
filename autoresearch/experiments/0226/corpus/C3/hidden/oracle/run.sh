#!/bin/sh
set -eu

if [ "$#" -ne 1 ] || [ ! -d "$1/src/cachetools" ]; then
    echo "usage: $0 <tree>" >&2
    exit 2
fi

tree=$(cd "$1" && pwd)
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT HUP INT TERM

oracle_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TMPDIR="$scratch" PYTHONPATH="$tree/src" PYTHONNOUSERSITE=1 \
    PYTHONDONTWRITEBYTECODE=1 python "$oracle_dir/oracle.py"
