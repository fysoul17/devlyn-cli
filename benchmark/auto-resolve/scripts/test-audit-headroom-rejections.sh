#!/usr/bin/env bash
# Regression tests for audit-headroom-rejections.py.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$SCRIPT_DIR/audit-headroom-rejections.py"
TMP_DIR="$(mktemp -d /tmp/audit-headroom-rejections-test.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

fixtures="$TMP_DIR/fixtures"
results="$TMP_DIR/results"
registry="$TMP_DIR/pair-rejected-fixtures.sh"
mkdir -p "$fixtures/F16-cli-quote-tax-rules" \
  "$fixtures/F33-cli-new-candidate" \
  "$fixtures/F34-cli-rejected-candidate" \
  "$fixtures/F35-cli-missing-judge" \
  "$fixtures/F36-unsupported-rejection" \
  "$results/old-f16" \
  "$results/f33-headroom" \
  "$results/f33-weak-pair-pass" \
  "$results/f34-headroom" \
  "$results/f35-missing-judge" \
  "$results/20260512-f36-headroom" \
  "$results/bad-json-headroom" \
  "$results/malformed-headroom" \
  "$results/f16-pair-pass"

cat > "$registry" <<'SH'
rejected_pair_fixture_reason() {
  local fid="$1"
  case "$fid" in
    F34-*|F34)
      echo "measured solo ceiling"
      ;;
    F36-*|F36)
      echo "bare 33 / solo_claude 98 in 20260512-missing-headroom"
      ;;
    *)
      return 1
      ;;
  esac
}
SH

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

