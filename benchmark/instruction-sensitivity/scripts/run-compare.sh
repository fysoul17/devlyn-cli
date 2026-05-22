#!/usr/bin/env bash
# Lane B driver — v0 skeleton.
#
# Runs each named fixture against two arms (baseline-ref vs candidate-ref) and
# emits a run manifest. Driver-to-LLM wiring (Day 2) is NOT yet implemented —
# this script currently sets up the run directory layout and writes the
# manifest so downstream scripts (detect-mechanical.py, judge-blind.sh,
# score-behavior.py) have a stable contract to consume.
#
# Day 2 will plug an actual LLM driver (claude-code CLI, codex CLI, or a
# minimal API call) into the per-arm execution step.
#
# Usage:
#   bash run-compare.sh --baseline-ref <sha> --candidate-ref <sha> \
#                       --run-id <id> --fixtures B1-... B2-... ...

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

# Resolve canonical paths relative to repo root.
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
LANE_ROOT="$REPO_ROOT/benchmark/instruction-sensitivity"
RUN_DIR="$LANE_ROOT/results/$RUN_ID"

mkdir -p "$RUN_DIR/arms/solo_old" "$RUN_DIR/arms/solo_new"

# Verify the two refs actually exist in git (commit-pinned only — see README).
for ref in "$BASELINE_REF" "$CANDIDATE_REF"; do
  if ! git -C "$REPO_ROOT" rev-parse --verify "$ref^{commit}" >/dev/null 2>&1; then
    echo "error: ref not found: $ref" >&2
    exit 1
  fi
done

# Write run manifest with A/B slot randomization seed.
# A/B mapping is consulted ONLY at score aggregation, NOT during the judge call.
RANDOM_SEED="$(date -u +%s%N)"
cat > "$RUN_DIR/manifest.json" <<JSON
{
  "run_id": "$RUN_ID",
  "baseline_ref": "$BASELINE_REF",
  "candidate_ref": "$CANDIDATE_REF",
  "fixtures": [$(printf '"%s",' "${FIXTURES[@]}" | sed 's/,$//')],
  "random_seed": "$RANDOM_SEED",
  "status": "scaffolded",
  "next_step": "Day 2: wire LLM driver into arm execution loop, then run detect-mechanical.py + judge-blind.sh"
}
JSON

echo "Run directory created: $RUN_DIR"
echo "Manifest: $RUN_DIR/manifest.json"
echo ""
echo "NEXT: Day 2 will plug a driver (claude / codex CLI) into the arm-execution step."
echo "For now you can:"
echo "  1. Manually run a fixture against each ref using your driver of choice"
echo "  2. Write the diff to $RUN_DIR/arms/<solo_old|solo_new>/<fixture-id>/diff.patch"
echo "  3. Write the assistant transcript to .../transcript.txt"
echo "  4. Run detect-mechanical.py per arm-fixture pair"
echo "  5. Run judge-blind.sh per fixture (A/B paired)"
echo "  6. Run score-behavior.py to aggregate"
