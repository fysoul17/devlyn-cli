#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <tree>" >&2
    exit 2
fi

oracle_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 -B -I "$oracle_dir/run.py" "$1"
