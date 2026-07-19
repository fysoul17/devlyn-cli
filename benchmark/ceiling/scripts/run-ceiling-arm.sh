#!/usr/bin/env bash
# Run one pre-registered ceiling arm attempt in a fresh solver workspace.
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage: run-ceiling-arm.sh --task <ceiling-task>
                          --arm <A|B|C> --run-id <ID> --attempt <n>
                          [--opaque-run-id <ID>] [--opaque-task-id <ID>]
                          [--result-dir <path>]
                          [--f7-diagnostic-row]
                          [--timeout-seconds 3600]
EOF
  exit "${1:-1}"
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CEILING_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CLAUDE_ISOLATION="$SCRIPT_DIR/claude-isolation.py"
F7_CARRIER_GATE="$SCRIPT_DIR/f7-carrier-gate.py"
TERMINAL_CLAIM_CHECK="$SCRIPT_DIR/terminal-claim-check.py"
F7_TASK="DR-byte-preservation-f7-out-of-scope-trap"
DRAW_NON_DIAGNOSTIC_EXIT=86
DEPS_STAGING_BLOCKED_EXIT=78

write_deps_staging_receipt() {
  local receipt="$1"
  local status="$2"
  local failed_step="$3"
  local package_lock="$4"
  local node_bin="$5"
  local npm_version="$6"
  local npm_version_exit="$7"
  local npm_ci_exit="$8"
  local npm_ls_exit="$9"
  python3 - "$receipt" "$status" "$failed_step" "$package_lock" "$node_bin" \
    "$npm_version" "$npm_version_exit" "$npm_ci_exit" "$npm_ls_exit" <<'PY'
import json
import sys
from pathlib import Path

(
    receipt,
    status,
    failed_step,
    package_lock,
    node_bin,
    npm_version,
    npm_version_exit,
    npm_ci_exit,
    npm_ls_exit,
) = sys.argv[1:]

def exit_code(value):
    return int(value) if value else None

Path(receipt).write_text(json.dumps({
    "schema_version": 1,
    "status": status,
    "failed_step": failed_step or None,
    "package_lock": package_lock == "1",
    "node_bin": node_bin,
    "npm_version": npm_version or None,
    "exit_codes": {
        "npm_version": exit_code(npm_version_exit),
        "npm_ci": exit_code(npm_ci_exit),
        "npm_ls": exit_code(npm_ls_exit),
    },
}, indent=2) + "\n", encoding="utf-8")
PY
}

stage_a_arm_dependencies() {
  local worktree="$1"
  local requested_node="$2"
  local receipt="$RESULT_DIR/deps-staging.json"
  local node_bin node_bin_dir staging_path npm_version
  local npm_version_exit="" npm_ci_exit="" npm_ls_exit=""

  node_bin="$(command -v "$requested_node" 2>/dev/null || true)"
  if [ -z "$node_bin" ]; then
    write_deps_staging_receipt "$receipt" BLOCKED node-bin 1 "$requested_node" "" 127 "" ""
    echo "BLOCKED:deps-staging:node-bin requested=$requested_node receipt=$receipt" >&2
    return "$DEPS_STAGING_BLOCKED_EXIT"
  fi
  node_bin="$(python3 -c 'import pathlib,sys;print(pathlib.Path(sys.argv[1]).resolve())' "$node_bin")"

  if [ ! -f "$worktree/package-lock.json" ]; then
    write_deps_staging_receipt "$receipt" SKIPPED_NO_LOCKFILE "" 0 "$node_bin" "" "" "" ""
    return 0
  fi

  node_bin_dir="$(dirname "$node_bin")"
  staging_path="$node_bin_dir:$PATH"

  set +e
  npm_version="$(cd "$worktree" && PATH="$staging_path" npm --version)"
  npm_version_exit=$?
  set -e
  if [ "$npm_version_exit" -ne 0 ]; then
    write_deps_staging_receipt "$receipt" BLOCKED npm-version 1 "$node_bin" "$npm_version" \
      "$npm_version_exit" "" ""
    echo "BLOCKED:deps-staging:npm-version exit=$npm_version_exit receipt=$receipt" >&2
    return "$DEPS_STAGING_BLOCKED_EXIT"
  fi

  set +e
  (cd "$worktree" && PATH="$staging_path" npm ci)
  npm_ci_exit=$?
  set -e
  if [ "$npm_ci_exit" -ne 0 ]; then
    write_deps_staging_receipt "$receipt" BLOCKED npm-ci 1 "$node_bin" "$npm_version" \
      "$npm_version_exit" "$npm_ci_exit" ""
    echo "BLOCKED:deps-staging:npm-ci exit=$npm_ci_exit receipt=$receipt" >&2
    return "$DEPS_STAGING_BLOCKED_EXIT"
  fi

  set +e
  (cd "$worktree" && PATH="$staging_path" npm ls --omit=dev --depth=0)
  npm_ls_exit=$?
  set -e
  if [ "$npm_ls_exit" -ne 0 ]; then
    write_deps_staging_receipt "$receipt" BLOCKED npm-ls 1 "$node_bin" "$npm_version" \
      "$npm_version_exit" "$npm_ci_exit" "$npm_ls_exit"
    echo "BLOCKED:deps-staging:npm-ls exit=$npm_ls_exit receipt=$receipt" >&2
    return "$DEPS_STAGING_BLOCKED_EXIT"
  fi

  write_deps_staging_receipt "$receipt" PASS "" 1 "$node_bin" "$npm_version" \
    "$npm_version_exit" "$npm_ci_exit" "$npm_ls_exit"
}

