#!/usr/bin/env bash
# run-full-pipeline-pair-candidate.sh — measure full-pipeline L2/pair candidates.
#
# Runs bare + solo_claude first and applies headroom-gate.py. Only if the set
# leaves room for L2 does it run the selected pair arm, rejudge, and apply
# full-pipeline-pair-gate.py. Default pair arm is l2_risk_probes because that is
# the current measured solo<pair proof path.

set -euo pipefail

usage() {
  local code="${1:-1}"
  cat >&2 <<'EOF'
usage: run-full-pipeline-pair-candidate.sh [options] <fixture> [<fixture> ...]

Options:
  --run-id ID
  --bare-max N
  --solo-max N
  --min-bare-headroom N
  --min-solo-headroom N
  --min-fixtures N
  --min-pair-margin N
  --max-pair-solo-wall-ratio N  (default: 3)
  --pair-arm ARM  (default: l2_risk_probes; use l2_gated only for diagnostics)
  --reuse-calibrated-from RUN_ID
  --allow-rejected-fixtures
                  allow rejected/ceiling fixtures for diagnostics only
  --dry-run       validate args/fixtures and print replay command only
EOF
  exit "$code"
}

require_value() {
  local flag="$1"
  local value="${2:-}"
  if [ -z "$value" ] || [[ "$value" == --* ]]; then
    echo "$flag requires a value" >&2
    exit 1
  fi
}

RUN_ID=""
BARE_MAX=60
SOLO_MAX=80
MIN_BARE_HEADROOM=5
MIN_SOLO_HEADROOM=5
MIN_FIXTURES=2
MIN_PAIR_MARGIN=5
MAX_PAIR_SOLO_WALL_RATIO=3
PAIR_ARM="l2_risk_probes"
REUSE_CALIBRATED_FROM=""
ALLOW_REJECTED_FIXTURES=0
DRY_RUN=0
FIXTURES=()
while [ $# -gt 0 ]; do
  case "$1" in
    --run-id) require_value "$1" "${2:-}"; RUN_ID="$2"; shift 2;;
    --bare-max) require_value "$1" "${2:-}"; BARE_MAX="$2"; shift 2;;
    --solo-max) require_value "$1" "${2:-}"; SOLO_MAX="$2"; shift 2;;
    --min-bare-headroom) require_value "$1" "${2:-}"; MIN_BARE_HEADROOM="$2"; shift 2;;
    --min-solo-headroom) require_value "$1" "${2:-}"; MIN_SOLO_HEADROOM="$2"; shift 2;;
    --min-fixtures) require_value "$1" "${2:-}"; MIN_FIXTURES="$2"; shift 2;;
    --min-pair-margin) require_value "$1" "${2:-}"; MIN_PAIR_MARGIN="$2"; shift 2;;
    --max-pair-solo-wall-ratio) require_value "$1" "${2:-}"; MAX_PAIR_SOLO_WALL_RATIO="$2"; shift 2;;
    --pair-arm) require_value "$1" "${2:-}"; PAIR_ARM="$2"; shift 2;;
    --reuse-calibrated-from) require_value "$1" "${2:-}"; REUSE_CALIBRATED_FROM="$2"; shift 2;;
    --allow-rejected-fixtures) ALLOW_REJECTED_FIXTURES=1; shift;;
    --dry-run) DRY_RUN=1; shift;;
    -h|--help) usage 0;;
    [FS][0-9]*) FIXTURES+=("$1"); shift;;
    *) echo "unknown arg: $1" >&2; usage;;
  esac
done

for threshold in BARE_MAX SOLO_MAX MIN_BARE_HEADROOM MIN_SOLO_HEADROOM MIN_FIXTURES MIN_PAIR_MARGIN; do
  value="${!threshold}"
  case "$threshold" in
    BARE_MAX) flag="bare-max" ;;
    SOLO_MAX) flag="solo-max" ;;
    MIN_BARE_HEADROOM) flag="min-bare-headroom" ;;
    MIN_SOLO_HEADROOM) flag="min-solo-headroom" ;;
    MIN_FIXTURES) flag="min-fixtures" ;;
    MIN_PAIR_MARGIN) flag="min-pair-margin" ;;
  esac
  if [[ ! "$value" =~ ^[0-9]+$ ]]; then
    echo "--$flag must be an integer: $value" >&2
    exit 1
  fi
done
if [ "$MIN_FIXTURES" -lt 1 ]; then
  echo "--min-fixtures must be >= 1" >&2
  exit 1
fi
if [ "$MIN_BARE_HEADROOM" -lt 0 ]; then
  echo "--min-bare-headroom must be >= 0" >&2
  exit 1
