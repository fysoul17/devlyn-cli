#!/usr/bin/env bash
# run-drift-bait-probe-resolve.sh — iter-0046 verification instrument.
#
# run-drift-bait-probe.sh deliberately hands the probe's task.txt to `claude
# -p` BARE (no /devlyn:resolve framing) — that IS the measurement instrument
# iter-0042/0045 used to show the drift classes persist across model tiers,
# and it must stay bare so future bare-vs-pipeline comparisons stay valid.
# It is not edited here.
#
# This sibling script answers a different question: does /devlyn:resolve's
# new PLAN-declared-surface + BUILD_GATE mechanical gate (iter-0046) catch a
# scope leak when the SAME starter/ tree is run THROUGH the phase-gated
# pipeline instead of bare? Reuses the probe's starter/ tree unmodified
# (fixture untouched) but frames the invocation exactly like
# run-compliance-cell.sh's proven "/devlyn:resolve ... follow the full
# phase-gated pipeline" prompt, and additionally captures the post-run
# .devlyn snapshot so BUILD_GATE findings can be inspected.
#
# Usage:
#   run-drift-bait-probe-resolve.sh --probe-dir <path> --run-id <ID> [--task-file <path>] [--label <name>]
#   MODEL=<alias|full-name> run-drift-bait-probe-resolve.sh --probe-dir <path> --run-id <ID>
#
# --task-file overrides the probe's own task.txt with an ad-hoc task while
# still seeding the probe's starter/ tree (used for negative-control runs
# that must NOT touch the probe's own task.txt).
set -euo pipefail

usage() {
  echo "usage: $0 --probe-dir <path> --run-id <ID> [--task-file <path>] [--label <name>] (optional: MODEL=<alias> env var)"
  exit 1
}

PROBE_DIR=""; RUN_ID=""; MODEL="${MODEL:-}"; TASK_FILE_OVERRIDE=""; LABEL=""
while [ $# -gt 0 ]; do
  case "$1" in
    --probe-dir) PROBE_DIR="$2"; shift 2;;
    --run-id)    RUN_ID="$2";    shift 2;;
    --task-file) TASK_FILE_OVERRIDE="$2"; shift 2;;
    --label)     LABEL="$2";     shift 2;;
    *) usage;;
  esac
done
[ -n "$PROBE_DIR" ] && [ -n "$RUN_ID" ] || usage
[ -d "$PROBE_DIR" ] || { echo "probe-dir not found: $PROBE_DIR" >&2; exit 1; }

PROBE_ID="$(basename "$PROBE_DIR")"
[ -n "$LABEL" ] || LABEL="$PROBE_ID"
TASK_FILE="${TASK_FILE_OVERRIDE:-$PROBE_DIR/task.txt}"
STARTER_DIR="$PROBE_DIR/starter"
for f in "$TASK_FILE" "$STARTER_DIR"; do
  [ -e "$f" ] || { echo "missing required path: $f" >&2; exit 1; }
done

PROBES_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$PROBES_ROOT/../.." && pwd)"

RESULT_DIR="$PROBES_ROOT/results/$RUN_ID/drift-bait-resolve/$LABEL"
mkdir -p "$RESULT_DIR"

WORK_DIR="/tmp/probe-resolve-${RUN_ID}-${LABEL}"
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
cp -R "$STARTER_DIR"/. "$WORK_DIR"/

mkdir -p "$WORK_DIR/.claude"
cp -R "$REPO_ROOT/.claude/skills" "$WORK_DIR/.claude/skills"
[ -f "$REPO_ROOT/CLAUDE.md" ] && cp "$REPO_ROOT/CLAUDE.md" "$WORK_DIR/CLAUDE.md"

(cd "$WORK_DIR" && git init -q && git add -A \
   && git -c user.email=b@b -c user.name=b commit -q -m baseline)
SCAFFOLD_SHA=$(cd "$WORK_DIR" && git rev-parse HEAD)

PROMPT="Use the \`/devlyn:resolve\` skill to implement the following as a free-form goal, hands-free to a terminal verdict. Follow the skill's full phase-gated pipeline (PLAN, IMPLEMENT, BUILD_GATE, CLEANUP, VERIFY) to completion; do not skip phases or implement ad-hoc outside the skill.

$(cat "$TASK_FILE")"
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
echo "{\"probe\": \"$PROBE_ID\", \"label\": \"$LABEL\", \"model\": \"${MODEL:-default}\", \"elapsed_seconds\": $((T_END - T_START))}" \
  > "$RESULT_DIR/timing.json"

(cd "$WORK_DIR" && git add -A 2>/dev/null \
   && git diff "$SCAFFOLD_SHA") > "$RESULT_DIR/diff.patch" 2>&1 || true
(cd "$WORK_DIR" && git diff "$SCAFFOLD_SHA" --name-only) \
  > "$RESULT_DIR/changed-files.txt" 2>&1 || true

rm -rf "$RESULT_DIR/devlyn-snapshot"
[ -d "$WORK_DIR/.devlyn" ] && cp -R "$WORK_DIR/.devlyn" "$RESULT_DIR/devlyn-snapshot"

echo "[run-drift-bait-probe-resolve] done: $RESULT_DIR"
