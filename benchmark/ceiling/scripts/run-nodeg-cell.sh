#!/usr/bin/env bash
# Sequential A-only driver for the iter-0068 no-degradation control cell.
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage: run-nodeg-cell.sh --run-id <ID> [--tasks csv] [--resume] [--check-only]
EOF
  exit "${1:-1}"
}

RUN_ID=""
TASKS_CSV=""
RESUME=0
CHECK_ONLY=0

require_value() {
  local flag="$1"
  local value="${2:-}"
  if [ -z "$value" ] || [[ "$value" == --* ]]; then
    echo "$flag requires a value" >&2
    exit 1
  fi
}

while [ $# -gt 0 ]; do
  case "$1" in
    --run-id) require_value "$1" "${2:-}"; RUN_ID="$2"; shift 2;;
    --tasks) require_value "$1" "${2:-}"; TASKS_CSV="$2"; shift 2;;
    --resume) RESUME=1; shift;;
    --check-only) CHECK_ONLY=1; shift;;
    -h|--help) usage 0;;
    *) echo "unknown arg: $1" >&2; usage 1;;
  esac
done
[ -n "$RUN_ID" ] || usage 1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CEILING_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$CEILING_ROOT/../.." && pwd)"
if [ "${NODEG_SELFTEST:-0}" = 1 ]; then
  CEILING_ROOT="${NODEG_CEILING_ROOT:-$CEILING_ROOT}"
  REPO_ROOT="${NODEG_REPO_ROOT:-$REPO_ROOT}"
fi

common_args=(--run-id "$RUN_ID" --repo-root "$REPO_ROOT" --ceiling-root "$CEILING_ROOT")
[ -z "$TASKS_CSV" ] || common_args+=(--tasks "$TASKS_CSV")
[ "$RESUME" -eq 0 ] || common_args+=(--resume)

preflight_args=("${common_args[@]}")
[ "$CHECK_ONLY" -eq 1 ] || preflight_args+=(--initialize)
TASK_OUTPUT="$(python3 "$SCRIPT_DIR/nodeg-cell.py" preflight "${preflight_args[@]}")"
if [ "$CHECK_ONLY" -eq 1 ]; then
  printf '%s\n' "$TASK_OUTPUT"
  exit 0
fi

timing_has_exit() {
  python3 - "$1" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    raise SystemExit(1)
raise SystemExit(0 if "invoke_exit" in data else 1)
PY
}

while IFS= read -r task || [ -n "$task" ]; do
  [ -n "$task" ] || continue
  attempt_dir="$CEILING_ROOT/results/$RUN_ID/$task/A1"
  if [ "$RESUME" -eq 1 ] && timing_has_exit "$attempt_dir/timing.json"; then
    echo "[nodeg-cell] skip existing $task A1: $attempt_dir/timing.json"
  else
    if ! bash "$SCRIPT_DIR/run-ceiling-arm.sh" \
      --run-id "$RUN_ID" --task "$task" --arm A --attempt 1; then
      echo "[nodeg-cell] $task A1 runner returned nonzero; evaluating recorded patch" >&2
    fi
  fi
  if [ ! -f "$attempt_dir/objective.json" ] || [ "$RESUME" -eq 0 ]; then
    bash "$SCRIPT_DIR/ceiling-eval.sh" \
      --run-id "$RUN_ID" --task "$task" --arm-attempt A1
  fi
done <<< "$TASK_OUTPUT"

python3 "$SCRIPT_DIR/nodeg-cell.py" judge "${common_args[@]}"
python3 "$SCRIPT_DIR/nodeg-cell.py" verdict "${common_args[@]}"