spec = importlib.util.spec_from_file_location("audit_headroom_rejections", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
assert module.registry_short_ids(pathlib.Path(sys.argv[2])) == {"S3"}
PY

write_headroom_fail() {
  local run_id="$1"
  local fixture="$2"
  local bare="$3"
  local solo="$4"
  cat > "$results/$run_id/headroom-gate.json" <<JSON
{
  "run_id": "$run_id",
  "verdict": "FAIL",
  "rows": [
    {
      "fixture": "$fixture",
      "status": "FAIL",
      "bare_score": $bare,
      "solo_score": $solo,
      "reason": "solo_claude score $solo > 80"
    }
  ]
}
JSON
}

write_headroom_fail old-f16 F16-cli-quote-tax-rules 50 98
write_headroom_fail f33-headroom F33-cli-new-candidate 33 98
write_headroom_fail f34-headroom F34-cli-rejected-candidate 33 98

cat > "$results/f35-missing-judge/headroom-gate.json" <<'JSON'
{
  "run_id": "f35-missing-judge",
  "verdict": "FAIL",
  "rows": [
    {
      "fixture": "F35-cli-missing-judge",
      "status": "MISSING_JUDGE",
      "reason": "judge.json missing"
    }
  ]
}
JSON

cat > "$results/malformed-headroom/headroom-gate.json" <<'JSON'
{
  "run_id": "malformed-headroom",
  "verdict": "FAIL",
  "rows": []
}
JSON

printf '{not-json\n' > "$results/bad-json-headroom/headroom-gate.json"

cat > "$results/f16-pair-pass/full-pipeline-pair-gate.json" <<'JSON'
{
  "run_id": "f16-pair-pass",
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
      "pair_solo_wall_ratio": 1.28
    }
  ]
}
JSON
mkdir -p "$results/f16-pair-pass/F16-cli-quote-tax-rules/l2_risk_probes"
cat > "$results/f16-pair-pass/F16-cli-quote-tax-rules/l2_risk_probes/result.json" <<'JSON'
{
  "pair_trigger": {
    "eligible": true,
    "reasons": ["complexity.high"],
    "skipped_reason": null
  }
}
JSON
python3 - "$SCRIPT" "$results" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("audit_headroom_rejections", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
results_root = pathlib.Path(sys.argv[2])
kwargs = {
    "results_root": results_root,
    "run_id": "f16-pair-pass",
    "fixture": "F16-cli-quote-tax-rules",
    "pair_arm": "l2_risk_probes",
}
assert module.pair_result_trigger_reasons(**kwargs) == ["complexity.high"]
path = (
    results_root
    / "f16-pair-pass"
    / "F16-cli-quote-tax-rules"
    / "l2_risk_probes"
    / "result.json"
)
path.write_text(
    '{"pair_trigger":{"eligible":true,"reasons":["risk high"],"skipped_reason":null}}\n',
    encoding="utf8",
)
assert module.pair_result_trigger_reasons(**kwargs) == []
path.write_text(
    '{"pair_trigger":{"eligible":true,"reasons":["complexity.high"],"skipped_reason":null}}\n',
    encoding="utf8",
)
PY

cat > "$results/f33-weak-pair-pass/full-pipeline-pair-gate.json" <<'JSON'
{
  "run_id": "f33-weak-pair-pass",
  "verdict": "PASS",
  "pair_arm": "l2_risk_probes",
  "rows": [
    {
      "fixture": "F33-cli-new-candidate",
      "status": "PASS",
      "bare_score": 33,
      "solo_score": 98,
      "pair_score": 96,
      "pair_margin": -2,
      "pair_mode": true,
      "pair_trigger_eligible": true,
      "pair_solo_wall_ratio": 1.1
    }
  ]
}
JSON

if python3 "$SCRIPT" \
  --fixtures-root "$fixtures" \
  --registry "$registry" \
  --results-root "$results" \
  --out-json "$TMP_DIR/audit.json" > "$TMP_DIR/audit.out" 2> "$TMP_DIR/audit.err"; then
  echo "expected unrecorded F33 failure" >&2
  exit 1
fi
grep -Fq 'F33-cli-new-candidate' "$TMP_DIR/audit.err"
grep -Fq 'F35-cli-missing-judge' "$TMP_DIR/audit.err"
grep -Fq 'status=MISSING_JUDGE' "$TMP_DIR/audit.err"
grep -Fq 'malformed-headroom <unknown>' "$TMP_DIR/audit.err"
grep -Fq 'status=MALFORMED_ROWS' "$TMP_DIR/audit.err"
grep -Fq 'bad-json-headroom <unknown>' "$TMP_DIR/audit.err"
grep -Fq 'status=MALFORMED_JSON' "$TMP_DIR/audit.err"
grep -Fq 'unsupported registry rejection(s)' "$TMP_DIR/audit.err"
grep -Fq 'F36-unsupported-rejection' "$TMP_DIR/audit.err"
grep -Fq 'expected_run=20260512-missing-headroom' "$TMP_DIR/audit.err"
grep -Fq 'solo_claude=98' "$TMP_DIR/audit.err"
grep -Fq 'expected_solo_claude=98' "$TMP_DIR/audit.err"
grep -Fq '"verdict": "FAIL"' "$TMP_DIR/audit.json"
grep -Fq '"fixture": "F33-cli-new-candidate"' "$TMP_DIR/audit.json"
grep -Fq '"fixture": "F35-cli-missing-judge"' "$TMP_DIR/audit.json"
grep -Fq '"fixture": "<unknown>"' "$TMP_DIR/audit.json"
grep -Fq '"unsupported_registry_rejections"' "$TMP_DIR/audit.json"
if grep -Fq 'F16-cli-quote-tax-rules' "$TMP_DIR/audit.err"; then
  echo "F16 has passing pair evidence and must not be reported" >&2
  cat "$TMP_DIR/audit.err" >&2
  exit 1
fi
if grep -Fq 'F34-cli-rejected-candidate' "$TMP_DIR/audit.err"; then
  echo "F34 is rejected and must not be reported" >&2
  cat "$TMP_DIR/audit.err" >&2
  exit 1
fi

python3 - "$registry" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
text = text.replace(
    '    F34-*|F34)',
    '    F33-*|F33)\n'
    '      echo "measured solo ceiling"\n'
    '      ;;\n'
    '    F35-*|F35)\n'
    '      echo "missing judge artifact"\n'
    '      ;;\n'
    '    F34-*|F34)'
)
path.write_text(text)
PY

rm -rf "$results/malformed-headroom"
rm -rf "$results/bad-json-headroom"

write_headroom_fail 20260512-f36-headroom F36-unsupported-rejection 33 98
python3 - "$registry" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
text = text.replace(
    "bare 33 / solo_claude 98 in 20260512-missing-headroom",
    "bare 33 / solo_claude 98 in 20260512-f36-headroom",
)
path.write_text(text)
PY

python3 "$SCRIPT" \
  --fixtures-root "$fixtures" \
  --registry "$registry" \
  --results-root "$results" \
  --out-json "$TMP_DIR/audit-pass.json" \
  > "$TMP_DIR/audit-pass.out"
grep -Fq 'PASS audit-headroom-rejections' "$TMP_DIR/audit-pass.out"
grep -Fq '"verdict": "PASS"' "$TMP_DIR/audit-pass.json"
grep -Fq '"unsupported_registry_rejections": []' "$TMP_DIR/audit-pass.json"

echo "PASS test-audit-headroom-rejections"
