#!/bin/sh
set -eu

if [ "$#" -ne 1 ] || [ ! -d "$1/src/attr" ]; then
    echo 'usage: oracle/run.sh <tree>' >&2
    exit 2
fi

tree=$(cd "$1" && pwd)
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT HUP INT TERM

PYTHONPATH="$tree/src" PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX="$scratch/pycache" HYPOTHESIS_STORAGE_DIRECTORY="$scratch/hypothesis" TMPDIR="$scratch" /Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/python -B "$(dirname "$0")/rows.py"
