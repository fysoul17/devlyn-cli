#!/usr/bin/env bash
# run-full-pipeline-pair-candidate.sh — measure full-pipeline L2/pair candidates.
#
# Runs bare + solo_claude first and applies headroom-gate.py. Only if the set
# leaves room for L2 does it run l2_gated, rejudge, and apply
# full-pipeline-pair-gate.py.

set -euo pipefail

usage() {
  local code="${1:-1}"
  cat >&2 <<'EOF'
usage: run-full-pipeline-pair-candidate.sh [options] <fixture> [<fixture> ...]

Options:
  --run-id ID
  --bare-max N
  --solo-max N
  --min-fixtures N
  --min-pair-margin N
  --max-pair-solo-wall-ratio N
  --pair-arm ARM
  --reuse-calibrated-from RUN_ID
EOF
  exit "$code"
}

RUN_ID=""
BARE_MAX=60
SOLO_MAX=80
MIN_FIXTURES=2
MIN_PAIR_MARGIN=5
MAX_PAIR_SOLO_WALL_RATIO=""
PAIR_ARM="l2_gated"
REUSE_CALIBRATED_FROM=""
FIXTURES=()
while [ $# -gt 0 ]; do
  case "$1" in
    --run-id) RUN_ID="$2"; shift 2;;
    --bare-max) BARE_MAX="$2"; shift 2;;
    --solo-max) SOLO_MAX="$2"; shift 2;;
    --min-fixtures) MIN_FIXTURES="$2"; shift 2;;
    --min-pair-margin) MIN_PAIR_MARGIN="$2"; shift 2;;
    --max-pair-solo-wall-ratio) MAX_PAIR_SOLO_WALL_RATIO="$2"; shift 2;;
    --pair-arm) PAIR_ARM="$2"; shift 2;;
    --reuse-calibrated-from) REUSE_CALIBRATED_FROM="$2"; shift 2;;
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
  RUN_ID="${TS}-${SHA}-full-pipeline-pair"
fi

echo ""
echo "═══ Full-Pipeline Pair Candidate Run ═══"
echo "Run-id:   $RUN_ID"
echo "Fixtures: ${FIXTURES[*]}"
echo "Arms:     bare solo_claude $PAIR_ARM"
[ -z "$REUSE_CALIBRATED_FROM" ] || echo "Reuse:    bare+solo from $REUSE_CALIBRATED_FROM"
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
echo "[full-pipeline-pair] mirrored $mirrored committed skill(s): config/skills/ -> .claude/skills/"

copy_calibrated_arm() {
  local fid="$1"
  local arm="$2"
  local src="$BENCH_ROOT/results/$REUSE_CALIBRATED_FROM/$fid/$arm"
  local dst="$BENCH_ROOT/results/$RUN_ID/$fid/$arm"
  if [ -f "$dst/result.json" ]; then
    echo "[full-pipeline-pair] reuse skip: $fid / $arm already exists in $RUN_ID"
    return 0
  fi
  [ -d "$src" ] || { echo "reuse source missing: $src" >&2; exit 1; }
  [ -f "$src/result.json" ] || { echo "reuse source missing result.json: $src" >&2; exit 1; }
  mkdir -p "$(dirname "$dst")"
  cp -R "$src" "$dst"
  echo "[full-pipeline-pair] reused $fid / $arm from $REUSE_CALIBRATED_FROM"
}

for fid in "${FIXTURES[@]}"; do
  if [ -n "$REUSE_CALIBRATED_FROM" ]; then
    copy_calibrated_arm "$fid" bare
    copy_calibrated_arm "$fid" solo_claude
  else
    echo "[full-pipeline-pair] ► $fid / bare"
    bash "$BENCH_ROOT/scripts/run-fixture.sh" \
      --fixture "$fid" --arm bare --run-id "$RUN_ID" \
      || echo "[full-pipeline-pair] ✗ $fid / bare (arm failure tolerated; gate will fail if dirty)"

    echo "[full-pipeline-pair] ► $fid / solo_claude"
    bash "$BENCH_ROOT/scripts/run-fixture.sh" \
      --fixture "$fid" --arm solo_claude --run-id "$RUN_ID" \
      || echo "[full-pipeline-pair] ✗ $fid / solo_claude (arm failure tolerated; gate will fail if dirty)"
  fi

  echo "[full-pipeline-pair] ► headroom judge $fid"
  bash "$BENCH_ROOT/scripts/judge.sh" --fixture "$fid" --run-id "$RUN_ID" \
    || echo "[full-pipeline-pair] ✗ headroom judge failed for $fid"
done

headroom_args=(
  --run-id "$RUN_ID"
  --bare-max "$BARE_MAX"
  --solo-max "$SOLO_MAX"
  --min-fixtures "$MIN_FIXTURES"
  --out-json "$BENCH_ROOT/results/$RUN_ID/headroom-gate.json"
  --out-md "$BENCH_ROOT/results/$RUN_ID/headroom-gate.md"
)
python3 "$BENCH_ROOT/scripts/headroom-gate.py" "${headroom_args[@]}"

for fid in "${FIXTURES[@]}"; do
  echo "[full-pipeline-pair] ► $fid / $PAIR_ARM"
  bash "$BENCH_ROOT/scripts/run-fixture.sh" \
    --fixture "$fid" --arm "$PAIR_ARM" --run-id "$RUN_ID" \
    || echo "[full-pipeline-pair] ✗ $fid / $PAIR_ARM (arm failure tolerated; gate will fail if dirty)"

  echo "[full-pipeline-pair] ► final judge $fid"
  bash "$BENCH_ROOT/scripts/judge.sh" --fixture "$fid" --run-id "$RUN_ID" \
    || echo "[full-pipeline-pair] ✗ final judge failed for $fid"
done

pair_args=(
  --run-id "$RUN_ID"
  --bare-max "$BARE_MAX"
  --solo-max "$SOLO_MAX"
  --min-fixtures "$MIN_FIXTURES"
  --min-pair-margin "$MIN_PAIR_MARGIN"
  --pair-arm "$PAIR_ARM"
  --out-json "$BENCH_ROOT/results/$RUN_ID/full-pipeline-pair-gate.json"
  --out-md "$BENCH_ROOT/results/$RUN_ID/full-pipeline-pair-gate.md"
)
[ -z "$MAX_PAIR_SOLO_WALL_RATIO" ] || pair_args+=(--max-pair-solo-wall-ratio "$MAX_PAIR_SOLO_WALL_RATIO")

python3 "$BENCH_ROOT/scripts/full-pipeline-pair-gate.py" "${pair_args[@]}"
cat "$BENCH_ROOT/results/$RUN_ID/full-pipeline-pair-gate.md"
