#!/bin/bash
# Watch one nodeg row: gate at PLAN time, snapshot .devlyn while live, full gate at row end.
# Row worktrees may be deleted at row end; PHASE-6 also archives root state into
# .devlyn/runs/. The snapshot remains the fallback when the worktree is gone.
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

( while [ -d "$WS" ]; do
    cp -a "$WS/.devlyn" "$ARC/devlyn.tmp" 2>/dev/null \
      && rm -rf "$ARC/devlyn.snapshot" && mv "$ARC/devlyn.tmp" "$ARC/devlyn.snapshot"
    sleep 15
  done ) &
SNAP=$!

until [ -f "$RES/timing.json" ]; do sleep 20; done
kill "$SNAP" 2>/dev/null
wait "$SNAP" 2>/dev/null || true
if [ -d "$WS" ]; then
  TEMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/watch-nodeg-row.XXXXXX")"
  trap 'rm -rf "$TEMP_ROOT"' EXIT
  GATE_WS="$TEMP_ROOT/repo"
  cp -a "$WS" "$GATE_WS" || {
    echo "BLOCKED:watcher:temp-copy-failed source=$WS" >&2
    exit 78
  }

  NEWEST_RUN=""
  for candidate in "$GATE_WS/.devlyn/runs/"*; do
    [ -d "$candidate" ] || continue
    if [ -z "$NEWEST_RUN" ] || [ "$candidate" -nt "$NEWEST_RUN" ]; then
      NEWEST_RUN="$candidate"
    fi
  done
  if [ -z "$NEWEST_RUN" ]; then
    echo "BLOCKED:watcher:archived-state-missing workspace=$WS" >&2
    exit 78
  fi

  for required in pipeline.state.json goal.raw.txt criteria.generated.md plan.md; do
    [ -f "$NEWEST_RUN/$required" ] || {
      echo "BLOCKED:watcher:archived-state-missing file=$NEWEST_RUN/$required" >&2
      exit 78
    }
    cp -a "$NEWEST_RUN/$required" "$GATE_WS/.devlyn/$required"
  done
  for archived in "$NEWEST_RUN"/surface-close.*; do
    [ -e "$archived" ] || continue
    cp -a "$archived" "$GATE_WS/.devlyn/"
  done

  echo "ROW-COMPLETE $TASK target=temp-copy archived_run=$(basename "$NEWEST_RUN")"
  python3 "$GATE" "$GATE_WS" "${GATE_ARGS[@]}" --post-implement 2>&1 | tail -16
else
  echo "ROW-COMPLETE $TASK target=snapshot ($ARC/devlyn.snapshot + $RES)"
fi
