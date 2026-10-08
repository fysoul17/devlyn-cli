#!/usr/bin/env bash
# Operator loop (not apparatus): drive.sh <tsv[:prefix]>... Runs each cell without a verdict in file order; with
# ":prefix", only cells whose name starts with prefix (e.g. cells.tsv:r measured, smoke.tsv:s smoke).
# rc 0 → next cell; rc 3 (preflight refused, nothing dispatched) → refresh the host Claude login when it is short,
# wait, retry; any other rc → stop for inspection.
set -uo pipefail
live=$HOME/.local/share/nx01/0235-live
here=$HOME/.local/share/nx01/0235-reg/autoresearch/experiments/0235
cd "$live" || exit 1  # git cannot read a launch directory under macOS privacy protection (~/Documents)
left() { security find-generic-password -s 'Claude Code-credentials' -w | python3 -c "import json,sys,time;print(int(json.load(sys.stdin)['claudeAiOauth']['expiresAt']/1000-time.time()))"; }
for spec in "$@"; do
  tsv=${spec%%:*}; prefix=""; [ "$spec" != "$tsv" ] && prefix=${spec#*:}
  while read -r name task arm config _; do
    case "$name" in ''|'#'*) continue ;; esac
    case "$name" in "$prefix"*) ;; *) continue ;; esac
    while [ ! -e "$live/out/verdict-$name.json" ]; do
      # Operator hold (2026-10-07): no cell starts while root holds the accounts (HOLD file) or another cell runs.
      while [ -e "$live/HOLD" ] || pgrep -f "[0]235/run_cell.py" >/dev/null; do sleep 30; done
      [ -e "$live/out/verdict-$name.json" ] && break
      echo "$(date -u +%FT%TZ) $name start"
      python3 -B "$here/run_cell.py" "$live/runtime.json" "$name" "$task" "$arm" "$config"
      rc=$?
      echo "$(date -u +%FT%TZ) $name rc=$rc"
      [ "$rc" -eq 0 ] && break
      [ "$rc" -eq 3 ] || { echo "$(date -u +%FT%TZ) drive stopped at $name (rc=$rc)"; exit "$rc"; }
      cat "$live/out/not-dispatched-$name.json"; echo
      if [ "$(left)" -lt 6300 ]; then (cd /tmp && claude -p --model claude-sonnet-5-5 'Reply OK' >/dev/null 2>&1); fi
      sleep 300
    done
  done < "$here/$tsv"
  echo "$(date -u +%FT%TZ) drive finished $spec"
done
