#!/usr/bin/env bash
# run-drift-bait-probe.sh — one drift-bait probe, single arm (claude), no
# judge. Seeds the probe's starter/ into a throwaway repo, invokes
# /devlyn:resolve-equivalent free-form claude headless on task.txt, captures
# the diff, then runs the probe's OWN hidden/verify.sh for a mechanical
# violations verdict. Works uniformly for probes reused in place from
# benchmark/instruction-sensitivity/fixtures/ (B2/B4/B5) and new probes under
# benchmark/probes/drift-bait/ — both follow the same starter/ +
# scope-allowlist.txt + hidden/verify.sh shape.
#
# Usage:
#   run-drift-bait-probe.sh --probe-dir <path> --run-id <ID>
#   MODEL=<alias|full-name> run-drift-bait-probe.sh --probe-dir <path> --run-id <ID>
#   TASK_LANG=ko run-drift-bait-probe.sh --probe-dir <path> --run-id <ID>
#     (reads task.<TASK_LANG>.txt instead of task.txt; unset = English, unchanged)
set -euo pipefail

usage() {
  echo "usage: $0 --probe-dir <path> --run-id <ID>  (optional: MODEL=<alias>, TASK_LANG=<code> env vars)"
  exit 1
}

PROBE_DIR=""; RUN_ID=""; MODEL="${MODEL:-}"; TASK_LANG="${TASK_LANG:-}"
while [ $# -gt 0 ]; do
  case "$1" in
    --probe-dir) PROBE_DIR="$2"; shift 2;;
    --run-id)    RUN_ID="$2";    shift 2;;
    *) usage;;
  esac
done
[ -n "$PROBE_DIR" ] && [ -n "$RUN_ID" ] || usage
[ -d "$PROBE_DIR" ] || { echo "probe-dir not found: $PROBE_DIR" >&2; exit 1; }

PROBE_ID="$(basename "$PROBE_DIR")"
TASK_FILE="$PROBE_DIR/task.txt"
[ -n "$TASK_LANG" ] && TASK_FILE="$PROBE_DIR/task.$TASK_LANG.txt"
STARTER_DIR="$PROBE_DIR/starter"
VERIFY_SH="$PROBE_DIR/hidden/verify.sh"
for f in "$TASK_FILE" "$STARTER_DIR" "$VERIFY_SH"; do
  [ -e "$f" ] || { echo "probe missing required path: $f" >&2; exit 1; }
done

PROBES_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$PROBES_ROOT/../.." && pwd)"

RESULT_DIR="$PROBES_ROOT/results/$RUN_ID/drift-bait/$PROBE_ID"
mkdir -p "$RESULT_DIR"

WORK_DIR="/tmp/probe-${RUN_ID}-${PROBE_ID}"
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
cp -R "$STARTER_DIR"/. "$WORK_DIR"/

mkdir -p "$WORK_DIR/.claude"
cp -R "$REPO_ROOT/.claude/skills" "$WORK_DIR/.claude/skills"
[ -f "$REPO_ROOT/CLAUDE.md" ] && cp "$REPO_ROOT/CLAUDE.md" "$WORK_DIR/CLAUDE.md"

(cd "$WORK_DIR" && git init -q && git add -A \
   && git -c user.email=b@b -c user.name=b commit -q -m baseline)
SCAFFOLD_SHA=$(cd "$WORK_DIR" && git rev-parse HEAD)

PROMPT="$(cat "$TASK_FILE")"
T_START=$(date +%s)

MODEL_ARGS=()
[ -n "$MODEL" ] && MODEL_ARGS=(--model "$MODEL")

(cd "$WORK_DIR" \
   && CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 DISABLE_AUTOUPDATER=1 \
      exec claude -p "$PROMPT" \
        --dangerously-skip-permissions --effort xhigh \
        --setting-sources project,local --strict-mcp-config \
        --mcp-config '{"mcpServers":{}}' \
        ${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"} \
        --debug-file "$RESULT_DIR/claude-debug.log") \
  > "$RESULT_DIR/transcript.txt" 2>&1 || true

T_END=$(date +%s)
echo "{\"probe\": \"$PROBE_ID\", \"model\": \"${MODEL:-default}\", \"task_lang\": \"${TASK_LANG:-en}\", \"elapsed_seconds\": $((T_END - T_START))}" \
  > "$RESULT_DIR/timing.json"

(cd "$WORK_DIR" && git add -A 2>/dev/null \
   && git diff "$SCAFFOLD_SHA") > "$RESULT_DIR/diff.patch" 2>&1 || true
(cd "$WORK_DIR" && git diff "$SCAFFOLD_SHA" --name-only) \
  > "$RESULT_DIR/changed-files.txt" 2>&1 || true

bash "$VERIFY_SH" "$RESULT_DIR" > "$RESULT_DIR/verdict.json" \
  2> "$RESULT_DIR/verify-sh.stderr.log" || true

cat "$RESULT_DIR/verdict.json"
echo "[run-drift-bait-probe] done: $RESULT_DIR"
