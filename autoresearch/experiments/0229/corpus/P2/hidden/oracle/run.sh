#!/bin/sh
set -eu

if [ "$#" -ne 1 ] || [ ! -d "$1/src/dateutil" ]; then
    exit 2
fi

candidate=$(cd "$1" && pwd -P)
oracle_dir=$(cd "$(dirname "$0")" && pwd -P)
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT HUP INT TERM
cd "$scratch"

PYTHONPATH="$candidate/src" PYTHONDONTWRITEBYTECODE=1 \
    /Users/Shared/devlyn-vr-0228-dev/screen-0229/toolchains/dateutil/venv/bin/python \
    "$oracle_dir/check.py"
