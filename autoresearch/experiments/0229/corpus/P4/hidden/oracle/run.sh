#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    echo 'usage: oracle/run.sh <tree>' >&2
    exit 2
fi

TREE_DIR=$(cd "$1" && pwd -P)
ORACLE_DIR=$(cd "$(dirname "$0")" && pwd -P)
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT HUP INT TERM
cd "$TEMP_DIR"

PYTHONPATH="$TREE_DIR/src" PYTHONDONTWRITEBYTECODE=1 \
    /Users/Shared/devlyn-vr-0228-dev/screen-0229/toolchains/dateutil/venv/bin/python \
    "$ORACLE_DIR/check.py"
