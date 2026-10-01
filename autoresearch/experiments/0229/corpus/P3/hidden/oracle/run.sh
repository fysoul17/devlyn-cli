#!/bin/sh
set -eu

if [ "$#" -ne 1 ] || [ ! -d "$1/src/dateutil" ]; then
    echo 'usage: run.sh <tree>' >&2
    exit 2
fi

ORACLE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHONPATH="$1/src" PYTHONDONTWRITEBYTECODE=1 \
    exec /Users/Shared/devlyn-vr-0228-dev/screen-0229/toolchains/dateutil/venv/bin/python \
    "$ORACLE_DIR/run.py"