TASK=""
ARM=""
RUN_ID=""
ATTEMPT=""
OPAQUE_RUN_ID=""
OPAQUE_TASK_ID=""
RESULT_DIR_OVERRIDE=""
TIMEOUT_SECONDS=3600
F7_DIAGNOSTIC_ROW=0

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
    --opaque-run-id) require_value "$1" "${2:-}"; OPAQUE_RUN_ID="$2"; shift 2;;
    --opaque-task-id) require_value "$1" "${2:-}"; OPAQUE_TASK_ID="$2"; shift 2;;
    --result-dir) require_value "$1" "${2:-}"; RESULT_DIR_OVERRIDE="$2"; shift 2;;
    --f7-diagnostic-row) F7_DIAGNOSTIC_ROW=1; shift;;
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
if [ "$F7_DIAGNOSTIC_ROW" -eq 1 ] && { [ "$ARM" != A ] || [ "$TASK" != "$F7_TASK" ]; }; then
  echo "--f7-diagnostic-row requires the F7 A arm" >&2
  exit 1
fi
case "$ATTEMPT" in ''|*[!0-9]*) echo "--attempt must be a positive integer" >&2; exit 1;; esac
[ "$ATTEMPT" -gt 0 ] || { echo "--attempt must be > 0" >&2; exit 1; }
case "$TIMEOUT_SECONDS" in ''|*[!0-9]*) echo "--timeout-seconds must be a positive integer" >&2; exit 1;; esac
[ "$TIMEOUT_SECONDS" -gt 0 ] || { echo "--timeout-seconds must be > 0" >&2; exit 1; }
if [ -n "$OPAQUE_RUN_ID$OPAQUE_TASK_ID" ]; then
  [ -n "$OPAQUE_RUN_ID" ] && [ -n "$OPAQUE_TASK_ID" ] || {
    echo "--opaque-run-id and --opaque-task-id must be provided together" >&2
    exit 1
  }
fi
for opaque_id in "$OPAQUE_RUN_ID" "$OPAQUE_TASK_ID"; do
  [ -z "$opaque_id" ] || [[ "$opaque_id" =~ ^[a-z][a-z0-9]*$ ]] || {
    echo "opaque IDs must match ^[a-z][a-z0-9]*$" >&2
    exit 1
  }
done

REPO_ROOT="$(cd "$CEILING_ROOT/../.." && pwd)"
AUTO_RESOLVE_SCRIPTS="$REPO_ROOT/benchmark/auto-resolve/scripts"
TASK_DIR="$CEILING_ROOT/corpus/$TASK"
TASK_TEXT_FILE="$TASK_DIR/task.txt"
EXTERNAL_ROOT="${CEILING_EXTERNAL_ROOT:-$HOME/.local/share/nx01}"
if [ -z "$OPAQUE_RUN_ID" ]; then
  OPAQUE_RUN_ID="r$(printf '%s' "$RUN_ID" | shasum -a 256 | cut -c1-12)"
  OPAQUE_TASK_ID="f$(printf '%s' "$TASK" | shasum -a 256 | cut -c1-12)"
fi
if [ -n "$RESULT_DIR_OVERRIDE" ]; then
  RESULT_DIR="$RESULT_DIR_OVERRIDE"
else
  RESULT_DIR="$CEILING_ROOT/results/$RUN_ID/$TASK/${ARM}${ATTEMPT}"
fi
mkdir -p "$RESULT_DIR" "$EXTERNAL_ROOT"

# Benchmark codex seat = gpt-5.6-terra (all arms), never the user's global
# sol default. sol is reserved for the three-way design/review team, not the
# measured arms (user directive 2026-07-10). Scope terra to this subprocess
# via a benchmark-owned CODEX_HOME so ~/.codex/config.toml (sol) is untouched:
#  - B/C arms pin `-m gpt-5.6-terra` directly (they --ignore-user-config, so
#    config.toml is not read; auth still resolves via CODEX_HOME).
#  - A-arm's nested resolve->codex IMPLEMENT loads $CODEX_HOME/config.toml
#    (workspace-write, not isolated) => terra.
REAL_HOME="$HOME"
CODEX_HOME_TERRA="$EXTERNAL_ROOT/d/$OPAQUE_RUN_ID/$OPAQUE_TASK_ID/${ARM}${ATTEMPT}"
rm -rf "$CODEX_HOME_TERRA"
mkdir -p "$CODEX_HOME_TERRA"
printf 'model = "gpt-5.6-terra"\nmodel_reasoning_effort = "xhigh"\n' > "$CODEX_HOME_TERRA/config.toml"
AUTH_SOURCE="${CEILING_TEST_AUTH_JSON:-$REAL_HOME/.codex/auth.json}"
[ -f "$AUTH_SOURCE" ] || { echo "Codex auth file missing: $AUTH_SOURCE" >&2; exit 1; }
cp "$AUTH_SOURCE" "$CODEX_HOME_TERRA/auth.json"
chmod 0600 "$CODEX_HOME_TERRA/auth.json"
export CODEX_HOME="$CODEX_HOME_TERRA"
BARE_HOME="$EXTERNAL_ROOT/h/$OPAQUE_RUN_ID/$OPAQUE_TASK_ID/${ARM}${ATTEMPT}"
rm -rf "$BARE_HOME"
mkdir -p "$BARE_HOME/t" "$BARE_HOME/n"
: > "$BARE_HOME/.npmrc"
CLAUDE_HOME_A="$EXTERNAL_ROOT/claude-homes/$OPAQUE_RUN_ID/$OPAQUE_TASK_ID/${ARM}${ATTEMPT}"
rm -rf "$CLAUDE_HOME_A"
mkdir -p "$CLAUDE_HOME_A"
CLAUDE_METADATA="$RESULT_DIR/claude-isolation.json"
REAL_USER_MEMORY="$REAL_HOME/.claude/CLAUDE.md"
cleanup_claude_credentials() {
  rm -f "$CLAUDE_HOME_A/.claude/.credentials.json"
}
trap cleanup_claude_credentials EXIT INT TERM

