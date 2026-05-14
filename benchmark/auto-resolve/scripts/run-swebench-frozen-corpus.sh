#!/usr/bin/env bash
# Run a prepared SWE-bench frozen VERIFY corpus and gate the result set.
set -euo pipefail

usage() {
  cat >&2 <<EOF
usage: $0 --manifest <path> [--run-prefix ID] [--pair-mode forced|gated]
          [--min-runs N] [--out-json <path>] [--out-md <path>]
          [--max-pair-solo-wall-ratio N] [--timeout-seconds N]
          [--run-ids-out <path>] [--resume-completed-arms]
          [--prepare-only] [--gate-only-run-ids <path>]

Reads the manifest from prepare-swebench-frozen-corpus.py, runs each prepared
case through run-frozen-verify-pair.sh, then applies frozen-verify-gate.py to
the resulting run ids. --prepare-only validates patch application without
provider calls and skips the gate. --gate-only-run-ids reruns the gate over an
existing newline-delimited run-id file without invoking providers.
EOF
  exit "${1:-1}"
}

require_value() {
  local flag="$1"
  local value="${2:-}"
  if [ -z "$value" ] || [[ "$value" == --* ]]; then
    echo "$flag requires a value" >&2
    exit 1
  fi
}

MANIFEST=""
RUN_PREFIX=""
PAIR_MODE="gated"
MIN_RUNS=2
OUT_JSON=""
OUT_MD=""
MAX_PAIR_SOLO_WALL_RATIO=""
PREPARE_ONLY=0
GATE_ONLY_RUN_IDS=""
TIMEOUT_SECONDS=""
RUN_IDS_OUT=""
RESUME_COMPLETED_ARMS=0
while [ $# -gt 0 ]; do
  case "$1" in
    --manifest) require_value "$1" "${2:-}"; MANIFEST="$2"; shift 2;;
    --run-prefix) require_value "$1" "${2:-}"; RUN_PREFIX="$2"; shift 2;;
    --pair-mode) require_value "$1" "${2:-}"; PAIR_MODE="$2"; shift 2;;
    --min-runs) require_value "$1" "${2:-}"; MIN_RUNS="$2"; shift 2;;
    --out-json) require_value "$1" "${2:-}"; OUT_JSON="$2"; shift 2;;
    --out-md) require_value "$1" "${2:-}"; OUT_MD="$2"; shift 2;;
    --max-pair-solo-wall-ratio) require_value "$1" "${2:-}"; MAX_PAIR_SOLO_WALL_RATIO="$2"; shift 2;;
    --timeout-seconds) require_value "$1" "${2:-}"; TIMEOUT_SECONDS="$2"; shift 2;;
    --run-ids-out) require_value "$1" "${2:-}"; RUN_IDS_OUT="$2"; shift 2;;
    --resume-completed-arms) RESUME_COMPLETED_ARMS=1; shift;;
    --prepare-only) PREPARE_ONLY=1; shift;;
    --gate-only-run-ids) require_value "$1" "${2:-}"; GATE_ONLY_RUN_IDS="$2"; shift 2;;
    -h|--help) usage 0;;
    *) echo "unknown arg: $1" >&2; usage 1;;
  esac
done

[ -n "$MANIFEST" ] || usage 1
[ -f "$MANIFEST" ] || { echo "manifest not found: $MANIFEST" >&2; exit 1; }
[ "$PAIR_MODE" = "forced" ] || [ "$PAIR_MODE" = "gated" ] || { echo "--pair-mode must be forced|gated" >&2; exit 1; }
case "$MIN_RUNS" in ''|*[!0-9]*) echo "--min-runs must be an integer" >&2; exit 1;; esac
[ "$MIN_RUNS" -gt 0 ] || { echo "--min-runs must be > 0" >&2; exit 1; }
if [ -n "$TIMEOUT_SECONDS" ]; then
  case "$TIMEOUT_SECONDS" in ''|*[!0-9]*) echo "--timeout-seconds must be an integer" >&2; exit 1;; esac
  [ "$TIMEOUT_SECONDS" -gt 0 ] || { echo "--timeout-seconds must be > 0" >&2; exit 1; }
fi
if [ -n "$MAX_PAIR_SOLO_WALL_RATIO" ]; then
  python3 - "$MAX_PAIR_SOLO_WALL_RATIO" <<'PY' || { echo "--max-pair-solo-wall-ratio must be a positive number" >&2; exit 1; }
import sys
try:
    value = float(sys.argv[1])
except ValueError:
    raise SystemExit(1)
if value <= 0:
    raise SystemExit(1)
