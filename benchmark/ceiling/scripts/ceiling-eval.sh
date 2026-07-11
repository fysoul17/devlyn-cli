#!/usr/bin/env bash
# Evaluate ceiling arm patches in disposable workspaces.
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage: ceiling-eval.sh --run-id <ID> --task <task> [--arm-attempt <A1|B1|...>]...
                       [--opaque-run-id <ID>] [--opaque-task-id <ID>]
                       [--attempt-dir <path>]
EOF
  exit "${1:-1}"
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CEILING_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

RUN_ID=""
TASK=""
ARM_ATTEMPTS=()
OPAQUE_RUN_ID=""
OPAQUE_TASK_ID=""
ATTEMPT_DIR_OVERRIDE=""

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
    --opaque-run-id) require_value "$1" "${2:-}"; OPAQUE_RUN_ID="$2"; shift 2;;
    --opaque-task-id) require_value "$1" "${2:-}"; OPAQUE_TASK_ID="$2"; shift 2;;
    --attempt-dir) require_value "$1" "${2:-}"; ATTEMPT_DIR_OVERRIDE="$2"; shift 2;;
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
EXTERNAL_ROOT="${CEILING_EXTERNAL_ROOT:-$HOME/.local/share/nx01}"
if [ -z "$OPAQUE_RUN_ID" ]; then
  OPAQUE_RUN_ID="r$(printf '%s' "$RUN_ID" | shasum -a 256 | cut -c1-12)"
  OPAQUE_TASK_ID="f$(printf '%s' "$TASK" | shasum -a 256 | cut -c1-12)"
fi
if [ -z "$OPAQUE_TASK_ID" ] || ! [[ "$OPAQUE_RUN_ID" =~ ^[a-z][a-z0-9]*$ && "$OPAQUE_TASK_ID" =~ ^[a-z][a-z0-9]*$ ]]; then
  echo "opaque IDs must be provided together and match ^[a-z][a-z0-9]*$" >&2
  exit 1
fi
mkdir -p "$EXTERNAL_ROOT/v/$OPAQUE_RUN_ID/$OPAQUE_TASK_ID"

if [ "${#ARM_ATTEMPTS[@]}" -eq 0 ]; then
  while IFS= read -r dir; do
    ARM_ATTEMPTS+=("$(basename "$dir")")
  done < <(find "$RESULT_TASK_DIR" -maxdepth 1 -type d -regex '.*/[ABC][0-9]+' 2>/dev/null | sort)
fi
[ "${#ARM_ATTEMPTS[@]}" -gt 0 ] || { echo "no arm attempts found for $RUN_ID/$TASK" >&2; exit 1; }
if [ -n "$ATTEMPT_DIR_OVERRIDE" ] && [ "${#ARM_ATTEMPTS[@]}" -ne 1 ]; then
  echo "--attempt-dir requires exactly one --arm-attempt" >&2
  exit 1
fi

