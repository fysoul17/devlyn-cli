#!/usr/bin/env bash
# Regression tests for pair-candidate-frontier.py.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$SCRIPT_DIR/pair-candidate-frontier.py"
TMP_DIR="$(mktemp -d /tmp/pair-candidate-frontier-test.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

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
  if ! grep -Fq -- "$needle" "$out"; then
    echo "missing expected text for $label: $needle" >&2
    cat "$out" >&2
    exit 1
  fi
}

fixtures="$TMP_DIR/fixtures"
results="$TMP_DIR/results"
mkdir -p "$fixtures/F2-cli-medium-subcommand" \
  "$fixtures/F16-cli-quote-tax-rules" \
  "$fixtures/F21-cli-scheduler-priority" \
  "$fixtures/F22-cli-low-margin" \
  "$fixtures/F23-cli-high-wall" \
  "$fixtures/retired/F99-retired"

cat > "$TMP_DIR/pair-rejected-fixtures.sh" <<'SH'
rejected_pair_fixture_reason() {
  local fid="$1"
  case "$fid" in
    F2-*|F2)
      echo "measured ceiling"
      ;;
    *)
      return 1
      ;;
  esac
}
SH

mkdir -p "$results/pass-run"
cat > "$results/pass-run/full-pipeline-pair-gate.json" <<'JSON'
{
  "run_id": "pass-run",
  "verdict": "PASS",
  "pair_arm": "l2_risk_probes",
  "rows": [
    {
      "fixture": "F16-cli-quote-tax-rules",
      "status": "PASS",
      "bare_score": 50,
      "solo_score": 75,
      "pair_score": 96,
      "pair_margin": 21,
      "pair_mode": true,
      "pair_trigger_eligible": true,
      "pair_trigger_reasons": ["complexity.high"],
      "pair_trigger_has_canonical_reason": true,
      "pair_solo_wall_ratio": 1.28
    }
  ]
}
JSON

mkdir -p "$results/incomplete-high-run"
cat > "$results/incomplete-high-run/full-pipeline-pair-gate.json" <<'JSON'
{
  "run_id": "incomplete-high-run",
  "verdict": "PASS",
  "rows": [
    {
      "fixture": "F16-cli-quote-tax-rules",
      "status": "PASS",
      "bare_score": 50,
      "solo_score": 75,
      "pair_score": 98,
      "pair_margin": 23,
      "pair_mode": true,
      "pair_trigger_eligible": true,
      "pair_solo_wall_ratio": 1.32
    }
  ]
}
JSON

mkdir -p "$results/low-margin-run"
cat > "$results/low-margin-run/full-pipeline-pair-gate.json" <<'JSON'
{
  "run_id": "low-margin-run",
  "verdict": "PASS",
  "pair_arm": "l2_risk_probes",
  "rows": [
    {
      "fixture": "F22-cli-low-margin",
      "status": "PASS",
      "bare_score": 50,
      "solo_score": 80,
      "pair_score": 84,
      "pair_margin": 4,
      "pair_mode": true,
      "pair_trigger_eligible": true,
      "pair_trigger_reasons": ["complexity.high"],
      "pair_trigger_has_canonical_reason": true,
      "pair_solo_wall_ratio": 1.1
    }
  ]
}
JSON

mkdir -p "$results/high-wall-run"
cat > "$results/high-wall-run/full-pipeline-pair-gate.json" <<'JSON'
{
  "run_id": "high-wall-run",
  "verdict": "PASS",
  "pair_arm": "l2_risk_probes",
  "rows": [
    {
      "fixture": "F23-cli-high-wall",
      "status": "PASS",
      "bare_score": 45,
      "solo_score": 70,
      "pair_score": 91,
      "pair_margin": 21,
      "pair_mode": true,
      "pair_trigger_eligible": true,
      "pair_trigger_reasons": ["complexity.high"],
      "pair_trigger_has_canonical_reason": true,
      "pair_solo_wall_ratio": 3.5
    }
  ]
}
JSON