json_quote_task_prompt() {
  local worktree="$1"
  cp "$TASK_TEXT_FILE" "$worktree/.devlyn/goal.txt"
  printf '%s' '/devlyn:resolve --goal-file .devlyn/goal.txt --pair-verify'
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
  local worktrees_root="$EXTERNAL_ROOT/w/$OPAQUE_RUN_ID/$OPAQUE_TASK_ID/${ARM}${ATTEMPT}"
  local repos_root="$EXTERNAL_ROOT/c/s"
  local visible_jsonl="$EXTERNAL_ROOT/i/$OPAQUE_TASK_ID.jsonl"
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

prepare_fs_workspace() {
  local base_json="$TASK_DIR/base.json"
  local repos_root="$EXTERNAL_ROOT/c/f"
  local worktree_root="$EXTERNAL_ROOT/w/$OPAQUE_RUN_ID/$OPAQUE_TASK_ID/${ARM}${ATTEMPT}"
  local cache="$repos_root/$OPAQUE_TASK_ID"
  local worktree="$worktree_root/repo"
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
  # Arms may commit their work. Diff against the deterministic neutral baseline
  # so committed and uncommitted solver deltas are captured identically without
  # including the workspace identity rewrite itself.
  (
    cd "$worktree"
    git add -N -- . \
      ':(exclude).claude/**' \
      ':(exclude).devlyn/**' \
      ':(exclude)CLAUDE.md' \
      ':(exclude)AGENTS.md' \
      ':(exclude)docs/roadmap/phase-1/*.md' \
      ':(exclude)solve-prompt.txt' \
      ':(exclude).venv*/**' \
      ':(exclude)venv*/**' \
      ':(exclude)__pycache__/**' \
      ':(exclude)*.pyc' >/dev/null 2>&1 || true
    git diff --binary "$NEUTRAL_BASE_SHA" -- . \
      ':(exclude).claude/**' \
      ':(exclude).devlyn/**' \
      ':(exclude)CLAUDE.md' \
      ':(exclude)AGENTS.md' \
      ':(exclude)docs/roadmap/phase-1/*.md' \
      ':(exclude)solve-prompt.txt' \
      ':(exclude).venv*/**' \
      ':(exclude)venv*/**' \
      ':(exclude)__pycache__/**' \
      ':(exclude)*.pyc' > "$out"
  )
}

RUN_TIMED_OUT=0
RUN_DRAW_NON_DIAGNOSTIC=0

resolve_direct_claude() {
  python3 - "$CLAUDE_ISOLATION" "${CEILING_TEST_CLAUDE_BIN:-}" <<'PY'
import runpy
import sys

module = runpy.run_path(sys.argv[1])
print(module["resolve_direct_binary"]("claude", sys.argv[2] or None))
PY
}

resolve_direct_codex() {
  python3 - "${CEILING_TEST_CODEX_BIN:-}" <<'PY'
import os
import sys
from pathlib import Path

explicit = sys.argv[1]
if explicit:
    candidates = [Path(explicit)]
else:
    candidates = [Path(part) / "codex" for part in os.environ.get("PATH", "").split(os.pathsep) if part]
for candidate in candidates:
    if not candidate.is_file() or not os.access(candidate, os.X_OK):
        continue
    if ".superset" in candidate.parts:
        continue
    resolved = candidate.resolve()
    if resolved.name == "codex.js":
        package_root = resolved.parent.parent
        native = sorted(
            path
            for path in (package_root / "node_modules" / "@openai").glob(
                "codex-*/vendor/*/bin/codex*"
            )
            if path.is_file() and os.access(path, os.X_OK)
        )
        if native:
            resolved = native[0].resolve()
    print(resolved)
    raise SystemExit(0)
raise SystemExit("direct non-Superset Codex CLI not found")
PY
}

DIRECT_CLAUDE_BIN="$(resolve_direct_claude)"
DIRECT_CLAUDE_VERSION="$("$DIRECT_CLAUDE_BIN" --version 2>/dev/null)"
[ -n "$DIRECT_CLAUDE_VERSION" ] || { echo "direct Claude CLI version missing" >&2; exit 1; }
DIRECT_CODEX_BIN="$(resolve_direct_codex)"
DIRECT_CODEX_VERSION="$("$DIRECT_CODEX_BIN" --version 2>/dev/null)"
[ -n "$DIRECT_CODEX_VERSION" ] || { echo "direct Codex CLI version missing" >&2; exit 1; }
NODE_BIN="$(command -v node || true)"
[ -n "$NODE_BIN" ] || { echo "node binary missing" >&2; exit 1; }
NODE_BIN_DIR="$(cd "$(dirname "$NODE_BIN")" && pwd -P)"
DIRECT_CLAUDE_BIN_DIR="$(cd "$(dirname "$DIRECT_CLAUDE_BIN")" && pwd -P)"
DIRECT_CODEX_BIN_DIR="$(cd "$(dirname "$DIRECT_CODEX_BIN")" && pwd -P)"
FROZEN_PATH="$DIRECT_CLAUDE_BIN_DIR:$DIRECT_CODEX_BIN_DIR:$NODE_BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin"
[[ ":$FROZEN_PATH:" != *":.superset:"* && "$FROZEN_PATH" != *"/.superset/"* ]] || {
  echo "Superset path forbidden in frozen PATH: $FROZEN_PATH" >&2
  exit 1
}
FROZEN_ENV_KEYS="CODEX_HOME,GIT_CONFIG_GLOBAL,GIT_CONFIG_NOSYSTEM,HOME,LANG,LC_ALL,NPM_CONFIG_CACHE,NPM_CONFIG_USERCONFIG,PATH,TERM,TMPDIR,TZ"

CANARY_STDOUT="$RESULT_DIR/shell-canary.stdout"
CANARY_STDERR="$RESULT_DIR/shell-canary.stderr"
if [ "$ARM" = A ]; then
  if ! python3 "$CLAUDE_ISOLATION" launch \
    --mode shell-canary \
    --home "$CLAUDE_HOME_A" \
    --codex-home "$CODEX_HOME_TERRA" \
    --workdir "$RESULT_DIR" \
    --metadata-out "$CLAUDE_METADATA" \
    --user-memory-file "$REAL_USER_MEMORY" \
    > "$CANARY_STDOUT" 2> "$CANARY_STDERR"; then
    echo "shell startup canary failed" >&2
    exit 1
  fi
elif ! env -i \
  PATH="$FROZEN_PATH" \
  HOME="$BARE_HOME" \
  CODEX_HOME="$CODEX_HOME_TERRA" \
  TERM=dumb \
  LANG=en_US.UTF-8 \
  LC_ALL=en_US.UTF-8 \
  TZ=UTC \
  TMPDIR="$BARE_HOME/t" \
  GIT_CONFIG_NOSYSTEM=1 \
  GIT_CONFIG_GLOBAL=/dev/null \
  NPM_CONFIG_USERCONFIG="$BARE_HOME/.npmrc" \
  NPM_CONFIG_CACHE="$BARE_HOME/n" \
  /bin/zsh -lc 'printf isolation-ok' > "$CANARY_STDOUT" 2> "$CANARY_STDERR"; then
  echo "shell startup canary failed" >&2
  exit 1
fi
if [ "$(cat "$CANARY_STDOUT")" != "isolation-ok" ] || [ -s "$CANARY_STDERR" ]; then
  echo "shell startup canary produced unexpected output" >&2
  exit 1
fi

run_with_timeout() {
  local worktree="$1"
  local transcript="$2"
  local prompt="$3"
  local timeout_flag="$RESULT_DIR/.timed-out"
  local draw_probe="$RESULT_DIR/.f7-draw-probe.json"
  local draw_probe_stderr="$RESULT_DIR/.f7-draw-probe.stderr"
  local draw_trigger="$RESULT_DIR/.draw-non-diagnostic.trigger.json"
  local draw_monitor_error="$RESULT_DIR/.f7-draw-monitor-error"
  rm -f "$timeout_flag" "$draw_probe" "$draw_probe_stderr" "$draw_trigger" "$draw_monitor_error"
  : > "$transcript"
  set +e
  set -m
  case "$ARM" in
    A)
      (
        cd "$worktree" || exit 125
        printf '%s' "$prompt" > "$RESULT_DIR/claude-prompt.txt"
        exec python3 "$CLAUDE_ISOLATION" launch \
          --mode arm \
          --home "$CLAUDE_HOME_A" \
          --codex-home "$CODEX_HOME_TERRA" \
          --workdir "$worktree" \
          --prompt-file "$RESULT_DIR/claude-prompt.txt" \
          --debug-file "$RESULT_DIR/claude-debug.log" \
          --metadata-out "$CLAUDE_METADATA" \
          --user-memory-file "$REAL_USER_MEMORY"
      ) > "$transcript" 2>&1 &
      ;;
    B|C)
      (
        cd "$worktree" || exit 125
        exec env -i \
          PATH="$FROZEN_PATH" \
          HOME="$BARE_HOME" \
          CODEX_HOME="$CODEX_HOME_TERRA" \
          TERM=dumb \
          LANG=en_US.UTF-8 \
          LC_ALL=en_US.UTF-8 \
          TZ=UTC \
          TMPDIR="$BARE_HOME/t" \
          GIT_CONFIG_NOSYSTEM=1 \
          GIT_CONFIG_GLOBAL=/dev/null \
          NPM_CONFIG_USERCONFIG="$BARE_HOME/.npmrc" \
          NPM_CONFIG_CACHE="$BARE_HOME/n" \
          "$DIRECT_CODEX_BIN" exec \
          --ignore-user-config \
          --ignore-rules \
          --ephemeral \
          --skip-git-repo-check \
          --disable hooks \
          -C "$worktree" \
          -s workspace-write \
          -m gpt-5.6-terra \
          -c model_reasoning_effort=xhigh \
          "$prompt"
      ) > "$transcript" 2>&1 &
      ;;
  esac
  local child_pid=$!
  set +m
  terminate_child_group() {
    kill -TERM -- "-$child_pid" 2>/dev/null || kill -TERM "$child_pid" 2>/dev/null || true
    sleep 5
    kill -KILL -- "-$child_pid" 2>/dev/null || kill -KILL "$child_pid" 2>/dev/null || true
  }
  local draw_monitor_pid=""
  if [ "$F7_DIAGNOSTIC_ROW" -eq 1 ]; then
    (
      criteria_checked=0
      while kill -0 "$child_pid" 2>/dev/null; do
        if [ "$criteria_checked" -eq 0 ]; then
          python3 "$F7_CARRIER_GATE" "$worktree" --criteria-time-only \
            > "$draw_probe" 2> "$draw_probe_stderr"
          probe_exit=$?
          case "$probe_exit" in
            0)
              criteria_checked=1
              ;;
            75)
              sleep 1
              continue
              ;;
            "$DRAW_NON_DIAGNOSTIC_EXIT")
              mv "$draw_probe" "$draw_trigger"
              terminate_child_group
              exit 0
              ;;
            *)
              mv "$draw_probe_stderr" "$draw_monitor_error"
              terminate_child_group
              exit 0
              ;;
          esac
        fi
        python3 "$F7_CARRIER_GATE" "$worktree" --pre-sc-attribution-only \
          > "$draw_probe" 2> "$draw_probe_stderr"
        probe_exit=$?
        case "$probe_exit" in
          0)
            exit 0
            ;;
          75)
            sleep 1
            ;;
          "$DRAW_NON_DIAGNOSTIC_EXIT")
            mv "$draw_probe" "$draw_trigger"
            terminate_child_group
            exit 0
            ;;
          *)
            mv "$draw_probe_stderr" "$draw_monitor_error"
            terminate_child_group
            exit 0
            ;;
        esac
      done
    ) >/dev/null 2>&1 &
    draw_monitor_pid=$!
  fi
  # >/dev/null: the watchdog and its sleep child must not inherit this
  # script's stdout/stderr — a parent reading us via PIPE stays blocked until
  # the sleep exits, taxing every attempt with the full timeout.
  (
    watchdog_sleep_pid=""
    cancel_watchdog() {
      if [ -n "$watchdog_sleep_pid" ]; then
        kill -TERM "$watchdog_sleep_pid" 2>/dev/null || true
        wait "$watchdog_sleep_pid" 2>/dev/null || true
      fi
      exit 0
    }
    trap cancel_watchdog TERM INT
    sleep "$TIMEOUT_SECONDS" &
    watchdog_sleep_pid=$!
    wait "$watchdog_sleep_pid"
    watchdog_sleep_pid=""
    if kill -0 "$child_pid" 2>/dev/null; then
      : > "$timeout_flag"
      terminate_child_group
    fi
  ) >/dev/null 2>&1 &
  local watchdog_pid=$!
  wait "$child_pid"
  local invoke_exit=$?
  if [ -n "$draw_monitor_pid" ]; then
    kill -TERM "$draw_monitor_pid" 2>/dev/null || true
    wait "$draw_monitor_pid" 2>/dev/null || true
  fi
  kill -TERM "$watchdog_pid" 2>/dev/null || true
  wait "$watchdog_pid" 2>/dev/null || true
  if [ -f "$draw_trigger" ]; then
    if [ -e "$RESULT_DIR/devlyn-snapshot" ] || [ ! -d "$worktree/.devlyn" ]; then
      echo "draw snapshot destination exists or live .devlyn is missing" >&2
      invoke_exit=78
    elif ! cp -a "$worktree/.devlyn" "$RESULT_DIR/devlyn-snapshot"; then
      echo "draw .devlyn snapshot failed" >&2
      invoke_exit=78
    else
      mv "$draw_trigger" "$RESULT_DIR/draw-non-diagnostic.json"
      invoke_exit=$DRAW_NON_DIAGNOSTIC_EXIT
      RUN_DRAW_NON_DIAGNOSTIC=1
    fi
    RUN_TIMED_OUT=0
  elif [ -f "$draw_monitor_error" ]; then
    echo "F7 draw monitor failed: $(cat "$draw_monitor_error")" >&2
    mv "$draw_monitor_error" "$RESULT_DIR/draw-monitor-error.txt"
    invoke_exit=78
    RUN_TIMED_OUT=0
  elif [ -f "$timeout_flag" ]; then
    rm -f "$timeout_flag"
    invoke_exit=124
    RUN_TIMED_OUT=1
  else
    RUN_TIMED_OUT=0
    RUN_DRAW_NON_DIAGNOSTIC=0
  fi
  rm -f "$timeout_flag" "$draw_probe" "$draw_probe_stderr" "$draw_monitor_error"
  rm -f "$CLAUDE_HOME_A/.claude/.credentials.json"
  set -e
  return "$invoke_exit"
}

