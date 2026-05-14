#!/usr/bin/env bash
# Regression tests for audit-pair-evidence.py.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$SCRIPT_DIR/audit-pair-evidence.py"
TMP_DIR="$(mktemp -d /tmp/audit-pair-evidence-test.XXXXXX)"
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
registry="$TMP_DIR/pair-rejected-fixtures.sh"
mkdir -p "$fixtures/F16-cli-quote-tax-rules" \
  "$fixtures/F21-cli-scheduler-priority" \
  "$fixtures/F34-cli-rejected-candidate" \
  "$results/pair-pass" \
  "$results/pair-pass-2" \
  "$results/rejected-headroom"

cat > "$registry" <<'SH'
rejected_pair_fixture_reason() {
  local fid="$1"
  case "$fid" in
    F34-*|F34)
      echo "measured solo ceiling"
      ;;
    *)
      return 1
      ;;
  esac
}
SH

cat > "$results/pair-pass/full-pipeline-pair-gate.json" <<'JSON'
{
  "run_id": "pair-pass",
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

cat > "$results/rejected-headroom/headroom-gate.json" <<'JSON'
{
  "run_id": "rejected-headroom",
  "verdict": "FAIL",
  "rows": [
    {
      "fixture": "F34-cli-rejected-candidate",
      "status": "FAIL",
      "bare_score": 33,
      "solo_score": 98,
      "reason": "solo_claude score 98 > 80"
    }
  ]
}
JSON

expect_fail_contains unmeasured "unmeasured candidate fixture(s): F21-cli-scheduler-priority" \
  python3 "$SCRIPT" \
    --fixtures-root "$fixtures" \
    --registry "$registry" \
    --results-root "$results" \
    --out-dir "$TMP_DIR/out-fail"

expect_fail_contains bad-min-pair-evidence "--min-pair-evidence must be >= 1" \
  python3 "$SCRIPT" \
    --fixtures-root "$fixtures" \
    --registry "$registry" \
    --results-root "$results" \
    --min-pair-evidence 0

expect_fail_contains bad-min-pair-margin "--min-pair-margin must be >= 1" \
  python3 "$SCRIPT" \
    --fixtures-root "$fixtures" \
    --registry "$registry" \
    --results-root "$results" \
    --min-pair-margin 0

expect_fail_contains bad-max-wall-ratio "--max-pair-solo-wall-ratio must be finite and > 0" \
  python3 "$SCRIPT" \
    --fixtures-root "$fixtures" \
    --registry "$registry" \
    --results-root "$results" \
    --max-pair-solo-wall-ratio 0

expect_fail_contains nan-max-wall-ratio "--max-pair-solo-wall-ratio must be finite and > 0" \
  python3 "$SCRIPT" \
    --fixtures-root "$fixtures" \
    --registry "$registry" \
    --results-root "$results" \
    --max-pair-solo-wall-ratio NaN

cat > "$results/pair-pass-2/full-pipeline-pair-gate.json" <<'JSON'
{
  "run_id": "pair-pass-2",
  "verdict": "PASS",
  "pair_arm": "l2_risk_probes",
  "rows": [
    {
      "fixture": "F21-cli-scheduler-priority",
      "status": "PASS",
      "bare_score": 33,
      "solo_score": 66,
      "pair_score": 99,
      "pair_margin": 33,
      "pair_mode": true,
      "pair_trigger_eligible": true,
      "pair_trigger_reasons": ["complexity.high", "risk_profile.high_risk"],
      "pair_trigger_has_canonical_reason": true,
      "pair_solo_wall_ratio": 1.47
    }
  ]
}
JSON

expect_fail_contains pair-evidence-hypotheses "pair evidence hypotheses missing for fixture(s): F16-cli-quote-tax-rules, F21-cli-scheduler-priority" \
  python3 "$SCRIPT" \
    --fixtures-root "$fixtures" \
    --registry "$registry" \
    --results-root "$results" \
    --min-pair-evidence 2 \
    --out-dir "$TMP_DIR/out-hypothesis-fail"

for fixture in F16-cli-quote-tax-rules F21-cli-scheduler-priority; do
  cat > "$fixtures/$fixture/spec.md" <<'EOF'
# Spec

## Verification

- Visible pair-evidence fixture.

## Solo-headroom hypothesis

A capable solo_claude baseline is expected to miss the ordering interaction;
observable command `node "$BENCH_FIXTURE_DIR/verifiers/visible.js"` exposes the miss.
EOF
  cat > "$fixtures/$fixture/NOTES.md" <<'EOF'
# Notes
EOF
  cat > "$fixtures/$fixture/expected.json" <<'EOF'
{
  "verification_commands": [
    {
      "cmd": "node \"$BENCH_FIXTURE_DIR/verifiers/visible.js\"",
      "exit_code": 0
    }
  ]
}
EOF
done

python3 "$SCRIPT" \
  --fixtures-root "$fixtures" \
  --registry "$registry" \
  --results-root "$results" \
  --min-pair-evidence 2 \
  --out-dir "$TMP_DIR/out-pass" \
  > "$TMP_DIR/pass.out"
grep -Fq 'PASS audit-pair-evidence' "$TMP_DIR/pass.out"
test -f "$TMP_DIR/out-pass/frontier.json"
test -f "$TMP_DIR/out-pass/frontier.stdout"
test -f "$TMP_DIR/out-pass/frontier.stderr"
test -f "$TMP_DIR/out-pass/headroom-audit.json"
test -f "$TMP_DIR/out-pass/headroom-rejections.stdout"
test -f "$TMP_DIR/out-pass/headroom-rejections.stderr"
test -f "$TMP_DIR/out-pass/audit.json"
grep -Fq 'F16-cli-quote-tax-rules: bare=50 solo_claude=75 pair=96 arm=l2_risk_probes margin=+21' "$TMP_DIR/out-pass/frontier.stdout"
grep -Fq 'pair_margin_avg=+27.00 pair_margin_min=+21 wall_avg=1.38x wall_max=1.47x' "$TMP_DIR/out-pass/frontier.stdout"
grep -Fq 'verdict=pair_evidence_passed' "$TMP_DIR/out-pass/frontier.stdout"
grep -Fq 'PASS pair-candidate-frontier' "$TMP_DIR/out-pass/frontier.stdout"
grep -Fq 'headroom_rejections=PASS verdict=PASS unrecorded=0 unsupported=0' "$TMP_DIR/pass.out"
grep -Fq 'pair_evidence_quality=PASS min_pair_margin_actual=+21 min_pair_margin_required=+5 max_wall_actual=1.47x max_wall_allowed=3.00x' "$TMP_DIR/pass.out"
grep -Fq 'pair_trigger_reasons=PASS canonical=2 historical_alias=1 exposed=2 total=2 summary=2 rows_match=true' "$TMP_DIR/pass.out"
grep -Fq 'pair_trigger_historical_aliases=F21-cli-scheduler-priority=risk_profile.high_risk' "$TMP_DIR/pass.out"
grep -Fq 'pair_evidence_hypotheses=PASS documented=2 total=2' "$TMP_DIR/pass.out"
grep -Fq 'pair_evidence_hypothesis_triggers=WARN matched=0 documented=2 total=2' "$TMP_DIR/pass.out"
grep -Fq 'pair_evidence_hypothesis_trigger_gaps=F16-cli-quote-tax-rules=complexity.high;F21-cli-scheduler-priority=complexity.high,risk_profile.high_risk' "$TMP_DIR/pass.out"
python3 - "$TMP_DIR/out-pass/audit.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf8"))
assert report["verdict"] == "PASS"
assert report["min_pair_evidence"] == 2
assert report["min_pair_margin"] == 5
assert report["max_pair_solo_wall_ratio"] == 3.0
assert report["frontier_summary"]["min_pair_margin"] == 5
assert report["frontier_summary"]["max_pair_solo_wall_ratio"] == 3.0
assert report["frontier_summary"]["fixtures_total"] == 3
assert report["frontier_summary"]["candidate_count"] == 2
assert report["frontier_summary"]["pair_evidence_count"] == 2
assert report["frontier_summary"]["unmeasured_count"] == 0
assert report["frontier_summary"]["pair_margin_avg"] == 27
assert report["frontier_summary"]["pair_margin_min"] == 21
assert report["frontier_summary"]["pair_solo_wall_ratio_avg"] == 1.38
assert report["frontier_summary"]["pair_solo_wall_ratio_max"] == 1.47
assert report["pair_evidence_rows"] == [
    {
        "fixture": "F16-cli-quote-tax-rules",
        "verdict": "pair_evidence_passed",
        "run_id": "pair-pass",
        "pair_arm": "l2_risk_probes",
        "bare_score": 50,
        "solo_score": 75,
        "pair_score": 96,
        "pair_margin": 21,
        "pair_mode": True,
        "pair_trigger_eligible": True,
        "pair_trigger_reasons": ["complexity.high"],
        "pair_trigger_has_canonical_reason": True,
        "pair_trigger_has_hypothesis_reason": False,
        "pair_solo_wall_ratio": 1.28,
    },
    {
        "fixture": "F21-cli-scheduler-priority",
        "verdict": "pair_evidence_passed",
        "run_id": "pair-pass-2",
        "pair_arm": "l2_risk_probes",
        "bare_score": 33,
        "solo_score": 66,
        "pair_score": 99,
        "pair_margin": 33,
        "pair_mode": True,
        "pair_trigger_eligible": True,
        "pair_trigger_reasons": ["complexity.high", "risk_profile.high_risk"],
        "pair_trigger_has_canonical_reason": True,
        "pair_trigger_has_hypothesis_reason": False,
        "pair_solo_wall_ratio": 1.47,
    },
]
assert report["checks"]["frontier"]["status"] == "PASS"
assert report["checks"]["headroom_rejections"]["status"] == "PASS"
assert report["checks"]["headroom_rejections"]["exit_code"] == 0
assert report["checks"]["headroom_rejections"]["report_check_exit_code"] == 0
assert report["checks"]["headroom_rejections"]["verdict"] == "PASS"
assert report["checks"]["headroom_rejections"]["unrecorded_failure_count"] == 0
assert report["checks"]["headroom_rejections"]["unsupported_registry_rejection_count"] == 0
assert report["checks"]["frontier_report"]["status"] == "PASS"
assert report["checks"]["frontier_report"]["verdict"] == "PASS"
assert report["checks"]["frontier_report"]["unmeasured_count"] == 0
assert report["checks"]["frontier_stdout"]["status"] == "PASS"
assert report["checks"]["frontier_stdout"]["summary_rows"] == 1
assert report["checks"]["frontier_stdout"]["aggregate_rows"] == 1
assert report["checks"]["frontier_stdout"]["final_verdict_rows"] == 1
assert report["checks"]["frontier_stdout"]["expected_rows"] == 2
assert report["checks"]["frontier_stdout"]["stdout_rows"] == 2
assert report["checks"]["frontier_stdout"]["trigger_rows"] == 2
assert report["checks"]["frontier_stdout"]["hypothesis_trigger_rows"] == 2
assert report["checks"]["frontier_stdout"]["rows_match_count"] is True
assert report["checks"]["frontier_stdout"]["trigger_rows_match_count"] is True
assert report["checks"]["frontier_stdout"]["hypothesis_trigger_rows_match_count"] is True
assert report["checks"]["min_pair_evidence"]["status"] == "PASS"
assert report["checks"]["min_pair_evidence"]["required"] == 2
assert report["checks"]["min_pair_evidence"]["actual"] == 2
assert report["checks"]["min_pair_evidence"]["actual_rows"] == 2
assert report["checks"]["min_pair_evidence"]["rows_match_count"] is True
assert report["checks"]["pair_evidence_quality"]["status"] == "PASS"
assert report["checks"]["pair_evidence_quality"]["min_pair_margin_required"] == 5
assert report["checks"]["pair_evidence_quality"]["min_pair_margin_actual"] == 21
assert report["checks"]["pair_evidence_quality"]["max_pair_solo_wall_ratio_allowed"] == 3.0
assert report["checks"]["pair_evidence_quality"]["max_pair_solo_wall_ratio_actual"] == 1.47
assert report["checks"]["pair_evidence_quality"]["summary_min_pair_margin"] == 21
assert report["checks"]["pair_evidence_quality"]["summary_max_pair_solo_wall_ratio"] == 1.47
assert report["checks"]["pair_trigger_reasons"]["status"] == "PASS"
assert report["checks"]["pair_trigger_reasons"]["summary_pair_evidence_count"] == 2
assert report["checks"]["pair_trigger_reasons"]["canonical_rows"] == 2
assert report["checks"]["pair_trigger_reasons"]["historical_alias_rows"] == 1
assert report["checks"]["pair_trigger_reasons"]["historical_alias_details"] == [
    {"fixture": "F21-cli-scheduler-priority", "aliases": ["risk_profile.high_risk"]}
]
assert report["checks"]["pair_trigger_reasons"]["exposed_rows"] == 2
assert report["checks"]["pair_trigger_reasons"]["total_rows"] == 2
assert report["checks"]["pair_trigger_reasons"]["rows_match_count"] is True
assert report["checks"]["pair_evidence_hypothesis_triggers"]["status"] == "WARN"
assert report["checks"]["pair_evidence_hypothesis_triggers"]["exit_code"] == 0
assert report["checks"]["pair_evidence_hypothesis_triggers"]["required"] is False
assert report["checks"]["pair_evidence_hypothesis_triggers"]["matched_rows"] == 0
assert report["checks"]["pair_evidence_hypothesis_triggers"]["documented_rows"] == 2
assert report["checks"]["pair_evidence_hypothesis_triggers"]["total_rows"] == 2
assert report["checks"]["pair_evidence_hypothesis_triggers"]["gap_details"] == [
    {
        "fixture": "F16-cli-quote-tax-rules",
        "pair_trigger_reasons": ["complexity.high"],
    },
    {
        "fixture": "F21-cli-scheduler-priority",
        "pair_trigger_reasons": ["complexity.high", "risk_profile.high_risk"],
    },
]
assert report["artifacts"] == {
    "frontier_json": "frontier.json",
    "frontier_stdout": "frontier.stdout",
    "frontier_stderr": "frontier.stderr",
    "headroom_audit_json": "headroom-audit.json",
    "headroom_rejections_stdout": "headroom-rejections.stdout",
    "headroom_rejections_stderr": "headroom-rejections.stderr",
    "audit_json": "audit.json",
}
PY

