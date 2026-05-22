#!/usr/bin/env bash
# Single-fixture runner — v0 skeleton.
#
# Used by run-compare.sh to execute one fixture against one arm (one ref).
# v0 currently prints the prompt the driver should send and the expected
# output paths; Day 2 will replace this with a real LLM call.
#
# Usage:
#   bash run-fixture.sh --fixture <id> --ref <sha> --out-dir <path>

set -euo pipefail

FIXTURE=""
REF=""
OUT_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --fixture) FIXTURE="$2"; shift 2 ;;
    --ref) REF="$2"; shift 2 ;;
    --out-dir) OUT_DIR="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$FIXTURE" || -z "$REF" || -z "$OUT_DIR" ]]; then
  echo "usage: $0 --fixture <id> --ref <sha> --out-dir <path>" >&2
  exit 2
fi

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
FIXTURE_DIR="$REPO_ROOT/benchmark/instruction-sensitivity/fixtures/$FIXTURE"

if [[ ! -d "$FIXTURE_DIR" ]]; then
  echo "error: fixture not found: $FIXTURE_DIR" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
cat "$FIXTURE_DIR/task.txt" > "$OUT_DIR/prompt.txt"

echo "=== Fixture: $FIXTURE ==="
echo "Ref pinned: $REF"
echo "Spec: $FIXTURE_DIR/spec.md"
echo "Allowlist: $(tr '\n' ' ' < "$FIXTURE_DIR/scope-allowlist.txt")"
echo ""
echo "PROMPT (to feed to driver at $REF):"
echo "---"
cat "$FIXTURE_DIR/task.txt"
echo "---"
echo ""
echo "EXPECTED OUTPUT FILES IN $OUT_DIR:"
echo "  - diff.patch       (driver-produced unified diff)"
echo "  - transcript.txt   (assistant turns only, ≤4kB ideally)"
echo "  - meta.json        (driver, model, wall-time, exit status)"
echo ""
echo "TODO Day 2: wire a real driver (claude-code CLI / codex CLI / API) here."
