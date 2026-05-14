#!/usr/bin/env bash
# Regression tests for iter-0033c-compare.py score-source handling.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPARE="$SCRIPT_DIR/iter-0033c-compare.py"
TMP_DIR="$(mktemp -d /tmp/iter-0033c-compare-test.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

write_manifest() {
  local path="$1"
  cat > "$path" <<'JSON'
{
  "manifest_sha256": "synthetic",
  "fixtures_pair_eligible": ["F1"],
  "gate3_threshold_count": 1,
  "gate3_total": 1
}
JSON
}

write_manifest_with_values() {
  local path="$1"
  local eligible="$2"
  local threshold="$3"
  local total="$4"
  cat > "$path" <<JSON
{
  "manifest_sha256": "synthetic",
  "fixtures_pair_eligible": $eligible,
  "gate3_threshold_count": $threshold,
  "gate3_total": $total
}
JSON
}

write_fixture() {
  local run_dir="$1"
  local mapping_c="$2"
  local fixture="$run_dir/F1-synthetic"
  mkdir -p "$fixture"/{solo_claude,l2_gated}
  cat > "$fixture/solo_claude/result.json" <<'JSON'
{"elapsed_seconds": 100, "timed_out": false}
JSON
  cat > "$fixture/l2_gated/result.json" <<'JSON'
{"elapsed_seconds": 150, "timed_out": false}
JSON
  cat > "$fixture/judge.json" <<JSON
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "C": "$mapping_c", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "l2_gated": 70},
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "l2_gated": {"disqualifier": false}
  }
}
JSON
}

write_fixture_with_malformed_mapping() {
  local run_dir="$1"
  local fixture="$run_dir/F1-synthetic"
  mkdir -p "$fixture"/{solo_claude,l2_gated}
  cat > "$fixture/solo_claude/result.json" <<'JSON'
{"elapsed_seconds": 100, "timed_out": false}
JSON
  cat > "$fixture/l2_gated/result.json" <<'JSON'
{"elapsed_seconds": 150, "timed_out": false}
JSON
  cat > "$fixture/judge.json" <<'JSON'
{
  "_blind_mapping": "not-a-dict",
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "l2_gated": 70},
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "l2_gated": {"disqualifier": false}
  }
}
JSON
}

write_fixture_with_malformed_scores() {
  local run_dir="$1"
  local fixture="$run_dir/F1-synthetic"
  mkdir -p "$fixture"/{solo_claude,l2_gated}
  cat > "$fixture/solo_claude/result.json" <<'JSON'
{"elapsed_seconds": 100, "timed_out": false}
JSON
  cat > "$fixture/l2_gated/result.json" <<'JSON'
{"elapsed_seconds": 150, "timed_out": false}
JSON
  cat > "$fixture/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "C": "l2_gated", "seed": 1},
  "scores_by_arm": ["not", "a", "dict"],
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "l2_gated": {"disqualifier": false}
  }
}
JSON
}

write_fixture_with_malformed_dq_entry() {
  local run_dir="$1"
  local fixture="$run_dir/F1-synthetic"
  mkdir -p "$fixture"/{solo_claude,l2_gated}
  cat > "$fixture/solo_claude/result.json" <<'JSON'
{"elapsed_seconds": 100, "timed_out": false}
JSON
  cat > "$fixture/l2_gated/result.json" <<'JSON'
{"elapsed_seconds": 150, "timed_out": false}
JSON
  cat > "$fixture/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "C": "l2_gated", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "l2_gated": 70},
  "disqualifiers_by_arm": {"l2_gated": true}
}
JSON
}

write_fixture_with_malformed_legacy_dq() {
  local run_dir="$1"
  local fixture="$run_dir/F1-synthetic"
  mkdir -p "$fixture"/{solo_claude,l2_gated}
  cat > "$fixture/solo_claude/result.json" <<'JSON'
{"elapsed_seconds": 100, "timed_out": false}
JSON
  cat > "$fixture/l2_gated/result.json" <<'JSON'
{"elapsed_seconds": 150, "timed_out": false}
JSON
  cat > "$fixture/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "C": "l2_gated", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "l2_gated": 70},
  "disqualifiers": ["not", "a", "dict"]
}
JSON
}