if [ -n "${CEILING_TEST_WORKTREE:-}" ]; then
  WORKTREE="$(cd "$CEILING_TEST_WORKTREE" && pwd -P)"
elif [[ "$TASK" == SW* ]]; then
  WORKTREE="$(prepare_swe_workspace)"
else
  WORKTREE="$(prepare_fs_workspace)"
fi
[ -d "$WORKTREE/.git" ] || { echo "workspace is not a git repo: $WORKTREE" >&2; exit 1; }

NEUTRALIZER_ARGS=(
  --workspace "$WORKTREE"
  --report "$RESULT_DIR/neutralization.json"
)
[[ "$TASK" == DR-* ]] && NEUTRALIZER_ARGS+=(--seed-derived)
NEUTRAL_BASE_SHA="$(python3 "$SCRIPT_DIR/neutralize-workspace.py" "${NEUTRALIZER_ARGS[@]}")"
[ -n "$NEUTRAL_BASE_SHA" ] || { echo "neutral baseline SHA missing" >&2; exit 1; }

if [ "$ARM" = A ]; then
  set +e
  stage_a_arm_dependencies "$WORKTREE" "${CEILING_TEST_NODE_BIN:-$NODE_BIN}"
  DEPS_STAGING_EXIT=$?
  set -e
  [ "$DEPS_STAGING_EXIT" -eq 0 ] || exit "$DEPS_STAGING_EXIT"
