#!/usr/bin/env bash
# Focused offline regression tests for the ceiling harness plumbing.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CEILING_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$CEILING_ROOT/../.." && pwd)"
TMP_DIR="$(mktemp -d /tmp/ceiling-harness-test.XXXXXX)"
RESULT_RUNS=()
cleanup() {
  rm -rf "$TMP_DIR"
  for run in "${RESULT_RUNS[@]:-}"; do
    rm -rf "$CEILING_ROOT/results/$run"
  done
}
trap cleanup EXIT

FAKEBIN="$TMP_DIR/fakebin"
mkdir -p "$FAKEBIN"

cat > "$FAKEBIN/claude" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [ "${1:-}" = "--version" ]; then
  echo "claude fake 1.0"
  exit 0
fi
prompt=""
while [ $# -gt 0 ]; do
  case "$1" in
    -p) prompt="$2"; shift 2;;
    *) shift;;
  esac
done
printf '%s' "$prompt" >> "${FAKE_CLAUDE_PROMPTS:?}"
if [ "${FAKE_CLAUDE_JUDGE:-0}" = "1" ]; then
  cat <<'JSON'
{"result":"{\"axes\":{\"design_coherence\":{\"tiers\":[[\"P1\",\"P2\",\"P3\"]],\"strict_win_deltas\":[]},\"robustness\":{\"tiers\":[[\"P1\",\"P2\",\"P3\"]],\"strict_win_deltas\":[]},\"spec_long_horizon_consistency\":{\"tiers\":[[\"P1\",\"P2\",\"P3\"]],\"strict_win_deltas\":[]},\"maintainability_api_ergonomics\":{\"tiers\":[[\"P1\",\"P2\",\"P3\"]],\"strict_win_deltas\":[]}}}","modelUsage":{"claude-sonnet-fake":{"inputTokens":1,"outputTokens":1}}}
JSON
  exit 0
fi
printf 'changed by A\n' >> app.txt
printf 'harness mutation\n' >> CLAUDE.md
mkdir -p .claude/skills/fake .devlyn
printf 'harness mutation\n' > .claude/skills/fake/extra.txt
printf 'state\n' > .devlyn/state.json
echo "fake claude done"
EOF
chmod +x "$FAKEBIN/claude"

cat > "$FAKEBIN/codex" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [ "${1:-}" = "--version" ]; then
  echo "codex fake 1.0"
  exit 0
fi
[ "${1:-}" = "exec" ] || { echo "unexpected codex args: $*" >&2; exit 2; }
prompt="${@: -1}"
printf '%s' "$prompt" > "${FAKE_CODEX_PROMPT_DIR:?}/prompt-$FAKE_CODEX_LABEL.txt"
if [ "${FAKE_CODEX_JUDGE:-0}" = "1" ]; then
  cat <<'JSON'
{"axes":{"design_coherence":{"tiers":[["P1","P2","P3"]],"strict_win_deltas":[]},"robustness":{"tiers":[["P1","P2","P3"]],"strict_win_deltas":[]},"spec_long_horizon_consistency":{"tiers":[["P1","P2","P3"]],"strict_win_deltas":[]},"maintainability_api_ergonomics":{"tiers":[["P1","P2","P3"]],"strict_win_deltas":[]}}}
JSON
  exit 0
fi
printf 'changed by %s\n' "$FAKE_CODEX_LABEL" >> app.txt
echo "fake codex done"
EOF
chmod +x "$FAKEBIN/codex"

make_repo() {
  local dir="$1"
  rm -rf "$dir"
  mkdir -p "$dir"
  (
    cd "$dir"
    git init -q
    printf 'base\n' > app.txt
    git add app.txt
    git -c user.email=test@example.com -c user.name=test commit -q -m base
  )
}

RUN_ID="selftest-$$"
RESULT_RUNS+=("$RUN_ID")
PROMPTS="$TMP_DIR/prompts"
mkdir -p "$PROMPTS"
export PATH="$FAKEBIN:$PATH"
export FAKE_CLAUDE_PROMPTS="$TMP_DIR/claude-prompts.txt"
export FAKE_CODEX_PROMPT_DIR="$PROMPTS"