if python3 "$SCRIPT" \
  --fixtures-root "$fixtures" \
  --registry "$registry" \
  --results-root "$results" \
  --min-pair-evidence 2 \
  --require-hypothesis-trigger \
  --out-dir "$TMP_DIR/out-strict-trigger" \
  > "$TMP_DIR/strict-trigger.out" 2>&1; then
  echo "audit must fail when --require-hypothesis-trigger sees trigger gaps" >&2
  cat "$TMP_DIR/strict-trigger.out" >&2
  exit 1
fi
grep -Fq 'pair evidence hypothesis triggers missing for fixture(s): F16-cli-quote-tax-rules, F21-cli-scheduler-priority' "$TMP_DIR/strict-trigger.out"
grep -Fq 'pair_evidence_hypothesis_triggers=FAIL matched=0 documented=2 total=2' "$TMP_DIR/strict-trigger.out"
grep -Fq 'pair_evidence_hypothesis_trigger_gaps=F16-cli-quote-tax-rules=complexity.high;F21-cli-scheduler-priority=complexity.high,risk_profile.high_risk' "$TMP_DIR/strict-trigger.out"
grep -Fq 'FAIL audit-pair-evidence' "$TMP_DIR/strict-trigger.out"
python3 - "$TMP_DIR/out-strict-trigger/audit.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf8"))
assert report["verdict"] == "FAIL"
assert report["checks"]["pair_evidence_hypothesis_triggers"]["status"] == "FAIL"
assert report["checks"]["pair_evidence_hypothesis_triggers"]["exit_code"] == 1
assert report["checks"]["pair_evidence_hypothesis_triggers"]["required"] is True
assert report["checks"]["pair_evidence_hypothesis_triggers"]["gap_details"] == [
    {
        "fixture": "F16-cli-quote-tax-rules",
        "pair_trigger_reasons": ["complexity.high"],
    },
    {
        "fixture": "F21-cli-scheduler-priority",
        "pair_trigger_reasons": ["complexity.high", "risk_profile.high_risk"],
    },
]
PY