PY
fi
[ -z "$GATE_ONLY_RUN_IDS" ] || [ -f "$GATE_ONLY_RUN_IDS" ] || { echo "run ids file not found: $GATE_ONLY_RUN_IDS" >&2; exit 1; }
[ "$PREPARE_ONLY" -eq 0 ] || [ -z "$GATE_ONLY_RUN_IDS" ] || { echo "--prepare-only and --gate-only-run-ids are mutually exclusive" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BENCH_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if [ -z "$RUN_PREFIX" ]; then
  RUN_PREFIX="$(date -u +%Y%m%dT%H%M%SZ)-swebench-frozen"
fi

print_command() {
  local cmd=(bash "$0" --manifest "$MANIFEST" --run-prefix "$RUN_PREFIX")
  cmd+=(--pair-mode "$PAIR_MODE")
  cmd+=(--min-runs "$MIN_RUNS")
  [ -z "$OUT_JSON" ] || cmd+=(--out-json "$OUT_JSON")
  [ -z "$OUT_MD" ] || cmd+=(--out-md "$OUT_MD")
  [ -z "$MAX_PAIR_SOLO_WALL_RATIO" ] || cmd+=(--max-pair-solo-wall-ratio "$MAX_PAIR_SOLO_WALL_RATIO")
  [ -z "$TIMEOUT_SECONDS" ] || cmd+=(--timeout-seconds "$TIMEOUT_SECONDS")
  [ -z "$RUN_IDS_OUT" ] || cmd+=(--run-ids-out "$RUN_IDS_OUT")
  [ "$RESUME_COMPLETED_ARMS" -eq 0 ] || cmd+=(--resume-completed-arms)
  [ "$PREPARE_ONLY" -eq 0 ] || cmd+=(--prepare-only)
  [ -z "$GATE_ONLY_RUN_IDS" ] || cmd+=(--gate-only-run-ids "$GATE_ONLY_RUN_IDS")
  printf 'Command: '
  printf '%q ' "${cmd[@]}"
  printf '\n'
}

echo ""
echo "═══ SWE-bench Frozen VERIFY Corpus Run ═══"
echo "Run-prefix: $RUN_PREFIX"
echo "Pair mode:  $PAIR_MODE"
echo "Min runs:   $MIN_RUNS"
[ -z "$MAX_PAIR_SOLO_WALL_RATIO" ] || echo "Wall cap:   pair/solo <= ${MAX_PAIR_SOLO_WALL_RATIO}x"
print_command
echo ""

TMP_RUN_IDS="$(mktemp)"
trap 'rm -f "$TMP_RUN_IDS"' EXIT
ROW_FAILURES=0

python3 - "$MANIFEST" "$GATE_ONLY_RUN_IDS" "$SCRIPT_DIR" <<'PY'
import pathlib
import sys

sys.path.insert(0, sys.argv[3])
from pair_evidence_contract import loads_strict_json_object

manifest_path = pathlib.Path(sys.argv[1])
gate_only_run_ids = sys.argv[2]
try:
    manifest = loads_strict_json_object(manifest_path.read_text())
except ValueError as exc:
    if str(exc) == "top-level JSON value must be an object":
        raise SystemExit("manifest malformed: expected JSON object") from exc
    raise
if not isinstance(manifest, dict):
    raise SystemExit("manifest malformed: expected JSON object")
cases_root = manifest.get("cases_root")
if not isinstance(cases_root, str) or not cases_root.strip():
    raise SystemExit("manifest malformed: missing non-empty cases_root")
if gate_only_run_ids:
    raise SystemExit(0)
prepared = manifest.get("prepared")
if not isinstance(prepared, list) or not prepared:
    raise SystemExit("manifest malformed: prepared must be a non-empty array")
for index, row in enumerate(prepared, start=1):
    if not isinstance(row, dict):
        raise SystemExit(f"manifest malformed: prepared[{index}] expected JSON object")
    for key in ("instance_id", "case_dir", "repo_dir"):
        value = row.get(key)
        if not isinstance(value, str) or not value.strip():
            raise SystemExit(f"manifest malformed: prepared[{index}] missing non-empty {key}")
PY

if [ -n "$GATE_ONLY_RUN_IDS" ]; then
  python3 - "$GATE_ONLY_RUN_IDS" "$TMP_RUN_IDS" <<'PY'
import pathlib
import re
import sys

source = pathlib.Path(sys.argv[1])
dest = pathlib.Path(sys.argv[2])
safe = re.compile(r"^[A-Za-z0-9_.-]+$")
run_ids: list[str] = []
for line_no, line in enumerate(source.read_text(encoding="utf8").splitlines(), start=1):
    run_id = line.strip()
    if not run_id:
        raise SystemExit(f"run ids malformed: line {line_no} is empty")
    if not safe.match(run_id):
        raise SystemExit(f"run ids malformed: line {line_no} has unsafe run id")
    run_ids.append(run_id)
if not run_ids:
    raise SystemExit("run ids malformed: no run ids")
dest.write_text("\n".join(run_ids) + "\n", encoding="utf8")
PY
else
  while IFS=$'\t' read -r index instance_id cases_root repo_dir diff_path; do
    [ -n "$instance_id" ] || continue
    run_id="${RUN_PREFIX}-${index}-${instance_id}"
    safe_run_id="$(printf '%s' "$run_id" | tr -c 'A-Za-z0-9_.-' '-')"
    echo "[swebench-frozen-corpus] ${index}: ${instance_id} -> ${safe_run_id}"
    cmd=(
      bash "$SCRIPT_DIR/run-frozen-verify-pair.sh"
      --fixture "$instance_id"
      --fixtures-root "$cases_root"
      --base-repo "$repo_dir"
      --diff "$diff_path"
      --run-id "$safe_run_id"
      --pair-mode "$PAIR_MODE"
    )
    if [ -n "$TIMEOUT_SECONDS" ]; then
      cmd+=(--timeout-seconds "$TIMEOUT_SECONDS")
    fi
    if [ "$PREPARE_ONLY" -eq 1 ]; then
      cmd+=(--prepare-only)
    fi
    if [ "$RESUME_COMPLETED_ARMS" -eq 1 ]; then
      cmd+=(--resume-completed-arms)
    fi
    set +e
    "${cmd[@]}" </dev/null
    row_exit=$?
    set -e
    if [ "$row_exit" -ne 0 ]; then
      echo "[swebench-frozen-corpus] row failed: ${safe_run_id} exit=${row_exit}" >&2
      ROW_FAILURES=$((ROW_FAILURES + 1))
      python3 - "$BENCH_ROOT/results/$safe_run_id" "$instance_id" "$row_exit" <<'PY'
import json
import pathlib
import sys

run_root = pathlib.Path(sys.argv[1])
instance_id = sys.argv[2]
row_exit = int(sys.argv[3])
run_root.mkdir(parents=True, exist_ok=True)
for arm in ("solo", "pair"):
    arm_root = run_root / arm
    arm_root.mkdir(parents=True, exist_ok=True)
    input_path = arm_root / "input.md"
    if not input_path.exists():
        input_path.write_text(
            f"Use /devlyn:resolve --verify-only --spec docs/roadmap/phase-1/{instance_id}.md.\n",
            encoding="utf8",
        )
compare_path = run_root / "compare.json"
if not compare_path.exists():
    compare_path.write_text(
        json.dumps(
            {
                "solo": {"invoke_exit": row_exit, "timed_out": False},
                "pair": {"invoke_exit": row_exit, "timed_out": False, "pair_mode": False},
                "comparison": {
                    "pair_trigger_missed": False,
                    "pair_verdict_lift": False,
                    "pair_internal_verdict_lift": False,
                    "row_failed_before_compare": True,
                    "row_exit": row_exit,
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf8",
    )
PY
    fi
    printf '%s\n' "$safe_run_id" >> "$TMP_RUN_IDS"
  done < <(python3 - "$MANIFEST" "$SCRIPT_DIR" <<'PY'
import pathlib, sys

sys.path.insert(0, sys.argv[2])
from pair_evidence_contract import loads_strict_json_object

manifest = loads_strict_json_object(pathlib.Path(sys.argv[1]).read_text())
for index, row in enumerate(manifest["prepared"], start=1):
    instance_id = row["instance_id"]
    case_dir = pathlib.Path(row["case_dir"])
    repo_dir = pathlib.Path(row["repo_dir"])
    print("\t".join([
        str(index),
        instance_id,
        str(case_dir.parent),
        str(repo_dir),
        str(case_dir / "model.patch"),
    ]))
PY
)
fi

if [ -n "$RUN_IDS_OUT" ]; then
  mkdir -p "$(dirname "$RUN_IDS_OUT")"
  cp "$TMP_RUN_IDS" "$RUN_IDS_OUT"
fi

if [ "$PREPARE_ONLY" -eq 1 ]; then
  echo "[swebench-frozen-corpus] prepare-only complete; gate skipped"
  if [ "$ROW_FAILURES" -gt 0 ]; then
    echo "[swebench-frozen-corpus] row failures: $ROW_FAILURES" >&2
    exit 1
  fi
  exit 0
fi

run_count="$(wc -l < "$TMP_RUN_IDS" | tr -d ' ')"
[ "$run_count" -gt 0 ] || { echo "manifest prepared no runs" >&2; exit 1; }

fixtures_root="$(python3 - "$MANIFEST" "$SCRIPT_DIR" <<'PY'
import pathlib, sys

sys.path.insert(0, sys.argv[2])
from pair_evidence_contract import loads_strict_json_object

manifest = loads_strict_json_object(pathlib.Path(sys.argv[1]).read_text())
print(manifest["cases_root"])
PY
)"
gate_args=(
  python3 "$SCRIPT_DIR/frozen-verify-gate.py"
  --fixtures-root "$fixtures_root"
  --min-runs "$MIN_RUNS"
  --require-hypothesis-trigger
)
[ -z "$OUT_JSON" ] || gate_args+=(--out-json "$OUT_JSON")
[ -z "$OUT_MD" ] || gate_args+=(--out-md "$OUT_MD")
[ -z "$MAX_PAIR_SOLO_WALL_RATIO" ] || gate_args+=(--max-pair-solo-wall-ratio "$MAX_PAIR_SOLO_WALL_RATIO")
while IFS= read -r run_id; do
  gate_args+=(--run-id "$run_id")
done < "$TMP_RUN_IDS"

"${gate_args[@]}"
