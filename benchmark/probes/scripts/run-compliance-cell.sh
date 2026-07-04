#!/usr/bin/env bash
# run-compliance-cell.sh — one CLI x one size, real /devlyn:resolve-equivalent
# headless invocation, then mechanical-only assertions (check-compliance-cell.py).
# No LLM judge. Reuses F1/F2's task.txt (in place, no copy) against a fresh
# copy of benchmark/auto-resolve/fixtures/test-repo/ as the base repo — same
# task material and base repo the golden suite already uses.
#
# Usage:
#   run-compliance-cell.sh --cli <claude|codex|omp> --size <small|medium> --run-id <ID>
set -euo pipefail

usage() {
  echo "usage: $0 --cli <claude|codex|omp> --size <small|medium> --run-id <ID>"
  exit 1
}

CLI=""; SIZE=""; RUN_ID=""
while [ $# -gt 0 ]; do
  case "$1" in
    --cli)     CLI="$2";    shift 2;;
    --size)    SIZE="$2";   shift 2;;
    --run-id)  RUN_ID="$2"; shift 2;;
    *) usage;;
  esac
done
[ -n "$CLI" ] && [ -n "$SIZE" ] && [ -n "$RUN_ID" ] || usage
case "$CLI" in claude|codex|omp) ;; *) usage;; esac
case "$SIZE" in small|medium) ;; *) usage;; esac

PROBES_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$PROBES_ROOT/../.." && pwd)"
BENCH_ROOT="$REPO_ROOT/benchmark/auto-resolve"

case "$SIZE" in
  small)  TASK_FILE="$BENCH_ROOT/fixtures/F1-cli-trivial-flag/task.txt" ;;
  medium) TASK_FILE="$BENCH_ROOT/fixtures/F2-cli-medium-subcommand/task.txt" ;;
esac
[ -f "$TASK_FILE" ] || { echo "task file missing: $TASK_FILE" >&2; exit 1; }

CELL="${CLI}-${SIZE}"
RESULT_DIR="$PROBES_ROOT/results/$RUN_ID/compliance/$CELL"
mkdir -p "$RESULT_DIR"

WORK_DIR="/tmp/probe-${RUN_ID}-compliance-${CELL}"
rm -rf "$WORK_DIR"
cp -R "$BENCH_ROOT/fixtures/test-repo" "$WORK_DIR"

if [ "$CLI" = "claude" ]; then
  mkdir -p "$WORK_DIR/.claude"
  cp -R "$REPO_ROOT/.claude/skills" "$WORK_DIR/.claude/skills"
  [ -f "$REPO_ROOT/CLAUDE.md" ] && cp "$REPO_ROOT/CLAUDE.md" "$WORK_DIR/CLAUDE.md"
fi

(cd "$WORK_DIR" && git init -q && git add -A \
   && git -c user.email=b@b -c user.name=b commit -q -m baseline)

# Explicitly invoke /devlyn:resolve free-form (iter-0040's confirmed method)
# rather than handing over the raw task text. Without this framing, every CLI
# just implements the task ad-hoc (bare-arm behavior) and .devlyn/ never
# exists regardless of CLI — that isn't a compliance finding, it's an
# unrelated probe-construction bug (caught in this iteration's own first
# run: all 3 CLIs failed identically at state_found before this fix).
PROMPT="Use the \`/devlyn:resolve\` skill to implement the following as a free-form goal, hands-free to a terminal verdict. Follow the skill's full phase-gated pipeline (PLAN, IMPLEMENT, BUILD_GATE, CLEANUP, VERIFY) to completion; do not skip phases or implement ad-hoc outside the skill.

$(cat "$TASK_FILE")"
T_START=$(date +%s)

case "$CLI" in
  claude)
    (cd "$WORK_DIR" \
       && CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 DISABLE_AUTOUPDATER=1 \
          exec claude -p "$PROMPT" \
            --dangerously-skip-permissions --effort xhigh \
            --setting-sources project,local --strict-mcp-config \
            --mcp-config '{"mcpServers":{}}' \
            --debug-file "$RESULT_DIR/claude-debug.log") \
      > "$RESULT_DIR/transcript.txt" 2>&1 || true
    ;;
  codex)
    (cd "$WORK_DIR" && exec codex exec -C "$WORK_DIR" -s workspace-write --json "$PROMPT") \
      > "$RESULT_DIR/transcript.txt" 2>&1 || true
    ;;
  omp)
    (cd "$WORK_DIR" && exec omp -p --cwd "$WORK_DIR" --auto-approve --mode json "$PROMPT") \
      > "$RESULT_DIR/transcript.txt" 2>&1 || true
    ;;
esac

T_END=$(date +%s)
echo "{\"cli\": \"$CLI\", \"size\": \"$SIZE\", \"elapsed_seconds\": $((T_END - T_START))}" \
  > "$RESULT_DIR/timing.json"

(cd "$WORK_DIR" && git add -A 2>/dev/null && git diff HEAD) \
  > "$RESULT_DIR/diff.patch" 2>&1 || true

rm -rf "$RESULT_DIR/devlyn-snapshot"
[ -d "$WORK_DIR/.devlyn" ] && cp -R "$WORK_DIR/.devlyn" "$RESULT_DIR/devlyn-snapshot"

python3 "$PROBES_ROOT/scripts/check-compliance-cell.py" \
  --workdir "$WORK_DIR" --cli "$CLI" --transcript "$RESULT_DIR/transcript.txt" \
  > "$RESULT_DIR/compliance-check.json" 2> "$RESULT_DIR/compliance-check.stderr.log" || true

cat "$RESULT_DIR/compliance-check.json"
echo "[run-compliance-cell] done: $RESULT_DIR"