write_swe_objective() {
  local attempt="$1"
  local attempt_dir="${ATTEMPT_DIR_OVERRIDE:-$RESULT_TASK_DIR/$attempt}"
  local eval_dir="$EXTERNAL_ROOT/v/$OPAQUE_RUN_ID/$OPAQUE_TASK_ID/$attempt"
  local instances_jsonl="$eval_dir/instances.jsonl"
  local predictions_jsonl="$eval_dir/predictions.jsonl"
  local report_id="$OPAQUE_RUN_ID-$OPAQUE_TASK_ID-$attempt"
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

clone_fs_base() {
  local worktree="$1"
  local base_json="$TASK_DIR/base.json"
  local repos_root="$EXTERNAL_ROOT/c/f"
  local cache="$repos_root/$OPAQUE_TASK_ID"
  # Bash 3.2 (macOS /bin/bash) has no mapfile — judge.sh iter-0019.4 precedent
  local repo sha
  repo="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["repo"])' "$base_json")"
  sha="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["sha"])' "$base_json")"
  case "$repo" in
    ./*|../*) repo="$(cd "$TASK_DIR/$(dirname "$repo")" && pwd -P)/$(basename "$repo")" ;;
  esac
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

write_fs_objective() {
  local attempt="$1"
  local attempt_dir="${ATTEMPT_DIR_OVERRIDE:-$RESULT_TASK_DIR/$attempt}"
  local eval_dir="$EXTERNAL_ROOT/v/$OPAQUE_RUN_ID/$OPAQUE_TASK_ID/$attempt"
  local worktree="$eval_dir/worktree"
  local oracle="$TASK_DIR/hidden/oracle.sh"
  [ -f "$oracle" ] || { echo "hidden oracle missing: $oracle" >&2; exit 1; }
  rm -rf "$eval_dir"
  mkdir -p "$eval_dir"
  clone_fs_base "$worktree"
  local neutral_args=(
    --workspace "$worktree"
    --report "$eval_dir/neutralization.json"
  )
  [[ "$TASK" == DR-* ]] && neutral_args+=(--seed-derived)
  local neutral_baseline_sha
  neutral_baseline_sha="$(python3 "$SCRIPT_DIR/neutralize-workspace.py" "${neutral_args[@]}")"
  if [ -f "$attempt_dir/isolation.json" ]; then
    python3 - "$attempt_dir/isolation.json" "$eval_dir/neutralization.json" <<'PY'
import json
import sys
from pathlib import Path

attempt = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["neutralization"]
evaluation = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
for key in ("seed_derived", "neutralization_diff_sha256", "neutral_baseline_sha"):
    if attempt.get(key) != evaluation.get(key):
        raise SystemExit(
            f"neutralization mismatch for {key}: "
            f"attempt={attempt.get(key)!r} evaluation={evaluation.get(key)!r}"
        )
PY
  fi
  local transported_patch="$eval_dir/transported.patch.diff"
  python3 "$SCRIPT_DIR/neutralize-workspace.py" \
    --transform-patch "$attempt_dir/patch.diff" "$transported_patch"
  local apply_exit=0
  if [ -s "$transported_patch" ]; then
    set +e
    git -C "$worktree" apply --whitespace=nowarn "$transported_patch" > "$eval_dir/git-apply.stdout.log" 2> "$eval_dir/git-apply.stderr.log"
    apply_exit=$?
    set -e
  fi
  local oracle_exit=1
  if [ "$apply_exit" -eq 0 ]; then
    set +e
    (cd "$worktree" && bash "$oracle") > "$eval_dir/oracle.log" 2>&1
    oracle_exit=$?
    set -e
  else
    echo "git apply failed" > "$eval_dir/oracle.log"
  fi
  python3 - "$attempt_dir/objective.json" "$TASK" "$attempt" "$apply_exit" "$oracle_exit" "$eval_dir" "$eval_dir/neutralization.json" "$neutral_baseline_sha" <<'PY'
import json
import sys
from pathlib import Path
out, task, attempt, apply_exit, oracle_exit, eval_dir, neutral_path, baseline_sha = sys.argv[1:]
passed = int(apply_exit) == 0 and int(oracle_exit) == 0
neutral = json.loads(Path(neutral_path).read_text(encoding="utf-8"))
payload = {
    "task": task,
    "arm_attempt": attempt,
    "resolved": passed,
    "tests_passed": int(passed),
    "tests_total": 1,
    "hidden_test_failures": int(not passed),
    "apply_exit": int(apply_exit),
    "oracle_exit": int(oracle_exit),
    "report_path": str(Path(eval_dir) / "oracle.log"),
    "neutralization_diff_sha256": neutral["neutralization_diff_sha256"],
    "neutral_baseline_sha": baseline_sha,
}
Path(out).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
}

for attempt in "${ARM_ATTEMPTS[@]}"; do
  [[ "$attempt" =~ ^[ABC][0-9]+$ ]] || { echo "invalid arm attempt: $attempt" >&2; exit 1; }
  attempt_dir="${ATTEMPT_DIR_OVERRIDE:-$RESULT_TASK_DIR/$attempt}"
  [ -f "$attempt_dir/patch.diff" ] || { echo "missing patch.diff: $attempt_dir/patch.diff" >&2; exit 1; }
  if [[ "$TASK" == SW* ]]; then
    echo "[ceiling-eval] SWE $TASK $attempt"
    write_swe_objective "$attempt"
  else
    echo "[ceiling-eval] FS $TASK $attempt"
    write_fs_objective "$attempt"
  fi
done
