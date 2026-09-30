#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! -d "$1" ]]; then
  printf 'usage: %s <tree>\n' "$0" >&2
  exit 2
fi

ORACLE_TREE=$(cd "$1" && pwd)
if [[ ! -f "$ORACLE_TREE/dist/esm/node/index.js" ]]; then
  oracle_tmp=$(mktemp -d /private/tmp/j1-oracle.XXXXXX)
  trap 'rm -rf "$oracle_tmp"' EXIT
  cp -R "$ORACLE_TREE" "$oracle_tmp/tree"
  if ! (cd "$oracle_tmp/tree" && \
    PATH=/Users/Shared/devlyn-vr-0227/toolchains/node-lru-cache/node-bin:$PATH \
      npm run prepare > "$oracle_tmp/build.log" 2>&1); then
    cat "$oracle_tmp/build.log" >&2
    exit 1
  fi
  ORACLE_TREE="$oracle_tmp/tree"
fi
export ORACLE_TREE
PATH=/Users/Shared/devlyn-vr-0227/toolchains/node-lru-cache/node-bin:$PATH \
  node "$(dirname "$0")/rows.mjs"