python3 - "$SCRIPT" "$TMP_DIR/out-pass/frontier.json" "$TMP_DIR/out-pass/frontier.stdout" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_frontier_stdout(pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])))
PY

cat > "$TMP_DIR/missing-trigger-reasons.json" <<'JSON'
{
  "pair_evidence_count": 1,
  "rows": [
    {
      "fixture": "F16-cli-quote-tax-rules",
      "status": "pair_evidence_passed",
      "passing_pair_evidence": [
        {
          "run_id": "pair-pass",
          "pair_arm": "l2_risk_probes",
          "bare_score": 50,
          "solo_score": 75,
          "pair_score": 96,
          "pair_margin": 21,
          "pair_mode": true,
          "pair_trigger_eligible": true,
          "pair_solo_wall_ratio": 1.28
        }
      ]
    }
  ]
}
JSON
expect_fail_contains missing-trigger-reasons "pair trigger reason rows 0 do not match summary count 1" \
  python3 - "$SCRIPT" "$TMP_DIR/missing-trigger-reasons.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_pair_trigger_reasons(pathlib.Path(sys.argv[2])))
PY

cat > "$TMP_DIR/malformed-trigger-reason-rows.json" <<'JSON'
{
  "pair_evidence_count": 1,
  "rows": [
    {
      "fixture": "F16-cli-quote-tax-rules",
      "status": "pair_evidence_passed",
      "passing_pair_evidence": [
        {
          "run_id": "pair-pass",
          "pair_arm": "l2_risk_probes",
          "bare_score": 50,
          "solo_score": 75,
          "pair_score": 96,
          "pair_margin": 21,
          "pair_mode": true,
          "pair_trigger_eligible": true,
          "pair_trigger_reasons": [],
          "pair_trigger_has_canonical_reason": true,
          "pair_solo_wall_ratio": 1.28
        }
      ]
    }
  ]
}
JSON
expect_fail_contains malformed-trigger-reason-rows "pair trigger reason rows 0 do not match summary count 1" \
  python3 - "$SCRIPT" "$TMP_DIR/malformed-trigger-reason-rows.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_pair_trigger_reasons(pathlib.Path(sys.argv[2])))
PY

cat > "$TMP_DIR/mixed-unknown-trigger-reason-rows.json" <<'JSON'
{
  "pair_evidence_count": 1,
  "rows": [
    {
      "fixture": "F16-cli-quote-tax-rules",
      "status": "pair_evidence_passed",
      "passing_pair_evidence": [
        {
          "run_id": "pair-pass",
          "pair_arm": "l2_risk_probes",
          "bare_score": 50,
          "solo_score": 75,
          "pair_score": 96,
          "pair_margin": 21,
          "pair_mode": true,
          "pair_trigger_eligible": true,
          "pair_trigger_reasons": ["complexity.high", "looks-hard"],
          "pair_trigger_has_canonical_reason": true,
          "pair_solo_wall_ratio": 1.28
        }
      ]
    }
  ]
}
JSON
expect_fail_contains mixed-unknown-trigger-reason-rows "pair trigger reason rows 0 do not match summary count 1" \
  python3 - "$SCRIPT" "$TMP_DIR/mixed-unknown-trigger-reason-rows.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_pair_trigger_reasons(pathlib.Path(sys.argv[2])))
PY

cat > "$TMP_DIR/normalized-canonical-trigger-reason-rows.json" <<'JSON'
{
  "pair_evidence_count": 1,
  "rows": [
    {
      "fixture": "F16-cli-quote-tax-rules",
      "status": "pair_evidence_passed",
      "passing_pair_evidence": [
        {
          "run_id": "pair-pass",
          "pair_arm": "l2_risk_probes",
          "bare_score": 50,
          "solo_score": 75,
          "pair_score": 96,
          "pair_margin": 21,
          "pair_mode": true,
          "pair_trigger_eligible": true,
          "pair_trigger_reasons": ["risk high"],
          "pair_trigger_has_canonical_reason": true,
          "pair_solo_wall_ratio": 1.28
        }
      ]
    }
  ]
}
JSON
expect_fail_contains normalized-canonical-trigger-reason-rows "pair trigger reason rows 0 do not match summary count 1" \
  python3 - "$SCRIPT" "$TMP_DIR/normalized-canonical-trigger-reason-rows.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_pair_trigger_reasons(pathlib.Path(sys.argv[2])))
