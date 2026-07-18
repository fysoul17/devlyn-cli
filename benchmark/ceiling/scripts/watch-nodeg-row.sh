#!/bin/bash
# Watch one nodeg row: gate at PLAN time, snapshot .devlyn while live, full gate at row end.
# Row worktrees are DELETED at row end (0072.8/0072.13 instrument gap) — the
# snapshot is the only durable copy of raw criteria/plan/state bytes.
# usage: watch-nodeg-row.sh <run-id> <task-dir-name> <archive-dir> [gate-args…]
#   e.g. watch-nodeg-row.sh nodeg-20260719 DR-byte-preservation-f7-out-of-scope-trap /tmp/r6/f7-live --v5
set -uo pipefail
RUN_ID="$1"; TASK="$2"; ARC="$3"; shift 3
GATE_ARGS=("$@")
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
GATE="$SCRIPT_DIR/f7-carrier-gate.py"
RH="r$(printf '%s' "$RUN_ID" | shasum -a 256 | cut -c1-12)"
TH="f$(printf '%s' "$TASK" | shasum -a 256 | cut -c1-12)"
WS="${CEILING_EXTERNAL_ROOT:-$HOME/.local/share/nx01}/w/$RH/$TH/A1/repo"
RES="$REPO_ROOT/benchmark/ceiling/results/$RUN_ID/$TASK/A1"
mkdir -p "$ARC"

until [ -f "$WS/.devlyn/plan.md" ]; do sleep 20; done
sleep 5
echo "ROW-PLAN-ARTIFACT-READY $TASK"
python3 "$GATE" "$WS" "${GATE_ARGS[@]}" 2>&1 | tail -6

( while [ -d "$WS/.devlyn" ]; do
    cp -a "$WS/.devlyn" "$ARC/devlyn.tmp" 2>/dev/null \
      && rm -rf "$ARC/devlyn.snapshot" && mv "$ARC/devlyn.tmp" "$ARC/devlyn.snapshot"
    sleep 15
  done ) &
SNAP=$!

until [ -f "$RES/timing.json" ]; do sleep 20; done
kill "$SNAP" 2>/dev/null
if [ -f "$WS/.devlyn/pipeline.state.json" ]; then
  echo "ROW-COMPLETE $TASK target=live"
  python3 "$GATE" "$WS" "${GATE_ARGS[@]}" --post-implement 2>&1 | tail -16
else
  echo "ROW-COMPLETE $TASK target=snapshot ($ARC/devlyn.snapshot + $RES)"
fi