mkdir -p "$results/nan-wall-run"
cat > "$results/nan-wall-run/full-pipeline-pair-gate.json" <<'JSON'
{
  "run_id": "nan-wall-run",
  "verdict": "PASS",
  "pair_arm": "l2_risk_probes",
  "rows": [
    {
      "fixture": "F21-cli-scheduler-priority",
      "status": "PASS",
      "bare_score": 45,
      "solo_score": 70,
      "pair_score": 91,
      "pair_margin": 21,
      "pair_mode": true,
      "pair_trigger_eligible": true,
      "pair_solo_wall_ratio": NaN
    }
  ]
}
JSON
expect_fail_contains nan-json-constant "pair evidence artifact malformed" \
  python3 "$SCRIPT" \
    --fixtures-root "$fixtures" \
    --registry "$TMP_DIR/pair-rejected-fixtures.sh" \
    --results-root "$results"
rm -rf "$results/nan-wall-run"

mkdir -p "$results/inflated-margin-run"
cat > "$results/inflated-margin-run/full-pipeline-pair-gate.json" <<'JSON'
{
  "run_id": "inflated-margin-run",
  "verdict": "PASS",
  "pair_arm": "l2_risk_probes",
  "rows": [
    {
      "fixture": "F21-cli-scheduler-priority",
      "status": "PASS",
      "bare_score": 45,
      "solo_score": 70,
      "pair_score": 71,
      "pair_margin": 21,
      "pair_mode": true,
      "pair_trigger_eligible": true,
      "pair_solo_wall_ratio": 1.2
    }
  ]
}
JSON

mkdir -p "$results/overrange-score-run"
cat > "$results/overrange-score-run/full-pipeline-pair-gate.json" <<'JSON'
{
  "run_id": "overrange-score-run",
  "verdict": "PASS",
  "pair_arm": "l2_risk_probes",
  "rows": [
    {
      "fixture": "F21-cli-scheduler-priority",
      "status": "PASS",
      "bare_score": 45,
      "solo_score": 70,
      "pair_score": 101,
      "pair_margin": 31,
      "pair_mode": true,
      "pair_trigger_eligible": true,
      "pair_solo_wall_ratio": 1.2
    }
  ]
}
JSON

mkdir -p "$results/invalid-arm-run"
cat > "$results/invalid-arm-run/full-pipeline-pair-gate.json" <<'JSON'
{
  "run_id": "invalid-arm-run",
  "verdict": "PASS",
  "pair_arm": "bare",
  "rows": [
    {
      "fixture": "F21-cli-scheduler-priority",
      "status": "PASS",
      "bare_score": 45,
      "solo_score": 70,
      "pair_score": 91,
      "pair_margin": 21,
      "pair_mode": true,
      "pair_trigger_eligible": true,
      "pair_solo_wall_ratio": 1.2
    }
  ]
}
JSON

mkdir -p "$results/false-pair-mode-run"
cat > "$results/false-pair-mode-run/full-pipeline-pair-gate.json" <<'JSON'
{
  "run_id": "false-pair-mode-run",
  "verdict": "PASS",
  "pair_arm": "l2_risk_probes",
  "rows": [
    {
      "fixture": "F21-cli-scheduler-priority",
      "status": "PASS",
      "bare_score": 45,
      "solo_score": 70,
      "pair_score": 91,
      "pair_margin": 21,
      "pair_mode": false,
      "pair_solo_wall_ratio": 1.2
    }
  ]
}
JSON

mkdir -p "$results/zero-wall-run"
cat > "$results/zero-wall-run/full-pipeline-pair-gate.json" <<'JSON'
{
  "run_id": "zero-wall-run",
  "verdict": "PASS",
  "pair_arm": "l2_risk_probes",
  "rows": [
    {
      "fixture": "F21-cli-scheduler-priority",
      "status": "PASS",
      "bare_score": 45,
      "solo_score": 70,
      "pair_score": 91,
      "pair_margin": 21,
      "pair_mode": true,
      "pair_trigger_eligible": true,
      "pair_solo_wall_ratio": 0
    }
  ]
}
JSON