PY

grep -Fv 'PASS pair-candidate-frontier' "$TMP_DIR/out-pass/frontier.stdout" \
  > "$TMP_DIR/missing-final-verdict-frontier.stdout"
expect_fail_contains missing-final-frontier-verdict "frontier stdout final verdict row count is not exactly 1" \
  python3 - "$SCRIPT" "$TMP_DIR/out-pass/frontier.json" "$TMP_DIR/missing-final-verdict-frontier.stdout" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_frontier_stdout(pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])))
PY

cp "$TMP_DIR/out-pass/frontier.stdout" "$TMP_DIR/duplicate-final-verdict-frontier.stdout"
printf 'PASS pair-candidate-frontier\n' >> "$TMP_DIR/duplicate-final-verdict-frontier.stdout"
expect_fail_contains duplicate-final-frontier-verdict "frontier stdout final verdict row count is not exactly 1" \
  python3 - "$SCRIPT" "$TMP_DIR/out-pass/frontier.json" "$TMP_DIR/duplicate-final-verdict-frontier.stdout" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_frontier_stdout(pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])))
PY

printf 'fixtures=3 rejected=1 candidates=2 pair_evidence=2 unmeasured=0 verdict=PASS\n' \
  > "$TMP_DIR/bad-frontier.stdout"
printf 'pair_margin_avg=+27.00 pair_margin_min=+21 wall_avg=1.38x wall_max=1.47x\n' \
  >> "$TMP_DIR/bad-frontier.stdout"
printf 'F16-cli-quote-tax-rules: bare=50 solo_claude=75 pair=95 arm=l2_risk_probes margin=+20 wall=1.28x run=pair-pass verdict=pair_evidence_passed\n' \
  >> "$TMP_DIR/bad-frontier.stdout"
printf 'F21-cli-scheduler-priority: bare=33 solo_claude=66 pair=99 arm=l2_risk_probes margin=+33 wall=1.47x run=pair-pass-2 verdict=pair_evidence_passed\n' \
  >> "$TMP_DIR/bad-frontier.stdout"
expect_fail_contains missing-frontier-score-row "frontier stdout missing score row for F16-cli-quote-tax-rules" \
  python3 - "$SCRIPT" "$TMP_DIR/out-pass/frontier.json" "$TMP_DIR/bad-frontier.stdout" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_frontier_stdout(pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])))
PY

sed -E 's/ triggers=[^[:space:]]+//' "$TMP_DIR/out-pass/frontier.stdout" \
  > "$TMP_DIR/no-trigger-frontier.stdout"
expect_fail_contains missing-frontier-triggers "frontier stdout missing score row for F16-cli-quote-tax-rules" \
  python3 - "$SCRIPT" "$TMP_DIR/out-pass/frontier.json" "$TMP_DIR/no-trigger-frontier.stdout" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_frontier_stdout(pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])))
PY

cat > "$TMP_DIR/no-aggregate-frontier.stdout" <<'OUT'
fixtures=3 rejected=1 candidates=2 pair_evidence=2 unmeasured=0 verdict=PASS
F16-cli-quote-tax-rules: bare=50 solo_claude=75 pair=96 arm=l2_risk_probes margin=+21 wall=1.28x run=pair-pass verdict=pair_evidence_passed
F21-cli-scheduler-priority: bare=33 solo_claude=66 pair=99 arm=l2_risk_probes margin=+33 wall=1.47x run=pair-pass-2 verdict=pair_evidence_passed
OUT
expect_fail_contains missing-frontier-aggregate-row "frontier stdout aggregate score row count is not exactly 1" \
  python3 - "$SCRIPT" "$TMP_DIR/out-pass/frontier.json" "$TMP_DIR/no-aggregate-frontier.stdout" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_frontier_stdout(pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])))
PY

cp "$TMP_DIR/out-pass/frontier.stdout" "$TMP_DIR/duplicate-summary-frontier.stdout"
printf 'fixtures=3 rejected=1 candidates=2 pair_evidence=2 unmeasured=0 verdict=PASS\n' \
  >> "$TMP_DIR/duplicate-summary-frontier.stdout"
expect_fail_contains duplicate-frontier-summary-row "frontier stdout summary score row count is not exactly 1" \
  python3 - "$SCRIPT" "$TMP_DIR/out-pass/frontier.json" "$TMP_DIR/duplicate-summary-frontier.stdout" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_frontier_stdout(pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])))
PY

cp "$TMP_DIR/out-pass/frontier.stdout" "$TMP_DIR/duplicate-aggregate-frontier.stdout"
printf 'pair_margin_avg=+27.00 pair_margin_min=+21 wall_avg=1.38x wall_max=1.47x\n' \
  >> "$TMP_DIR/duplicate-aggregate-frontier.stdout"
expect_fail_contains duplicate-frontier-aggregate-row "frontier stdout aggregate score row count is not exactly 1" \
  python3 - "$SCRIPT" "$TMP_DIR/out-pass/frontier.json" "$TMP_DIR/duplicate-aggregate-frontier.stdout" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_frontier_stdout(pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])))
PY

cat > "$TMP_DIR/partial-frontier.stdout" <<'OUT'
fixtures=3 rejected=1 candidates=2 pair_evidence=2 unmeasured=0 verdict=PASS
pair_margin_avg=+27.00 pair_margin_min=+21 wall_avg=1.38x wall_max=1.47x
F16-cli-quote-tax-rules: bare=50 solo_claude=75 pair=96 arm=l2_risk_probes margin=+21 verdict=pair_evidence_passed
F21-cli-scheduler-priority: bare=33 solo_claude=66 pair=99 arm=l2_risk_probes margin=+33 wall=1.47x run=pair-pass-2 verdict=pair_evidence_passed
OUT
expect_fail_contains partial-frontier-score-row "frontier stdout missing score row for F16-cli-quote-tax-rules" \
  python3 - "$SCRIPT" "$TMP_DIR/out-pass/frontier.json" "$TMP_DIR/partial-frontier.stdout" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_frontier_stdout(pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])))
PY

cp "$TMP_DIR/out-pass/frontier.stdout" "$TMP_DIR/extra-frontier.stdout"
printf 'F99-stale-fixture: bare=1 solo_claude=2 pair=3 arm=l2_risk_probes margin=+1 wall=1.00x run=stale verdict=pair_evidence_passed\n' \
  >> "$TMP_DIR/extra-frontier.stdout"
expect_fail_contains extra-frontier-score-row "frontier stdout score row count 3 does not match frontier evidence row count 2" \
  python3 - "$SCRIPT" "$TMP_DIR/out-pass/frontier.json" "$TMP_DIR/extra-frontier.stdout" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_frontier_stdout(pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])))
PY

