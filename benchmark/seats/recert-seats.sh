#!/usr/bin/env bash
# Re-certify bounded seat-fitness cells, then emit a seat matrix.
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage: recert-seats.sh --engines <csv> --run-prefix <ID> [--reps N] [--skip <suite,csv>] [--date YYYY-MM-DD]

Suites: violation, compliance, judge_quality, seat_matrix
EOF
  exit 1
}

require_value() {
  local flag="$1"
  local value="${2:-}"
  if [ -z "$value" ] || [[ "$value" == --* ]]; then
    echo "$flag requires a value" >&2
    exit 1
  fi
}

require_safe_id() {
  local label="$1"
  local value="$2"
  if [[ ! "$value" =~ ^[A-Za-z0-9_.-]+$ ]]; then
    echo "$label must match [A-Za-z0-9_.-]+: $value" >&2
    exit 1
  fi
}

ENGINES=""
RUN_PREFIX=""
REPS=4
SKIP=""
DATE="$(date -u +%F)"
while [ $# -gt 0 ]; do
  case "$1" in
    --engines) require_value "$1" "${2:-}"; ENGINES="$2"; shift 2;;
    --run-prefix) require_value "$1" "${2:-}"; RUN_PREFIX="$2"; shift 2;;
    --reps) require_value "$1" "${2:-}"; REPS="$2"; shift 2;;
    --skip) require_value "$1" "${2:-}"; SKIP="$2"; shift 2;;
    --date) require_value "$1" "${2:-}"; DATE="$2"; shift 2;;
    -h|--help) usage;;
    *) echo "unknown arg: $1" >&2; usage;;
  esac
done
[ -n "$ENGINES" ] && [ -n "$RUN_PREFIX" ] || usage
require_safe_id "--run-prefix" "$RUN_PREFIX"
case "$REPS" in ''|*[!0-9]*) echo "--reps must be an integer" >&2; exit 1;; esac
[ "$REPS" -gt 0 ] || { echo "--reps must be > 0" >&2; exit 1; }
[[ "$DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { echo "--date must be YYYY-MM-DD" >&2; exit 1; }

SEATS_ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SEATS_ROOT/../.." && pwd)"
PROBES_ROOT="$REPO_ROOT/benchmark/probes"
STATUS_DIR="$SEATS_ROOT/results/$RUN_PREFIX"
mkdir -p "$STATUS_DIR"
STATUS_JSON="$STATUS_DIR/recert-status.json"

skip_suite() {
  local suite="$1"
  [[ ",$SKIP," == *",$suite,"* ]]
}

record_status() {
  local failures_csv="$1"
  python3 - "$STATUS_JSON" "$RUN_PREFIX" "$DATE" "$ENGINES" "$SKIP" "$failures_csv" <<'PY'
import json
import pathlib
import sys

out, run_prefix, date, engines, skip, failures = sys.argv[1:7]
payload = {
    "run_prefix": run_prefix,
    "date": date,
    "engines": [e for e in engines.split(",") if e],
    "skip": [s for s in skip.split(",") if s],
    "failures": [f for f in failures.split(",") if f],
}
pathlib.Path(out).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
}

run_suite() {
  local suite="$1"
  shift
  if skip_suite "$suite"; then
    echo "[recert-seats] skip suite: $suite"
    return 0
  fi
  echo "[recert-seats] run suite: $suite"
  if "$@"; then
    echo "[recert-seats] PASS suite: $suite"
    return 0
  fi
  echo "[recert-seats] FAIL suite: $suite" >&2
  FAILURES+=("$suite")
  return 0
}

IFS=',' read -r -a ENGINE_LIST <<< "$ENGINES"
CLAUDE_MODELS=()
COMPLIANCE_ENGINES=()
JUDGES=()
for engine in "${ENGINE_LIST[@]}"; do
  [ -n "$engine" ] || continue
  case "$engine" in
    sonnet|opus)
      CLAUDE_MODELS+=("$engine")
      COMPLIANCE_ENGINES+=("$engine")
      [ "$engine" != "sonnet" ] || JUDGES+=("sonnet")
      ;;
    codex)
      COMPLIANCE_ENGINES+=("codex")
      JUDGES+=("codex")
      ;;
    *)
      echo "unsupported engine: $engine" >&2
      exit 1
      ;;
  esac
done

FAILURES=()

if [ ${#CLAUDE_MODELS[@]} -gt 0 ]; then
  IFS=','; MODELS_CSV="${CLAUDE_MODELS[*]}"; unset IFS
  run_suite violation \
    bash "$PROBES_ROOT/scripts/run-violation-matrix.sh" \
      --models "$MODELS_CSV" --reps "$REPS" --run-prefix "$RUN_PREFIX-violation"
fi

if [ ${#COMPLIANCE_ENGINES[@]} -gt 0 ]; then
  if ! skip_suite compliance; then
    for engine in "${COMPLIANCE_ENGINES[@]}"; do
      case "$engine" in
        codex)
          run_suite compliance \
            bash "$PROBES_ROOT/scripts/run-compliance-cell.sh" \
              --cli codex --size small --run-id "$RUN_PREFIX-codex-compliance"
          ;;
        sonnet|opus)
          run_suite compliance \
            env MODEL="$engine" bash "$PROBES_ROOT/scripts/run-compliance-cell.sh" \
              --cli claude --size small --run-id "$RUN_PREFIX-$engine-compliance"
          ;;
      esac
    done
  else
    echo "[recert-seats] skip suite: compliance"
  fi
fi

if [ ${#JUDGES[@]} -gt 0 ]; then
  IFS=','; JUDGES_CSV="${JUDGES[*]}"; unset IFS
  run_suite judge_quality \
    python3 "$PROBES_ROOT/judge-quality/run_judge_quality.py" \
      --reps 2 --judges "$JUDGES_CSV" --run-id "$RUN_PREFIX-judge-quality"
fi

CLAUDE_VERSION="$(claude --version 2>/dev/null | head -1 || true)"
CODEX_VERSION="$(codex --version 2>/dev/null | head -1 || true)"
ENGINE_VERSIONS="$(
  python3 - "$ENGINES" "$CLAUDE_VERSION" "$CODEX_VERSION" <<'PY'
import json
import os
import sys

engines, claude_version, codex_version = sys.argv[1:4]
out = {}
for engine in [e for e in engines.split(",") if e]:
    if engine in {"sonnet", "opus"}:
        out[engine] = f"{claude_version}/{engine}" if claude_version else engine
    elif engine == "codex":
        model = os.environ.get("CODEX_MODEL") or os.environ.get("OPENAI_MODEL")
        out[engine] = f"{codex_version}/{model}" if codex_version and model else (codex_version or "codex")
print(json.dumps(out, sort_keys=True))
PY
)"

run_suite seat_matrix \
  python3 "$SEATS_ROOT/seat-matrix.py" --date "$DATE" --engine-versions "$ENGINE_VERSIONS"

FAILURES_CSV=""
if [ ${#FAILURES[@]} -gt 0 ]; then
  IFS=','; FAILURES_CSV="${FAILURES[*]}"; unset IFS
fi
record_status "$FAILURES_CSV"
echo "[recert-seats] status: $STATUS_JSON"
if [ ${#FAILURES[@]} -gt 0 ]; then
  echo "[recert-seats] failed suites: $FAILURES_CSV" >&2
  exit 1
fi
