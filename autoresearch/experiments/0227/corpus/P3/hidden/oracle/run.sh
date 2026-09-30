#!/bin/sh
set -eu

if [ "$#" -ne 1 ] || [ ! -d "$1/src" ]; then
    echo "usage: oracle/run.sh <tree>" >&2
    exit 2
fi

target_tree=$(CDPATH= cd -- "$1" && pwd)
oracle_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHONPATH="$target_tree/src" PYTHONDONTWRITEBYTECODE=1 \
    /Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/python "$oracle_dir/run.py"
