#!/usr/bin/env bash
# Evaluate ceiling arm patches in disposable workspaces.
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage: ceiling-eval.sh --run-id <ID> --task <task> [--arm-attempt <A1|B1|...>]...
EOF
  exit "${1:-1}"
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CEILING_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

RUN_ID=""
TASK=""
ARM_ATTEMPTS=()

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
    --task) require_value "$1" "${2:-}"; TASK="$2"; shift 2;;
    --arm-attempt) require_value "$1" "${2:-}"; ARM_ATTEMPTS+=("$2"); shift 2;;
    -h|--help) usage 0;;
    *) echo "unknown arg: $1" >&2; usage 1;;
  esac
done

[ -n "$RUN_ID" ] && [ -n "$TASK" ] || usage 1
validate_task() {
  python3 - "$SCRIPT_DIR/ceiling-gate.py" "$CEILING_ROOT" "$TASK" <<'PY'
import runpy
import sys
from pathlib import Path

gate_path, ceiling_root, task = sys.argv[1:]
gate = runpy.run_path(gate_path)
valid_tasks = gate["task_ids"](None)
task_text = Path(ceiling_root) / "corpus" / task / "task.txt"
if task not in valid_tasks:
    print(f"invalid ceiling task: {task}", file=sys.stderr)
    print("valid tasks: " + ", ".join(valid_tasks), file=sys.stderr)
    raise SystemExit(1)
if not task_text.is_file():
    print(f"task text missing: {task_text}", file=sys.stderr)
    raise SystemExit(1)
PY
}
if ! validate_task; then
  usage 1
fi

TASK_DIR="$CEILING_ROOT/corpus/$TASK"
RESULT_TASK_DIR="$CEILING_ROOT/results/$RUN_ID/$TASK"
EXTERNAL_ROOT="$CEILING_ROOT/external"
mkdir -p "$EXTERNAL_ROOT/eval/$RUN_ID/$TASK"

if [ "${#ARM_ATTEMPTS[@]}" -eq 0 ]; then
  while IFS= read -r dir; do
    ARM_ATTEMPTS+=("$(basename "$dir")")
  done < <(find "$RESULT_TASK_DIR" -maxdepth 1 -type d -regex '.*/[ABC][0-9]+' 2>/dev/null | sort)
fi
[ "${#ARM_ATTEMPTS[@]}" -gt 0 ] || { echo "no arm attempts found for $RUN_ID/$TASK" >&2; exit 1; }

