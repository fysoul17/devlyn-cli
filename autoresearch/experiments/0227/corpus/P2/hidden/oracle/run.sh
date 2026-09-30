#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    exit 2
fi

tree=$(cd "$1" && pwd)
oracle_dir=$(cd "$(dirname "$0")" && pwd)
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT HUP INT TERM
cd "$scratch"
PYTHONPATH="$tree/src" PYTHONDONTWRITEBYTECODE=1 \
    /Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/python \
    "$oracle_dir/check.py"
