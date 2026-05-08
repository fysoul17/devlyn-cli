#!/usr/bin/env bash
# Prepare SWE-bench solver worktrees, run a direct solver, and collect patches.
set -euo pipefail

usage() {
  cat >&2 <<EOF
usage: $0 --instances-jsonl <path> --predictions-out <path>
          [--instance-id ID ...] [--limit N] [--model-name NAME]
          [--repos-root <path>] [--worktrees-root <path>]
          [--timeout-seconds N] [--copy-devlyn-context] [--resume]

Runs Claude Code directly against each selected SWE-bench instance without
reading gold patch/test_patch fields. Each worktree receives patch.diff plus
direct-transcript.txt and claude-direct-debug.log. At the end, patch.diff files
are collected into a SWE-bench predictions JSONL.
EOF
  exit "${1:-1}"
}

INSTANCES_JSONL=""
PREDICTIONS_OUT=""
MODEL_NAME="claude-direct"
REPOS_ROOT="benchmark/auto-resolve/external/swebench/repos-solver"
WORKTREES_ROOT="benchmark/auto-resolve/external/swebench/worktrees"
TIMEOUT_SECONDS=2400
COPY_DEVLYN_CONTEXT=0
RESUME=0
LIMIT=""
INSTANCE_IDS=()

while [ $# -gt 0 ]; do
  case "$1" in
    --instances-jsonl) INSTANCES_JSONL="$2"; shift 2;;
    --predictions-out) PREDICTIONS_OUT="$2"; shift 2;;
    --model-name) MODEL_NAME="$2"; shift 2;;
    --repos-root) REPOS_ROOT="$2"; shift 2;;
    --worktrees-root) WORKTREES_ROOT="$2"; shift 2;;
    --timeout-seconds) TIMEOUT_SECONDS="$2"; shift 2;;
    --copy-devlyn-context) COPY_DEVLYN_CONTEXT=1; shift;;
    --resume) RESUME=1; shift;;
    --limit) LIMIT="$2"; shift 2;;
    --instance-id) INSTANCE_IDS+=("$2"); shift 2;;
    -h|--help) usage 0;;
    *) echo "unknown arg: $1" >&2; usage 1;;
  esac
done

[ -n "$INSTANCES_JSONL" ] || usage 1
[ -n "$PREDICTIONS_OUT" ] || usage 1
[ -f "$INSTANCES_JSONL" ] || { echo "instances JSONL not found: $INSTANCES_JSONL" >&2; exit 1; }
case "$TIMEOUT_SECONDS" in ''|*[!0-9]*) echo "--timeout-seconds must be an integer" >&2; exit 1;; esac
[ "$TIMEOUT_SECONDS" -gt 0 ] || { echo "--timeout-seconds must be > 0" >&2; exit 1; }
if [ -n "$LIMIT" ]; then
  case "$LIMIT" in ''|*[!0-9]*) echo "--limit must be an integer" >&2; exit 1;; esac
  [ "$LIMIT" -gt 0 ] || { echo "--limit must be > 0" >&2; exit 1; }
fi
command -v claude >/dev/null 2>&1 || { echo "claude command not found" >&2; exit 1; }
mkdir -p "$REPOS_ROOT" "$WORKTREES_ROOT" "$(dirname "$PREDICTIONS_OUT")"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TMP_IDS="$(mktemp)"
TMP_SELECTED_INSTANCES="$(mktemp)"
trap 'rm -f "$TMP_IDS" "$TMP_SELECTED_INSTANCES"' EXIT

python3 - "$INSTANCES_JSONL" "$TMP_SELECTED_INSTANCES" "$LIMIT" "${INSTANCE_IDS[@]}" > "$TMP_IDS" <<'PY'
import json
import sys
from pathlib import Path