cat > "$TMP_DIR/malformed-frontier-summary.json" <<'JSON'
{
  "verdict": "PASS"
}
JSON
expect_fail_contains malformed-frontier-stdout-summary "frontier stdout check missing summary fields" \
  python3 - "$SCRIPT" "$TMP_DIR/malformed-frontier-summary.json" "$TMP_DIR/bad-frontier.stdout" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_frontier_stdout(pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])))
PY

cat > "$TMP_DIR/malformed-frontier-count.json" <<'JSON'
{
  "verdict": "PASS",
  "fixtures_total": 3,
  "rejected_count": 1,
  "candidate_count": 2,
  "pair_evidence_count": "2",
  "unmeasured_count": 0
}
JSON
expect_fail_contains malformed-frontier-stdout-counts "frontier stdout summary counts malformed" \
  python3 - "$SCRIPT" "$TMP_DIR/malformed-frontier-count.json" "$TMP_DIR/bad-frontier.stdout" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_frontier_stdout(pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])))
PY

cat > "$TMP_DIR/malformed-frontier-aggregate.json" <<'JSON'
{
  "verdict": "PASS",
  "fixtures_total": 3,
  "rejected_count": 1,
  "candidate_count": 2,
  "pair_evidence_count": 2,
  "unmeasured_count": 0,
  "pair_margin_avg": "27",
  "pair_margin_min": 21,
  "pair_solo_wall_ratio_avg": 1.38,
  "pair_solo_wall_ratio_max": 1.47,
  "rows": []
}
JSON
expect_fail_contains malformed-frontier-stdout-aggregate "frontier stdout aggregate fields malformed" \
  python3 - "$SCRIPT" "$TMP_DIR/malformed-frontier-aggregate.json" "$TMP_DIR/bad-frontier.stdout" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_frontier_stdout(pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])))
PY

cat > "$TMP_DIR/frontier-fail-verdict.json" <<'JSON'
{
  "verdict": "FAIL",
  "unmeasured_count": 1,
  "pair_evidence_count": 1,
  "rows": []
}
JSON
expect_fail_contains frontier-fail-verdict "frontier verdict 'FAIL' is not PASS" \
  python3 - "$SCRIPT" "$TMP_DIR/frontier-fail-verdict.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_frontier_report(pathlib.Path(sys.argv[2])))
PY

cat > "$TMP_DIR/frontier-unmeasured.json" <<'JSON'
{
  "verdict": "PASS",
  "unmeasured_count": 1,
  "pair_evidence_count": 1,
  "rows": []
}
JSON
expect_fail_contains frontier-unmeasured "frontier has 1 unmeasured candidate fixture(s)" \
  python3 - "$SCRIPT" "$TMP_DIR/frontier-unmeasured.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_frontier_report(pathlib.Path(sys.argv[2])))
PY

cat > "$TMP_DIR/frontier-malformed-unmeasured.json" <<'JSON'
{
  "verdict": "PASS",
  "unmeasured_count": true,
  "pair_evidence_count": 1,
  "rows": []
}
JSON
expect_fail_contains frontier-malformed-unmeasured "frontier unmeasured count missing or malformed" \
  python3 - "$SCRIPT" "$TMP_DIR/frontier-malformed-unmeasured.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_frontier_report(pathlib.Path(sys.argv[2])))
PY

cat > "$TMP_DIR/headroom-fail-verdict.json" <<'JSON'
{
  "verdict": "FAIL",
  "unrecorded_failures": [],
  "unsupported_registry_rejections": []
}
JSON
expect_fail_contains headroom-fail-verdict "headroom audit verdict 'FAIL' is not PASS" \
  python3 - "$SCRIPT" "$TMP_DIR/headroom-fail-verdict.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_headroom_audit_report(pathlib.Path(sys.argv[2])))
PY

cat > "$TMP_DIR/headroom-missing-unsupported.json" <<'JSON'
{
  "verdict": "PASS",
  "unrecorded_failures": []
}
JSON
expect_fail_contains headroom-missing-unsupported "headroom audit unsupported registry rejection count missing or malformed" \
  python3 - "$SCRIPT" "$TMP_DIR/headroom-missing-unsupported.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_headroom_audit_report(pathlib.Path(sys.argv[2])))
PY

cat > "$TMP_DIR/headroom-unsupported.json" <<'JSON'
{
  "verdict": "PASS",
  "unrecorded_failures": [],
  "unsupported_registry_rejections": [{"fixture": "F36-unsupported-rejection"}]
}
JSON
expect_fail_contains headroom-unsupported "headroom audit has 1 unsupported registry rejection(s)" \
  python3 - "$SCRIPT" "$TMP_DIR/headroom-unsupported.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_headroom_audit_report(pathlib.Path(sys.argv[2])))
PY

python3 - "$SCRIPT" "$TMP_DIR/headroom-unsupported.json" > "$TMP_DIR/headroom-summary.out" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
module.print_headroom_rejections_summary(pathlib.Path(sys.argv[2]), status=1)
PY
grep -Fq 'headroom_rejections=FAIL verdict=PASS unrecorded=0 unsupported=1' "$TMP_DIR/headroom-summary.out"

