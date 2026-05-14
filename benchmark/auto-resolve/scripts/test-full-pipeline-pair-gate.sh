#!/usr/bin/env bash
# Regression tests for full-pipeline-pair-gate.py.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GATE="$SCRIPT_DIR/full-pipeline-pair-gate.py"
TMP_DIR="$(mktemp -d /tmp/full-pipeline-pair-gate-test.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

write_fixture() {
  local run_id="$1"
  local fixture="$2"
  local bare="$3"
  local solo="$4"
  local pair="$5"
  local pair_mode="${6:-true}"
  local pair_elapsed="${7:-200}"
  local solo_elapsed="${8:-100}"
  local pair_arm="${9:-l2_risk_probes}"
  local dir="$TMP_DIR/$run_id/$fixture"
  mkdir -p "$dir/bare" "$dir/solo_claude" "$dir/$pair_arm"
  cat > "$dir/judge.json" <<EOF
{
  "scores_by_arm": {"bare": $bare, "solo_claude": $solo, "$pair_arm": $pair},
  "_blind_mapping": {"A": "bare", "B": "solo_claude", "C": "$pair_arm", "seed": 1},
  "disqualifiers_by_arm": {}
}
EOF
  for arm in bare solo_claude "$pair_arm"; do
    cat > "$dir/$arm/verify.json" <<'EOF'
{"disqualifier": false, "verify_score": 1.0}
EOF
    : > "$dir/$arm/diff.patch"
  done
  cat > "$dir/bare/result.json" <<'EOF'
{"timed_out": false, "invoke_failure": false, "disqualifier": false, "elapsed_seconds": 20}
EOF
  cat > "$dir/solo_claude/result.json" <<EOF
{"timed_out": false, "invoke_failure": false, "disqualifier": false, "elapsed_seconds": $solo_elapsed, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
EOF
  cat > "$dir/$pair_arm/result.json" <<EOF
{"timed_out": false, "invoke_failure": false, "disqualifier": false, "elapsed_seconds": $pair_elapsed, "pair_mode": $pair_mode, "pair_trigger": {"eligible": true, "reasons": ["complexity.high"], "skipped_reason": null}, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
EOF
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

write_fixture pass F21 50 75 82 true 220 110
write_fixture pass F23 55 75 83 true 280 140
expect_fail_contains missing-rejected-registry "rejected fixture registry missing" \
  env PAIR_REJECTED_FIXTURES_REGISTRY="$TMP_DIR/missing-registry.sh" \
    python3 "$GATE" --results-root "$TMP_DIR" --run-id pass --min-fixtures 1
empty_registry="$TMP_DIR/empty-registry.sh"
: > "$empty_registry"
expect_fail_contains empty-rejected-registry "rejected fixture registry has no fixture entries" \
  env PAIR_REJECTED_FIXTURES_REGISTRY="$empty_registry" \
    python3 "$GATE" --results-root "$TMP_DIR" --run-id pass --min-fixtures 1
python3 "$GATE" --results-root "$TMP_DIR" --run-id pass \
  --max-pair-solo-wall-ratio 3 \
  --out-json "$TMP_DIR/pass.json" \
  --out-md "$TMP_DIR/pass.md"
grep -Fq '"verdict": "PASS"' "$TMP_DIR/pass.json"
grep -Fq '"avg_pair_margin": 7.5' "$TMP_DIR/pass.json"
grep -Fq '"avg_pair_solo_wall_ratio": 2.0' "$TMP_DIR/pass.json"
grep -Fq '"max_pair_solo_wall_ratio": 3.0' "$TMP_DIR/pass.json"
grep -Fq '"max_observed_pair_solo_wall_ratio": 2.0' "$TMP_DIR/pass.json"
grep -Fq '"require_hypothesis_trigger": false' "$TMP_DIR/pass.json"
grep -Fq '"pair_trigger_has_canonical_reason": true' "$TMP_DIR/pass.json"
grep -Fq '"pair_trigger_has_hypothesis_reason": false' "$TMP_DIR/pass.json"
grep -Fq 'pair_trigger eligible with a canonical reason' "$TMP_DIR/pass.json"
grep -Fq 'Verdict: **PASS**' "$TMP_DIR/pass.md"
grep -Fq 'Fixtures passed: 2/2 (minimum required: 2)' "$TMP_DIR/pass.md"
grep -Fq 'Average pair margin: +7.5' "$TMP_DIR/pass.md"
grep -Fq 'Allowed pair/solo wall ratio: 3.00x' "$TMP_DIR/pass.md"
grep -Fq 'Maximum observed pair/solo wall ratio: 2.00x' "$TMP_DIR/pass.md"
grep -Fq 'Hypothesis trigger required: false' "$TMP_DIR/pass.md"
grep -Fq 'pair_trigger eligible with canonical reason' "$TMP_DIR/pass.md"
grep -Fq '"min_bare_headroom_required": 5' "$TMP_DIR/pass.json"
grep -Fq '"min_solo_headroom_required": 5' "$TMP_DIR/pass.json"
grep -Fq '| Fixture | Bare | Bare headroom | Solo_claude | Solo_claude headroom | Pair | Margin | Pair mode | Hypothesis trigger | Triggers | Wall ratio | Status | Reason |' "$TMP_DIR/pass.md"
grep -Fq '| F21 | 50 | 10 | 75 | 5 | 82 | +7 | true | false | complexity.high | 2.00x | PASS |  |' "$TMP_DIR/pass.md"
grep -Fq '| F23 | 55 | 5 | 75 | 5 | 83 | +8 | true | false | complexity.high | 2.00x | PASS |  |' "$TMP_DIR/pass.md"

write_fixture nan-result F21 50 75 85 true
cat > "$TMP_DIR/nan-result/F21/l2_risk_probes/result.json" <<'EOF'
{"timed_out": false, "invoke_failure": false, "disqualifier": false, "elapsed_seconds": NaN, "pair_mode": true, "pair_trigger": {"eligible": true, "reasons": ["complexity.high"], "skipped_reason": null}, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
EOF
expect_fail_contains nan-result-json "l2_risk_probes result.json malformed" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id nan-result --min-fixtures 1

write_fixture rejected-direct F2 50 75 85 true
write_fixture rejected-direct F21 50 75 85 true
expect_fail_contains rejected-direct "fixture rejected for pair-candidate runs" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id rejected-direct --min-fixtures 1

write_fixture rejected-shadow-direct S3-cli-ticket-assignment 50 75 85 true
write_fixture rejected-shadow-direct F21 50 75 85 true
expect_fail_contains rejected-shadow-direct "fixture rejected for pair-candidate runs" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id rejected-shadow-direct --min-fixtures 1

write_fixture partial-baseline F21 50 75 85 true
write_fixture partial-baseline F23 55 75 90 true
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
  --max-pair-solo-wall-ratio 3 \
  --out-json "$TMP_DIR/partial-baseline.json" \
  --out-md "$TMP_DIR/partial-baseline.md"
grep -Fq '"verdict": "PASS"' "$TMP_DIR/partial-baseline.json"
grep -Fq '| F21 | 50 | 10 | 75 | 5 | 85 | +10 | true | false | complexity.high | 2.00x | PASS |  |' "$TMP_DIR/partial-baseline.md"

write_fixture no-headroom F21 50 81 90 true
write_fixture no-headroom F23 55 75 83 true
expect_fail_contains no-headroom "solo_claude score 81 > 80" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id no-headroom

write_fixture marginal-headroom F21 59 66 85 true
write_fixture marginal-headroom F23 50 75 82 true
expect_fail_contains marginal-headroom "bare headroom 1 < 5" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id marginal-headroom

write_fixture dirty-bare F21 50 75 85 true
python3 - "$TMP_DIR/dirty-bare/F21/bare/result.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["disqualifier"] = True
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains dirty-bare "bare result disqualifier" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id dirty-bare --min-fixtures 1

write_fixture dirty-solo F21 50 75 85 true
python3 - "$TMP_DIR/dirty-solo/F21/solo_claude/verify.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["disqualifier"] = True
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains dirty-solo "solo_claude verify disqualifier" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id dirty-solo --min-fixtures 1

write_fixture control-ceiling F22-cli-ledger-close 94 98 99 true 140 100 l2_risk_probes
write_fixture control-ceiling F26-cli-payout-ledger-rules 25 98 99 true 140 100 l2_risk_probes
expect_fail_contains control-ceiling "solo_claude score 98 > 80" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id control-ceiling \
    --pair-arm l2_risk_probes --min-fixtures 2
python3 "$GATE" --results-root "$TMP_DIR" --run-id control-ceiling \
  --pair-arm l2_risk_probes --min-fixtures 2 \
  --out-json "$TMP_DIR/control-ceiling.json" \
  --out-md "$TMP_DIR/control-ceiling.md" >/dev/null 2>&1 || true
grep -Fq '"verdict": "FAIL"' "$TMP_DIR/control-ceiling.json"
grep -Fq 'F22-cli-ledger-close' "$TMP_DIR/control-ceiling.md"
grep -Fq 'F26-cli-payout-ledger-rules' "$TMP_DIR/control-ceiling.md"

write_fixture no-pair-mode F21 50 75 85 false 200 100 l2_gated
write_fixture no-pair-mode F23 55 75 85 true 200 100 l2_gated
expect_fail_contains no-pair-mode "l2_gated pair_mode not true" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id no-pair-mode \
    --pair-arm l2_gated

write_fixture malformed-pair-trigger F21 50 75 85 true
python3 - "$TMP_DIR/malformed-pair-trigger/F21/l2_risk_probes/result.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["pair_trigger"] = {"eligible": True, "reasons": "complexity.high", "skipped_reason": None}
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains malformed-pair-trigger "l2_risk_probes pair_trigger.reasons malformed" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id malformed-pair-trigger --min-fixtures 1

write_fixture unknown-pair-trigger-reason F21 50 75 85 true
python3 - "$TMP_DIR/unknown-pair-trigger-reason/F21/l2_risk_probes/result.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["pair_trigger"] = {"eligible": True, "reasons": ["looks-hard"], "skipped_reason": None}
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains unknown-pair-trigger-reason "l2_risk_probes pair_trigger reasons missing known trigger reason" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id unknown-pair-trigger-reason --min-fixtures 1

write_fixture mixed-unknown-pair-trigger-reason F21 50 75 85 true
python3 - "$TMP_DIR/mixed-unknown-pair-trigger-reason/F21/l2_risk_probes/result.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["pair_trigger"] = {"eligible": True, "reasons": ["complexity.high", "looks-hard"], "skipped_reason": None}
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains mixed-unknown-pair-trigger-reason "l2_risk_probes pair_trigger reasons contain unknown trigger reason" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id mixed-unknown-pair-trigger-reason --min-fixtures 1

write_fixture normalized-canonical-pair-trigger-reason F21 50 75 85 true
python3 - "$TMP_DIR/normalized-canonical-pair-trigger-reason/F21/l2_risk_probes/result.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["pair_trigger"] = {"eligible": True, "reasons": ["risk high"], "skipped_reason": None}
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains normalized-canonical-pair-trigger-reason "l2_risk_probes pair_trigger reasons missing known trigger reason" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id normalized-canonical-pair-trigger-reason --min-fixtures 1

write_fixture historical-only-pair-trigger-reason F21 50 75 85 true
python3 - "$TMP_DIR/historical-only-pair-trigger-reason/F21/l2_risk_probes/result.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["pair_trigger"] = {"eligible": True, "reasons": ["risk_profile.high_risk"], "skipped_reason": None}
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains historical-only-pair-trigger-reason "l2_risk_probes pair_trigger reasons missing canonical trigger reason" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id historical-only-pair-trigger-reason --min-fixtures 1

write_fixture missing-hypothesis-trigger F16-cli-quote-tax-rules 50 75 85 true
expect_fail_contains missing-hypothesis-trigger "l2_risk_probes pair_trigger missing spec.solo_headroom_hypothesis" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id missing-hypothesis-trigger --min-fixtures 1 --require-hypothesis-trigger
python3 - "$TMP_DIR/missing-hypothesis-trigger/F16-cli-quote-tax-rules/l2_risk_probes/result.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["pair_trigger"]["reasons"] = ["complexity.high", "spec.solo_headroom_hypothesis"]
json.dump(data, open(path, "w"), indent=2)
PY
python3 "$GATE" --results-root "$TMP_DIR" --run-id missing-hypothesis-trigger \
  --min-fixtures 1 \
  --require-hypothesis-trigger \
  --out-json "$TMP_DIR/hypothesis-trigger-pass.json" \
  --out-md "$TMP_DIR/hypothesis-trigger-pass.md"
grep -Fq '"verdict": "PASS"' "$TMP_DIR/hypothesis-trigger-pass.json"
grep -Fq '"require_hypothesis_trigger": true' "$TMP_DIR/hypothesis-trigger-pass.json"
grep -Fq '"pair_trigger_has_hypothesis_reason": true' "$TMP_DIR/hypothesis-trigger-pass.json"
grep -Fq 'Hypothesis trigger required: true' "$TMP_DIR/hypothesis-trigger-pass.md"
grep -Fq '| F16-cli-quote-tax-rules | 50 | 10 | 75 | 5 | 85 | +10 | true | true | complexity.high,spec.solo_headroom_hypothesis | 2.00x | PASS |  |' "$TMP_DIR/hypothesis-trigger-pass.md"
grep -Fq 'complexity.high,spec.solo_headroom_hypothesis' "$TMP_DIR/hypothesis-trigger-pass.md"

write_fixture weak-margin F21 50 75 79 true
write_fixture weak-margin F23 55 75 88 true
expect_fail_contains weak-margin "l2_risk_probes margin +4 < +5" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id weak-margin

write_fixture dirty-pair F21 50 75 85 true
python3 - "$TMP_DIR/dirty-pair/F21/l2_risk_probes/verify.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["disqualifier"] = True
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains dirty-pair "l2_risk_probes verify disqualifier" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id dirty-pair --min-fixtures 1

write_fixture dirty-pair-verify-score F21 50 75 85 true
python3 - "$TMP_DIR/dirty-pair-verify-score/F21/l2_risk_probes/verify.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["verify_score"] = 0.75
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains dirty-pair-verify-score "l2_risk_probes verify_score < 1.0" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id dirty-pair-verify-score --min-fixtures 1

write_fixture boolean-pair-verify-score F21 50 75 85 true
python3 - "$TMP_DIR/boolean-pair-verify-score/F21/l2_risk_probes/verify.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["verify_score"] = True
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains boolean-pair-verify-score "l2_risk_probes verify_score < 1.0" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id boolean-pair-verify-score --min-fixtures 1

write_fixture dirty-pair-verdict F21 50 75 85 true
python3 - "$TMP_DIR/dirty-pair-verdict/F21/l2_risk_probes/result.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["terminal_verdict"] = "BLOCKED:probe-derive-malformed"
data["verify_verdict"] = "BLOCKED"
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains dirty-pair-verdict "l2_risk_probes terminal verdict not pass" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id dirty-pair-verdict --min-fixtures 1

write_fixture dirty-pair-axis F21 50 75 85 true
python3 - "$TMP_DIR/dirty-pair-axis/F21/judge.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["_blind_mapping"] = {"A": "bare", "B": "solo_claude", "C": "l2_risk_probes", "seed": 1}
data["_axis_validation"] = {
    "out_of_range_count": 1,
    "out_of_range_cells": [{"breakdown": "c_breakdown", "axis": "quality", "value": 26}],
    "axis_range": [0, 25],
}
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains dirty-pair-axis "l2_risk_probes judge axis-invalid (1)" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id dirty-pair-axis --min-fixtures 1

write_fixture dirty-solo-axis F21 50 75 85 true
python3 - "$TMP_DIR/dirty-solo-axis/F21/judge.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["_blind_mapping"] = {"A": "bare", "B": "solo_claude", "C": "l2_risk_probes", "seed": 1}
data["_axis_validation"] = {
    "out_of_range_count": 1,
    "out_of_range_cells": [{"breakdown": "b_breakdown", "axis": "quality", "value": 26}],
    "axis_range": [0, 25],
}
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains dirty-solo-axis "solo_claude judge axis-invalid (1)" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id dirty-solo-axis --min-fixtures 1

write_fixture unmapped-axis F21 50 75 85 true
python3 - "$TMP_DIR/unmapped-axis/F21/judge.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["_blind_mapping"] = {"A": "bare", "B": "solo_claude", "C": "l2_forced", "seed": 1}
data["_axis_validation"] = {
    "out_of_range_count": 1,
    "out_of_range_cells": [{"breakdown": "c_breakdown", "axis": "quality", "value": 26}],
    "axis_range": [0, 25],
}
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains unmapped-axis "judge axis-invalid unmapped (1)" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id unmapped-axis --min-fixtures 1

write_fixture missing-mapping F21 50 75 85 true
python3 - "$TMP_DIR/missing-mapping/F21/judge.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
del data["_blind_mapping"]
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains missing-mapping "judge blind mapping missing" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id missing-mapping --min-fixtures 1
python3 "$GATE" --results-root "$TMP_DIR" --run-id missing-mapping --min-fixtures 1 \
  --out-json "$TMP_DIR/missing-mapping.json" >/dev/null 2>&1 || true
grep -Fq '"bare_score": null' "$TMP_DIR/missing-mapping.json"
grep -Fq '"solo_score": null' "$TMP_DIR/missing-mapping.json"
grep -Fq '"pair_score": null' "$TMP_DIR/missing-mapping.json"

write_fixture malformed-mapping-axis F21 50 75 85 true
python3 - "$TMP_DIR/malformed-mapping-axis/F21/judge.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["_blind_mapping"] = "not-a-dict"
data["_axis_validation"] = {
    "out_of_range_count": 1,
    "out_of_range_cells": [{"breakdown": "c_breakdown", "axis": "quality", "value": 26}],
    "axis_range": [0, 25],
}
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains malformed-mapping-axis "judge blind mapping missing" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id malformed-mapping-axis --min-fixtures 1
python3 "$GATE" --results-root "$TMP_DIR" --run-id malformed-mapping-axis --min-fixtures 1 \
  --out-json "$TMP_DIR/malformed-mapping-axis.json" >/dev/null 2>&1 || true
grep -Fq '"bare_score": null' "$TMP_DIR/malformed-mapping-axis.json"
grep -Fq '"solo_score": null' "$TMP_DIR/malformed-mapping-axis.json"
grep -Fq '"pair_score": null' "$TMP_DIR/malformed-mapping-axis.json"

write_fixture wrong-pair-mapping F21 50 75 85 true
python3 - "$TMP_DIR/wrong-pair-mapping/F21/judge.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["_blind_mapping"] = {"A": "bare", "B": "solo_claude", "C": "l2_gated", "seed": 1}
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains wrong-pair-mapping "judge blind mapping missing arm(s): l2_risk_probes" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id wrong-pair-mapping --min-fixtures 1
python3 "$GATE" --results-root "$TMP_DIR" --run-id wrong-pair-mapping --min-fixtures 1 \
  --out-json "$TMP_DIR/wrong-pair-mapping.json" >/dev/null 2>&1 || true
grep -Fq '"bare_score": 50' "$TMP_DIR/wrong-pair-mapping.json"
grep -Fq '"solo_score": 75' "$TMP_DIR/wrong-pair-mapping.json"
grep -Fq '"pair_score": null' "$TMP_DIR/wrong-pair-mapping.json"
grep -Fq '"pair_margin": null' "$TMP_DIR/wrong-pair-mapping.json"

write_fixture malformed-scores F21 50 75 85 true
python3 - "$TMP_DIR/malformed-scores/F21/judge.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["scores_by_arm"] = ["not", "a", "dict"]
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains malformed-scores "bare score missing" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id malformed-scores --min-fixtures 1
python3 "$GATE" --results-root "$TMP_DIR" --run-id malformed-scores --min-fixtures 1 \
  --out-json "$TMP_DIR/malformed-scores.json" >/dev/null 2>&1 || true
grep -Fq '"bare_score": null' "$TMP_DIR/malformed-scores.json"
grep -Fq '"solo_score": null' "$TMP_DIR/malformed-scores.json"
grep -Fq '"pair_score": null' "$TMP_DIR/malformed-scores.json"
grep -Fq '"pair_margin": null' "$TMP_DIR/malformed-scores.json"

write_fixture overrange-score F21 50 75 101 true
expect_fail_contains overrange-score "l2_risk_probes score missing" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id overrange-score --min-fixtures 1

write_fixture boolean-score F21 true 75 85 true
expect_fail_contains boolean-score "bare score missing" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id boolean-score --min-fixtures 1

write_fixture boolean-wall-time F21 50 75 85 true true 100
expect_fail_contains boolean-wall-time "pair/solo wall ratio missing" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id boolean-wall-time --min-fixtures 1

write_fixture dirty-pair-env F21 50 75 85 true
python3 - "$TMP_DIR/dirty-pair-env/F21/l2_risk_probes/result.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["environment_contamination"] = True
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains dirty-pair-env "l2_risk_probes environment contamination" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id dirty-pair-env --min-fixtures 1

write_fixture malformed-pair-bool F21 50 75 85 true
python3 - "$TMP_DIR/malformed-pair-bool/F21/l2_risk_probes/result.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["timed_out"] = "false"
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains malformed-pair-bool "l2_risk_probes result timed_out malformed" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id malformed-pair-bool --min-fixtures 1

write_fixture malformed-judge-bool F21 50 75 85 true
python3 - "$TMP_DIR/malformed-judge-bool/F21/judge.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["disqualifiers_by_arm"] = {"l2_risk_probes": {"disqualifier": "false"}}
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains malformed-judge-bool "l2_risk_probes judge disqualifier malformed" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id malformed-judge-bool --min-fixtures 1

write_fixture missing-pair-diff F21 50 75 85 true
rm "$TMP_DIR/missing-pair-diff/F21/l2_risk_probes/diff.patch"
expect_fail_contains missing-pair-diff "l2_risk_probes diff.patch missing" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id missing-pair-diff --min-fixtures 1

write_fixture malformed-result-artifact F21 50 75 85 true
printf '["not", "a", "dict"]\n' > "$TMP_DIR/malformed-result-artifact/F21/l2_risk_probes/result.json"
expect_fail_contains malformed-result-artifact "l2_risk_probes result.json malformed" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id malformed-result-artifact --min-fixtures 1

write_fixture malformed-verify-artifact F21 50 75 85 true
printf '["not", "a", "dict"]\n' > "$TMP_DIR/malformed-verify-artifact/F21/l2_risk_probes/verify.json"
expect_fail_contains malformed-verify-artifact "l2_risk_probes verify.json malformed" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id malformed-verify-artifact --min-fixtures 1

write_fixture malformed-judge-artifact F21 50 75 85 true
printf '["not", "a", "dict"]\n' > "$TMP_DIR/malformed-judge-artifact/F21/judge.json"
expect_fail_contains malformed-judge-artifact "judge.json malformed" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id malformed-judge-artifact --min-fixtures 1

write_fixture custom-pair-arm F21 50 75 82 true 220 110 l2_gated
write_fixture custom-pair-arm F23 55 75 83 true 280 140 l2_gated
python3 "$GATE" --results-root "$TMP_DIR" --run-id custom-pair-arm \
  --pair-arm l2_gated \
  --max-pair-solo-wall-ratio 3 \
  --out-json "$TMP_DIR/custom-pair-arm.json" \
  --out-md "$TMP_DIR/custom-pair-arm.md"
grep -Fq '"pair_arm": "l2_gated"' "$TMP_DIR/custom-pair-arm.json"
grep -Fq 'l2_gated must be evidence-clean' "$TMP_DIR/custom-pair-arm.json"
grep -Fq 'pair_trigger eligible with a canonical reason' "$TMP_DIR/custom-pair-arm.json"
grep -Fq 'l2_gated - solo_claude >= 5' "$TMP_DIR/custom-pair-arm.md"

write_fixture provider-limit F21 50 75 85 true 37 100 l2_risk_probes
python3 - "$TMP_DIR/provider-limit/F21/l2_risk_probes/result.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["invoke_failure"] = True
data["invoke_failure_reason"] = "provider_limit"
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains provider-limit "l2_risk_probes invoke failure (provider_limit)" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id provider-limit \
    --pair-arm l2_risk_probes --min-fixtures 1
python3 "$GATE" --results-root "$TMP_DIR" --run-id provider-limit \
  --pair-arm l2_risk_probes --min-fixtures 1 \
  --out-json "$TMP_DIR/provider-limit.json" \
  --out-md "$TMP_DIR/provider-limit.md" >/dev/null 2>&1 || true
grep -Fq '"pair_margin": null' "$TMP_DIR/provider-limit.json"
grep -Fq '"avg_pair_margin": null' "$TMP_DIR/provider-limit.json"
grep -Fq '"pair_solo_wall_ratio": null' "$TMP_DIR/provider-limit.json"
if grep -Fq 'margin -' "$TMP_DIR/provider-limit.md"; then
  echo "provider-limit row must not report quality margin" >&2
  cat "$TMP_DIR/provider-limit.md" >&2
  exit 1
fi

write_fixture slow-pair F21 50 75 85 true 401 100
write_fixture slow-pair F23 55 75 83 true 280 140
expect_fail_contains slow-pair "pair/solo wall ratio 4.01 > 3.00" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id slow-pair
python3 "$GATE" --results-root "$TMP_DIR" --run-id slow-pair \
  --max-pair-solo-wall-ratio 5 \
  --out-json "$TMP_DIR/slow-pair-diagnostic.json" >/dev/null
grep -Fq '"verdict": "PASS"' "$TMP_DIR/slow-pair-diagnostic.json"

write_fixture one-fixture F21 50 75 85 true
expect_fail_contains one-fixture "fixture_count_ok" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id one-fixture --out-json "$TMP_DIR/one-fixture.json"
grep -Fq '"fixture_count_ok": false' "$TMP_DIR/one-fixture.json"

write_fixture malformed-dq F21 50 75 85 true
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

write_fixture malformed-dq-entry F21 50 75 85 true
python3 - "$TMP_DIR/malformed-dq-entry/F21/judge.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["disqualifiers_by_arm"] = {"l2_risk_probes": True}
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains malformed-dq-entry "l2_risk_probes judge disqualifier" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id malformed-dq-entry --min-fixtures 1

write_fixture malformed-axis-wrapper F21 50 75 85 true
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

expect_fail_contains invalid-min-pair-margin "value must be > 0" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id pass --min-pair-margin 0

expect_fail_contains invalid-max-wall-ratio "value must be finite and > 0" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id pass --max-pair-solo-wall-ratio nan

expect_fail_contains invalid-min-fixtures "value must be > 0" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id pass --min-fixtures 0

expect_fail_contains invalid-min-bare-headroom "value must be >= 0" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id pass --min-bare-headroom -1

expect_fail_contains invalid-min-solo-headroom "value must be >= 0" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id pass --min-solo-headroom -1

expect_fail_contains invalid-pair-arm "pair-arm must be one of" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id pass --pair-arm variant

expect_fail_contains retired-pair-arm "pair-arm l2_forced is retired" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id pass --pair-arm l2_forced

echo "PASS test-full-pipeline-pair-gate"