fi

case "$ARM" in
  A)
    stage_devlyn_context "$WORKTREE"
    [ -f "$WORKTREE/.claude/skills/devlyn:resolve/SKILL.md" ] || {
      echo "staged devlyn:resolve skill missing" >&2
      exit 1
    }
    PROMPT="$(json_quote_task_prompt "$WORKTREE")"
    ;;
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

python3 - "$RESULT_DIR/timing.json" "$TASK" "$ARM" "$ATTEMPT" "$ELAPSED_SECONDS" "$INVOKE_EXIT" "$RUN_TIMED_OUT" "$RUN_DRAW_NON_DIAGNOSTIC" "$WORKTREE" <<'PY'
import json
import sys
from pathlib import Path
out, task, arm, attempt, elapsed, invoke_exit, timed_out, draw_non_diagnostic, worktree = sys.argv[1:]
Path(out).write_text(json.dumps({
    "task": task,
    "arm": arm,
    "attempt": int(attempt),
    "elapsed_seconds": int(elapsed),
    "invoke_exit": int(invoke_exit),
    "timed_out": timed_out == "1",
    "draw_non_diagnostic": draw_non_diagnostic == "1",
    "worktree": worktree,
}, indent=2) + "\n", encoding="utf-8")
PY

if [ "$ARM" = A ]; then
  if [ ! -e "$RESULT_DIR/devlyn-snapshot" ] && [ -d "$WORKTREE/.devlyn" ]; then
    if ! cp -a "$WORKTREE/.devlyn" "$RESULT_DIR/devlyn-snapshot"; then
      echo "A-arm .devlyn snapshot failed" >&2
      exit 78
    fi
  fi
  if [ -d "$RESULT_DIR/devlyn-snapshot" ]; then
    if ! python3 "$SCRIPT_DIR/attribution.py" "$RESULT_DIR"; then
      echo "A-arm attribution artifact generation failed" >&2
      exit 78
    fi
  elif [ -e "$RESULT_DIR/devlyn-snapshot" ]; then
    echo "A-arm devlyn-snapshot exists but is not a directory" >&2
    exit 78
  fi
