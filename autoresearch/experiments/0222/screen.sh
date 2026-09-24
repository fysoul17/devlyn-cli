#!/usr/bin/env bash
# Serial screen: screen.sh <runtime.json> <cells.tsv>. Each line: name task arm config.
# A cell with a verdict file is done; any non-zero run_cell exit stops the screen for inspection.
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
output=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["output"])' "$1")
while read -r name task arm config; do
  case "$name" in ''|'#'*) continue ;; esac
  [ -e "$output/verdict-$name.json" ] && continue
  python3 -B "$here/run_cell.py" "$1" "$name" "$task" "$arm" "$config"
  rc=$?
  [ "$rc" -eq 0 ] || { echo "screen stopped at $name (rc=$rc); see $output/verdict-$name.json" >&2; exit "$rc"; }
done < "$2"
