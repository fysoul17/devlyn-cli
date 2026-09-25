#!/usr/bin/env bash
# run-violation-matrix.sh — N-rep drift-bait violation-rate matrix (iter-0058), optionally per instruction
# variant. One run-id per (variant, model, rep) so result dirs never collide; aggregate each variant prefix
# with violation-rate-matrix.py. Cells with a verdict are skipped (resume). An infra exit stops the matrix.
#
# Usage:
#   run-violation-matrix.sh --models claude-opus-5-5,claude-sonnet-5 --reps 4 --run-prefix iter0058-base
#   ... --instructions current=<path>,slim=<path>,none   (run ids: <prefix>-<name>-<model>-r<rep>)
#   ... --probes <dir>,<dir>                               (default: the 6-probe drift-bait panel)
set -euo pipefail

usage() {
  echo "usage: $0 --models <m1,m2,...> --reps <N> --run-prefix <prefix> [--instructions name=path|none,...] [--probes dir,...]"
  exit 1
}

MODELS=""; REPS=""; RUN_PREFIX=""; INSTRUCTIONS=""; PROBES=""
while [ $# -gt 0 ]; do
  case "$1" in
    --models)       MODELS="$2";       shift 2;;
    --reps)         REPS="$2";         shift 2;;
    --run-prefix)   RUN_PREFIX="$2";   shift 2;;
    --instructions) INSTRUCTIONS="$2"; shift 2;;
    --probes)       PROBES="$2";       shift 2;;
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
[ -z "$PROBES" ] || IFS=',' read -r -a PROBE_DIRS <<< "$PROBES"
IFS=',' read -r -a MODEL_LIST <<< "$MODELS"
VARIANTS=("")
[ -z "$INSTRUCTIONS" ] || IFS=',' read -r -a VARIANTS <<< "$INSTRUCTIONS"

# Rep-major, then model; the variant order rotates each rep (0099 precedent).
for rep in $(seq 1 "$REPS"); do
  for model in "${MODEL_LIST[@]}"; do
    count=${#VARIANTS[@]}
    for i in $(seq 0 $((count - 1))); do
      variant="${VARIANTS[$(( (i + rep - 1) % count ))]}"
      name="${variant%%=*}"; src="${variant#*=}"
      if [ -z "$variant" ]; then run_id="${RUN_PREFIX}-${model}-r${rep}"
      else run_id="${RUN_PREFIX}-${name}-${model}-r${rep}"; fi
      for probe_dir in "${PROBE_DIRS[@]}"; do
        [ -f "$PROBES_ROOT/results/$run_id/drift-bait/$(basename "$probe_dir")/verdict.json" ] && continue
        echo "[violation-matrix] rep=$rep model=$model variant=${name:-default} probe=$(basename "$probe_dir")"
        rc=0
        if [ -z "$variant" ]; then
          MODEL="$model" bash "$PROBES_ROOT/scripts/run-drift-bait-probe.sh" --probe-dir "$probe_dir" --run-id "$run_id" || rc=$?
        else
          MODEL="$model" INSTRUCTION_SRC="$src" bash "$PROBES_ROOT/scripts/run-drift-bait-probe.sh" \
            --probe-dir "$probe_dir" --run-id "$run_id" || rc=$?
        fi
        [ "$rc" -eq 0 ] || { echo "[violation-matrix] stopped: rc=$rc at $run_id/$(basename "$probe_dir"); fix the cause and rerun to resume" >&2; exit "$rc"; }
      done
    done
  done
done
echo "[violation-matrix] done: ${RUN_PREFIX}"
