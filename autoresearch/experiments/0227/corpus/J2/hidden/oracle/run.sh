#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo 'usage: oracle/run.sh <tree>' >&2
  exit 2
fi

tree=$(cd "$1" && pwd -P)
oracle_dir=$(cd "$(dirname "$0")" && pwd -P)
export PATH=/Users/Shared/devlyn-vr-0227/toolchains/node-lru-cache/node-bin:$PATH

if [ ! -f "$tree/dist/esm/node/index.js" ]; then
  scratch=$(mktemp -d)
  trap 'rm -rf "$scratch"' EXIT HUP INT TERM
  mkdir "$scratch/tree"
  cp -R "$tree/." "$scratch/tree/"
  if ! (cd "$scratch/tree" && npm_config_offline=true npm run prepare > "$scratch/build.log" 2>&1); then
    cat "$scratch/build.log" >&2
    exit 1
  fi
  tree=$scratch/tree
fi

node "$oracle_dir/rows.mjs" "$tree"
