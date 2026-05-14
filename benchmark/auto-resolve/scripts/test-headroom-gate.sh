#!/usr/bin/env bash
# Regression tests for headroom-gate.py candidate-set guards.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GATE="$SCRIPT_DIR/headroom-gate.py"
TMP_DIR="$(mktemp -d /tmp/headroom-gate-test.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

write_fixture() {
  local run_id="$1"
  local fixture="$2"
  local bare="$3"
  local solo="$4"
  local solo_timed_out="${5:-false}"
  local dir="$TMP_DIR/$run_id/$fixture"
  mkdir -p "$dir/bare" "$dir/solo_claude"
  cat > "$dir/judge.json" <<EOF
{
  "scores_by_arm": {"bare": $bare, "solo_claude": $solo},
  "_blind_mapping": {"A": "bare", "B": "solo_claude", "seed": 1},
  "disqualifiers_by_arm": {}
}
EOF
  cat > "$dir/bare/result.json" <<'EOF'
{"timed_out": false, "invoke_failure": false}
EOF
  cat > "$dir/bare/verify.json" <<'EOF'
{"disqualifier": false, "verify_score": 1.0}
EOF
  : > "$dir/bare/diff.patch"
  cat > "$dir/solo_claude/result.json" <<EOF
{"timed_out": $solo_timed_out, "invoke_failure": false, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
EOF
  cat > "$dir/solo_claude/verify.json" <<'EOF'
{"disqualifier": false, "verify_score": 1.0}
EOF
  : > "$dir/solo_claude/diff.patch"
}

expect_fail_contains() {
  local label="$1"
  local needle="$2"
  shift 2
  local out="$TMP_DIR/$label.out"
  if "$@" > "$out" 2>&1; then
    echo "expected failure for $label" >&2
    cat "$out" >&2
    exit 1
  fi
  if ! grep -Fq "$needle" "$out"; then
    echo "missing expected text for $label: $needle" >&2
    cat "$out" >&2
    exit 1
  fi
}

write_fixture one-pass F16 50 75
expect_fail_contains missing-rejected-registry "rejected fixture registry missing" \
  env PAIR_REJECTED_FIXTURES_REGISTRY="$TMP_DIR/missing-registry.sh" \
    python3 "$GATE" --results-root "$TMP_DIR" --run-id one-pass --min-fixtures 1
empty_registry="$TMP_DIR/empty-registry.sh"
: > "$empty_registry"
expect_fail_contains empty-rejected-registry "rejected fixture registry has no fixture entries" \
  env PAIR_REJECTED_FIXTURES_REGISTRY="$empty_registry" \
    python3 "$GATE" --results-root "$TMP_DIR" --run-id one-pass --min-fixtures 1
expect_fail_contains min-fixtures 'Verdict: **FAIL**' \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id one-pass --out-json "$TMP_DIR/one-pass.json"
grep -Fq '"fixture_count_ok": false' "$TMP_DIR/one-pass.json"

expect_fail_contains invalid-min-fixtures "value must be > 0" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id one-pass --min-fixtures 0

expect_fail_contains invalid-min-bare-headroom "value must be >= 0" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id one-pass --min-bare-headroom -1

expect_fail_contains invalid-min-solo-headroom "value must be >= 0" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id one-pass --min-solo-headroom -1

write_fixture nan-result F16 50 75
cat > "$TMP_DIR/nan-result/F16/bare/result.json" <<'EOF'
{"timed_out": false, "invoke_failure": false, "elapsed_seconds": NaN}
EOF
expect_fail_contains nan-result-json "bare result.json malformed" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id nan-result --min-fixtures 1

write_fixture two-pass F16 50 75
write_fixture two-pass F21 55 75
python3 "$GATE" --results-root "$TMP_DIR" --run-id two-pass --out-json "$TMP_DIR/two-pass.json" \
  --out-md "$TMP_DIR/two-pass.md" > "$TMP_DIR/two-pass.out"
grep -Fq '"verdict": "PASS"' "$TMP_DIR/two-pass.json"
grep -Fq '"fixture_count_ok": true' "$TMP_DIR/two-pass.json"
grep -Fq '"min_bare_headroom_required": 5' "$TMP_DIR/two-pass.json"
grep -Fq '"min_solo_headroom_required": 5' "$TMP_DIR/two-pass.json"
grep -Fq '"avg_bare_headroom": 7.5' "$TMP_DIR/two-pass.json"
grep -Fq '"min_bare_headroom": 5' "$TMP_DIR/two-pass.json"
grep -Fq '"avg_solo_headroom": 5.0' "$TMP_DIR/two-pass.json"
grep -Fq '"min_solo_headroom": 5' "$TMP_DIR/two-pass.json"
grep -Fq '"bare_headroom": 10' "$TMP_DIR/two-pass.json"
grep -Fq '"solo_headroom": 5' "$TMP_DIR/two-pass.json"
grep -Fq 'headroom >= 5' "$TMP_DIR/two-pass.md"
grep -Fq 'Average bare headroom: 7.5' "$TMP_DIR/two-pass.md"
grep -Fq 'Minimum bare headroom: 5' "$TMP_DIR/two-pass.md"
grep -Fq 'Average solo_claude headroom: 5.0' "$TMP_DIR/two-pass.md"
grep -Fq 'Minimum solo_claude headroom: 5' "$TMP_DIR/two-pass.md"
grep -Fq 'Fixtures passed: 2/2 (minimum required: 2)' "$TMP_DIR/two-pass.md"
grep -Fq '| Fixture | Bare | Bare headroom | Solo_claude | Solo_claude headroom | Status | Reason |' "$TMP_DIR/two-pass.md"
grep -Fq '| F16 | 50 | 10 | 75 | 5 | PASS |  |' "$TMP_DIR/two-pass.md"
grep -Fq '| F21 | 55 | 5 | 75 | 5 | PASS |  |' "$TMP_DIR/two-pass.md"

write_fixture rejected-direct F2 50 75
write_fixture rejected-direct F16 50 75
expect_fail_contains rejected-direct "fixture rejected for pair-candidate runs" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id rejected-direct --min-fixtures 1

write_fixture rejected-shadow-direct S3-cli-ticket-assignment 50 75
write_fixture rejected-shadow-direct F16 50 75
expect_fail_contains rejected-shadow-direct "fixture rejected for pair-candidate runs" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id rejected-shadow-direct --min-fixtures 1

write_fixture marginal-bare F16 59 66
write_fixture marginal-bare F21 50 75
expect_fail_contains marginal-bare "bare headroom 1 < 5" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id marginal-bare

write_fixture marginal-solo F16 50 78
write_fixture marginal-solo F21 50 75
expect_fail_contains marginal-solo "solo_claude headroom 2 < 5" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id marginal-solo

write_fixture explicit-zero-margin F16 60 80
write_fixture explicit-zero-margin F21 50 75
python3 "$GATE" --results-root "$TMP_DIR" --run-id explicit-zero-margin \
  --min-bare-headroom 0 --min-solo-headroom 0 \
  --out-json "$TMP_DIR/explicit-zero-margin.json"
grep -Fq '"verdict": "PASS"' "$TMP_DIR/explicit-zero-margin.json"

write_fixture solo-ceiling F16 50 75
write_fixture solo-ceiling F21 20 92
expect_fail_contains solo-ceiling "solo_claude score 92 > 80" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id solo-ceiling

write_fixture dirty-solo F16 50 75
write_fixture dirty-solo F21 20 70 true
expect_fail_contains dirty-solo "solo_claude timed out" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id dirty-solo

write_fixture dirty-bare F16 50 75
write_fixture dirty-bare F21 20 70
python3 - "$TMP_DIR/dirty-bare/F16/bare/result.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["disqualifier"] = True
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains dirty-bare "bare result disqualifier" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id dirty-bare

write_fixture dirty-solo-axis F16 50 75
write_fixture dirty-solo-axis F21 20 70
python3 - "$TMP_DIR/dirty-solo-axis/F21/judge.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["_blind_mapping"] = {"A": "bare", "B": "solo_claude", "seed": 1}
data["_axis_validation"] = {
    "out_of_range_count": 1,
    "out_of_range_cells": [{"breakdown": "b_breakdown", "axis": "quality", "value": 26}],
    "axis_range": [0, 25],
}
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains dirty-solo-axis "solo_claude judge axis-invalid (1)" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id dirty-solo-axis

write_fixture unmapped-axis F16 50 75
write_fixture unmapped-axis F21 20 70
python3 - "$TMP_DIR/unmapped-axis/F21/judge.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["_blind_mapping"] = {"A": "bare", "B": "variant", "seed": 1}
data["_axis_validation"] = {
    "out_of_range_count": 1,
    "out_of_range_cells": [{"breakdown": "b_breakdown", "axis": "quality", "value": 26}],
    "axis_range": [0, 25],
}
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains unmapped-axis "judge axis-invalid unmapped (1)" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id unmapped-axis

write_fixture missing-mapping F16 50 75
write_fixture missing-mapping F21 20 70
python3 - "$TMP_DIR/missing-mapping/F21/judge.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
del data["_blind_mapping"]
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains missing-mapping "judge blind mapping missing" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id missing-mapping
python3 "$GATE" --results-root "$TMP_DIR" --run-id missing-mapping \
  --out-json "$TMP_DIR/missing-mapping.json" >/dev/null 2>&1 || true
grep -Fq '"bare_score": null' "$TMP_DIR/missing-mapping.json"
grep -Fq '"solo_score": null' "$TMP_DIR/missing-mapping.json"

write_fixture malformed-mapping-axis F16 50 75
write_fixture malformed-mapping-axis F21 20 70
python3 - "$TMP_DIR/malformed-mapping-axis/F21/judge.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["_blind_mapping"] = "not-a-dict"
data["_axis_validation"] = {
    "out_of_range_count": 1,
    "out_of_range_cells": [{"breakdown": "b_breakdown", "axis": "quality", "value": 26}],
    "axis_range": [0, 25],
}
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains malformed-mapping-axis "judge blind mapping missing" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id malformed-mapping-axis
python3 "$GATE" --results-root "$TMP_DIR" --run-id malformed-mapping-axis \
  --out-json "$TMP_DIR/malformed-mapping-axis.json" >/dev/null 2>&1 || true
grep -Fq '"bare_score": null' "$TMP_DIR/malformed-mapping-axis.json"
grep -Fq '"solo_score": null' "$TMP_DIR/malformed-mapping-axis.json"

write_fixture wrong-mapping F16 50 75
write_fixture wrong-mapping F21 20 70
python3 - "$TMP_DIR/wrong-mapping/F21/judge.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["_blind_mapping"] = {"A": "bare", "B": "variant", "seed": 1}
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains wrong-mapping "judge blind mapping missing arm(s): solo_claude" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id wrong-mapping
python3 "$GATE" --results-root "$TMP_DIR" --run-id wrong-mapping \
  --out-json "$TMP_DIR/wrong-mapping.json" >/dev/null 2>&1 || true
grep -Fq '"bare_score": 20' "$TMP_DIR/wrong-mapping.json"
grep -Fq '"solo_score": null' "$TMP_DIR/wrong-mapping.json"

write_fixture malformed-scores F16 50 75
write_fixture malformed-scores F21 20 70
python3 - "$TMP_DIR/malformed-scores/F21/judge.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["scores_by_arm"] = ["not", "a", "dict"]
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains malformed-scores "bare score missing" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id malformed-scores
python3 "$GATE" --results-root "$TMP_DIR" --run-id malformed-scores \
  --out-json "$TMP_DIR/malformed-scores.json" >/dev/null 2>&1 || true
grep -Fq '"bare_score": null' "$TMP_DIR/malformed-scores.json"
grep -Fq '"solo_score": null' "$TMP_DIR/malformed-scores.json"

write_fixture overrange-score F16 50 75
write_fixture overrange-score F21 20 101
expect_fail_contains overrange-score "solo_claude score missing" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id overrange-score

write_fixture boolean-score F16 true 75
write_fixture boolean-score F21 20 70
expect_fail_contains boolean-score "bare score missing" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id boolean-score

write_fixture partial-baseline F16 50 75
write_fixture partial-baseline F21 20 70
python3 - "$TMP_DIR/partial-baseline/F21/solo_claude/verify.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["verify_score"] = 0.75
json.dump(data, open(path, "w"), indent=2)
PY
python3 - "$TMP_DIR/partial-baseline/F21/solo_claude/result.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["terminal_verdict"] = "FAIL"
data["verify_verdict"] = "FAIL"
json.dump(data, open(path, "w"), indent=2)
PY
python3 "$GATE" --results-root "$TMP_DIR" --run-id partial-baseline \
  --out-json "$TMP_DIR/partial-baseline.json" \
  --out-md "$TMP_DIR/partial-baseline.md"
grep -Fq '"verdict": "PASS"' "$TMP_DIR/partial-baseline.json"
grep -Fq '| F21 | 20 | 40 | 70 | 10 | PASS |  |' "$TMP_DIR/partial-baseline.md"

write_fixture dirty-bare-env F16 50 75
write_fixture dirty-bare-env F21 20 70
python3 - "$TMP_DIR/dirty-bare-env/F16/bare/result.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["environment_contamination"] = True
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains dirty-bare-env "bare environment contamination" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id dirty-bare-env

write_fixture malformed-bare-bool F16 50 75
write_fixture malformed-bare-bool F21 20 70
python3 - "$TMP_DIR/malformed-bare-bool/F16/bare/result.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["timed_out"] = "false"
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains malformed-bare-bool "bare result timed_out malformed" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id malformed-bare-bool

write_fixture malformed-judge-bool F16 50 75
write_fixture malformed-judge-bool F21 20 70
python3 - "$TMP_DIR/malformed-judge-bool/F16/judge.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["disqualifiers_by_arm"] = {"bare": {"disqualifier": "false"}}
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains malformed-judge-bool "bare judge disqualifier malformed" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id malformed-judge-bool

write_fixture missing-artifact F16 50 75
write_fixture missing-artifact F21 20 70
rm "$TMP_DIR/missing-artifact/F21/solo_claude/verify.json"
expect_fail_contains missing-artifact "solo_claude verify.json missing" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id missing-artifact

write_fixture malformed-result-artifact F16 50 75
write_fixture malformed-result-artifact F21 20 70
printf '["not", "a", "dict"]\n' > "$TMP_DIR/malformed-result-artifact/F21/solo_claude/result.json"
expect_fail_contains malformed-result-artifact "solo_claude result.json malformed" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id malformed-result-artifact

write_fixture malformed-verify-artifact F16 50 75
write_fixture malformed-verify-artifact F21 20 70
printf '["not", "a", "dict"]\n' > "$TMP_DIR/malformed-verify-artifact/F21/solo_claude/verify.json"
expect_fail_contains malformed-verify-artifact "solo_claude verify.json malformed" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id malformed-verify-artifact

write_fixture malformed-judge-artifact F16 50 75
write_fixture malformed-judge-artifact F21 20 70
printf '["not", "a", "dict"]\n' > "$TMP_DIR/malformed-judge-artifact/F21/judge.json"
expect_fail_contains malformed-judge-artifact "judge.json malformed" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id malformed-judge-artifact

write_fixture missing-diff F16 50 75
write_fixture missing-diff F21 20 70
rm "$TMP_DIR/missing-diff/F21/solo_claude/diff.patch"
expect_fail_contains missing-diff "solo_claude diff.patch missing" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id missing-diff

write_fixture malformed-dq F16 50 75
write_fixture malformed-dq F21 20 70
python3 - "$TMP_DIR/malformed-dq/F21/judge.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["disqualifiers_by_arm"] = ["not", "a", "dict"]
json.dump(data, open(path, "w"), indent=2)
PY
python3 "$GATE" --results-root "$TMP_DIR" --run-id malformed-dq --min-fixtures 1 \
  --out-json "$TMP_DIR/malformed-dq.json" >/dev/null
grep -Fq '"verdict": "PASS"' "$TMP_DIR/malformed-dq.json"

write_fixture malformed-dq-entry F16 50 75
write_fixture malformed-dq-entry F21 20 70
python3 - "$TMP_DIR/malformed-dq-entry/F21/judge.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["disqualifiers_by_arm"] = {"solo_claude": True}
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains malformed-dq-entry "solo_claude judge disqualifier" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id malformed-dq-entry

write_fixture malformed-axis-wrapper F16 50 75
write_fixture malformed-axis-wrapper F21 20 70
python3 - "$TMP_DIR/malformed-axis-wrapper/F21/judge.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["_axis_validation"] = ["not", "a", "dict"]
json.dump(data, open(path, "w"), indent=2)
PY
python3 "$GATE" --results-root "$TMP_DIR" --run-id malformed-axis-wrapper --min-fixtures 1 \
  --out-json "$TMP_DIR/malformed-axis-wrapper.json" >/dev/null
grep -Fq '"verdict": "PASS"' "$TMP_DIR/malformed-axis-wrapper.json"

echo "✓ test-headroom-gate"
