#!/bin/sh
set -u

if [ "$#" -ne 1 ] || [ ! -f "$1/src/index.ts" ]; then
  printf '%s\n' 'usage: oracle/run.sh <tree>' >&2
  exit 2
fi

oracle_dir=$(cd "$(dirname "$0")" && pwd) || exit 2
tree_dir=$(cd "$1" && pwd) || exit 2
PATH=/Users/Shared/devlyn-vr-0228-dev/screen-0229/toolchains/markdown-it/node-bin:$PATH
export PATH

if ! command -v node >/dev/null 2>&1; then
  printf '%s\n' 'node is unavailable' >&2
  exit 2
fi

scratch=$(mktemp -d /private/tmp/j1-oracle.XXXXXX) || exit 2
trap 'rm -rf "$scratch"' EXIT HUP INT TERM
cd "$tree_dir" || exit 2

printf '{"rows":{'
separator=''
for id in J1-O1 J1-O2 J1-O3 J1-O4 J1-O5; do
  cat "$oracle_dir/prelude.mjs" "$oracle_dir/cases/$id.mjs" > "$scratch/row.mjs" || exit 2
  if node --input-type=module < "$scratch/row.mjs" > "$scratch/stdout" 2> "$scratch/stderr"; then
    result=true
  else
    result=false
  fi
  printf '%s"%s":%s' "$separator" "$id" "$result"
  separator=,
done
printf '}}\n'
