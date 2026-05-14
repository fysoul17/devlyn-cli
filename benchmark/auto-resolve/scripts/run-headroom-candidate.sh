#!/usr/bin/env bash
# run-headroom-candidate.sh — calibrate candidate fixtures for L2/pair headroom.
#
# Runs only the arms needed by headroom-gate.py: bare and solo_claude.
# Then blind-judges those two arms and applies the mechanical gate.

set -euo pipefail

usage() {
  local code="${1:-1}"
  cat >&2 <<'EOF'
usage: run-headroom-candidate.sh [options] <fixture> [<fixture> ...]

Options:
  --run-id ID
  --bare-max N       (default: 60)
  --solo-max N       (default: 80)
  --min-bare-headroom N  (default: 5)
  --min-solo-headroom N  (default: 5)
  --min-fixtures N   (default: 2)
  --allow-rejected-fixtures
                    allow rejected/ceiling fixtures for diagnostics only
  --dry-run          validate args/fixtures and print replay command only
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
    --allow-rejected-fixtures) ALLOW_REJECTED_FIXTURES=1; shift;;
    --dry-run) DRY_RUN=1; shift;;
    -h|--help) usage 0;;
    [FS][0-9]*) FIXTURES+=("$1"); shift;;
    *) echo "unknown arg: $1" >&2; usage;;
  esac
done

for threshold in BARE_MAX SOLO_MAX MIN_BARE_HEADROOM MIN_SOLO_HEADROOM MIN_FIXTURES; do
  value="${!threshold}"
  case "$threshold" in
    BARE_MAX) flag="bare-max" ;;
    SOLO_MAX) flag="solo-max" ;;
    MIN_BARE_HEADROOM) flag="min-bare-headroom" ;;
    MIN_SOLO_HEADROOM) flag="min-solo-headroom" ;;
    MIN_FIXTURES) flag="min-fixtures" ;;
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

[ ${#FIXTURES[@]} -gt 0 ] || usage

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
  RUN_ID="${TS}-${SHA}-headroom"
fi

print_command() {
  local cmd
  if [ "${DEVLYN_BENCHMARK_CLI_SUBCOMMAND:-}" = "headroom" ]; then
    cmd=(npx devlyn-cli benchmark headroom --run-id "$RUN_ID")
  else
    cmd=(bash "$0" --run-id "$RUN_ID")
  fi
  cmd+=(--bare-max "$BARE_MAX")
  cmd+=(--solo-max "$SOLO_MAX")
  cmd+=(--min-bare-headroom "$MIN_BARE_HEADROOM")
  cmd+=(--min-solo-headroom "$MIN_SOLO_HEADROOM")
  cmd+=(--min-fixtures "$MIN_FIXTURES")
  [ "$ALLOW_REJECTED_FIXTURES" -eq 0 ] || cmd+=(--allow-rejected-fixtures)
  [ "$DRY_RUN" -eq 0 ] || cmd+=(--dry-run)
  cmd+=("${FIXTURES[@]}")
  printf 'Command: '
  printf '%q ' "${cmd[@]}"
  printf '\n'
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
echo "═══ Headroom Candidate Run ═══"
echo "Run-id:   $RUN_ID"
echo "Fixtures: ${FIXTURES[*]}"
echo "Arms:     bare solo_claude"
echo "Gate:     bare <= $BARE_MAX (headroom >= $MIN_BARE_HEADROOM), solo_claude <= $SOLO_MAX (headroom >= $MIN_SOLO_HEADROOM), baseline evidence-complete, min fixtures $MIN_FIXTURES"
[ "$DRY_RUN" -eq 0 ] || echo "Mode:     DRY RUN (no model/provider invocations)"
print_command
if [ ${#FIXTURES[@]} -lt "$MIN_FIXTURES" ]; then
  echo "Gate:     will FAIL set gate unless at least $MIN_FIXTURES fixtures are supplied"
fi
echo ""

validate_fixtures

if [ "$DRY_RUN" -eq 1 ] && [ "${#FIXTURES[@]}" -lt "$MIN_FIXTURES" ]; then
  echo "[headroom] DRY RUN failed — ${#FIXTURES[@]} fixture(s) supplied, --min-fixtures requires $MIN_FIXTURES." >&2
  exit 1
fi

if [ "$DRY_RUN" -eq 1 ]; then
  echo "[headroom] DRY RUN complete — fixtures resolved, no arms or judges executed."
  exit 0
fi

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
  --bare-max "$BARE_MAX" \
  --solo-max "$SOLO_MAX" \
  --min-bare-headroom "$MIN_BARE_HEADROOM" \
  --min-solo-headroom "$MIN_SOLO_HEADROOM" \
  --min-fixtures "$MIN_FIXTURES" \
  --out-json "$BENCH_ROOT/results/$RUN_ID/headroom-gate.json" \
  --out-md "$BENCH_ROOT/results/$RUN_ID/headroom-gate.md"
GATE_EXIT=$?
set -e

if [ -f "$BENCH_ROOT/results/$RUN_ID/headroom-gate.md" ]; then
  cat "$BENCH_ROOT/results/$RUN_ID/headroom-gate.md"
else
  echo "[headroom] headroom gate report missing: $BENCH_ROOT/results/$RUN_ID/headroom-gate.md" >&2
fi
if [ "$GATE_EXIT" -eq 0 ]; then
  echo "[headroom] headroom gate passed — candidate set accepted."
else
  echo "[headroom] headroom gate failed — candidate set rejected."
fi
exit "$GATE_EXIT"
