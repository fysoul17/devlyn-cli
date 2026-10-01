#!/usr/bin/env bash

set -u

if [ "$#" -ne 1 ]; then
  printf 'usage: %s <tree>\n' "$0" >&2
  exit 2
fi

oracle_dir=$(cd "$(dirname "$0")" && pwd -P) || exit 2
tree=$1
if ! cd "$tree"; then
  exit 2
fi

export PATH=/Users/Shared/devlyn-vr-0228-dev/screen-0229/toolchains/markdown-it/node-bin:$PATH
scratch=$(mktemp -d) || exit 2
trap 'rm -rf "$scratch"' EXIT

result='{"rows": {'
separator=''
for row in J4-O1 J4-O2 J4-O3 J4-O4 J4-O5; do
  if ORACLE_ROW="$row" node --input-type=module < "$oracle_dir/rows.mjs" > "$scratch/stdout" 2> "$scratch/stderr"; then
    passed=true
  else
    status=$?
    if [ "$status" -ne 42 ]; then
      cat "$scratch/stderr" >&2
      exit 2
    fi
    passed=false
  fi
  if [ -s "$scratch/stdout" ]; then
    printf 'oracle row %s produced unexpected output\n' "$row" >&2
    exit 2
  fi
  result="$result$separator\"$row\": $passed"
  separator=', '
done

printf '%s}}\n' "$result"