fi
if [ "$MIN_SOLO_HEADROOM" -lt 0 ]; then
  echo "--min-solo-headroom must be >= 0" >&2
  exit 1
fi
if [ -n "$MAX_PAIR_SOLO_WALL_RATIO" ]; then
  if ! [[ "$MAX_PAIR_SOLO_WALL_RATIO" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
    echo "--max-pair-solo-wall-ratio must be a positive number: $MAX_PAIR_SOLO_WALL_RATIO" >&2
    exit 1
  fi
  if ! awk "BEGIN { exit !($MAX_PAIR_SOLO_WALL_RATIO > 0) }"; then
    echo "--max-pair-solo-wall-ratio must be > 0" >&2
    exit 1
  fi
fi
[ ${#FIXTURES[@]} -gt 0 ] || usage

case "$PAIR_ARM" in
  l2_risk_probes|l2_gated) ;;
  l2_forced)
    echo "pair-arm l2_forced is retired: it leaks pair-awareness before IMPLEMENT; use l2_risk_probes for current proof runs or l2_gated for diagnostics." >&2
    exit 1
    ;;
  *)
    echo "pair-arm must be l2_risk_probes or l2_gated (diagnostic): $PAIR_ARM" >&2
    exit 1
    ;;
esac

BENCH_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$BENCH_ROOT/../.." && pwd)"
source "$BENCH_ROOT/scripts/pair-rejected-fixtures.sh"
if ! declare -F rejected_pair_fixture_reason >/dev/null; then
  echo "rejected fixture registry must define rejected_pair_fixture_reason" >&2
  exit 1
fi

if [ -z "$RUN_ID" ]; then
  TS=$(date -u +%Y%m%dT%H%M%SZ)
  SHA=$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo nogit)
  RUN_ID="${TS}-${SHA}-full-pipeline-pair"
fi

print_command() {
  local cmd
  if [ "${DEVLYN_BENCHMARK_CLI_SUBCOMMAND:-}" = "pair" ]; then
    cmd=(npx devlyn-cli benchmark pair --run-id "$RUN_ID")
  else
    cmd=(bash "$0" --run-id "$RUN_ID")
  fi
  cmd+=(--bare-max "$BARE_MAX")
  cmd+=(--solo-max "$SOLO_MAX")
  cmd+=(--min-bare-headroom "$MIN_BARE_HEADROOM")
  cmd+=(--min-solo-headroom "$MIN_SOLO_HEADROOM")
  cmd+=(--min-fixtures "$MIN_FIXTURES")
  cmd+=(--min-pair-margin "$MIN_PAIR_MARGIN")
  [ -z "$MAX_PAIR_SOLO_WALL_RATIO" ] || cmd+=(--max-pair-solo-wall-ratio "$MAX_PAIR_SOLO_WALL_RATIO")
  cmd+=(--pair-arm "$PAIR_ARM")
  [ -z "$REUSE_CALIBRATED_FROM" ] || cmd+=(--reuse-calibrated-from "$REUSE_CALIBRATED_FROM")
  [ "$ALLOW_REJECTED_FIXTURES" -eq 0 ] || cmd+=(--allow-rejected-fixtures)
  [ "$DRY_RUN" -eq 0 ] || cmd+=(--dry-run)
  cmd+=("${FIXTURES[@]}")
  printf 'Command: '
  printf '%q ' "${cmd[@]}"
  printf '\n'
}

run_gate_with_report() {
  local label="$1"
  local report="$2"
  shift 2
  set +e
  "$@"
  local status=$?
  set -e
  if [ -f "$report" ]; then
    cat "$report"
  else
    echo "[full-pipeline-pair] ${label} report missing: $report" >&2
  fi
  return "$status"
}

fixture_exists() {
  local fid="$1"
  [ -d "$BENCH_ROOT/fixtures/$fid" ] || [ -d "$BENCH_ROOT/shadow-fixtures/$fid" ]
}

fixture_dir() {
  local fid="$1"
  if [ -d "$BENCH_ROOT/fixtures/$fid" ]; then
    printf '%s\n' "$BENCH_ROOT/fixtures/$fid"
  else
    printf '%s\n' "$BENCH_ROOT/shadow-fixtures/$fid"
  fi
}

is_shadow_fixture() {
  local fid="$1"
  [ -d "$BENCH_ROOT/shadow-fixtures/$fid" ]
}

retired_fixture_exists() {
  local fid="$1"
  [ -d "$BENCH_ROOT/fixtures/retired/$fid" ]
}

fixture_smoke_only() {
  local fid="$1"
  [[ "$fid" == S1 || "$fid" == S1-* ]]
}

fixture_category() {
  local dir="$1"
  python3 - "$dir/metadata.json" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as handle:
        print(json.load(handle).get("category", ""))
except FileNotFoundError:
    print("")
PY
}

