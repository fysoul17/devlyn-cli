#!/usr/bin/env bash
# Lane B instruction-blind judge caller.
#
# Builds the judge input (task + spec + allowlist + A/B diff + transcripts),
# invokes Codex CLI with strict JSON schema, resolves A/B back to arm identity
# via manifest.slot_map, and appends one JSONL row to judge-findings.jsonl.
#
# Cross-model contract: the judge model (codex CLI default = gpt-5.3-codex)
# differs from the model under test (claude). Do NOT change to a claude-family
# judge — that re-introduces self-judgment bias.
#
# Usage:
#   bash judge-blind.sh --run-dir <path> --fixture <id>
#
# Environment knobs:
#   LANE_B_JUDGE_MODEL   optional, passed as codex `--model`. Default = codex CLI default.
#   LANE_B_JUDGE_TIMEOUT_S  default 300.

set -euo pipefail

RUN_DIR=""
FIXTURE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run-dir) RUN_DIR="$2"; shift 2 ;;
    --fixture) FIXTURE="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$RUN_DIR" || -z "$FIXTURE" ]]; then
  echo "usage: $0 --run-dir <path> --fixture <id>" >&2
  exit 2
fi

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
LANE_ROOT="$REPO_ROOT/benchmark/instruction-sensitivity"
FIXTURE_DIR="$LANE_ROOT/fixtures/$FIXTURE"
JUDGE_SCHEMA="$LANE_ROOT/scripts/judge.schema.json"
JUDGE_TIMEOUT="${LANE_B_JUDGE_TIMEOUT_S:-300}"
JUDGE_REASONING="${LANE_B_JUDGE_REASONING:-xhigh}"

JUDGE_INPUT="$RUN_DIR/judge-tmp/$FIXTURE.input.json"
JUDGE_PROMPT="$RUN_DIR/judge-tmp/$FIXTURE.prompt.txt"
JUDGE_LAST="$RUN_DIR/judge-tmp/$FIXTURE.last.json"
JUDGE_STDOUT="$RUN_DIR/judge-tmp/$FIXTURE.stdout.log"
JUDGE_STDERR="$RUN_DIR/judge-tmp/$FIXTURE.stderr.log"
mkdir -p "$RUN_DIR/judge-tmp"

# Pre-flight — manifest, slot_map, and both arm outputs must exist.
if ! python3 - "$RUN_DIR/manifest.json" "$FIXTURE" "$RUN_DIR" <<'PY'
import json, sys
manifest_p, fixture, run_dir = sys.argv[1:]
m = json.load(open(manifest_p))
if fixture not in m.get("slot_map", {}):
    print(f"error: no slot_map entry for {fixture}", file=sys.stderr); sys.exit(2)
slot = m["slot_map"][fixture]
import os
for arm in (slot["A"], slot["B"]):
    arm_dir = os.path.join(run_dir, "arms", arm, fixture)
    if not os.path.isfile(os.path.join(arm_dir, "diff.patch")):
        print(f"error: missing diff.patch in {arm_dir}", file=sys.stderr); sys.exit(2)
PY
then
  exit 2
fi

python3 "$LANE_ROOT/scripts/build-judge-input.py" \
  --run-dir "$RUN_DIR" --fixture "$FIXTURE" > "$JUDGE_INPUT"

# Compose the final prompt: rubric body + the JSON payload + strict-JSON reminder.
{
  echo "You are an instruction-blind judge. Apply the RUBRIC exactly to the two arms (A, B)."
  echo "Output ONLY the JSON object defined by the schema. No commentary, no markdown fences."
  echo ""
  echo "===== RUBRIC ====="
  cat "$LANE_ROOT/RUBRIC.md"
  echo ""
  echo "===== JUDGE_INPUT_JSON ====="
  cat "$JUDGE_INPUT"
} > "$JUDGE_PROMPT"

MODEL_FLAG=()
if [[ -n "${LANE_B_JUDGE_MODEL:-}" ]]; then
  MODEL_FLAG=(--model "$LANE_B_JUDGE_MODEL")
fi

set +e
bash "$LANE_ROOT/scripts/_with-timeout.sh" "$JUDGE_TIMEOUT" \
  codex exec \
    --ignore-user-config \
    --ignore-rules \
    --ephemeral \
    --skip-git-repo-check \
    --sandbox read-only \
    --output-last-message "$JUDGE_LAST" \
    -c model_reasoning_effort="\"$JUDGE_REASONING\"" \
    ${MODEL_FLAG[@]+"${MODEL_FLAG[@]}"} \
    - < "$JUDGE_PROMPT" \
    > "$JUDGE_STDOUT" 2> "$JUDGE_STDERR"
JUDGE_EXIT=$?
set -e

if [[ ! -s "$JUDGE_LAST" ]]; then
  echo "warn: judge produced no last-message file ($JUDGE_LAST); using stdout as fallback" >&2
  cp "$JUDGE_STDOUT" "$JUDGE_LAST" || true
fi

python3 "$LANE_ROOT/scripts/append-judge-row.py" \
  --manifest "$RUN_DIR/manifest.json" \
  --fixture "$FIXTURE" \
  --judge-json "$JUDGE_LAST" \
  >> "$RUN_DIR/judge-findings.jsonl"

echo "judge-blind: $FIXTURE -> exit=$JUDGE_EXIT (rubric -> judge-findings.jsonl)"