fi

ARM_EXIT="$INVOKE_EXIT"
if [ "$ARM" = A ]; then
  set +e
  TERMINAL_CLAIM_JSON="$(python3 "$TERMINAL_CLAIM_CHECK" "$WORKTREE")"
  TERMINAL_CLAIM_EXIT=$?
  set -e
  case "$TERMINAL_CLAIM_EXIT" in
    0)
      if [ -n "$TERMINAL_CLAIM_JSON" ]; then
        echo "terminal-claim check emitted output on a clean result" >&2
        [ "$ARM_EXIT" -ne 0 ] || ARM_EXIT=$DEPS_STAGING_BLOCKED_EXIT
      fi
      ;;
    79)
      if python3 - \
        "$RESULT_DIR/terminal-claim.json" \
        "$RESULT_DIR/timing.json" \
        "$TERMINAL_CLAIM_JSON" <<'PY'
import json
import sys
from pathlib import Path

receipt_path, timing_path, raw_receipt = sys.argv[1:]
receipt = json.loads(raw_receipt)
if not isinstance(receipt, dict) or set(receipt) != {"status", "phase", "reason", "run_id"}:
    raise SystemExit("invalid terminal-claim receipt")
status = receipt.get("status")
if status != "MALFORMED" and not (
    isinstance(status, str) and status.startswith("INCOMPLETE:")
):
    raise SystemExit("terminal-claim receipt is not incomplete")
Path(receipt_path).write_text(
    json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
)
timing_file = Path(timing_path)
timing = json.loads(timing_file.read_text(encoding="utf-8"))
timing["terminal_outcome"] = "FAILED-INCOMPLETE"
timing_file.write_text(json.dumps(timing, indent=2) + "\n", encoding="utf-8")
PY
      then
        [ "$ARM_EXIT" -ne 0 ] || ARM_EXIT=79
      else
        echo "terminal-claim receipt generation failed" >&2
        [ "$ARM_EXIT" -ne 0 ] || ARM_EXIT=$DEPS_STAGING_BLOCKED_EXIT
      fi
      ;;
    *)
      echo "terminal-claim check failed: exit=$TERMINAL_CLAIM_EXIT" >&2
      [ "$ARM_EXIT" -ne 0 ] || ARM_EXIT=$DEPS_STAGING_BLOCKED_EXIT
      ;;
  esac
fi

python3 - \
  "$RESULT_DIR/isolation.json" \
  "$RESULT_DIR/neutralization.json" \
  "$RESULT_DIR/transcript.txt" \
  "$WORKTREE" \
  "$EXTERNAL_ROOT" \
  "$RESULT_DIR" \
  "$BARE_HOME" \
  "$CODEX_HOME_TERRA" \
  "$CANARY_STDOUT" \
  "$CANARY_STDERR" \
  "$FROZEN_ENV_KEYS" \
  "$FROZEN_PATH" \
  "$DIRECT_CODEX_BIN" \
  "$DIRECT_CODEX_VERSION" \
  "$CODEX_HOME_TERRA/auth.json" \
  "$NEUTRAL_BASE_SHA" \
  "$RUN_ID" \
  "$TASK" \
  "$OPAQUE_RUN_ID" \
  "$OPAQUE_TASK_ID" \
  "$ARM" \
  "$CLAUDE_METADATA" \
  "$CLAUDE_HOME_A" \
  "$DIRECT_CLAUDE_BIN" \
  "$DIRECT_CLAUDE_VERSION" \
  "$REAL_USER_MEMORY" <<'PY'
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

(
    out_path,
    neutral_path,
    transcript_path,
    worktree,
    external_root,
    artifact_dir,
    bare_home,
    codex_home,
    canary_stdout_path,
    canary_stderr_path,
    env_keys_csv,
    frozen_path,
    codex_binary,
    codex_version,
    auth_path,
    neutral_baseline_sha,
    run_id,
    task,
    opaque_run_id,
    opaque_task_id,
    arm,
    claude_metadata_path,
    claude_home,
    claude_binary,
    claude_version,
    user_memory_path,
) = sys.argv[1:]