expect_fail_contains missing-registry "rejected fixture registry missing" \
  python3 "$SCRIPT" \
    --fixtures-root "$fixtures" \
    --registry "$TMP_DIR/missing.sh" \
    --results-root "$results"

empty_registry="$TMP_DIR/empty-registry.sh"
: > "$empty_registry"
expect_fail_contains empty-registry "rejected fixture registry has no fixture entries" \
  python3 "$SCRIPT" \
    --fixtures-root "$fixtures" \
    --registry "$empty_registry" \
    --results-root "$results"

s_only_registry="$TMP_DIR/s-only-registry.sh"
cat > "$s_only_registry" <<'SH'
rejected_pair_fixture_reason() {
  local fid="$1"
  case "$fid" in
    S3-*|S3)
      echo "shadow solo ceiling"
      ;;
    *)
      return 1
      ;;
  esac
}
SH
python3 - "$SCRIPT" "$s_only_registry" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("pair_candidate_frontier", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
assert module.registry_short_ids(pathlib.Path(sys.argv[2])) == {"S3"}
PY

mkdir -p "$results/bad-json-run"
printf '{not-json\n' > "$results/bad-json-run/full-pipeline-pair-gate.json"
expect_fail_contains bad-pair-evidence-json "pair evidence artifact malformed" \
  python3 "$SCRIPT" \
    --fixtures-root "$fixtures" \
    --registry "$TMP_DIR/pair-rejected-fixtures.sh" \
    --results-root "$results"
rm -rf "$results/bad-json-run"

mkdir -p "$results/bad-rows-run"
cat > "$results/bad-rows-run/full-pipeline-pair-gate.json" <<'JSON'
{
  "run_id": "bad-rows-run",
  "verdict": "PASS",
  "pair_arm": "l2_risk_probes",
  "rows": []
}
JSON
expect_fail_contains bad-pair-evidence-rows "pair evidence artifact rows malformed" \
  python3 "$SCRIPT" \
    --fixtures-root "$fixtures" \
    --registry "$TMP_DIR/pair-rejected-fixtures.sh" \
    --results-root "$results"
rm -rf "$results/bad-rows-run"

mkdir -p "$results/direct-trigger-run/F16-cli-quote-tax-rules/l2_risk_probes"
cat > "$results/direct-trigger-run/F16-cli-quote-tax-rules/l2_risk_probes/result.json" <<'JSON'
{
  "pair_trigger": {
    "eligible": true,
    "reasons": ["complexity.high", "looks-hard"],
    "skipped_reason": null
  }
}
JSON
python3 - "$SCRIPT" "$results" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("pair_candidate_frontier", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
results_root = pathlib.Path(sys.argv[2])
kwargs = {
    "results_root": results_root,
    "run_id": "direct-trigger-run",
    "fixture": "F16-cli-quote-tax-rules",
    "pair_arm": "l2_risk_probes",
}
assert module.pair_result_trigger_reasons(**kwargs) == []
path = (
    results_root
    / "direct-trigger-run"
    / "F16-cli-quote-tax-rules"
    / "l2_risk_probes"
    / "result.json"
)
path.write_text(
    '{"pair_trigger":{"eligible":true,"reasons":["complexity.high","risk_profile.high_risk"],"skipped_reason":null}}\n',
    encoding="utf8",
)
assert module.pair_result_trigger_reasons(**kwargs) == [
    "complexity.high",
    "risk_profile.high_risk",
]
path.write_text(
    '{"pair_trigger":{"eligible":true,"reasons":["risk high"],"skipped_reason":null}}\n',
    encoding="utf8",
)
assert module.pair_result_trigger_reasons(**kwargs) == []
PY

python3 "$SCRIPT" \
  --fixtures-root "$fixtures" \
  --registry "$TMP_DIR/pair-rejected-fixtures.sh" \
  --results-root "$results" \
  --out-json "$TMP_DIR/frontier.json" \
  --out-md "$TMP_DIR/frontier.md" \
  > "$TMP_DIR/frontier.stdout"

python3 - "$TMP_DIR/frontier.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf8"))
assert report["verdict"] == "FAIL"
assert report["min_pair_margin"] == 5
assert report["max_pair_solo_wall_ratio"] == 3.0
assert report["fixtures_total"] == 5
assert report["rejected_total"] == 1
assert report["candidate_total"] == 4
assert report["pair_evidence_total"] == 1
assert report["unmeasured_candidate_total"] == 3
assert report["rejected_count"] == 1
assert report["candidate_count"] == 4
assert report["pair_evidence_count"] == 1
assert report["unmeasured_count"] == 3
assert report["pair_margin_avg"] == 21
assert report["pair_margin_min"] == 21
assert report["pair_solo_wall_ratio_avg"] == 1.28
assert report["pair_solo_wall_ratio_max"] == 1.28
rows = {row["fixture"]: row for row in report["rows"]}
assert rows["F2-cli-medium-subcommand"]["status"] == "rejected"
assert rows["F2-cli-medium-subcommand"]["rejected_reason"] == "measured ceiling"
assert rows["F16-cli-quote-tax-rules"]["status"] == "pair_evidence_passed"
assert len(rows["F16-cli-quote-tax-rules"]["passing_pair_evidence"]) == 1
assert rows["F16-cli-quote-tax-rules"]["passing_pair_evidence"][0]["run_id"] == "pass-run"
assert rows["F21-cli-scheduler-priority"]["status"] == "candidate_unmeasured"
assert rows["F22-cli-low-margin"]["status"] == "candidate_unmeasured"
assert rows["F23-cli-high-wall"]["status"] == "candidate_unmeasured"
PY

