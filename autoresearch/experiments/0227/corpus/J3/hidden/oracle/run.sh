#!/bin/sh
set -eu
if [ "$#" -ne 1 ]; then
  echo 'usage: oracle/run.sh <tree>' >&2
  exit 2
fi
tree=$(cd "$1" && pwd)
oracle_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT HUP INT TERM
PATH=/Users/Shared/devlyn-vr-0227/toolchains/node-lru-cache/node-bin:$PATH
export PATH
"$tree/node_modules/.bin/esbuild" "$tree/src/index.ts" --bundle --platform=node --format=esm --outfile="$scratch/cache.mjs" >/dev/null 2>&1
node "$oracle_dir/rows.mjs" "$scratch/cache.mjs"