write_fixture_with_string_dq_entry() {
  local run_dir="$1"
  local fixture="$run_dir/F1-synthetic"
  mkdir -p "$fixture"/{solo_claude,l2_gated}
  cat > "$fixture/solo_claude/result.json" <<'JSON'
{"elapsed_seconds": 100, "timed_out": false}
JSON
  cat > "$fixture/l2_gated/result.json" <<'JSON'
{"elapsed_seconds": 150, "timed_out": false}
JSON
  cat > "$fixture/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "C": "l2_gated", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "l2_gated": 70},
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "l2_gated": {"disqualifier": "false"}
  }
}
JSON
}

write_fixture_with_string_timeout() {
  local run_dir="$1"
  local fixture="$run_dir/F1-synthetic"
  mkdir -p "$fixture"/{solo_claude,l2_gated}
  cat > "$fixture/solo_claude/result.json" <<'JSON'
{"elapsed_seconds": 100, "timed_out": false}
JSON
  cat > "$fixture/l2_gated/result.json" <<'JSON'
{"elapsed_seconds": 150, "timed_out": "false"}
JSON
  cat > "$fixture/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "C": "l2_gated", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "l2_gated": 70},
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "l2_gated": {"disqualifier": false}
  }
}
JSON
}

write_fixture_with_malformed_result() {
  local run_dir="$1"
  local fixture="$run_dir/F1-synthetic"
  mkdir -p "$fixture"/{solo_claude,l2_gated}
  printf '["not", "a", "dict"]\n' > "$fixture/solo_claude/result.json"
  cat > "$fixture/l2_gated/result.json" <<'JSON'
{"elapsed_seconds": 150, "timed_out": false}
JSON
  cat > "$fixture/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "C": "l2_gated", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "l2_gated": 70},
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "l2_gated": {"disqualifier": false}
  }
}
JSON
}