grep -Fq 'fixtures=5 rejected=1 candidates=4 pair_evidence=1 unmeasured=3 verdict=FAIL' "$TMP_DIR/frontier.stdout"
grep -Fq 'pair_margin_avg=+21.00 pair_margin_min=+21 wall_avg=1.28x wall_max=1.28x' "$TMP_DIR/frontier.stdout"
grep -Fq 'F16-cli-quote-tax-rules: bare=50 solo_claude=75 pair=96 arm=l2_risk_probes margin=+21 wall=1.28x run=pass-run verdict=pair_evidence_passed triggers=complexity.high hypothesis_trigger=false' "$TMP_DIR/frontier.stdout"
grep -Fq 'FAIL pair-candidate-frontier' "$TMP_DIR/frontier.stdout"

grep -Fq 'Average pair margin: +21.00' "$TMP_DIR/frontier.md"
grep -Fq 'Verdict: FAIL' "$TMP_DIR/frontier.md"
grep -Fq 'Minimum pair margin required: +5' "$TMP_DIR/frontier.md"
grep -Fq 'Maximum pair/solo wall ratio allowed: 3.00x' "$TMP_DIR/frontier.md"
grep -Fq 'Maximum pair/solo wall ratio: 1.28x' "$TMP_DIR/frontier.md"
grep -Fq '| Fixture | Status | Verdict | Evidence | Pair arm | Triggers | Hypothesis trigger | Bare | Solo_claude | Pair | Margin | Wall ratio | Rejected reason |' "$TMP_DIR/frontier.md"
grep -Fq '| F2-cli-medium-subcommand | rejected | rejected |  |  |  |  |  |  |  |  |  | measured ceiling |' "$TMP_DIR/frontier.md"
grep -Fq '| F16-cli-quote-tax-rules | pair_evidence_passed | pair_evidence_passed | pass-run | l2_risk_probes | complexity.high | false | 50 | 75 | 96 | +21 | 1.28x |  |' "$TMP_DIR/frontier.md"
grep -Fq '| F21-cli-scheduler-priority | candidate_unmeasured | candidate_unmeasured |  |  |  |  |  |  |  |  |  |  |' "$TMP_DIR/frontier.md"