instances_path = Path(sys.argv[1])
selected_path = Path(sys.argv[2])
limit = int(sys.argv[3]) if sys.argv[3] else None
requested = sys.argv[4:]
requested_set = set(requested)
rows = []
with instances_path.open(encoding="utf8") as f:
    for line_no, line in enumerate(f, start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        instance_id = row.get("instance_id")
        if not isinstance(instance_id, str) or not instance_id:
            raise SystemExit(f"{instances_path}:{line_no}: missing instance_id")
        if requested_set and instance_id not in requested_set:
            continue
        rows.append(row)
        if limit is not None and len(rows) >= limit:
            break
if requested_set:
    missing = sorted(requested_set - {row["instance_id"] for row in rows})
    if missing:
        raise SystemExit(f"requested instance ids not found: {', '.join(missing)}")
for instance_id in rows:
    print(instance_id["instance_id"])
with selected_path.open("w", encoding="utf8") as f:
    for row in rows:
        f.write(json.dumps(row) + "\n")
PY

run_solver() {
  local worktree
  worktree="$(cd "$1" && pwd -P)"
  local timeout_seconds="$2"
  local prompt_file="$worktree/solve-prompt.txt"
  local transcript="$worktree/direct-transcript.txt"
  local debug_log="$worktree/claude-direct-debug.log"
  local timeout_flag="$worktree/.solver-timed-out"

  rm -f "$transcript" "$debug_log" "$timeout_flag"
  set +e
  set -m
  (
    cd "$worktree"
    exec claude \
      -p "$(cat "$prompt_file")" \
      --dangerously-skip-permissions \
      --effort xhigh \
      --strict-mcp-config \
      --mcp-config '{"mcpServers":{}}' \
      --debug-file "$debug_log" \
      </dev/null
  ) > "$transcript" 2>&1 &
  local child_pid=$!
  set +m

  (
    sleep "$timeout_seconds"
    if kill -0 "$child_pid" 2>/dev/null; then
      : > "$timeout_flag"
      kill -TERM -- "-$child_pid" 2>/dev/null
      sleep 5
      kill -KILL -- "-$child_pid" 2>/dev/null
    fi
  ) &
  local watchdog_pid=$!

  wait "$child_pid"
  local invoke_exit=$?
  kill -TERM "$watchdog_pid" 2>/dev/null || true
  wait "$watchdog_pid" 2>/dev/null || true

  if [ -f "$timeout_flag" ]; then
    rm -f "$timeout_flag"
    invoke_exit=124
  fi
  set -e
  return "$invoke_exit"
}

write_patch() {
  local worktree
  worktree="$(cd "$1" && pwd -P)"
  (
    cd "$worktree"
    git add -N -- . \
      ':(exclude).claude/**' \
      ':(exclude)CLAUDE.md' \
      ':(exclude)benchmark/**' \
      ':(exclude)docs/roadmap/phase-1/*.md' \
      ':(exclude)solve-prompt.txt' \
      ':(exclude)direct-transcript.txt' \
      ':(exclude)claude-direct-debug.log' \
      ':(exclude)latest' \
      ':(exclude).solver-timed-out' >/dev/null 2>&1 || true
    git diff --binary -- . \
      ':(exclude).claude/**' \
      ':(exclude)CLAUDE.md' \
      ':(exclude)benchmark/**' \
      ':(exclude)docs/roadmap/phase-1/*.md' \
      ':(exclude)solve-prompt.txt' \
      ':(exclude)direct-transcript.txt' \
      ':(exclude)claude-direct-debug.log' \
      ':(exclude)latest' \
      ':(exclude).solver-timed-out' > patch.diff
  )
}

while IFS= read -r instance_id; do
  [ -n "$instance_id" ] || continue
  worktree="$WORKTREES_ROOT/$instance_id"
  if [ "$RESUME" -eq 1 ] && [ -s "$worktree/patch.diff" ]; then
    echo "[swebench-solver] skip existing patch: $instance_id"
    continue
  fi

  echo "[swebench-solver] prepare: $instance_id"
  prepare_cmd=(
    python3 "$SCRIPT_DIR/prepare-swebench-solver-worktree.py"
    --instances-jsonl "$INSTANCES_JSONL"
    --instance-id "$instance_id"
    --repos-root "$REPOS_ROOT"
    --worktrees-root "$WORKTREES_ROOT"
  )
  if [ "$COPY_DEVLYN_CONTEXT" -eq 1 ]; then
    prepare_cmd+=(--copy-devlyn-context)
  fi
  "${prepare_cmd[@]}" > "$worktree.prepare.json"

  echo "[swebench-solver] solve: $instance_id"
  if run_solver "$worktree" "$TIMEOUT_SECONDS"; then
    invoke_exit=0
  else
    invoke_exit=$?
  fi
  write_patch "$worktree"
  python3 - "$worktree" "$instance_id" "$invoke_exit" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

worktree = Path(sys.argv[1])
instance_id = sys.argv[2]
invoke_exit = int(sys.argv[3])
patch = worktree / "patch.diff"
stat = subprocess.run(
    ["git", "-C", str(worktree), "diff", "--stat", "--", "."],
    text=True,
    capture_output=True,
    check=False,
)
report = {
    "instance_id": instance_id,
    "invoke_exit": invoke_exit,
    "patch_path": str(patch),
    "patch_bytes": patch.stat().st_size if patch.exists() else 0,
    "diff_stat": stat.stdout.strip(),
}
(worktree / "solver-result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
print(json.dumps(report, indent=2))
PY
done < "$TMP_IDS"

python3 "$SCRIPT_DIR/collect-swebench-predictions.py" \
  --patch-root "$WORKTREES_ROOT" \
  --instances-jsonl "$TMP_SELECTED_INSTANCES" \
  --model-name "$MODEL_NAME" \
  --out "$PREDICTIONS_OUT" \
  --allow-empty