fixture_has_solo_headroom_hypothesis() {
  local dir="$1"
  python3 "$BENCH_ROOT/scripts/solo-headroom-hypothesis.py" --expected-json "$dir/expected.json" "$dir/spec.md"
}

fixture_has_solo_ceiling_avoidance_note() {
  local dir="$1"
  python3 "$BENCH_ROOT/scripts/solo-ceiling-avoidance.py" "$dir/NOTES.md"
}

fixture_has_pair_evidence() {
  local fid="$1"
  python3 - "$BENCH_ROOT/results" "$fid" <<'PY'
import json
import pathlib
import sys

results = pathlib.Path(sys.argv[1])
fixture = sys.argv[2]
if not results.is_dir():
    sys.exit(1)
for path in results.glob("*/full-pipeline-pair-gate.json"):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        continue
    if data.get("verdict") != "PASS":
        continue
    rows = data.get("rows")
    if not isinstance(rows, list):
        continue
    for row in rows:
        if isinstance(row, dict) and row.get("fixture") == fixture and row.get("status") == "PASS":
            sys.exit(0)
sys.exit(1)
PY
}

validate_fixtures() {
  local missing=0
  local fid reason dir category
  for fid in "${FIXTURES[@]}"; do
    if ! fixture_exists "$fid"; then
      if retired_fixture_exists "$fid"; then
        echo "fixture is retired and is not rerun by pair-candidate runners: $fid. Use preserved results/docs for historical replay." >&2
        missing=1
        continue
      fi
      echo "fixture not found in fixtures/ or shadow-fixtures/: $fid" >&2
      missing=1
      continue
    fi
    if [ "$DRY_RUN" -eq 0 ] && fixture_smoke_only "$fid"; then
      echo "fixture is smoke-only and cannot run providers: $fid. Use --dry-run for runner/package validation." >&2
      missing=1
      continue
    fi
    reason="$(rejected_pair_fixture_reason "$fid" || true)"
    if [ "$ALLOW_REJECTED_FIXTURES" -eq 0 ]; then
      if [ -n "$reason" ]; then
        echo "fixture rejected for pair-candidate runs: $fid ($reason). Use --allow-rejected-fixtures for diagnostics only." >&2
        missing=1
        continue
      fi
    fi
    if [ -z "$reason" ]; then
      dir="$(fixture_dir "$fid")"
      category="$(fixture_category "$dir")"
      if [ "$category" = "high-risk" ] && ! fixture_has_pair_evidence "$fid"; then
        if ! fixture_has_solo_headroom_hypothesis "$dir"; then
          echo "fixture spec.md needs a solo-headroom hypothesis with solo_claude miss and observable command from expected.json before provider spend: $fid" >&2
          missing=1
        fi
        if is_shadow_fixture "$fid" && ! fixture_has_solo_ceiling_avoidance_note "$dir"; then
          echo "shadow fixture NOTES.md needs ## Solo ceiling avoidance with solo_claude, a rejected/solo-saturated control comparison, and headroom reasoning before provider spend: $fid" >&2
          missing=1
        fi
      fi
    fi
  done
  [ "$missing" -eq 0 ] || exit 1
}

echo ""
echo "═══ Full-Pipeline Pair Candidate Run ═══"
echo "Run-id:   $RUN_ID"
echo "Fixtures: ${FIXTURES[*]}"
echo "Arms:     bare solo_claude $PAIR_ARM"
echo "Headroom: bare <= $BARE_MAX (headroom >= $MIN_BARE_HEADROOM), solo_claude <= $SOLO_MAX (headroom >= $MIN_SOLO_HEADROOM), baseline evidence-complete, min fixtures $MIN_FIXTURES"
echo "Pair:     $PAIR_ARM evidence-clean, canonical trigger, margin >= +$MIN_PAIR_MARGIN${MAX_PAIR_SOLO_WALL_RATIO:+, wall ratio <= $MAX_PAIR_SOLO_WALL_RATIO}"
[ -z "$REUSE_CALIBRATED_FROM" ] || echo "Reuse:    bare+solo from $REUSE_CALIBRATED_FROM"
[ "$DRY_RUN" -eq 0 ] || echo "Mode:     DRY RUN (no model/provider invocations)"
print_command
echo ""

validate_fixtures

if [ "$DRY_RUN" -eq 1 ] && [ "${#FIXTURES[@]}" -lt "$MIN_FIXTURES" ]; then
  echo "[full-pipeline-pair] DRY RUN failed — ${#FIXTURES[@]} fixture(s) supplied, --min-fixtures requires $MIN_FIXTURES." >&2
  exit 1
fi