cat > "$TMP_DIR/frontier-incomplete-best.json" <<'JSON'
{
  "pair_evidence_count": 1,
  "rows": [
    {
      "fixture": "F16-cli-quote-tax-rules",
      "status": "pair_evidence_passed",
      "passing_pair_evidence": [
        {
          "run_id": "higher-incomplete",
          "bare_score": 50,
          "solo_score": 75,
          "pair_score": 98,
          "pair_margin": 23,
          "pair_mode": true,
          "pair_trigger_eligible": true,
          "pair_solo_wall_ratio": 1.32
        },
        {
          "run_id": "lower-complete",
          "pair_arm": "l2_risk_probes",
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
  ]
}
JSON
python3 - "$SCRIPT" "$TMP_DIR/frontier-incomplete-best.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
rows = module.load_pair_evidence_rows(pathlib.Path(sys.argv[2]))
assert rows == [
    {
        "fixture": "F16-cli-quote-tax-rules",
        "verdict": "pair_evidence_passed",
        "run_id": "lower-complete",
        "pair_arm": "l2_risk_probes",
        "bare_score": 50,
        "solo_score": 75,
        "pair_score": 96,
        "pair_margin": 21,
        "pair_mode": True,
        "pair_trigger_eligible": True,
        "pair_trigger_reasons": ["complexity.high"],
        "pair_trigger_has_canonical_reason": True,
        "pair_trigger_has_hypothesis_reason": False,
        "pair_solo_wall_ratio": 1.28,
    }
]
PY

cat > "$TMP_DIR/bad-frontier-rows.json" <<'JSON'
{
  "pair_evidence_count": 2,
  "rows": [
    {
      "fixture": "F16-cli-quote-tax-rules",
      "status": "pair_evidence_passed",
      "passing_pair_evidence": []
    },
    {
      "fixture": "F21-cli-scheduler-priority",
      "status": "pair_evidence_passed",
      "passing_pair_evidence": "malformed"
    }
  ]
}
JSON
expect_fail_contains missing-pair-evidence-rows "pair evidence rows 0 do not match summary count 2" \
  python3 - "$SCRIPT" "$TMP_DIR/bad-frontier-rows.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_min_pair_evidence(pathlib.Path(sys.argv[2]), 2))
PY

cat > "$TMP_DIR/bad-frontier-row-fields.json" <<'JSON'
{
  "pair_evidence_count": 2,
  "rows": [
    {
      "fixture": "F16-cli-quote-tax-rules",
      "status": "pair_evidence_passed",
      "passing_pair_evidence": [
        {
          "run_id": "pair-pass",
          "pair_arm": "l2_risk_probes",
          "bare_score": null,
          "solo_score": 75,
          "pair_score": 96,
          "pair_margin": 21,
          "pair_mode": true,
          "pair_trigger_eligible": true,
          "pair_solo_wall_ratio": 1.28
        }
      ]
    },
    {
      "fixture": "F21-cli-scheduler-priority",
      "status": "pair_evidence_passed",
      "passing_pair_evidence": [
        {
          "run_id": "pair-pass-2",
          "pair_arm": "l2_risk_probes",
          "bare_score": 33,
          "solo_score": 66,
          "pair_score": 99,
          "pair_margin": 33,
          "pair_mode": true,
          "pair_trigger_eligible": true,
          "pair_solo_wall_ratio": true
        }
      ]
    }
  ]
}
JSON
expect_fail_contains malformed-pair-evidence-row-fields "pair evidence rows 0 do not match summary count 2" \
  python3 - "$SCRIPT" "$TMP_DIR/bad-frontier-row-fields.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_min_pair_evidence(pathlib.Path(sys.argv[2]), 2))
PY

cat > "$TMP_DIR/nan-frontier-row-fields.json" <<'JSON'
{
  "pair_evidence_count": 1,
  "rows": [
    {
      "fixture": "F16-cli-quote-tax-rules",
      "status": "pair_evidence_passed",
      "passing_pair_evidence": [
        {
          "run_id": "nan-wall-run",
          "pair_arm": "l2_risk_probes",
          "bare_score": 50,
          "solo_score": 75,
          "pair_score": 96,
          "pair_margin": 21,
          "pair_mode": true,
          "pair_trigger_eligible": true,
          "pair_solo_wall_ratio": NaN
        }
      ]
    }
  ]
}
JSON
expect_fail_contains nan-pair-evidence-row-fields "pair evidence count missing or malformed from frontier report" \
  python3 - "$SCRIPT" "$TMP_DIR/nan-frontier-row-fields.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_min_pair_evidence(pathlib.Path(sys.argv[2]), 1))
PY

cat > "$TMP_DIR/mismatched-margin-row-fields.json" <<'JSON'
{
  "pair_evidence_count": 1,
  "rows": [
    {
      "fixture": "F16-cli-quote-tax-rules",
      "status": "pair_evidence_passed",
      "passing_pair_evidence": [
        {
          "run_id": "inflated-margin-run",
          "pair_arm": "l2_risk_probes",
          "bare_score": 50,
          "solo_score": 75,
          "pair_score": 76,
          "pair_margin": 21,
          "pair_mode": true,
          "pair_trigger_eligible": true,
          "pair_solo_wall_ratio": 1.28
        }
      ]
    }
  ]
}
JSON
expect_fail_contains mismatched-margin-row-fields "pair evidence rows 0 do not match summary count 1" \
  python3 - "$SCRIPT" "$TMP_DIR/mismatched-margin-row-fields.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_min_pair_evidence(pathlib.Path(sys.argv[2]), 1))
PY

cat > "$TMP_DIR/overrange-score-row-fields.json" <<'JSON'
{
  "pair_evidence_count": 1,
  "rows": [
    {
      "fixture": "F16-cli-quote-tax-rules",
      "status": "pair_evidence_passed",
      "passing_pair_evidence": [
        {
          "run_id": "overrange-score-run",
          "pair_arm": "l2_risk_probes",
          "bare_score": 50,
          "solo_score": 75,
          "pair_score": 101,
          "pair_margin": 26,
          "pair_mode": true,
          "pair_trigger_eligible": true,
          "pair_solo_wall_ratio": 1.28
        }
      ]
    }
  ]
}
JSON
expect_fail_contains overrange-score-row-fields "pair evidence rows 0 do not match summary count 1" \
  python3 - "$SCRIPT" "$TMP_DIR/overrange-score-row-fields.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_min_pair_evidence(pathlib.Path(sys.argv[2]), 1))
PY

cat > "$TMP_DIR/invalid-pair-arm-row-fields.json" <<'JSON'
{
  "pair_evidence_count": 1,
  "rows": [
    {
      "fixture": "F16-cli-quote-tax-rules",
      "status": "pair_evidence_passed",
      "passing_pair_evidence": [
        {
          "run_id": "invalid-arm-run",
          "pair_arm": "bare",
          "bare_score": 50,
          "solo_score": 75,
          "pair_score": 96,
          "pair_margin": 21,
          "pair_mode": true,
          "pair_trigger_eligible": true,
          "pair_solo_wall_ratio": 1.28
        }
      ]
    }
  ]
}
JSON
expect_fail_contains invalid-pair-arm-row-fields "pair evidence rows 0 do not match summary count 1" \
  python3 - "$SCRIPT" "$TMP_DIR/invalid-pair-arm-row-fields.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_min_pair_evidence(pathlib.Path(sys.argv[2]), 1))
PY

cat > "$TMP_DIR/false-pair-mode-row-fields.json" <<'JSON'
{
  "pair_evidence_count": 1,
  "rows": [
    {
      "fixture": "F16-cli-quote-tax-rules",
      "status": "pair_evidence_passed",
      "passing_pair_evidence": [
        {
          "run_id": "false-pair-mode-run",
          "pair_arm": "l2_risk_probes",
          "bare_score": 50,
          "solo_score": 75,
          "pair_score": 96,
          "pair_margin": 21,
          "pair_mode": false,
          "pair_solo_wall_ratio": 1.28
        }
      ]
    }
  ]
}
JSON
expect_fail_contains false-pair-mode-row-fields "pair evidence rows 0 do not match summary count 1" \
  python3 - "$SCRIPT" "$TMP_DIR/false-pair-mode-row-fields.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_min_pair_evidence(pathlib.Path(sys.argv[2]), 1))
PY

cat > "$TMP_DIR/missing-pair-trigger-row-fields.json" <<'JSON'
{
  "pair_evidence_count": 1,
  "rows": [
    {
      "fixture": "F16-cli-quote-tax-rules",
      "status": "pair_evidence_passed",
      "passing_pair_evidence": [
        {
          "run_id": "stale-gate-run",
          "pair_arm": "l2_risk_probes",
          "bare_score": 50,
          "solo_score": 75,
          "pair_score": 96,
          "pair_margin": 21,
          "pair_mode": true,
          "pair_solo_wall_ratio": 1.28
        }
      ]
    }
  ]
}
JSON
expect_fail_contains missing-pair-trigger-row-fields "pair evidence rows 0 do not match summary count 1" \
  python3 - "$SCRIPT" "$TMP_DIR/missing-pair-trigger-row-fields.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_min_pair_evidence(pathlib.Path(sys.argv[2]), 1))
PY

cat > "$TMP_DIR/zero-wall-row-fields.json" <<'JSON'
{
  "pair_evidence_count": 1,
  "rows": [
    {
      "fixture": "F16-cli-quote-tax-rules",
      "status": "pair_evidence_passed",
      "passing_pair_evidence": [
        {
          "run_id": "zero-wall-run",
          "pair_arm": "l2_risk_probes",
          "bare_score": 50,
          "solo_score": 75,
          "pair_score": 96,
          "pair_margin": 21,
          "pair_mode": true,
          "pair_trigger_eligible": true,
          "pair_solo_wall_ratio": 0
        }
      ]
    }
  ]
}
JSON
expect_fail_contains zero-wall-row-fields "pair evidence rows 0 do not match summary count 1" \
  python3 - "$SCRIPT" "$TMP_DIR/zero-wall-row-fields.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_min_pair_evidence(pathlib.Path(sys.argv[2]), 1))
PY

cat > "$TMP_DIR/bool-frontier-count.json" <<'JSON'
{
  "pair_evidence_count": true,
  "rows": [
    {
      "fixture": "F16-cli-quote-tax-rules",
      "status": "pair_evidence_passed",
      "passing_pair_evidence": [
        {
          "run_id": "pair-pass",
          "pair_arm": "l2_risk_probes",
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
  ]
}
JSON
expect_fail_contains malformed-pair-evidence-count "pair evidence count missing or malformed from frontier report" \
  python3 - "$SCRIPT" "$TMP_DIR/bool-frontier-count.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_min_pair_evidence(pathlib.Path(sys.argv[2]), 1))
PY

cat > "$TMP_DIR/mismatched-frontier-rows.json" <<'JSON'
{
  "pair_evidence_count": 2,
  "rows": [
    {
      "fixture": "F16-cli-quote-tax-rules",
      "status": "pair_evidence_passed",
      "passing_pair_evidence": [
        {
          "run_id": "pair-pass",
          "pair_arm": "l2_risk_probes",
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
    },
    {
      "fixture": "F21-cli-scheduler-priority",
      "status": "pair_evidence_passed",
      "passing_pair_evidence": [
        {
          "run_id": "incomplete-row",
          "bare_score": 33,
          "solo_score": 66,
          "pair_score": 99,
          "pair_margin": 33,
          "pair_mode": true,
          "pair_trigger_eligible": true,
          "pair_solo_wall_ratio": 1.47
        }
      ]
    }
  ]
}
JSON
expect_fail_contains mismatched-pair-evidence-rows "pair evidence rows 1 do not match summary count 2" \
  python3 - "$SCRIPT" "$TMP_DIR/mismatched-frontier-rows.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_min_pair_evidence(pathlib.Path(sys.argv[2]), 1))
PY

expect_fail_contains min-pair-evidence "pair evidence count 2 below required minimum 4" \
  python3 "$SCRIPT" \
    --fixtures-root "$fixtures" \
    --registry "$registry" \
    --results-root "$results" \
    --out-dir "$TMP_DIR/out-low-evidence"
grep -Fq 'FAIL audit-pair-evidence' "$TMP_DIR/min-pair-evidence.out"
grep -Fq 'headroom_rejections=PASS verdict=PASS unrecorded=0 unsupported=0' "$TMP_DIR/min-pair-evidence.out"
grep -Fq 'pair_evidence_quality=PASS min_pair_margin_actual=+21 min_pair_margin_required=+5 max_wall_actual=1.47x max_wall_allowed=3.00x' "$TMP_DIR/min-pair-evidence.out"
grep -Fq 'pair_trigger_reasons=PASS canonical=2 historical_alias=1 exposed=2 total=2 summary=2 rows_match=true' "$TMP_DIR/min-pair-evidence.out"
grep -Fq 'pair_trigger_historical_aliases=F21-cli-scheduler-priority=risk_profile.high_risk' "$TMP_DIR/min-pair-evidence.out"
grep -Fq 'pair_evidence_hypothesis_triggers=WARN matched=0 documented=2 total=2' "$TMP_DIR/min-pair-evidence.out"
grep -Fq 'pair_evidence_hypothesis_trigger_gaps=F16-cli-quote-tax-rules=complexity.high;F21-cli-scheduler-priority=complexity.high,risk_profile.high_risk' "$TMP_DIR/min-pair-evidence.out"
python3 - "$TMP_DIR/out-low-evidence/audit.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf8"))
assert report["verdict"] == "FAIL"
assert report["checks"]["frontier"]["status"] == "PASS"
assert report["checks"]["headroom_rejections"]["status"] == "PASS"
assert report["checks"]["headroom_rejections"]["report_check_exit_code"] == 0
assert report["checks"]["headroom_rejections"]["verdict"] == "PASS"
assert report["checks"]["headroom_rejections"]["unrecorded_failure_count"] == 0
assert report["checks"]["headroom_rejections"]["unsupported_registry_rejection_count"] == 0
assert report["checks"]["min_pair_evidence"]["status"] == "FAIL"
assert report["checks"]["min_pair_evidence"]["required"] == 4
assert report["checks"]["min_pair_evidence"]["actual_rows"] == 2
assert report["checks"]["pair_evidence_quality"]["status"] == "PASS"
assert report["checks"]["pair_evidence_quality"]["min_pair_margin_actual"] == 21
assert report["checks"]["pair_evidence_quality"]["max_pair_solo_wall_ratio_actual"] == 1.47
assert report["checks"]["pair_trigger_reasons"]["status"] == "PASS"
assert report["checks"]["pair_trigger_reasons"]["summary_pair_evidence_count"] == 2
assert report["checks"]["pair_trigger_reasons"]["canonical_rows"] == 2
assert report["checks"]["pair_trigger_reasons"]["historical_alias_rows"] == 1
assert report["checks"]["pair_trigger_reasons"]["historical_alias_details"] == [
    {"fixture": "F21-cli-scheduler-priority", "aliases": ["risk_profile.high_risk"]}
]
assert report["checks"]["pair_trigger_reasons"]["exposed_rows"] == 2
assert report["checks"]["pair_trigger_reasons"]["total_rows"] == 2
assert report["checks"]["pair_trigger_reasons"]["rows_match_count"] is True
assert report["checks"]["pair_evidence_hypotheses"]["status"] == "PASS"
assert report["checks"]["pair_evidence_hypotheses"]["documented_rows"] == 2
assert report["checks"]["pair_evidence_hypotheses"]["total_rows"] == 2
assert report["checks"]["pair_evidence_hypothesis_triggers"]["status"] == "WARN"
assert report["checks"]["pair_evidence_hypothesis_triggers"]["exit_code"] == 0
assert report["checks"]["pair_evidence_hypothesis_triggers"]["required"] is False
assert report["checks"]["pair_evidence_hypothesis_triggers"]["matched_rows"] == 0
assert report["checks"]["pair_evidence_hypothesis_triggers"]["documented_rows"] == 2
assert report["checks"]["pair_evidence_hypothesis_triggers"]["total_rows"] == 2
assert report["checks"]["pair_evidence_hypothesis_triggers"]["gap_details"] == [
    {
        "fixture": "F16-cli-quote-tax-rules",
        "pair_trigger_reasons": ["complexity.high"],
    },
    {
        "fixture": "F21-cli-scheduler-priority",
        "pair_trigger_reasons": ["complexity.high", "risk_profile.high_risk"],
    },
]
PY

cat > "$TMP_DIR/low-quality-frontier.json" <<'JSON'
{
  "pair_margin_min": 4,
  "pair_solo_wall_ratio_max": 1.2,
  "rows": [
    {
      "fixture": "F16-cli-quote-tax-rules",
      "status": "pair_evidence_passed",
      "passing_pair_evidence": [
        {
          "run_id": "low-quality-run",
          "pair_arm": "l2_risk_probes",
          "bare_score": 50,
          "solo_score": 75,
          "pair_score": 79,
          "pair_margin": 4,
          "pair_mode": true,
          "pair_trigger_eligible": true,
          "pair_trigger_reasons": ["complexity.high"],
          "pair_trigger_has_canonical_reason": true,
          "pair_solo_wall_ratio": 1.2
        }
      ]
    }
  ]
}
JSON
expect_fail_contains low-quality-pair-evidence "pair evidence margin below minimum for fixture(s): F16-cli-quote-tax-rules" \
  python3 - "$SCRIPT" "$TMP_DIR/low-quality-frontier.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_pair_evidence_quality(
    pathlib.Path(sys.argv[2]),
    min_pair_margin=5,
    max_pair_solo_wall_ratio=3.0,
))
PY
python3 - "$SCRIPT" "$TMP_DIR/low-quality-frontier.json" > "$TMP_DIR/low-quality-quality-row.out" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
module.print_pair_evidence_quality(
    pathlib.Path(sys.argv[2]),
    min_pair_margin=5,
    max_pair_solo_wall_ratio=3.0,
    status=1,
)
PY
grep -Fq 'pair_evidence_quality=FAIL min_pair_margin_actual=+4 min_pair_margin_required=+5 max_wall_actual=1.20x max_wall_allowed=3.00x' "$TMP_DIR/low-quality-quality-row.out"

cat > "$TMP_DIR/no-quality-rows-frontier.json" <<'JSON'
{
  "pair_margin_min": 21,
  "pair_solo_wall_ratio_max": 1.2,
  "rows": []
}
JSON
expect_fail_contains no-quality-rows "pair evidence quality check has no complete rows" \
  python3 - "$SCRIPT" "$TMP_DIR/no-quality-rows-frontier.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_pair_evidence_quality(
    pathlib.Path(sys.argv[2]),
    min_pair_margin=5,
    max_pair_solo_wall_ratio=3.0,
))
PY

cat > "$TMP_DIR/high-wall-frontier.json" <<'JSON'
{
  "pair_margin_min": 21,
  "pair_solo_wall_ratio_max": 3.5,
  "rows": [
    {
      "fixture": "F16-cli-quote-tax-rules",
      "status": "pair_evidence_passed",
      "passing_pair_evidence": [
        {
          "run_id": "high-wall-run",
          "pair_arm": "l2_risk_probes",
          "bare_score": 50,
          "solo_score": 75,
          "pair_score": 96,
          "pair_margin": 21,
          "pair_mode": true,
          "pair_trigger_eligible": true,
          "pair_trigger_reasons": ["complexity.high"],
          "pair_trigger_has_canonical_reason": true,
          "pair_solo_wall_ratio": 3.5
        }
      ]
    }
  ]
}
JSON
expect_fail_contains high-wall-pair-evidence "pair evidence wall ratio above maximum for fixture(s): F16-cli-quote-tax-rules" \
  python3 - "$SCRIPT" "$TMP_DIR/high-wall-frontier.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_pair_evidence_quality(
    pathlib.Path(sys.argv[2]),
    min_pair_margin=5,
    max_pair_solo_wall_ratio=3.0,
))
PY

