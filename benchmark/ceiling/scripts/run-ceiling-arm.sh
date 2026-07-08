#!/usr/bin/env bash
# Run one pre-registered ceiling arm attempt in a fresh solver workspace.
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage: run-ceiling-arm.sh --task <ceiling-task>
                          --arm <A|B|C> --run-id <ID> --attempt <n>
                          [--timeout-seconds 3600]
EOF
  exit "${1:-1}"
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CEILING_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

TASK=""
ARM=""
RUN_ID=""
ATTEMPT=""
TIMEOUT_SECONDS=3600

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
    --task) require_value "$1" "${2:-}"; TASK="$2"; shift 2;;
    --arm) require_value "$1" "${2:-}"; ARM="$2"; shift 2;;
    --run-id) require_value "$1" "${2:-}"; RUN_ID="$2"; shift 2;;
    --attempt) require_value "$1" "${2:-}"; ATTEMPT="$2"; shift 2;;
    --timeout-seconds) require_value "$1" "${2:-}"; TIMEOUT_SECONDS="$2"; shift 2;;
    -h|--help) usage 0;;
    *) echo "unknown arg: $1" >&2; usage 1;;
  esac
done

[ -n "$TASK" ] && [ -n "$ARM" ] && [ -n "$RUN_ID" ] && [ -n "$ATTEMPT" ] || usage 1
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
case "$ARM" in A|B|C) ;; *) usage 1;; esac
case "$ATTEMPT" in ''|*[!0-9]*) echo "--attempt must be a positive integer" >&2; exit 1;; esac
[ "$ATTEMPT" -gt 0 ] || { echo "--attempt must be > 0" >&2; exit 1; }
case "$TIMEOUT_SECONDS" in ''|*[!0-9]*) echo "--timeout-seconds must be a positive integer" >&2; exit 1;; esac
[ "$TIMEOUT_SECONDS" -gt 0 ] || { echo "--timeout-seconds must be > 0" >&2; exit 1; }

REPO_ROOT="$(cd "$CEILING_ROOT/../.." && pwd)"
AUTO_RESOLVE_SCRIPTS="$REPO_ROOT/benchmark/auto-resolve/scripts"
TASK_DIR="$CEILING_ROOT/corpus/$TASK"
TASK_TEXT_FILE="$TASK_DIR/task.txt"
RESULT_DIR="$CEILING_ROOT/results/$RUN_ID/$TASK/${ARM}${ATTEMPT}"
EXTERNAL_ROOT="$CEILING_ROOT/external"
mkdir -p "$RESULT_DIR" "$EXTERNAL_ROOT"

json_quote_task_prompt() {
  python3 - "$TASK_TEXT_FILE" <<'PY'
import json
import sys
from pathlib import Path
task = Path(sys.argv[1]).read_text(encoding="utf-8").rstrip("\n")
print("/devlyn:resolve " + json.dumps(task) + " --pair-verify", end="")
PY
}

bare_prompt() {
  python3 - "$TASK_TEXT_FILE" <<'PY'
import sys
from pathlib import Path
task = Path(sys.argv[1]).read_text(encoding="utf-8").rstrip("\n")
sys.stdout.write("Fix or implement the following in this repository. Verify your work before finishing.\n\n" + task)
PY
}

copycat_prompt() {
  python3 - "$CEILING_ROOT/corpus/copycat-doc.md" "$TASK_TEXT_FILE" <<'PY'
import sys
from pathlib import Path
copycat = Path(sys.argv[1]).read_text(encoding="utf-8")
task = Path(sys.argv[2]).read_text(encoding="utf-8").rstrip("\n")
sys.stdout.write(
    copycat
    + "\n\nFollow the methodology above end-to-end yourself (plan, implement, build gate, cleanup, then a fresh-eyes verification pass) while completing this task:\n\n"
    + task
)
PY
}

visible_swebench_jsonl() {
  local out="$1"
  python3 - "$TASK" "$TASK_DIR/hidden/instance.json" "$TASK_TEXT_FILE" "$out" <<'PY'
import json
import sys
from pathlib import Path
task_id, hidden_path, task_path, out_path = sys.argv[1:]
hidden = json.loads(Path(hidden_path).read_text(encoding="utf-8"))
visible = {
    "instance_id": hidden["instance_id"],
    "repo": hidden["repo"],
    "base_commit": hidden["base_commit"],
    "problem_statement": Path(task_path).read_text(encoding="utf-8").rstrip("\n"),
}
Path(out_path).parent.mkdir(parents=True, exist_ok=True)
Path(out_path).write_text(json.dumps(visible) + "\n", encoding="utf-8")
PY
}