if [ "$DRY_RUN" -eq 1 ]; then
  echo "[full-pipeline-pair] DRY RUN complete — fixtures resolved, no arms or judges executed."
  exit 0
fi

mirror_skills() {
  local src_skills="$REPO_ROOT/config/skills"
  local dst_skills="$REPO_ROOT/.claude/skills"
  local mirrored=0
  local src_dir name staging
  mkdir -p "$dst_skills"
  for src_dir in "$src_skills"/*/; do
    [ -d "$src_dir" ] || continue
    name=$(basename "$src_dir")
    case "$name" in
      devlyn:auto-resolve-workspace|devlyn:ideate-workspace|preflight-workspace|roadmap-archival-workspace)
        continue ;;
    esac
    staging="$dst_skills/.${name}.staging"
    rm -rf "$staging"
    cp -R "$src_dir" "$staging"
    rm -rf "$dst_skills/$name"
    mv "$staging" "$dst_skills/$name"
    mirrored=$((mirrored + 1))
  done
  echo "[full-pipeline-pair] mirrored $mirrored committed skill(s): config/skills/ -> .claude/skills/"
}

copy_calibrated_arm() {
  local fid="$1"
  local arm="$2"
  local src="$BENCH_ROOT/results/$REUSE_CALIBRATED_FROM/$fid/$arm"
  local dst="$BENCH_ROOT/results/$RUN_ID/$fid/$arm"
  if [ -e "$dst" ]; then
    [ -d "$dst" ] || { echo "reuse destination is not a directory: $dst" >&2; exit 1; }
    for required in result.json verify.json diff.patch; do
      [ -f "$dst/$required" ] || { echo "reuse destination incomplete $required: $dst" >&2; exit 1; }
    done
    echo "[full-pipeline-pair] reuse skip: $fid / $arm already exists in $RUN_ID"
    return 0
  fi
  [ -d "$src" ] || { echo "reuse source missing: $src" >&2; exit 1; }
  for required in result.json verify.json diff.patch; do
    [ -f "$src/$required" ] || { echo "reuse source missing $required: $src" >&2; exit 1; }
  done
  mkdir -p "$(dirname "$dst")"
  cp -R "$src" "$dst"
  echo "[full-pipeline-pair] reused $fid / $arm from $REUSE_CALIBRATED_FROM"
}

if [ -z "$REUSE_CALIBRATED_FROM" ]; then
  mirror_skills
fi

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
  --min-bare-headroom "$MIN_BARE_HEADROOM"
  --min-solo-headroom "$MIN_SOLO_HEADROOM"
  --min-fixtures "$MIN_FIXTURES"
  --out-json "$BENCH_ROOT/results/$RUN_ID/headroom-gate.json"
  --out-md "$BENCH_ROOT/results/$RUN_ID/headroom-gate.md"
)
if ! run_gate_with_report \
  "headroom gate" \
  "$BENCH_ROOT/results/$RUN_ID/headroom-gate.md" \
  python3 "$BENCH_ROOT/scripts/headroom-gate.py" "${headroom_args[@]}"; then
  echo "[full-pipeline-pair] headroom gate failed — pair arm not executed."
  exit 1
fi
echo "[full-pipeline-pair] headroom gate passed — executing $PAIR_ARM."

if [ -n "$REUSE_CALIBRATED_FROM" ]; then
  mirror_skills
fi

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
  --min-bare-headroom "$MIN_BARE_HEADROOM"
  --min-solo-headroom "$MIN_SOLO_HEADROOM"
  --min-fixtures "$MIN_FIXTURES"
  --min-pair-margin "$MIN_PAIR_MARGIN"
  --pair-arm "$PAIR_ARM"
  --require-hypothesis-trigger
  --out-json "$BENCH_ROOT/results/$RUN_ID/full-pipeline-pair-gate.json"
  --out-md "$BENCH_ROOT/results/$RUN_ID/full-pipeline-pair-gate.md"
)
[ -z "$MAX_PAIR_SOLO_WALL_RATIO" ] || pair_args+=(--max-pair-solo-wall-ratio "$MAX_PAIR_SOLO_WALL_RATIO")

if ! run_gate_with_report \
  "full-pipeline pair gate" \
  "$BENCH_ROOT/results/$RUN_ID/full-pipeline-pair-gate.md" \
  python3 "$BENCH_ROOT/scripts/full-pipeline-pair-gate.py" "${pair_args[@]}"; then
  echo "[full-pipeline-pair] pair gate failed — pair evidence rejected."
  exit 1
fi
echo "[full-pipeline-pair] pair gate passed — pair evidence accepted."
echo "[full-pipeline-pair] release audit: npx devlyn-cli benchmark audit --require-hypothesis-trigger --out-dir /tmp/devlyn-benchmark-audit-strict"
