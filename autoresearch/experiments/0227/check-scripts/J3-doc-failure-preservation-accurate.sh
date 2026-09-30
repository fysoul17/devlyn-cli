#!/bin/sh
# 0227 check (J3): the memo() API comment describes failure preservation and that description is true (a thrown calculation leaves recency, age and membership unchanged). Exit 0 = clause holds.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$1"
awk '/^  memo\($/ { print block; exit } /^  \/\*\*/ { block = "" } { block = block "\n" $0 }' src/index.ts |
  grep -q 'If memoMethod throws.*does not'
exec "$here/J3-failure-preserves-state.sh" "$(pwd)"