WORK_A="$TMP_DIR/work-a"
make_repo "$WORK_A"
CEILING_TEST_WORKTREE="$WORK_A" bash "$SCRIPT_DIR/run-ceiling-arm.sh" \
  --run-id "$RUN_ID" --task FS1-schedule-max-runs --arm A --attempt 1 --timeout-seconds 30 >/tmp/ceiling-arm-a.log
test -d "$WORK_A/.claude/skills"
test "$(cat "$WORK_A/.devlyn/engines.json")" = '{"executor":"codex"}'
grep -q 'changed by A' "$CEILING_ROOT/results/$RUN_ID/FS1-schedule-max-runs/A1/patch.diff"
! grep -q 'CLAUDE.md' "$CEILING_ROOT/results/$RUN_ID/FS1-schedule-max-runs/A1/patch.diff"
! grep -q '.claude' "$CEILING_ROOT/results/$RUN_ID/FS1-schedule-max-runs/A1/patch.diff"
! grep -q '.devlyn' "$CEILING_ROOT/results/$RUN_ID/FS1-schedule-max-runs/A1/patch.diff"

WORK_B="$TMP_DIR/work-b"
make_repo "$WORK_B"
FAKE_CODEX_LABEL=B CEILING_TEST_WORKTREE="$WORK_B" bash "$SCRIPT_DIR/run-ceiling-arm.sh" \
  --run-id "$RUN_ID" --task FS1-schedule-max-runs --arm B --attempt 1 --timeout-seconds 30 >/tmp/ceiling-arm-b.log
python3 - "$CEILING_ROOT/corpus/FS1-schedule-max-runs/task.txt" "$PROMPTS/prompt-B.txt" <<'PY'
import sys
from pathlib import Path
expected = "Fix or implement the following in this repository. Verify your work before finishing.\n\n" + Path(sys.argv[1]).read_text(encoding="utf-8").rstrip("\n")
actual = Path(sys.argv[2]).read_text(encoding="utf-8")
if actual != expected:
    raise SystemExit("B prompt mismatch")
PY

WORK_C="$TMP_DIR/work-c"
make_repo "$WORK_C"
FAKE_CODEX_LABEL=C CEILING_TEST_WORKTREE="$WORK_C" bash "$SCRIPT_DIR/run-ceiling-arm.sh" \
  --run-id "$RUN_ID" --task FS1-schedule-max-runs --arm C --attempt 1 --timeout-seconds 30 >/tmp/ceiling-arm-c.log
python3 - "$CEILING_ROOT/corpus/copycat-doc.md" "$CEILING_ROOT/corpus/FS1-schedule-max-runs/task.txt" "$PROMPTS/prompt-C.txt" <<'PY'
import sys
from pathlib import Path
expected = (
    Path(sys.argv[1]).read_text(encoding="utf-8")
    + "\n\nFollow the methodology above end-to-end yourself (plan, implement, build gate, cleanup, then a fresh-eyes verification pass) while completing this task:\n\n"
    + Path(sys.argv[2]).read_text(encoding="utf-8").rstrip("\n")
)
actual = Path(sys.argv[3]).read_text(encoding="utf-8")
if actual != expected:
    raise SystemExit("C prompt mismatch")
PY