prepare_swe_workspace() {
  local worktrees_root="$EXTERNAL_ROOT/workspaces/$RUN_ID/$TASK/${ARM}${ATTEMPT}"
  local repos_root="$EXTERNAL_ROOT/repos/swebench"
  local visible_jsonl="$EXTERNAL_ROOT/visible-instances/$TASK.jsonl"
  local prepared_json="$RESULT_DIR/workspace.prepare.json"
  visible_swebench_jsonl "$visible_jsonl"
  rm -rf "$worktrees_root"
  mkdir -p "$worktrees_root" "$repos_root"
  python3 "$AUTO_RESOLVE_SCRIPTS/prepare-swebench-solver-worktree.py" \
    --instances-jsonl "$visible_jsonl" \
    --instance-id "$(python3 - "$visible_jsonl" <<'PY'
import json, sys
print(json.loads(open(sys.argv[1], encoding="utf-8").readline())["instance_id"])
PY
)" \
    --repos-root "$repos_root" \
    --worktrees-root "$worktrees_root" > "$prepared_json"
  python3 - "$prepared_json" <<'PY'
import json, sys
print(json.loads(open(sys.argv[1], encoding="utf-8").read())["worktree"])
PY
}

prepare_fs1_workspace() {
  local base_json="$TASK_DIR/base.json"
  local repos_root="$EXTERNAL_ROOT/repos/fs1"
  local worktree_root="$EXTERNAL_ROOT/workspaces/$RUN_ID/$TASK/${ARM}${ATTEMPT}"
  local cache="$repos_root/schedule"
  local worktree="$worktree_root/repo"
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
  rm -rf "$worktree_root"
  mkdir -p "$worktree_root"
  git clone --quiet --no-hardlinks "$cache" "$worktree"
  git -C "$worktree" checkout --quiet "$sha"
  git -C "$worktree" reset --hard --quiet
  git -C "$worktree" clean -ffdqx
  printf '%s\n' "$worktree"
}

stage_devlyn_context() {
  local worktree="$1"
  mkdir -p "$worktree/.claude" "$worktree/.devlyn"
  rm -rf "$worktree/.claude/skills"
  cp -R "$REPO_ROOT/config/skills" "$worktree/.claude/skills"
  [ -f "$REPO_ROOT/CLAUDE.md" ] && cp "$REPO_ROOT/CLAUDE.md" "$worktree/CLAUDE.md"
  [ -f "$REPO_ROOT/AGENTS.md" ] && cp "$REPO_ROOT/AGENTS.md" "$worktree/AGENTS.md"
  printf '{"executor":"codex"}\n' > "$worktree/.devlyn/engines.json"
}

write_patch() {
  local worktree="$1"
  local out="$2"
  # Arms may commit their work (observed: devlyn IMPLEMENT committed
  # "chore(pipeline): implement", making diff-vs-HEAD empty). Diff against
  # the frozen corpus base sha so committed and uncommitted deltas are
  # captured identically regardless of arm git behavior.
  local base_sha
  if [ -n "${CEILING_TEST_BASE_SHA:-}" ]; then
    # test seam only (CEILING_TEST_WORKTREE fake workspaces lack corpus shas)
    base_sha="$CEILING_TEST_BASE_SHA"
  elif [[ "$TASK" == SW* ]]; then
    base_sha="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["base_commit"])' "$TASK_DIR/hidden/instance.json")"
  else
    base_sha="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["sha"])' "$TASK_DIR/base.json")"
  fi
  (
    cd "$worktree"
    git add -N -- . \
      ':(exclude).claude/**' \
      ':(exclude).devlyn/**' \
      ':(exclude)CLAUDE.md' \
      ':(exclude)AGENTS.md' \
      ':(exclude)docs/roadmap/phase-1/*.md' \
      ':(exclude)solve-prompt.txt' \
      ':(exclude).venv/**' \
      ':(exclude)venv/**' \
      ':(exclude)__pycache__/**' \
      ':(exclude)*.pyc' >/dev/null 2>&1 || true
    git diff --binary "$base_sha" -- . \
      ':(exclude).claude/**' \
      ':(exclude).devlyn/**' \
      ':(exclude)CLAUDE.md' \
      ':(exclude)AGENTS.md' \
      ':(exclude)docs/roadmap/phase-1/*.md' \
      ':(exclude)solve-prompt.txt' \
      ':(exclude).venv/**' \
      ':(exclude)venv/**' \
      ':(exclude)__pycache__/**' \
      ':(exclude)*.pyc' > "$out"
  )
}

