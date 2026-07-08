#!/usr/bin/env bash
# Sequential by design: single-machine wall-time comparability requires no hidden parallelism.
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage: run-ceiling-tranche.sh --run-id <ID> [--tasks csv] [--resume]
EOF
  exit "${1:-1}"
}

RUN_ID=""
TASKS_CSV=""
RESUME=0

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
    -h|--help) usage 0;;
    *) echo "unknown arg: $1" >&2; usage 1;;
  esac
done
[ -n "$RUN_ID" ] || usage 1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CEILING_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -n "$TASKS_CSV" ]; then
  IFS=',' read -r -a TASKS <<< "$TASKS_CSV"
else
  # Bash 3.2 (macOS /bin/bash) has no mapfile — judge.sh iter-0019.4 precedent
  TASKS=()
  while IFS= read -r task_line || [ -n "$task_line" ]; do
    TASKS+=("$task_line")
  done < <(python3 - "$SCRIPT_DIR/ceiling-gate.py" <<'PY'
import runpy
import sys

gate = runpy.run_path(sys.argv[1])
for task in gate["task_ids"](None):
    print(task)
PY
)
fi

timing_has_exit() {
  local path="$1"
  python3 - "$path" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
if not path.exists():
    raise SystemExit(1)
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    raise SystemExit(1)
raise SystemExit(0 if "invoke_exit" in data else 1)
PY
}

run_attempt() {
  local task="$1"
  local arm="$2"
  local attempt="$3"
  local timing="$CEILING_ROOT/results/$RUN_ID/$task/${arm}${attempt}/timing.json"
  if [ "$RESUME" -eq 1 ] && timing_has_exit "$timing"; then
    echo "[ceiling-tranche] skip existing ${task} ${arm}${attempt}: $timing"
    return
  fi
  bash "$SCRIPT_DIR/run-ceiling-arm.sh" --run-id "$RUN_ID" --task "$task" --arm "$arm" --attempt "$attempt"
}

successful_bounded() {
  local timing="$1"
  python3 - "$timing" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
if not path.exists():
    raise SystemExit(1)
data = json.loads(path.read_text(encoding="utf-8"))
raise SystemExit(0 if data.get("invoke_exit") == 0 and not data.get("timed_out") else 1)
PY
}

compute_n() {
  local task="$1"
  python3 - "$CEILING_ROOT/results/$RUN_ID/$task" <<'PY'
import json, math, sys
from pathlib import Path
root = Path(sys.argv[1])
a = json.loads((root / "A1/timing.json").read_text(encoding="utf-8"))
denom_attempt = None
for attempt in ("B1", "B2"):
    path = root / attempt / "timing.json"
    if not path.exists():
        continue
    b = json.loads(path.read_text(encoding="utf-8"))
    if b.get("invoke_exit") == 0 and not b.get("timed_out"):
        denom_attempt = attempt
        break
if denom_attempt is None:
    print("INVALID 0")
    raise SystemExit(0)
b = json.loads((root / denom_attempt / "timing.json").read_text(encoding="utf-8"))
ratio = max(float(a.get("elapsed_seconds", 0)), 1.0) / max(float(b.get("elapsed_seconds", 0)), 1.0)
n = max(1, min(3, int(math.floor(ratio + 0.5))))
print(f"{denom_attempt} {n}")
PY
}

eval_task_attempts() {
  local task="$1"
  local args=(--run-id "$RUN_ID" --task "$task")
  # BSD find -regex has no ERE '+' by default (macOS) — portable glob instead
  local dir
  for dir in "$CEILING_ROOT/results/$RUN_ID/$task"/[ABC][0-9]*; do
    [ -d "$dir" ] || continue
    args+=(--arm-attempt "$(basename "$dir")")
  done
  bash "$SCRIPT_DIR/ceiling-eval.sh" "${args[@]}"
}

for task in "${TASKS[@]}"; do
  [ -n "$task" ] || continue
  run_attempt "$task" A 1
  run_attempt "$task" B 1
  denom_and_n="$(compute_n "$task")"
  denom_attempt="${denom_and_n%% *}"
  n="${denom_and_n##* }"
  if [ "$denom_attempt" = "INVALID" ]; then
    run_attempt "$task" B 2
    denom_and_n="$(compute_n "$task")"
    denom_attempt="${denom_and_n%% *}"
    n="${denom_and_n##* }"
  fi
  if [ "$denom_attempt" = "INVALID" ]; then
    echo "[ceiling-tranche] $task INVALID-infra after B retry; skipping C/eval for this row"
    continue
  fi
  if [ "$denom_attempt" = "B1" ]; then
    start_b=2
    end_b="$n"
  else
    start_b=3
    end_b=$((n + 1))
  fi
  if [ "$start_b" -le "$end_b" ]; then
    for attempt in $(seq "$start_b" "$end_b"); do
      run_attempt "$task" B "$attempt"
    done
  fi
  for attempt in $(seq 1 "$n"); do
    run_attempt "$task" C "$attempt"
  done
  eval_task_attempts "$task"
done

gate_args=(--run-id "$RUN_ID")
[ -z "$TASKS_CSV" ] || gate_args+=(--tasks "$TASKS_CSV")
python3 "$SCRIPT_DIR/ceiling-gate.py" "${gate_args[@]}" --phase select

# Bash 3.2 (macOS /bin/bash) has no mapfile — judge.sh iter-0019.4 precedent
select_args=()
while IFS= read -r select_line || [ -n "$select_line" ]; do
  select_args+=("$select_line")
done < "$CEILING_ROOT/results/$RUN_ID/ceiling-select-args.txt"
if [ "${#select_args[@]}" -gt 0 ]; then
  python3 "$SCRIPT_DIR/ceiling-judge.py" --run-id "$RUN_ID" --judges sonnet,codex "${select_args[@]}"
fi
python3 "$SCRIPT_DIR/ceiling-gate.py" "${gate_args[@]}" --phase verdict