cat > "$TMP_DIR/summary-mismatch-frontier.json" <<'JSON'
{
  "pair_margin_min": 22,
  "pair_solo_wall_ratio_max": 1.2,
  "rows": [
    {
      "fixture": "F16-cli-quote-tax-rules",
      "status": "pair_evidence_passed",
      "passing_pair_evidence": [
        {
          "run_id": "summary-mismatch-run",
          "pair_arm": "l2_risk_probes",
          "bare_score": 50,
          "solo_score": 75,
          "pair_score": 96,
          "pair_margin": 21,
          "pair_mode": true,
          "pair_trigger_eligible": true,
          "pair_trigger_reasons": ["complexity.high"],
          "pair_trigger_has_canonical_reason": true,
          "pair_solo_wall_ratio": 1.2
        }
      ]
    }
  ]
}
JSON
expect_fail_contains summary-margin-mismatch "frontier pair_margin_min does not match pair evidence rows" \
  python3 - "$SCRIPT" "$TMP_DIR/summary-mismatch-frontier.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_pair_evidence_quality(
    pathlib.Path(sys.argv[2]),
    min_pair_margin=5,
    max_pair_solo_wall_ratio=3.0,
))
PY

cat > "$TMP_DIR/summary-wall-mismatch-frontier.json" <<'JSON'
{
  "pair_margin_min": 21,
  "pair_solo_wall_ratio_max": 1.3,
  "rows": [
    {
      "fixture": "F16-cli-quote-tax-rules",
      "status": "pair_evidence_passed",
      "passing_pair_evidence": [
        {
          "run_id": "summary-wall-mismatch-run",
          "pair_arm": "l2_risk_probes",
          "bare_score": 50,
          "solo_score": 75,
          "pair_score": 96,
          "pair_margin": 21,
          "pair_mode": true,
          "pair_trigger_eligible": true,
          "pair_trigger_reasons": ["complexity.high"],
          "pair_trigger_has_canonical_reason": true,
          "pair_solo_wall_ratio": 1.2
        }
      ]
    }
  ]
}
JSON
expect_fail_contains summary-wall-mismatch "frontier pair_solo_wall_ratio_max does not match pair evidence rows" \
  python3 - "$SCRIPT" "$TMP_DIR/summary-wall-mismatch-frontier.json" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_pair_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.exit(module.check_pair_evidence_quality(
    pathlib.Path(sys.argv[2]),
    min_pair_margin=5,
    max_pair_solo_wall_ratio=3.0,
))
PY

echo "PASS test-audit-pair-evidence"