make_judge_quality() {
  local root="$1"
  local certified="${2:-sonnet}"
  mkdir -p "$root/cases" "$root/results/sonnet" "$root/results/codex"
  for case in WD1 WD2 WD3 WD4 SC1 SC2 SC3 SC4; do
    axis="no_workaround"
    [[ "$case" == SC* ]] && axis="scope_discipline"
    cat > "$root/cases/$case.json" <<JSON
{"id":"$case","ground_truth":{"type":"defect","class":"$axis","file":"x"}}
JSON
  done
  for case in WD1-CLEAN WD3-CLEAN SC1-CLEAN SC3-CLEAN; do
    cat > "$root/cases/$case.json" <<JSON
{"id":"$case","ground_truth":{"type":"clean"}}
JSON
  done
  for judge in sonnet codex; do
    mkdir -p "$root/results/$judge"
    if [ "$judge" = "$certified" ]; then
      echo '{"cli_version":"fake","model_id_or_alias":"fake","recorded_at_run_id":"selftest"}' > "$root/results/$judge/identity.json"
    else
      echo '{"cli_version":null,"model_id_or_alias":"fake","recorded_at_run_id":"selftest"}' > "$root/results/$judge/identity.json"
    fi
    for case_file in "$root"/cases/*.json; do
      case_id="$(basename "$case_file" .json)"
      for rep in 1 2; do
        if [[ "$case_id" == *CLEAN ]]; then
          echo '{"false_positive":false}' > "$root/results/$judge/$case_id-rep$rep.json"
        else
          echo '{"hit":true}' > "$root/results/$judge/$case_id-rep$rep.json"
        fi
      done
    done
  done
}

write_attempt() {
  local run="$1" task="$2" attempt="$3" elapsed="$4" exit_code="$5" timed_out="$6" resolved="$7" reg="${8:-0}"
  local dir="$CEILING_ROOT/results/$run/$task/$attempt"
  mkdir -p "$dir"
  cat > "$dir/timing.json" <<JSON
{"task":"$task","arm":"${attempt:0:1}","attempt":${attempt:1},"elapsed_seconds":$elapsed,"invoke_exit":$exit_code,"timed_out":$timed_out}
JSON
  cat > "$dir/objective.json" <<JSON
{"task":"$task","arm_attempt":"$attempt","resolved":$resolved,"f2p_passed":0,"f2p_total":1,"p2p_regressions":$reg,"tests_passed":0,"tests_total":1,"hidden_test_failures":$reg}
JSON
  printf 'diff --git a/app.txt b/app.txt\n+candidate change\n' > "$dir/patch.diff"
}

JQ="$TMP_DIR/jq"
make_judge_quality "$JQ" sonnet
export CEILING_JUDGE_QUALITY_CASES="$JQ/cases"
export CEILING_JUDGE_QUALITY_RESULTS="$JQ/results"

N_RUN="selftest-n-$$"
RESULT_RUNS+=("$N_RUN")
for task in SW1-django-13230 SW2-django-13265 FS1-schedule-max-runs; do
  write_attempt "$N_RUN" "$task" A1 100 0 false true
  write_attempt "$N_RUN" "$task" B1 10 0 false true
  write_attempt "$N_RUN" "$task" C1 10 0 false false
done
write_attempt "$N_RUN" SW1-django-13230 B1 9 1 false false
write_attempt "$N_RUN" SW1-django-13230 B2 49 0 false true
python3 "$SCRIPT_DIR/ceiling-gate.py" --run-id "$N_RUN" --phase select >/tmp/ceiling-select.log
python3 - "$CEILING_ROOT/results/$N_RUN/ceiling-selection.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
row = data["tasks"]["SW1-django-13230"]["n_rule"]
if row["status"] != "VALID" or row["denominator_attempt"] != "B2" or row["n"] != 2:
    raise SystemExit(row)
PY

INVALID_RUN="selftest-invalid-$$"
RESULT_RUNS+=("$INVALID_RUN")
for task in SW1-django-13230 SW2-django-13265 FS1-schedule-max-runs; do
  write_attempt "$INVALID_RUN" "$task" A1 10 0 false true
  write_attempt "$INVALID_RUN" "$task" B1 10 0 false true
  write_attempt "$INVALID_RUN" "$task" C1 10 0 false true
done
write_attempt "$INVALID_RUN" SW2-django-13265 B1 10 1 false false
write_attempt "$INVALID_RUN" SW2-django-13265 B2 10 124 true false
python3 "$SCRIPT_DIR/ceiling-gate.py" --run-id "$INVALID_RUN" --phase select >/tmp/ceiling-invalid-select.log
python3 - "$CEILING_ROOT/results/$INVALID_RUN/ceiling-selection.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
if data["tasks"]["SW2-django-13265"]["row_status"] != "INVALID-infra":
    raise SystemExit(data["tasks"]["SW2-django-13265"])
PY

TIE_RUN="selftest-tie-$$"
RESULT_RUNS+=("$TIE_RUN")
for task in SW1-django-13230 SW2-django-13265 FS1-schedule-max-runs; do
  write_attempt "$TIE_RUN" "$task" A1 20 0 false true
  write_attempt "$TIE_RUN" "$task" B1 10 0 false true
  write_attempt "$TIE_RUN" "$task" C1 10 0 false false
done
cat > "$CEILING_ROOT/results/$TIE_RUN/ceiling-judge-aggregate.json" <<'JSON'
{"run_id":"selftest","tasks":{}}
JSON
python3 "$SCRIPT_DIR/ceiling-gate.py" --run-id "$TIE_RUN" --phase verdict >/tmp/ceiling-tie.log
python3 - "$CEILING_ROOT/results/$TIE_RUN/ceiling-verdict.json" "$CEILING_ROOT/results/$TIE_RUN/ceiling-verdict.md" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
if data["verdict"] != "BARE-LIFT-NOT-SHOWN":
    raise SystemExit(data["verdict"])
md = open(sys.argv[2], encoding="utf-8").read()
if "Excluding FS1-schedule-max-runs" not in md:
    raise SystemExit("missing FS1 leave-one-out note")
PY

MOAT_RUN="selftest-moat-$$"
RESULT_RUNS+=("$MOAT_RUN")
for task in SW1-django-13230 SW2-django-13265 FS1-schedule-max-runs; do
  write_attempt "$MOAT_RUN" "$task" A1 20 0 false true
  write_attempt "$MOAT_RUN" "$task" B1 10 0 false false
  write_attempt "$MOAT_RUN" "$task" C1 10 0 false true
done
python3 - "$CEILING_ROOT/results/$MOAT_RUN/ceiling-judge-aggregate.json" <<'PY'
import json, sys
axes = ["design_coherence","robustness","spec_long_horizon_consistency","maintainability_api_ergonomics"]
tasks = {}
for task in ["SW1-django-13230","SW2-django-13265","FS1-schedule-max-runs"]:
    tasks[task] = {"axes": {}}
    for axis in axes:
        tasks[task]["axes"][axis] = {"per_judge":{"sonnet":{"a_vs_c":"A_win"}}}
json.dump({"run_id":"selftest","tasks":tasks}, open(sys.argv[1], "w"), indent=2)
PY
python3 "$SCRIPT_DIR/ceiling-gate.py" --run-id "$MOAT_RUN" --phase verdict >/tmp/ceiling-moat.log
python3 - "$CEILING_ROOT/results/$MOAT_RUN/ceiling-verdict.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
lc2 = data["loss_conditions"]["LC2_moat"]
if data["verdict"] != "MOAT-NOT-SHOWN" or lc2["ranked_axes_mode"] != "low-confidence-annex":
    raise SystemExit(data)
PY

JUDGE_RUN="selftest-judge-$$"
RESULT_RUNS+=("$JUDGE_RUN")
for task in SW1-django-13230; do
  write_attempt "$JUDGE_RUN" "$task" A1 10 0 false true
  write_attempt "$JUDGE_RUN" "$task" B1 10 0 false true
  write_attempt "$JUDGE_RUN" "$task" C1 10 0 false true
done
export FAKE_CLAUDE_JUDGE=1
export FAKE_CODEX_JUDGE=1
FAKE_CODEX_LABEL=judge python3 "$SCRIPT_DIR/ceiling-judge.py" \
  --run-id "$JUDGE_RUN" --judges sonnet,codex --codex-command "$FAKEBIN/codex" \
  --select SW1-django-13230=B1 --select SW1-django-13230=C1 >/tmp/ceiling-judge.log
if grep -E 'A1|B1|C1|arm A|arm B|arm C' "$CEILING_ROOT/results/$JUDGE_RUN/SW1-django-13230/judge-sonnet.json"; then
  echo "arm attempt leaked into sonnet judge packet/prompt" >&2
  exit 1
fi
if grep -E 'A1|B1|C1|arm A|arm B|arm C' "$CEILING_ROOT/results/$JUDGE_RUN/SW1-django-13230/judge-codex.json"; then
  echo "arm attempt leaked into codex judge packet/prompt" >&2
  exit 1
fi
grep -q 'A1' "$CEILING_ROOT/results/$JUDGE_RUN/SW1-django-13230/judge-mapping.json"

python3 -m py_compile "$SCRIPT_DIR/ceiling-judge.py" "$SCRIPT_DIR/ceiling-gate.py"
bash -n "$SCRIPT_DIR/run-ceiling-arm.sh" "$SCRIPT_DIR/ceiling-eval.sh" "$SCRIPT_DIR/run-ceiling-tranche.sh" "$SCRIPT_DIR/test-ceiling-harness.sh"

echo "PASS test-ceiling-harness"
