#!/usr/bin/env bash
# Instruction-blind judge caller — v0 skeleton.
#
# Reads two arm outputs (A and B, slot-randomized) for one fixture, builds the
# judge prompt per benchmark/instruction-sensitivity/RUBRIC.md, calls the
# judge LLM, and appends a JSONL row to judge-findings.jsonl.
#
# Day 2 will wire an actual judge model call. For now this script validates
# inputs and prints what the judge prompt WOULD look like.
#
# Usage:
#   bash judge-blind.sh --run-dir <path> --fixture <id>

set -euo pipefail

RUN_DIR=""
FIXTURE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run-dir) RUN_DIR="$2"; shift 2 ;;
    --fixture) FIXTURE="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$RUN_DIR" || -z "$FIXTURE" ]]; then
  echo "usage: $0 --run-dir <path> --fixture <id>" >&2
  exit 2
fi

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
FIXTURE_DIR="$REPO_ROOT/benchmark/instruction-sensitivity/fixtures/$FIXTURE"
ARM_A="$RUN_DIR/arms/solo_old/$FIXTURE"  # placeholder pending randomization
ARM_B="$RUN_DIR/arms/solo_new/$FIXTURE"

for p in "$FIXTURE_DIR/spec.md" "$FIXTURE_DIR/task.txt" "$FIXTURE_DIR/scope-allowlist.txt" \
         "$FIXTURE_DIR/behavior-contract.json" "$ARM_A/diff.patch" "$ARM_B/diff.patch"; do
  if [[ ! -f "$p" ]]; then
    echo "error: missing input: $p" >&2
    exit 1
  fi
done

echo "Judge inputs validated. Judge call wiring (Day 2) NOT YET IMPLEMENTED."
echo ""
echo "Inputs that WILL be sent (instruction-blind, no arm identity):"
echo "  task            <- $FIXTURE_DIR/task.txt"
echo "  spec            <- $FIXTURE_DIR/spec.md"
echo "  scope_allowlist <- $FIXTURE_DIR/scope-allowlist.txt"
echo "  fixture_axes    <- $FIXTURE_DIR/behavior-contract.json (axes_scored keys)"
echo "  arm_A.diff      <- $ARM_A/diff.patch"
echo "  arm_A.transcript_excerpt <- $ARM_A/transcript.txt (last 4kB)"
echo "  arm_B.diff      <- $ARM_B/diff.patch"
echo "  arm_B.transcript_excerpt <- $ARM_B/transcript.txt (last 4kB)"
echo ""
echo "OUTPUT (Day 2): JSONL row appended to $RUN_DIR/judge-findings.jsonl with strict-JSON judge verdict."
echo "Rubric: $REPO_ROOT/benchmark/instruction-sensitivity/RUBRIC.md"