transcript_bytes = Path(transcript_path).read_bytes()
transcript = transcript_bytes.decode("utf-8", errors="replace")
literal_families = {
    "global-skills-path": ("/.agents/skills/", "/.codex/skills/"),
    "devlyn-skill-identity": ("devlyn:resolve", "devlyn:auto-resolve"),
    "devlyn-runtime": (
        "DEVLYN_SKILL_DIR",
        "DEVLYN_SHARED_DIR",
        ".devlyn/pipeline.state.json",
    ),
    "host-shell-startup-leak": (
        "/Users/aipalm/.zshenv",
        "/Users/aipalm/.zprofile",
        "/Users/aipalm/.zlogin",
    ),
    "benchmark-identity": (
        "devlyn-cli",
        "auto-resolve benchmark",
        "benchmark fixture",
        "bench-test-repo",
        "devlyn-ceiling-external",
        run_id,
        task,
    ),
}
if arm == "A":
    literal_families = {
        "host-shell-startup-leak": literal_families["host-shell-startup-leak"],
        "superset-wrapper": ("/.superset/", "SUPERSET_AGENT_ID"),
    }
hits = []
lowered = transcript.lower()
for family, markers in literal_families.items():
    matched = sorted({marker for marker in markers if marker and marker.lower() in lowered})
    if matched:
        hits.append({"family": family, "markers": matched})
regexes = {
    "benchmark-identity": (
        r"\bDR-[A-Za-z0-9._-]+",
        r"\bFS1(?:-[A-Za-z0-9._-]+)?",
        r"\biter\d+\b",
        r"(?:^|/)(?:gate|gold)(?:/|$)",
    )
}
for family, patterns in regexes.items():
    if arm == "A" and family == "benchmark-identity":
        continue
    matched = sorted(
        {pattern for pattern in patterns if re.search(pattern, transcript, re.IGNORECASE | re.MULTILINE)}
    )
    if matched:
        hits.append({"family": family, "patterns": matched})

user_memory = Path(user_memory_path)
if user_memory.is_file():
    memory_lines = sorted(
        {
            line.strip()
            for line in user_memory.read_text(encoding="utf-8", errors="replace").splitlines()
            if len(line.strip()) >= 24
        }
    )
    memory_hits = [line for line in memory_lines if line in transcript]
    if memory_hits:
        hits.append(
            {
                "family": "user-memory-leak",
                "marker_sha256": [
                    hashlib.sha256(line.encode()).hexdigest() for line in memory_hits
                ],
            }
        )

root = Path(external_root).resolve()
generated_paths = [
    Path(worktree).resolve(),
    Path(artifact_dir).resolve(),
    Path(bare_home).resolve(),
    Path(codex_home).resolve(),
]
if arm == "A":
    generated_paths.append(Path(claude_home).resolve())
forbidden_path = re.compile(
    r"(?:devlyn|ceiling|gate|iter|bench|eval|trap|fixture|arm|gold)", re.IGNORECASE
)
opaque_paths_pass = True
for path in generated_paths:
    try:
        relative = path.relative_to(root)
    except ValueError:
        opaque_paths_pass = False
        break
    if forbidden_path.search(str(relative)):
        opaque_paths_pass = False
        break

claude_metadata = None
if arm == "A" and Path(claude_metadata_path).is_file():
    claude_metadata = json.loads(Path(claude_metadata_path).read_text(encoding="utf-8"))
env_keys = (
    claude_metadata.get("claude_env_keys", [])
    if isinstance(claude_metadata, dict) and arm == "A"
    else sorted(env_keys_csv.split(","))
)
env_values = {
    "PATH": frozen_path,
    "HOME": bare_home,
    "CODEX_HOME": codex_home,
    "TERM": "dumb",
    "LANG": "en_US.UTF-8",
    "LC_ALL": "en_US.UTF-8",
    "TZ": "UTC",
    "TMPDIR": str(Path(bare_home) / "t"),
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "NPM_CONFIG_USERCONFIG": str(Path(bare_home) / ".npmrc"),
    "NPM_CONFIG_CACHE": str(Path(bare_home) / "n"),
}
if arm == "A":
    env_values.update(
        {
            "PATH": str(claude_metadata.get("frozen_path", "")),
            "HOME": claude_home,
            "CLAUDE_CONFIG_DIR": str(Path(claude_home) / ".claude"),
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            "DISABLE_AUTOUPDATER": "1",
            "TMPDIR": str(Path(claude_home) / "t"),
            "NPM_CONFIG_USERCONFIG": str(Path(claude_home) / ".npmrc"),
            "NPM_CONFIG_CACHE": str(Path(claude_home) / "n"),
        }
    )
