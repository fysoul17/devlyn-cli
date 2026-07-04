#!/usr/bin/env bash
# run-violation-matrix.sh — N-rep drift-bait violation-rate matrix (iter-0058).
# Runs every drift-bait probe N times per model through run-drift-bait-probe.sh
# (bare-arm instrument, unchanged), one run-id per (model, rep) so WORK_DIRs and
# result dirs never collide. Aggregate with violation-rate-matrix.py afterwards.
#
# Usage:
#   run-violation-matrix.sh --models sonnet,opus --reps 4 --run-prefix iter0058-base
set -euo pipefail

usage() {
  echo "usage: $0 --models <m1,m2,...> --reps <N> --run-prefix <prefix>"
  exit 1
}

MODELS=""; REPS=""; RUN_PREFIX=""
while [ $# -gt 0 ]; do
  case "$1" in
    --models)     MODELS="$2";     shift 2;;
    --reps)       REPS="$2";       shift 2;;
    --run-prefix) RUN_PREFIX="$2"; shift 2;;
    *) usage;;
  esac
done
[ -n "$MODELS" ] && [ -n "$REPS" ] && [ -n "$RUN_PREFIX" ] || usage

PROBES_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$PROBES_ROOT/../.." && pwd)"

# The canonical 6-probe drift-bait panel (benchmark/probes/README.md):
# 3 reused Lane-B fixtures + 3 DB-* probes.
PROBE_DIRS=(
  "$REPO_ROOT/benchmark/instruction-sensitivity/fixtures/B2-tangential-cleanup-bait"
  "$REPO_ROOT/benchmark/instruction-sensitivity/fixtures/B4-orthogonal-edit-trap"
  "$REPO_ROOT/benchmark/instruction-sensitivity/fixtures/B5-orphan-direction-trap"
  "$PROBES_ROOT/drift-bait/DB-silent-catch-root-cause"
  "$PROBES_ROOT/drift-bait/DB-failing-adjacent-test"
  "$PROBES_ROOT/drift-bait/DB-tempting-state-file"
)

IFS=',' read -r -a MODEL_LIST <<< "$MODELS"
for model in "${MODEL_LIST[@]}"; do
  for rep in $(seq 1 "$REPS"); do
    run_id="${RUN_PREFIX}-${model}-r${rep}"
    for probe_dir in "${PROBE_DIRS[@]}"; do
      echo "[violation-matrix] model=$model rep=$rep probe=$(basename "$probe_dir")"
      MODEL="$model" bash "$PROBES_ROOT/scripts/run-drift-bait-probe.sh" \
        --probe-dir "$probe_dir" --run-id "$run_id"
    done
  done
done
echo "[violation-matrix] done: ${RUN_PREFIX}-{$MODELS}-r1..r$REPS"
