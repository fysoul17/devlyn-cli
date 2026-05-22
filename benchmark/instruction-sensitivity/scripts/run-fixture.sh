#!/usr/bin/env bash
# Lane B — single-arm fixture runner.
#
# Executes one fixture against one git ref via `claude -p` in an isolated
# worktree, then captures diff.patch + transcript.txt + meta.json into the
# arm output directory.
#
# Usage:
#   bash run-fixture.sh --fixture <id> --ref <sha> --out-dir <path>
#
# Environment knobs:
#   LANE_B_CLAUDE_MODEL    optional, passed as `--model`. Default = claude CLI default.
#   LANE_B_MAX_TURNS       max claude turns per run. Default 8.
#   LANE_B_RUN_TIMEOUT_S   timeout in seconds for the claude call. Default 600.
set -euo pipefail

FIXTURE=""
REF=""
OUT_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --fixture) FIXTURE="$2"; shift 2 ;;
    --ref) REF="$2"; shift 2 ;;
    --out-dir) OUT_DIR="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$FIXTURE" || -z "$REF" || -z "$OUT_DIR" ]]; then
  echo "usage: $0 --fixture <id> --ref <sha> --out-dir <path>" >&2
  exit 2
fi

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
LANE_ROOT="$REPO_ROOT/benchmark/instruction-sensitivity"
FIXTURE_DIR="$LANE_ROOT/fixtures/$FIXTURE"

if [[ ! -d "$FIXTURE_DIR" ]]; then
  echo "error: fixture not found: $FIXTURE_DIR" >&2
  exit 1
fi
if [[ ! -d "$FIXTURE_DIR/starter" ]]; then
  echo "error: fixture starter missing: $FIXTURE_DIR/starter" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

MAX_TURNS="${LANE_B_MAX_TURNS:-8}"
RUN_TIMEOUT="${LANE_B_RUN_TIMEOUT_S:-600}"
MODEL_FLAG=()
if [[ -n "${LANE_B_CLAUDE_MODEL:-}" ]]; then
  MODEL_FLAG=(--model "$LANE_B_CLAUDE_MODEL")
fi

# Resolve the requested ref before touching disk. Refusing here prevents leaking
# a stale worktree on a typo.
if ! git -C "$REPO_ROOT" rev-parse --verify "$REF^{commit}" >/dev/null 2>&1; then
  echo "error: ref not found in repo: $REF" >&2
  exit 1
fi

# Isolated worktree OUTSIDE the main repo tree so claude CLI's CLAUDE.md
# discovery walks up only to the worktree root.
WT_DIR="$(mktemp -d -t "laneb-wt-${FIXTURE}-XXXXXX")"
cleanup() {
  git -C "$REPO_ROOT" worktree remove --force "$WT_DIR" >/dev/null 2>&1 || true
  rm -rf "$WT_DIR" >/dev/null 2>&1 || true
}
trap cleanup EXIT

git -C "$REPO_ROOT" worktree add --detach "$WT_DIR" "$REF" >/dev/null

# Drop fixture starter on top of the worktree, then commit so the post-run diff
# is taken relative to a known scaffold sha (not the ref's tree).
rsync -a "$FIXTURE_DIR/starter/" "$WT_DIR/"
(
  cd "$WT_DIR"
  git -c user.name=lane-b -c user.email=lane-b@local add -A >/dev/null
  git -c user.name=lane-b -c user.email=lane-b@local \
      commit --allow-empty -qm "__lane_b_scaffold__"
)
SCAFFOLD_SHA="$(git -C "$WT_DIR" rev-parse HEAD)"

PROMPT_TEXT="$(cat "$FIXTURE_DIR/task.txt")"

START_NS="$(python3 -c 'import time; print(time.time_ns())')"
set +e
(
  cd "$WT_DIR"
  env \
    CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
    DISABLE_AUTOUPDATER=1 \
    bash "$LANE_ROOT/scripts/_with-timeout.sh" "$RUN_TIMEOUT" \
    claude -p "$PROMPT_TEXT" \
      --dangerously-skip-permissions \
      --output-format json \
      --setting-sources project \
      --strict-mcp-config \
      --mcp-config '{"mcpServers":{}}' \
      --max-turns "$MAX_TURNS" \
      ${MODEL_FLAG[@]+"${MODEL_FLAG[@]}"} \
      > "$OUT_DIR/claude.raw.json" \
      2> "$OUT_DIR/claude.stderr.log"
)
CLAUDE_EXIT=$?
set -e
END_NS="$(python3 -c 'import time; print(time.time_ns())')"

python3 "$LANE_ROOT/scripts/extract-transcript.py" \
  --in "$OUT_DIR/claude.raw.json" \
  --out "$OUT_DIR/transcript.txt" \
  --out-json "$OUT_DIR/transcript.meta.json"

(
  cd "$WT_DIR"
  git add -A
  git diff "$SCAFFOLD_SHA"
) > "$OUT_DIR/diff.patch" || true

WALL_MS=$(( (END_NS - START_NS) / 1000000 ))

# meta.json — single source of truth for run-level diagnostics.
python3 - "$OUT_DIR/meta.json" <<PY
import json, os, sys
out = sys.argv[1]
data = {
    "fixture": "$FIXTURE",
    "ref": "$REF",
    "worktree_path": "$WT_DIR",
    "scaffold_sha": "$SCAFFOLD_SHA",
    "claude_exit": $CLAUDE_EXIT,
    "wall_ms": $WALL_MS,
    "max_turns": $MAX_TURNS,
    "timeout_s": $RUN_TIMEOUT,
    "model": os.environ.get("LANE_B_CLAUDE_MODEL", "default"),
}
open(out, "w").write(json.dumps(data, indent=2) + "\n")
PY

echo "run-fixture: $FIXTURE @ $REF -> exit=$CLAUDE_EXIT wall=${WALL_MS}ms"