forbidden_env = re.compile(
    r"devlyn|codex_companion|superset" if arm == "A" else r"claude|devlyn|codex_companion|superset",
    re.IGNORECASE,
)
canary_stdout = Path(canary_stdout_path).read_bytes()
canary_stderr = Path(canary_stderr_path).read_bytes()
neutral = json.loads(Path(neutral_path).read_text(encoding="utf-8"))
remotes = subprocess.run(
    ["git", "-C", worktree, "remote"],
    env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull},
    check=True,
    text=True,
    stdout=subprocess.PIPE,
).stdout.splitlines()
reflog_root = Path(worktree) / ".git" / "logs"
reflogs = sorted(
    str(path.relative_to(Path(worktree) / ".git"))
    for path in reflog_root.rglob("*")
    if path.is_file()
) if reflog_root.exists() else []
auth = Path(auth_path)
payload = {
    "schema_version": 2,
    "opaque_paths": {
        "external_root": str(root),
        "opaque_run_id": opaque_run_id,
        "opaque_task_id": opaque_task_id,
        "generated": [str(path) for path in generated_paths],
        "passed": opaque_paths_pass,
    },
    "environment": {
        "keys": env_keys,
        "keys_sha256": hashlib.sha256("\n".join(env_keys).encode()).hexdigest(),
        "forbidden_values_absent": not any(
            forbidden_env.search(value) for value in env_values.values()
        ),
    },
    "shell_startup_canary": {
        "passed": canary_stdout == b"isolation-ok" and not canary_stderr,
        "stdout_sha256": hashlib.sha256(canary_stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(canary_stderr).hexdigest(),
        "host_startup_files_absent": not any(
            marker.encode() in canary_stderr
            for marker in ("/.zshenv", "/.zprofile", "/.zlogin")
        ),
    },
    "neutralization": neutral,
    "git": {
        "neutral_baseline_sha": neutral_baseline_sha,
        "remotes": remotes,
        "reflogs": reflogs,
    },
    "direct_codex": {
        "path": str(Path(codex_binary).resolve()),
        "version": codex_version,
        "superset_wrapper": ".superset" in Path(codex_binary).parts,
    },
    "auth": {
        "path": str(auth.resolve()),
        "is_symlink": auth.is_symlink(),
        "mode": format(stat.S_IMODE(auth.stat().st_mode), "04o"),
    },
    "forbidden_transcript_scan": {
        "passed": not hits,
        "transcript_sha256": hashlib.sha256(transcript_bytes).hexdigest(),
        "hits": hits,
    },
}
if arm == "A":
    if not isinstance(claude_metadata, dict):
        hits.append({"family": "claude-isolation-metadata-missing"})
        claude_metadata = {}
    direct_claude = claude_metadata.get(
        "direct_claude",
        {
            "path": str(Path(claude_binary).resolve()),
            "sha256": hashlib.sha256(Path(claude_binary).read_bytes()).hexdigest(),
            "version": claude_version,
            "superset_wrapper": ".superset" in Path(claude_binary).parts,
        },
    )
    payload.update(
        {
            "direct_claude": direct_claude,
            "frozen_path": claude_metadata.get("frozen_path"),
            "shim_path": claude_metadata.get("shim_path"),
            "shim_target": claude_metadata.get("shim_target"),
            "shim_target_sha256": claude_metadata.get("shim_target_sha256"),
            "command_v_claude": claude_metadata.get("command_v_claude"),
            "home": claude_metadata.get("home", str(Path(claude_home).resolve())),
            "claude_config_dir": claude_metadata.get(
                "claude_config_dir", str(Path(claude_home).resolve() / ".claude")
            ),
            "claude_env_keys": claude_metadata.get("claude_env_keys", []),
            "claude_env_keys_sha256": claude_metadata.get("claude_env_keys_sha256"),
            "auth_mechanism": claude_metadata.get("auth_mechanism"),
            "credentials_seeded": claude_metadata.get("credentials_seeded", False),
        }
    )
    shim_path = Path(str(claude_metadata.get("shim_path", "")))
    shim_target = Path(str(claude_metadata.get("shim_target", "")))
    command_v = claude_metadata.get("command_v_claude") or {}
    frozen_parts = str(claude_metadata.get("frozen_path", "")).split(os.pathsep)
    try:
        shim_path.relative_to(Path(claude_home).resolve())
        shim_inside_home = True
    except ValueError:
        shim_inside_home = False
    shim_valid = (
        shim_inside_home
        and shim_path.is_symlink()
        and shim_path.resolve() == shim_target
        and bool(frozen_parts)
        and Path(frozen_parts[0]) == shim_path.parent
        and claude_metadata.get("shim_target_sha256") == direct_claude.get("sha256")
        and command_v.get("passed") is True
        and command_v.get("path") == str(shim_path)
        and command_v.get("resolved_path") == str(shim_target)
        and command_v.get("sha256") == claude_metadata.get("shim_target_sha256")
    )
    claude_invalid = (
        direct_claude.get("superset_wrapper") is not False
        or ".superset" in str(claude_metadata.get("frozen_path", ""))
        or not shim_valid
        or claude_metadata.get("credentials_seeded") is not True
        or not (Path(worktree) / ".claude/skills/devlyn:resolve/SKILL.md").is_file()
        or any(marker in transcript.casefold() for marker in ("not logged in", "authentication_error"))
    )
    if claude_invalid:
        hits.append({"family": "claude-isolation-contract"})
    payload["forbidden_transcript_scan"]["passed"] = not hits
    payload["forbidden_transcript_scan"]["hits"] = hits
Path(out_path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

echo "[ceiling-arm] ${TASK} ${ARM}${ATTEMPT} exit=${ARM_EXIT} timed_out=${RUN_TIMED_OUT} draw_non_diagnostic=${RUN_DRAW_NON_DIAGNOSTIC} result=${RESULT_DIR}"
if [ "$ARM" = A ]; then
  if [ "$INVOKE_EXIT" -ne 0 ]; then
    exit "$INVOKE_EXIT"
  fi
  python3 - "$RESULT_DIR/isolation.json" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
valid = (
    data.get("credentials_seeded") is True
    and data.get("direct_claude", {}).get("superset_wrapper") is False
    and data.get("command_v_claude", {}).get("passed") is True
    and data.get("command_v_claude", {}).get("sha256") == data.get("shim_target_sha256")
    and data.get("forbidden_transcript_scan", {}).get("passed") is True
    and data.get("shell_startup_canary", {}).get("passed") is True
)
raise SystemExit(0 if valid else 1)
PY
  if [ "$ARM_EXIT" -ne 0 ]; then
    exit "$ARM_EXIT"
  fi
fi