write_swe_objective() {
  local attempt="$1"
  local attempt_dir="$RESULT_TASK_DIR/$attempt"
  local eval_dir="$EXTERNAL_ROOT/eval/$RUN_ID/$TASK/$attempt"
  local instances_jsonl="$eval_dir/instances.jsonl"
  local predictions_jsonl="$eval_dir/predictions.jsonl"
  local report_id="$RUN_ID-$TASK-$attempt"
  rm -rf "$eval_dir"
  mkdir -p "$eval_dir"
  python3 - "$TASK_DIR/hidden/instance.json" "$instances_jsonl" "$attempt_dir/patch.diff" "$predictions_jsonl" <<'PY'
import json
import sys
from pathlib import Path
hidden, instances_out, patch_path, preds_out = map(Path, sys.argv[1:])
instance = json.loads(hidden.read_text(encoding="utf-8"))
instances_out.write_text(json.dumps(instance) + "\n", encoding="utf-8")
patch = patch_path.read_text(encoding="utf-8", errors="replace") if patch_path.exists() else ""
preds_out.write_text(json.dumps({
    "instance_id": instance["instance_id"],
    "model_name_or_path": "ceiling",
    "model_patch": patch,
}) + "\n", encoding="utf-8")
PY
  set +e
  (
    cd "$eval_dir"
    uvx --python 3.11 --from swebench python -m swebench.harness.run_evaluation \
      -d "$instances_jsonl" \
      -s test \
      -p "$predictions_jsonl" \
      -id "$report_id" \
      -n '' \
      --max_workers 1 \
      --cache_level env
  ) > "$eval_dir/harness.stdout.log" 2> "$eval_dir/harness.stderr.log"
  local harness_exit=$?
  set -e
  python3 - "$TASK_DIR/hidden/instance.json" "$eval_dir" "$attempt_dir/objective.json" "$harness_exit" <<'PY'
import json
import sys
from pathlib import Path

instance = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
eval_dir = Path(sys.argv[2])
out = Path(sys.argv[3])
harness_exit = int(sys.argv[4])
instance_id = instance["instance_id"]

def decode_test_list(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    return value or []

f2p_total = len(decode_test_list(instance.get("FAIL_TO_PASS")))
p2p_total = len(decode_test_list(instance.get("PASS_TO_PASS")))

def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

best_report = None
best_path = None
for path in sorted(eval_dir.rglob("*.json")):
    data = load_json(path)
    if not isinstance(data, dict):
        continue
    candidate = data.get(instance_id)
    if isinstance(candidate, dict):
        best_report = candidate
        best_path = path
        break
    if data.get("instance_id") == instance_id or "resolved" in data or "resolved_ids" in data:
        best_report = data
        best_path = path

resolved = False
f2p_passed = 0
p2p_regressions = p2p_total
if isinstance(best_report, dict):
    if "resolved_ids" in best_report:
        resolved = instance_id in (best_report.get("resolved_ids") or [])
    else:
        resolved = bool(best_report.get("resolved", False))
    statuses = best_report.get("tests_status") or best_report.get("test_status") or {}
    f2p = statuses.get("FAIL_TO_PASS") if isinstance(statuses, dict) else None
    p2p = statuses.get("PASS_TO_PASS") if isinstance(statuses, dict) else None
    if isinstance(f2p, dict):
        f2p_passed = len(f2p.get("success") or f2p.get("passed") or [])
        if not f2p_passed and resolved:
            f2p_passed = f2p_total
    elif resolved:
        f2p_passed = f2p_total
    if isinstance(p2p, dict):
        failures = p2p.get("failure") or p2p.get("failed") or []
        p2p_regressions = len(failures)
    elif resolved:
        p2p_regressions = 0

payload = {
    "task": out.parent.parent.name,
    "arm_attempt": out.parent.name,
    "resolved": resolved,
    "f2p_passed": f2p_passed,
    "f2p_total": f2p_total,
    "p2p_regressions": p2p_regressions,
    "p2p_total": p2p_total,
    "harness_exit": harness_exit,
    "report_path": str(best_path) if best_path else None,
}
out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
}

clone_fs1_base() {
  local worktree="$1"
  local base_json="$TASK_DIR/base.json"
  local repos_root="$EXTERNAL_ROOT/repos/fs1"
  local cache="$repos_root/schedule"
  # Bash 3.2 (macOS /bin/bash) has no mapfile — judge.sh iter-0019.4 precedent
  local repo sha
  repo="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["repo"])' "$base_json")"
  sha="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["sha"])' "$base_json")"
  mkdir -p "$repos_root"
  if [ ! -d "$cache/.git" ]; then
    rm -rf "$cache"
    git clone --quiet --no-checkout "$repo" "$cache"
  fi
  git -C "$cache" fetch --quiet --depth 1 origin "$sha" \
    || git -C "$cache" fetch --quiet origin "$sha"
  git -C "$cache" checkout --quiet "$sha"
  git -C "$cache" reset --hard --quiet
  git -C "$cache" clean -ffdqx
  rm -rf "$worktree"
  mkdir -p "$(dirname "$worktree")"
  git clone --quiet --no-hardlinks "$cache" "$worktree"
  git -C "$worktree" checkout --quiet "$sha"
  git -C "$worktree" reset --hard --quiet
  git -C "$worktree" clean -ffdqx
}

parse_pytest_counts() {
  python3 - "$1" <<'PY'
import json
import re
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace") if Path(sys.argv[1]).exists() else ""
counts = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}
for key in list(counts):
    singular = key[:-1] if key.endswith("s") else key
    match = re.search(rf"(\d+) (?:{key}|{singular})", text)
    if match:
        counts[key] = int(match.group(1))
print(json.dumps(counts))
PY
}

