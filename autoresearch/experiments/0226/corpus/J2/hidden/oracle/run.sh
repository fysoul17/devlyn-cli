#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! -d "$1" ]]; then
    echo 'usage: oracle/run.sh <tree>' >&2
    exit 2
fi

tree_dir=$(cd "$1" && pwd)
script_dir=$(cd "$(dirname "$0")" && pwd)
node "$script_dir/rows.js" "$tree_dir"