write_state_pair_judge() {
  local arm="$1"
  local pair_judge_json="$2"
  local run_dir="$TMP_DIR/bench-synthetic-F1-synthetic-$arm/.devlyn/runs/001"
  mkdir -p "$run_dir"
  cat > "$run_dir/pipeline.state.json" <<JSON
{
  "phases": {
    "verify": {
      "sub_verdicts": {
        "judge": "PASS_WITH_ISSUES",
        "pair_judge": $pair_judge_json
      }
    }
  }
}
JSON
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

MANIFEST="$TMP_DIR/manifest.json"
write_manifest "$MANIFEST"

cat > "$TMP_DIR/nan-threshold-manifest.json" <<'JSON'
{
  "fixtures_pair_eligible": ["F1"],
  "gate3_threshold_count": NaN,
  "gate3_total": 1,
  "manifest_sha256": "synthetic"
}
JSON
expect_fail_contains nan-threshold-manifest "manifest malformed: invalid JSON" \
  python3 "$COMPARE" \
    --manifest "$TMP_DIR/nan-threshold-manifest.json" \
    --results-dir "$TMP_DIR" \
    --work-dir-root "$TMP_DIR" \
    --run-id synthetic \
    --out-json "$TMP_DIR/nan-threshold.json" \
    --out-md "$TMP_DIR/nan-threshold.md"

write_manifest_with_values "$TMP_DIR/empty-manifest.json" '[]' 0 0
expect_fail_contains empty-manifest "fixtures_pair_eligible must not be empty" \
  python3 "$COMPARE" \
    --manifest "$TMP_DIR/empty-manifest.json" \
    --results-dir "$TMP_DIR" \
    --work-dir-root "$TMP_DIR" \
    --run-id synthetic \
    --out-json "$TMP_DIR/empty.json" \
    --out-md "$TMP_DIR/empty.md"

write_manifest_with_values "$TMP_DIR/zero-threshold-manifest.json" '["F1"]' 0 1
expect_fail_contains zero-threshold-manifest "gate3_threshold_count must be a positive integer" \
  python3 "$COMPARE" \
    --manifest "$TMP_DIR/zero-threshold-manifest.json" \
    --results-dir "$TMP_DIR" \
    --work-dir-root "$TMP_DIR" \
    --run-id synthetic \
    --out-json "$TMP_DIR/zero-threshold.json" \
    --out-md "$TMP_DIR/zero-threshold.md"

write_manifest_with_values "$TMP_DIR/total-mismatch-manifest.json" '["F1"]' 1 2
expect_fail_contains total-mismatch-manifest "gate3_total must equal fixtures_pair_eligible length" \
  python3 "$COMPARE" \
    --manifest "$TMP_DIR/total-mismatch-manifest.json" \
    --results-dir "$TMP_DIR" \
    --work-dir-root "$TMP_DIR" \
    --run-id synthetic \
    --out-json "$TMP_DIR/total-mismatch.json" \
    --out-md "$TMP_DIR/total-mismatch.md"

cat > "$TMP_DIR/bad-rejected-reasons-manifest.json" <<'JSON'
{
  "manifest_sha256": "synthetic",
  "fixtures_pair_eligible": ["F1"],
  "gate3_threshold_count": 1,
  "gate3_total": 1,
  "selection_rule": {
    "rejected_excluded": ["F2"],
    "rejected_excluded_reasons": {"F3": "wrong fixture"}
  }
}
JSON
expect_fail_contains bad-rejected-reasons-manifest "selection_rule.rejected_excluded_reasons keys must match rejected_excluded" \
  python3 "$COMPARE" \
    --manifest "$TMP_DIR/bad-rejected-reasons-manifest.json" \
    --results-dir "$TMP_DIR" \
    --work-dir-root "$TMP_DIR" \
    --run-id synthetic \
    --out-json "$TMP_DIR/bad-rejected-reasons.json" \
    --out-md "$TMP_DIR/bad-rejected-reasons.md"

PASS_DIR="$TMP_DIR/pass-results"
mkdir -p "$PASS_DIR"
write_fixture "$PASS_DIR" "l2_gated"
python3 "$COMPARE" \
  --manifest "$MANIFEST" \
  --results-dir "$PASS_DIR" \
  --work-dir-root "$TMP_DIR" \
  --run-id synthetic \
  --out-json "$TMP_DIR/pass.json" \
  --out-md "$TMP_DIR/pass.md"
grep -Fq '"ship_blockers_failed": []' "$TMP_DIR/pass.json"
grep -Fq '"l2_gated_score": 70' "$TMP_DIR/pass.json"

MALFORMED_PAIR_STATE_DIR="$TMP_DIR/malformed-pair-state-results"
mkdir -p "$MALFORMED_PAIR_STATE_DIR"
write_fixture "$MALFORMED_PAIR_STATE_DIR" "l2_gated"
write_state_pair_judge l2_gated '""'
python3 "$COMPARE" \
  --manifest "$MANIFEST" \
  --results-dir "$MALFORMED_PAIR_STATE_DIR" \
  --work-dir-root "$TMP_DIR" \
  --run-id synthetic \
  --out-json "$TMP_DIR/malformed-pair-state.json" \
  --out-md "$TMP_DIR/malformed-pair-state.md"
grep -Fq '"l2_gated_pair_judge_present": false' "$TMP_DIR/malformed-pair-state.json"
grep -Fq '"pair_fired": false' "$TMP_DIR/malformed-pair-state.json"
grep -Fq '"ship_blockers_failed": []' "$TMP_DIR/malformed-pair-state.json"

BAD_DIR="$TMP_DIR/bad-results"
mkdir -p "$BAD_DIR"
write_fixture "$BAD_DIR" "l2_forced"
expect_fail_contains bad-mapping "SHIP-BLOCKER FAIL" \
  python3 "$COMPARE" \
    --manifest "$MANIFEST" \
    --results-dir "$BAD_DIR" \
    --work-dir-root "$TMP_DIR" \
    --run-id synthetic \
    --out-json "$TMP_DIR/bad.json" \
    --out-md "$TMP_DIR/bad.md"
grep -Fq '"l2_gated_score": null' "$TMP_DIR/bad.json"
grep -Fq '"3-lift-on-pair-eligible"' "$TMP_DIR/bad.json"

MALFORMED_DIR="$TMP_DIR/malformed-results"
mkdir -p "$MALFORMED_DIR"
write_fixture_with_malformed_mapping "$MALFORMED_DIR"
expect_fail_contains malformed-mapping "SHIP-BLOCKER FAIL" \
  python3 "$COMPARE" \
    --manifest "$MANIFEST" \
    --results-dir "$MALFORMED_DIR" \
    --work-dir-root "$TMP_DIR" \
    --run-id synthetic \
    --out-json "$TMP_DIR/malformed.json" \
    --out-md "$TMP_DIR/malformed.md"
grep -Fq '"solo_score": null' "$TMP_DIR/malformed.json"
grep -Fq '"l2_gated_score": null' "$TMP_DIR/malformed.json"
grep -Fq '"solo_dq": true' "$TMP_DIR/malformed.json"
grep -Fq '"l2_gated_dq": true' "$TMP_DIR/malformed.json"

MALFORMED_SCORES_DIR="$TMP_DIR/malformed-scores-results"
mkdir -p "$MALFORMED_SCORES_DIR"
write_fixture_with_malformed_scores "$MALFORMED_SCORES_DIR"
expect_fail_contains malformed-scores "SHIP-BLOCKER FAIL" \
  python3 "$COMPARE" \
    --manifest "$MANIFEST" \
    --results-dir "$MALFORMED_SCORES_DIR" \
    --work-dir-root "$TMP_DIR" \
    --run-id synthetic \
    --out-json "$TMP_DIR/malformed-scores.json" \
    --out-md "$TMP_DIR/malformed-scores.md"
grep -Fq '"solo_score": null' "$TMP_DIR/malformed-scores.json"
grep -Fq '"l2_gated_score": null' "$TMP_DIR/malformed-scores.json"

OVERRANGE_SCORES_DIR="$TMP_DIR/overrange-scores-results"
mkdir -p "$OVERRANGE_SCORES_DIR"
write_fixture "$OVERRANGE_SCORES_DIR" "l2_gated"
python3 - "$OVERRANGE_SCORES_DIR/F1-synthetic/judge.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["scores_by_arm"]["l2_gated"] = 101
data["c_score"] = 101
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains overrange-scores "SHIP-BLOCKER FAIL" \
  python3 "$COMPARE" \
    --manifest "$MANIFEST" \
    --results-dir "$OVERRANGE_SCORES_DIR" \
    --work-dir-root "$TMP_DIR" \
    --run-id synthetic \
    --out-json "$TMP_DIR/overrange-scores.json" \
    --out-md "$TMP_DIR/overrange-scores.md"
grep -Fq '"l2_gated_score": null' "$TMP_DIR/overrange-scores.json"

BOOLEAN_SCORES_DIR="$TMP_DIR/boolean-scores-results"
mkdir -p "$BOOLEAN_SCORES_DIR"
write_fixture "$BOOLEAN_SCORES_DIR" "l2_gated"
python3 - "$BOOLEAN_SCORES_DIR/F1-synthetic/judge.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["scores_by_arm"]["solo_claude"] = True
data["a_score"] = True
json.dump(data, open(path, "w"), indent=2)
PY
expect_fail_contains boolean-scores "SHIP-BLOCKER FAIL" \
  python3 "$COMPARE" \
    --manifest "$MANIFEST" \
    --results-dir "$BOOLEAN_SCORES_DIR" \
    --work-dir-root "$TMP_DIR" \
    --run-id synthetic \
    --out-json "$TMP_DIR/boolean-scores.json" \
    --out-md "$TMP_DIR/boolean-scores.md"
grep -Fq '"solo_score": null' "$TMP_DIR/boolean-scores.json"

BOOLEAN_WALL_DIR="$TMP_DIR/boolean-wall-results"
mkdir -p "$BOOLEAN_WALL_DIR"
write_fixture "$BOOLEAN_WALL_DIR" "l2_gated"
python3 - "$BOOLEAN_WALL_DIR/F1-synthetic/l2_gated/result.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["elapsed_seconds"] = True
json.dump(data, open(path, "w"), indent=2)
PY
python3 "$COMPARE" \
  --manifest "$MANIFEST" \
  --results-dir "$BOOLEAN_WALL_DIR" \
  --work-dir-root "$TMP_DIR" \
  --run-id synthetic \
  --out-json "$TMP_DIR/boolean-wall.json" \
  --out-md "$TMP_DIR/boolean-wall.md" >/dev/null
grep -Fq '"l2_gated_wall": null' "$TMP_DIR/boolean-wall.json"

NAN_WALL_DIR="$TMP_DIR/nan-wall-results"
mkdir -p "$NAN_WALL_DIR"
write_fixture "$NAN_WALL_DIR" "l2_gated"
cat > "$NAN_WALL_DIR/F1-synthetic/l2_gated/result.json" <<'JSON'
{"elapsed_seconds": NaN, "timed_out": false}
JSON
python3 "$COMPARE" \
  --manifest "$MANIFEST" \
  --results-dir "$NAN_WALL_DIR" \
  --work-dir-root "$TMP_DIR" \
  --run-id synthetic \
  --out-json "$TMP_DIR/nan-wall.json" \
  --out-md "$TMP_DIR/nan-wall.md" >/dev/null
grep -Fq '"l2_gated_wall": null' "$TMP_DIR/nan-wall.json"

STRING_TIMEOUT_DIR="$TMP_DIR/string-timeout-results"
mkdir -p "$STRING_TIMEOUT_DIR"
write_fixture_with_string_timeout "$STRING_TIMEOUT_DIR"
expect_fail_contains string-timeout "SHIP-BLOCKER FAIL" \
  python3 "$COMPARE" \
    --manifest "$MANIFEST" \
    --results-dir "$STRING_TIMEOUT_DIR" \
    --work-dir-root "$TMP_DIR" \
    --run-id synthetic \
    --out-json "$TMP_DIR/string-timeout.json" \
    --out-md "$TMP_DIR/string-timeout.md"
grep -Fq '"l2_gated_timeout": true' "$TMP_DIR/string-timeout.json"

MALFORMED_DQ_ENTRY_DIR="$TMP_DIR/malformed-dq-entry-results"
mkdir -p "$MALFORMED_DQ_ENTRY_DIR"
write_fixture_with_malformed_dq_entry "$MALFORMED_DQ_ENTRY_DIR"
python3 "$COMPARE" \
  --manifest "$MANIFEST" \
  --results-dir "$MALFORMED_DQ_ENTRY_DIR" \
  --work-dir-root "$TMP_DIR" \
  --run-id synthetic \
  --out-json "$TMP_DIR/malformed-dq-entry.json" \
  --out-md "$TMP_DIR/malformed-dq-entry.md" >/dev/null
grep -Fq '"l2_gated_dq": true' "$TMP_DIR/malformed-dq-entry.json"

STRING_DQ_ENTRY_DIR="$TMP_DIR/string-dq-entry-results"
mkdir -p "$STRING_DQ_ENTRY_DIR"
write_fixture_with_string_dq_entry "$STRING_DQ_ENTRY_DIR"
python3 "$COMPARE" \
  --manifest "$MANIFEST" \
  --results-dir "$STRING_DQ_ENTRY_DIR" \
  --work-dir-root "$TMP_DIR" \
  --run-id synthetic \
  --out-json "$TMP_DIR/string-dq-entry.json" \
  --out-md "$TMP_DIR/string-dq-entry.md" >/dev/null
grep -Fq '"l2_gated_dq": true' "$TMP_DIR/string-dq-entry.json"

MALFORMED_LEGACY_DQ_DIR="$TMP_DIR/malformed-legacy-dq-results"
mkdir -p "$MALFORMED_LEGACY_DQ_DIR"
write_fixture_with_malformed_legacy_dq "$MALFORMED_LEGACY_DQ_DIR"
python3 "$COMPARE" \
  --manifest "$MANIFEST" \
  --results-dir "$MALFORMED_LEGACY_DQ_DIR" \
  --work-dir-root "$TMP_DIR" \
  --run-id synthetic \
  --out-json "$TMP_DIR/malformed-legacy-dq.json" \
  --out-md "$TMP_DIR/malformed-legacy-dq.md" >/dev/null
grep -Fq '"ship_blockers_failed": []' "$TMP_DIR/malformed-legacy-dq.json"
grep -Fq '"solo_dq": true' "$TMP_DIR/malformed-legacy-dq.json"
grep -Fq '"l2_gated_dq": true' "$TMP_DIR/malformed-legacy-dq.json"

MALFORMED_RESULT_DIR="$TMP_DIR/malformed-result-results"
mkdir -p "$MALFORMED_RESULT_DIR"
write_fixture_with_malformed_result "$MALFORMED_RESULT_DIR"
python3 "$COMPARE" \
  --manifest "$MANIFEST" \
  --results-dir "$MALFORMED_RESULT_DIR" \
  --work-dir-root "$TMP_DIR" \
  --run-id synthetic \
  --out-json "$TMP_DIR/malformed-result.json" \
  --out-md "$TMP_DIR/malformed-result.md" >/dev/null
grep -Fq '"solo_wall": null' "$TMP_DIR/malformed-result.json"

echo "PASS test-iter-0033c-compare"
