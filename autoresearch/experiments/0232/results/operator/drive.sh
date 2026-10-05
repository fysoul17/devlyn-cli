#!/usr/bin/env bash
# Operator loop (not apparatus): drive.sh <cells.tsv>. Runs each cell without a verdict in file order.
# rc 0 → next cell; rc 3 (preflight refused, nothing dispatched) → refresh the host Claude login when it is short,
# wait, retry; any other rc → stop for inspection.
set -uo pipefail
live=$HOME/.local/share/nx01/0232-live
here=$HOME/.local/share/nx01/0232-apparatus/autoresearch/experiments/0232
cd "$live" || exit 1  # git cannot read a launch directory under macOS privacy protection (~/Documents)
left() { security find-generic-password -s 'Claude Code-credentials' -w | python3 -c "import json,sys,time;print(int(json.load(sys.stdin)['claudeAiOauth']['expiresAt']/1000-time.time()))"; }
while read -r name task arm config _; do
  case "$name" in ''|'#'*) continue ;; esac
  while [ ! -e "$live/out/verdict-$name.json" ]; do
    python3 -B "$here/run_cell.py" "$live/runtime.json" "$name" "$task" "$arm" "$config"
    rc=$?
    echo "$(date -u +%FT%TZ) $name rc=$rc"
    [ "$rc" -eq 0 ] && break
    [ "$rc" -eq 3 ] || { echo "$(date -u +%FT%TZ) drive stopped at $name (rc=$rc)"; exit "$rc"; }
    cat "$live/out/not-dispatched-$name.json"; echo
    if [ "$(left)" -lt 6300 ]; then (cd /tmp && claude -p --model claude-sonnet-5-5 'Reply OK' >/dev/null 2>&1); fi
    sleep 300
  done
done < "$1"
echo "$(date -u +%FT%TZ) drive finished $1"
