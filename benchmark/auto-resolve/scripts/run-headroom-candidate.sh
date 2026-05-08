#!/usr/bin/env bash
# run-headroom-candidate.sh — calibrate candidate fixtures for L2/pair headroom.
#
# Runs only the arms needed by headroom-gate.py: bare and solo_claude.
# Then blind-judges those two arms and applies the mechanical gate.

set -euo pipefail

usage() {
  local code="${1:-1}"
  echo "usage: $0 [--run-id ID] <fixture> [<fixture> ...]" >&2
  exit "$code"
}

RUN_ID=""
FIXTURES=()
while [ $# -gt 0 ]; do
  case "$1" in
    --run-id) RUN_ID="$2"; shift 2;;
    -h|--help) usage 0;;
    F[0-9]*) FIXTURES+=("$1"); shift;;
    *) echo "unknown arg: $1" >&2; usage;;
  esac
done

[ ${#FIXTURES[@]} -gt 0 ] || usage

BENCH_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$BENCH_ROOT/../.." && pwd)"

if [ -z "$RUN_ID" ]; then
  TS=$(date -u +%Y%m%dT%H%M%SZ)
  SHA=$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo nogit)
  RUN_ID="${TS}-${SHA}-headroom"
fi

echo ""
echo "═══ Headroom Candidate Run ═══"
echo "Run-id:   $RUN_ID"
echo "Fixtures: ${FIXTURES[*]}"
echo "Arms:     bare solo_claude"
if [ ${#FIXTURES[@]} -lt 2 ]; then
  echo "Gate:     will FAIL set gate unless at least 2 fixtures are supplied"
fi
echo ""

SRC_SKILLS="$REPO_ROOT/config/skills"
DST_SKILLS="$REPO_ROOT/.claude/skills"
mkdir -p "$DST_SKILLS"
mirrored=0
for src_dir in "$SRC_SKILLS"/*/; do
  [ -d "$src_dir" ] || continue
  name=$(basename "$src_dir")
  case "$name" in
    devlyn:auto-resolve-workspace|devlyn:ideate-workspace|preflight-workspace|roadmap-archival-workspace)
      continue ;;
  esac
  staging="$DST_SKILLS/.${name}.staging"
  rm -rf "$staging"
  cp -R "$src_dir" "$staging"
  rm -rf "$DST_SKILLS/$name"
  mv "$staging" "$DST_SKILLS/$name"
  mirrored=$((mirrored + 1))
done
echo "[headroom] mirrored $mirrored committed skill(s): config/skills/ -> .claude/skills/"

for fid in "${FIXTURES[@]}"; do
  echo "[headroom] ► $fid / bare"
  bash "$BENCH_ROOT/scripts/run-fixture.sh" \
    --fixture "$fid" --arm bare --run-id "$RUN_ID" \
    || echo "[headroom] ✗ $fid / bare (arm failure tolerated; artifacts may still exist)"

  echo "[headroom] ► $fid / solo_claude"
  bash "$BENCH_ROOT/scripts/run-fixture.sh" \
    --fixture "$fid" --arm solo_claude --run-id "$RUN_ID" \
    || echo "[headroom] ✗ $fid / solo_claude (arm failure tolerated; artifacts may still exist)"

  echo "[headroom] ► judge $fid"
  bash "$BENCH_ROOT/scripts/judge.sh" --fixture "$fid" --run-id "$RUN_ID" \
    || echo "[headroom] ✗ judge failed for $fid"
done

echo ""
set +e
python3 "$BENCH_ROOT/scripts/headroom-gate.py" \
  --run-id "$RUN_ID" \
  --out-json "$BENCH_ROOT/results/$RUN_ID/headroom-gate.json" \
  --out-md "$BENCH_ROOT/results/$RUN_ID/headroom-gate.md"
GATE_EXIT=$?
set -e

cat "$BENCH_ROOT/results/$RUN_ID/headroom-gate.md"
exit "$GATE_EXIT"