write_fs1_objective() {
  local attempt="$1"
  local attempt_dir="$RESULT_TASK_DIR/$attempt"
  local eval_dir="$EXTERNAL_ROOT/eval/$RUN_ID/$TASK/$attempt"
  local worktree="$eval_dir/worktree"
  rm -rf "$eval_dir"
  mkdir -p "$eval_dir"
  clone_fs1_base "$worktree"
  local apply_exit=0
  if [ -s "$attempt_dir/patch.diff" ]; then
    set +e
    git -C "$worktree" apply --whitespace=nowarn "$attempt_dir/patch.diff" > "$eval_dir/git-apply.stdout.log" 2> "$eval_dir/git-apply.stderr.log"
    apply_exit=$?
    set -e
  fi
  local hidden_exit=1
  local upstream_exit=1
  if [ "$apply_exit" -eq 0 ]; then
    cp "$TASK_DIR/hidden/test_max_runs_oracle.py" "$worktree/test_max_runs_oracle.py"
    set +e
    (cd "$worktree" && uv venv --python 3.11 .venv) > "$eval_dir/uv-venv.stdout.log" 2> "$eval_dir/uv-venv.stderr.log"
    local venv_exit=$?
    if [ "$venv_exit" -eq 0 ]; then
      # uv venvs ship without pip — install via uv against the venv python
      (cd "$worktree" && uv pip install -q --python .venv/bin/python pytest) > "$eval_dir/pip-install.stdout.log" 2> "$eval_dir/pip-install.stderr.log"
      local pip_exit=$?
      if [ "$pip_exit" -eq 0 ]; then
        (cd "$worktree" && .venv/bin/python -m pytest -q test_max_runs_oracle.py) > "$eval_dir/hidden-pytest.log" 2>&1
        hidden_exit=$?
        if [ -f "$worktree/test_schedule.py" ]; then
          (cd "$worktree" && .venv/bin/python -m pytest -q test_schedule.py) > "$eval_dir/upstream-pytest.log" 2>&1
          upstream_exit=$?
        else
          echo "missing test_schedule.py" > "$eval_dir/upstream-pytest.log"
          upstream_exit=1
        fi
      else
        echo "pip install failed" > "$eval_dir/hidden-pytest.log"
        echo "pip install failed" > "$eval_dir/upstream-pytest.log"
      fi
    else
      echo "uv venv failed" > "$eval_dir/hidden-pytest.log"
      echo "uv venv failed" > "$eval_dir/upstream-pytest.log"
    fi
    set -e
  else
    echo "git apply failed" > "$eval_dir/hidden-pytest.log"
    echo "git apply failed" > "$eval_dir/upstream-pytest.log"
  fi
  local hidden_counts
  local upstream_counts
  hidden_counts="$(parse_pytest_counts "$eval_dir/hidden-pytest.log")"
  upstream_counts="$(parse_pytest_counts "$eval_dir/upstream-pytest.log")"
  python3 - "$attempt_dir/objective.json" "$TASK" "$attempt" "$apply_exit" "$hidden_exit" "$upstream_exit" "$hidden_counts" "$upstream_counts" "$eval_dir" <<'PY'
import json
import sys
from pathlib import Path
out, task, attempt, apply_exit, hidden_exit, upstream_exit, hidden_counts, upstream_counts, eval_dir = sys.argv[1:]
hidden = json.loads(hidden_counts)
upstream = json.loads(upstream_counts)
hidden_total = hidden["passed"] + hidden["failed"] + hidden["errors"]
hidden_failures = hidden["failed"] + hidden["errors"]
payload = {
    "task": task,
    "arm_attempt": attempt,
    "resolved": int(apply_exit) == 0 and int(hidden_exit) == 0 and int(upstream_exit) == 0 and hidden_total > 0,
    "tests_passed": hidden["passed"],
    "tests_total": hidden_total,
    "hidden_test_failures": hidden_failures,
    "upstream_suite_pass": int(upstream_exit) == 0,
    "upstream_counts": upstream,
    "apply_exit": int(apply_exit),
    "hidden_pytest_exit": int(hidden_exit),
    "upstream_pytest_exit": int(upstream_exit),
    "report_path": str(Path(eval_dir) / "hidden-pytest.log"),
}
Path(out).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
}

for attempt in "${ARM_ATTEMPTS[@]}"; do
  [[ "$attempt" =~ ^[ABC][0-9]+$ ]] || { echo "invalid arm attempt: $attempt" >&2; exit 1; }
  [ -f "$RESULT_TASK_DIR/$attempt/patch.diff" ] || { echo "missing patch.diff: $RESULT_TASK_DIR/$attempt/patch.diff" >&2; exit 1; }
  if [[ "$TASK" == SW* ]]; then
    echo "[ceiling-eval] SWE $TASK $attempt"
    write_swe_objective "$attempt"
  else
    echo "[ceiling-eval] FS1 $attempt"
    write_fs1_objective "$attempt"
  fi
done
