#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ] || [ ! -d "$1" ]; then
  printf 'usage: %s <tree>\n' "$0" >&2
  exit 2
fi

oracle_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
export PATH="/Users/Shared/devlyn-vr-0228-dev/screen-0229/toolchains/markdown-it/node-bin:$PATH"
exec node "$oracle_dir/runner.mjs" "$1"