expect_fail_contains fail-on-unmeasured "unmeasured candidate fixture(s): F21-cli-scheduler-priority" \
  python3 "$SCRIPT" \
    --fixtures-root "$fixtures" \
    --registry "$TMP_DIR/pair-rejected-fixtures.sh" \
    --results-root "$results" \
    --fail-on-unmeasured
grep -Fq 'FAIL pair-candidate-frontier' "$TMP_DIR/fail-on-unmeasured.out"

set +e
python3 "$SCRIPT" \
  --fixtures-root "$fixtures" \
  --registry "$TMP_DIR/pair-rejected-fixtures.sh" \
  --results-root "$results" \
  --fail-on-unmeasured \
  > "$TMP_DIR/fail-on-unmeasured.json" \
  2> "$TMP_DIR/fail-on-unmeasured.stderr"
fail_on_unmeasured_status=$?
set -e
if [ "$fail_on_unmeasured_status" -eq 0 ]; then
  echo "expected pure JSON fail-on-unmeasured path to fail" >&2
  exit 1
fi
grep -Fq 'unmeasured candidate fixture(s): F21-cli-scheduler-priority' "$TMP_DIR/fail-on-unmeasured.stderr"
grep -Fq 'FAIL pair-candidate-frontier' "$TMP_DIR/fail-on-unmeasured.stderr"
if grep -Fq 'FAIL pair-candidate-frontier' "$TMP_DIR/fail-on-unmeasured.json"; then
  echo "pure JSON stdout must not include final text verdict" >&2
  cat "$TMP_DIR/fail-on-unmeasured.json" >&2
  exit 1
fi
python3 - "$TMP_DIR/fail-on-unmeasured.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf8"))
assert report["verdict"] == "FAIL"
assert report["unmeasured_candidate_total"] == 3
PY

python3 "$SCRIPT" \
  --fixtures-root "$fixtures" \
  --registry "$TMP_DIR/pair-rejected-fixtures.sh" \
  --results-root "$results" \
  --min-pair-margin 4 \
  --out-json "$TMP_DIR/frontier-margin4.json" \
  > "$TMP_DIR/frontier-margin4.stdout"
python3 - "$TMP_DIR/frontier-margin4.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf8"))
assert report["min_pair_margin"] == 4
rows = {row["fixture"]: row for row in report["rows"]}
assert rows["F22-cli-low-margin"]["status"] == "pair_evidence_passed"
PY

python3 "$SCRIPT" \
  --fixtures-root "$fixtures" \
  --registry "$TMP_DIR/pair-rejected-fixtures.sh" \
  --results-root "$results" \
  --max-pair-solo-wall-ratio 4 \
  --out-json "$TMP_DIR/frontier-wall4.json" \
  > "$TMP_DIR/frontier-wall4.stdout"
python3 - "$TMP_DIR/frontier-wall4.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf8"))
assert report["max_pair_solo_wall_ratio"] == 4.0
rows = {row["fixture"]: row for row in report["rows"]}
assert rows["F23-cli-high-wall"]["status"] == "pair_evidence_passed"
PY

expect_fail_contains bad-min-pair-margin "--min-pair-margin must be >= 1" \
  python3 "$SCRIPT" \
    --fixtures-root "$fixtures" \
    --registry "$TMP_DIR/pair-rejected-fixtures.sh" \
    --results-root "$results" \
    --min-pair-margin 0

