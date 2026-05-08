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
  local pair_arm="${9:-l2_gated}"
  local dir="$TMP_DIR/$run_id/$fixture"
  mkdir -p "$dir/bare" "$dir/solo_claude" "$dir/$pair_arm"
  cat > "$dir/judge.json" <<EOF
{
  "scores_by_arm": {"bare": $bare, "solo_claude": $solo, "$pair_arm": $pair},
  "disqualifiers_by_arm": {}
}
EOF
  for arm in bare solo_claude "$pair_arm"; do
    cat > "$dir/$arm/verify.json" <<'EOF'
{"disqualifier": false}
EOF
  done
  cat > "$dir/bare/result.json" <<'EOF'
{"timed_out": false, "invoke_failure": false, "disqualifier": false, "elapsed_seconds": 20}
EOF
  cat > "$dir/solo_claude/result.json" <<EOF
{"timed_out": false, "invoke_failure": false, "disqualifier": false, "elapsed_seconds": $solo_elapsed}
EOF
  cat > "$dir/$pair_arm/result.json" <<EOF
{"timed_out": false, "invoke_failure": false, "disqualifier": false, "elapsed_seconds": $pair_elapsed, "pair_mode": $pair_mode}
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
write_fixture pass F22 60 80 88 true 280 140
python3 "$GATE" --results-root "$TMP_DIR" --run-id pass \
  --max-pair-solo-wall-ratio 3 \
  --out-json "$TMP_DIR/pass.json" \
  --out-md "$TMP_DIR/pass.md"
grep -Fq '"verdict": "PASS"' "$TMP_DIR/pass.json"
grep -Fq '"avg_pair_solo_wall_ratio": 2.0' "$TMP_DIR/pass.json"
grep -Fq 'Verdict: **PASS**' "$TMP_DIR/pass.md"

write_fixture no-headroom F21 50 81 90 true
write_fixture no-headroom F22 60 80 88 true
expect_fail_contains no-headroom "solo_claude score 81 > 80" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id no-headroom

write_fixture no-pair-mode F21 50 75 85 false
write_fixture no-pair-mode F22 60 80 90 true
expect_fail_contains no-pair-mode "l2_gated pair_mode not true" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id no-pair-mode

write_fixture weak-margin F21 50 75 79 true
write_fixture weak-margin F22 60 80 88 true
expect_fail_contains weak-margin "l2_gated margin +4 < +5" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id weak-margin

write_fixture custom-pair-arm F21 50 75 82 true 220 110 l2_risk_probes
write_fixture custom-pair-arm F22 60 80 88 true 280 140 l2_risk_probes
python3 "$GATE" --results-root "$TMP_DIR" --run-id custom-pair-arm \
  --pair-arm l2_risk_probes \
  --max-pair-solo-wall-ratio 3 \
  --out-json "$TMP_DIR/custom-pair-arm.json" \
  --out-md "$TMP_DIR/custom-pair-arm.md"
grep -Fq '"pair_arm": "l2_risk_probes"' "$TMP_DIR/custom-pair-arm.json"
grep -Fq 'l2_risk_probes - solo_claude >= 5' "$TMP_DIR/custom-pair-arm.md"

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
grep -Fq '"pair_solo_wall_ratio": null' "$TMP_DIR/provider-limit.json"
if grep -Fq 'margin -' "$TMP_DIR/provider-limit.md"; then
  echo "provider-limit row must not report quality margin" >&2
  cat "$TMP_DIR/provider-limit.md" >&2
  exit 1
fi

write_fixture slow-pair F21 50 75 85 true 401 100
write_fixture slow-pair F22 60 80 88 true 280 140
expect_fail_contains slow-pair "pair/solo wall ratio 4.01 > 3.00" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id slow-pair --max-pair-solo-wall-ratio 3

write_fixture one-fixture F21 50 75 85 true
expect_fail_contains one-fixture "fixture_count_ok" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id one-fixture --out-json "$TMP_DIR/one-fixture.json"
grep -Fq '"fixture_count_ok": false' "$TMP_DIR/one-fixture.json"

echo "PASS test-full-pipeline-pair-gate"