RUN_TIMED_OUT=0
run_with_timeout() {
  local worktree="$1"
  local transcript="$2"
  local prompt="$3"
  local timeout_flag="$RESULT_DIR/.timed-out"
  rm -f "$timeout_flag"
  : > "$transcript"
  set +e
  set -m
  case "$ARM" in
    A)
      (
        cd "$worktree" || exit 125
        CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 DISABLE_AUTOUPDATER=1 MODEL=sonnet \
          exec claude -p "$prompt" \
            --dangerously-skip-permissions --effort xhigh \
            --setting-sources project,local --strict-mcp-config \
            --mcp-config '{"mcpServers":{}}' \
            --model sonnet \
            --debug-file "$RESULT_DIR/claude-debug.log"
      ) > "$transcript" 2>&1 &
      ;;
    B|C)
      (
        cd "$worktree" || exit 125
        exec codex exec \
          --ignore-user-config \
          --ignore-rules \
          --ephemeral \
          --skip-git-repo-check \
          --disable codex_hooks \
          --disable hooks \
          -C "$worktree" \
          -s workspace-write \
          -c model_reasoning_effort=xhigh \
          "$prompt"
      ) > "$transcript" 2>&1 &
      ;;
  esac
  local child_pid=$!
  set +m
  (
    sleep "$TIMEOUT_SECONDS"
    if kill -0 "$child_pid" 2>/dev/null; then
      : > "$timeout_flag"
      kill -TERM -- "-$child_pid" 2>/dev/null || kill -TERM "$child_pid" 2>/dev/null || true
      sleep 5
      kill -KILL -- "-$child_pid" 2>/dev/null || kill -KILL "$child_pid" 2>/dev/null || true
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
    RUN_TIMED_OUT=1
  else
    RUN_TIMED_OUT=0
  fi
  set -e
  return "$invoke_exit"
}

if [ -n "${CEILING_TEST_WORKTREE:-}" ]; then
  WORKTREE="$(cd "$CEILING_TEST_WORKTREE" && pwd -P)"
elif [[ "$TASK" == SW* ]]; then
  WORKTREE="$(prepare_swe_workspace)"
else
  WORKTREE="$(prepare_fs1_workspace)"
fi
[ -d "$WORKTREE/.git" ] || { echo "workspace is not a git repo: $WORKTREE" >&2; exit 1; }

case "$ARM" in
  A) stage_devlyn_context "$WORKTREE"; PROMPT="$(json_quote_task_prompt)" ;;
  B) PROMPT="$(bare_prompt)" ;;
  C) PROMPT="$(copycat_prompt)" ;;
esac

START_SECONDS="$(date +%s)"
if run_with_timeout "$WORKTREE" "$RESULT_DIR/transcript.txt" "$PROMPT"; then
  INVOKE_EXIT=0
else
  INVOKE_EXIT=$?
fi
END_SECONDS="$(date +%s)"
ELAPSED_SECONDS=$((END_SECONDS - START_SECONDS))

write_patch "$WORKTREE" "$RESULT_DIR/patch.diff"

python3 - "$RESULT_DIR/timing.json" "$TASK" "$ARM" "$ATTEMPT" "$ELAPSED_SECONDS" "$INVOKE_EXIT" "$RUN_TIMED_OUT" "$WORKTREE" <<'PY'
import json
import sys
from pathlib import Path
out, task, arm, attempt, elapsed, invoke_exit, timed_out, worktree = sys.argv[1:]
Path(out).write_text(json.dumps({
    "task": task,
    "arm": arm,
    "attempt": int(attempt),
    "elapsed_seconds": int(elapsed),
    "invoke_exit": int(invoke_exit),
    "timed_out": timed_out == "1",
    "worktree": worktree,
}, indent=2) + "\n", encoding="utf-8")
PY

echo "[ceiling-arm] ${TASK} ${ARM}${ATTEMPT} exit=${INVOKE_EXIT} timed_out=${RUN_TIMED_OUT} result=${RESULT_DIR}"
