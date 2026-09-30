#!/bin/sh
set -eu

if [ "$#" -ne 1 ] || [ ! -d "$1/src" ]; then
    exit 2
fi

tree=$(cd "$1" && pwd)
oracle_dir=$(cd "$(dirname "$0")" && pwd)
scratch=$(mktemp -d "${TMPDIR:-/private/tmp}/attrs-oracle.XXXXXX")
trap 'rm -rf "$scratch"' EXIT HUP INT TERM
cd "$scratch"

export PYTHONPATH="$tree/src"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONNOUSERSITE=1
/Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/python "$oracle_dir/check.py"