expect_fail_contains bad-max-wall-ratio "--max-pair-solo-wall-ratio must be finite and > 0" \
  python3 "$SCRIPT" \
    --fixtures-root "$fixtures" \
    --registry "$TMP_DIR/pair-rejected-fixtures.sh" \
    --results-root "$results" \
    --max-pair-solo-wall-ratio 0

expect_fail_contains nan-max-wall-ratio "--max-pair-solo-wall-ratio must be finite and > 0" \
  python3 "$SCRIPT" \
    --fixtures-root "$fixtures" \
    --registry "$TMP_DIR/pair-rejected-fixtures.sh" \
    --results-root "$results" \
    --max-pair-solo-wall-ratio NaN

package_fixtures="$TMP_DIR/package-fixtures"
package_results="$TMP_DIR/package-results"
mkdir -p "$package_fixtures/F16-cli-quote-tax-rules" \
  "$package_fixtures/F21-cli-scheduler-priority" \
  "$package_fixtures/F23-cli-fulfillment-wave" \
  "$package_fixtures/F25-cli-cart-promotion-rules" \
  "$package_results/20260510-f16-f23-f25-combined-proof" \
  "$package_results/20260511-f21-current-riskprobes-v1"
cp "$SCRIPT_DIR/../results/20260510-f16-f23-f25-combined-proof/full-pipeline-pair-gate.json" \
  "$package_results/20260510-f16-f23-f25-combined-proof/full-pipeline-pair-gate.json"
cp "$SCRIPT_DIR/../results/20260511-f21-current-riskprobes-v1/full-pipeline-pair-gate.json" \
  "$package_results/20260511-f21-current-riskprobes-v1/full-pipeline-pair-gate.json"
for fixture in F16-cli-quote-tax-rules F23-cli-fulfillment-wave F25-cli-cart-promotion-rules; do
  mkdir -p "$package_results/20260510-f16-f23-f25-combined-proof/$fixture/l2_risk_probes"
  cp "$SCRIPT_DIR/../results/20260510-f16-f23-f25-combined-proof/$fixture/l2_risk_probes/result.json" \
    "$package_results/20260510-f16-f23-f25-combined-proof/$fixture/l2_risk_probes/result.json"
done
mkdir -p "$package_results/20260511-f21-current-riskprobes-v1/F21-cli-scheduler-priority/l2_risk_probes"
cp "$SCRIPT_DIR/../results/20260511-f21-current-riskprobes-v1/F21-cli-scheduler-priority/l2_risk_probes/result.json" \
  "$package_results/20260511-f21-current-riskprobes-v1/F21-cli-scheduler-priority/l2_risk_probes/result.json"
python3 "$SCRIPT" \
  --fixtures-root "$package_fixtures" \
  --registry "$SCRIPT_DIR/pair-rejected-fixtures.sh" \
  --results-root "$package_results" \
  --fail-on-unmeasured \
  --out-json "$TMP_DIR/package-frontier.json" \
  > "$TMP_DIR/package-frontier.out"
grep -Fq 'fixtures=4 rejected=0 candidates=4 pair_evidence=4 unmeasured=0' "$TMP_DIR/package-frontier.out"
grep -Fq 'PASS pair-candidate-frontier' "$TMP_DIR/package-frontier.out"
python3 - "$TMP_DIR/package-frontier.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf8"))
assert report["verdict"] == "PASS"
assert report["min_pair_margin"] == 5
assert report["max_pair_solo_wall_ratio"] == 3.0
assert report["fixtures_total"] == 4
assert report["pair_evidence_total"] == 4
assert report["unmeasured_candidate_total"] == 0
assert report["pair_evidence_count"] == 4
assert report["unmeasured_count"] == 0
assert report["pair_margin_avg"] is not None
assert report["pair_margin_min"] is not None
assert report["pair_solo_wall_ratio_avg"] is not None
assert report["pair_solo_wall_ratio_max"] is not None
PY

echo "PASS test-pair-candidate-frontier"
