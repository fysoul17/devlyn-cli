#!/usr/bin/env bash
# Lane B — baseline-vs-candidate runner.
#
# For each fixture, runs both arms (solo_old @ baseline-ref, solo_new @ candidate-ref),
# emits a manifest with A/B slot randomization, runs the mechanical detector, and
# invokes the instruction-blind judge.
#
# Usage:
#   bash run-compare.sh --baseline-ref <sha> --candidate-ref <sha> \
#                       --run-id <id> --fixtures B1-... [B2-...] ...
#
# Outputs land in benchmark/instruction-sensitivity/results/<run-id>/.

set -euo pipefail

BASELINE_REF=""
CANDIDATE_REF=""
RUN_ID=""
FIXTURES=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --baseline-ref) BASELINE_REF="$2"; shift 2 ;;
    --candidate-ref) CANDIDATE_REF="$2"; shift 2 ;;
    --run-id) RUN_ID="$2"; shift 2 ;;
    --fixtures) shift; while [[ $# -gt 0 && "$1" != --* ]]; do FIXTURES+=("$1"); shift; done ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$BASELINE_REF" || -z "$CANDIDATE_REF" || -z "$RUN_ID" || ${#FIXTURES[@]} -eq 0 ]]; then
  echo "usage: $0 --baseline-ref <sha> --candidate-ref <sha> --run-id <id> --fixtures <id>..." >&2
  exit 2
fi

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
LANE_ROOT="$REPO_ROOT/benchmark/instruction-sensitivity"
RUN_DIR="$LANE_ROOT/results/$RUN_ID"
mkdir -p "$RUN_DIR/arms/solo_old" "$RUN_DIR/arms/solo_new"

for ref in "$BASELINE_REF" "$CANDIDATE_REF"; do
  if ! git -C "$REPO_ROOT" rev-parse --verify "$ref^{commit}" >/dev/null 2>&1; then
    echo "error: ref not found: $ref" >&2
    exit 1
  fi
done

# Manifest + slot_map: A/B randomization is fixed at manifest-write time so the
# mapping survives partial reruns and is never re-derived during judge calls.
python3 - "$RUN_DIR/manifest.json" "$RUN_ID" "$BASELINE_REF" "$CANDIDATE_REF" "${FIXTURES[@]}" <<'PY'
import hashlib, json, sys
out, run_id, baseline, candidate, *fixtures = sys.argv[1:]
slot_map = {}
for f in fixtures:
    h = hashlib.sha256(f"{run_id}:{f}".encode()).hexdigest()
    if int(h, 16) % 2 == 0:
        slot_map[f] = {"A": "solo_old", "B": "solo_new", "seed": f"{run_id}:{f}"}
    else:
        slot_map[f] = {"A": "solo_new", "B": "solo_old", "seed": f"{run_id}:{f}"}
manifest = {
    "run_id": run_id,
    "baseline_ref": baseline,
    "candidate_ref": candidate,
    "fixtures": fixtures,
    "slot_map": slot_map,
    "status": "running",
    "schema_version": "v1",
}
open(out, "w").write(json.dumps(manifest, indent=2) + "\n")
PY

echo "manifest: $RUN_DIR/manifest.json"

# Per-arm execution loop. Each fixture is run on solo_old then solo_new.
for fixture in "${FIXTURES[@]}"; do
  for pair in "solo_old:$BASELINE_REF" "solo_new:$CANDIDATE_REF"; do
    arm="${pair%%:*}"
    ref="${pair##*:}"
    arm_dir="$RUN_DIR/arms/$arm/$fixture"
    mkdir -p "$arm_dir"
    echo ""
    echo "===== fixture=$fixture arm=$arm ref=$ref ====="
    if ! bash "$LANE_ROOT/scripts/run-fixture.sh" \
          --fixture "$fixture" --ref "$ref" --out-dir "$arm_dir"; then
      echo "warn: run-fixture failed for $fixture / $arm — continuing" >&2
    fi

    # Mechanical detector — fixture-generic.
    python3 "$LANE_ROOT/scripts/detect-mechanical.py" \
      --fixture-dir "$LANE_ROOT/fixtures/$fixture" \
      --arm-dir "$arm_dir" \
      --out "$RUN_DIR/detector-findings.jsonl" || true

    # Per-fixture hidden verifier (mechanical assertions tied to bad_signals).
    verify_sh="$LANE_ROOT/fixtures/$fixture/hidden/verify.sh"
    if [[ -x "$verify_sh" ]]; then
      python3 - "$verify_sh" "$arm_dir" "$fixture" "$arm" "$RUN_DIR/hidden-verify.jsonl" <<'PY'
import json, subprocess, sys
verify_sh, arm_dir, fixture, arm, out = sys.argv[1:]
res = subprocess.run(["bash", verify_sh, arm_dir], capture_output=True, text=True)
try:
    parsed = json.loads(res.stdout)
except Exception:
    parsed = {"raw_stdout": res.stdout, "stderr": res.stderr, "parse_error": True}
parsed["arm"] = arm
open(out, "a").write(json.dumps(parsed) + "\n")
PY
    fi
  done
done

# Judge pass — once per fixture.
for fixture in "${FIXTURES[@]}"; do
  echo ""
  echo "===== judge: $fixture ====="
  bash "$LANE_ROOT/scripts/judge-blind.sh" --run-dir "$RUN_DIR" --fixture "$fixture" || \
    echo "warn: judge failed for $fixture — continuing" >&2
done

# Mark manifest done.
python3 - "$RUN_DIR/manifest.json" <<'PY'
import json, sys
p = sys.argv[1]
m = json.load(open(p))
m["status"] = "complete"
open(p, "w").write(json.dumps(m, indent=2) + "\n")
PY

echo ""
echo "run-compare done. Aggregate with:"
echo "  python3 $LANE_ROOT/scripts/score-behavior.py --run-id $RUN_ID \\"
echo "    --out-json $RUN_DIR/behavior-score.json --out-md $RUN_DIR/behavior-score.md"
