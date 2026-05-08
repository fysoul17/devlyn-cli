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
  "disqualifiers_by_arm": {}
}
EOF
  cat > "$dir/bare/result.json" <<'EOF'
{"timed_out": false, "invoke_failure": false}
EOF
  cat > "$dir/bare/verify.json" <<'EOF'
{"disqualifier": false}
EOF
  cat > "$dir/solo_claude/result.json" <<EOF
{"timed_out": $solo_timed_out, "invoke_failure": false}
EOF
  cat > "$dir/solo_claude/verify.json" <<'EOF'
{"disqualifier": false}
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

write_fixture one-pass F10 50 75
expect_fail_contains min-fixtures 'Verdict: **FAIL**' \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id one-pass --out-json "$TMP_DIR/one-pass.json"
grep -Fq '"fixture_count_ok": false' "$TMP_DIR/one-pass.json"

write_fixture two-pass F10 50 75
write_fixture two-pass F12 60 80
python3 "$GATE" --results-root "$TMP_DIR" --run-id two-pass --out-json "$TMP_DIR/two-pass.json" \
  > "$TMP_DIR/two-pass.out"
grep -Fq '"verdict": "PASS"' "$TMP_DIR/two-pass.json"
grep -Fq '"fixture_count_ok": true' "$TMP_DIR/two-pass.json"

write_fixture solo-ceiling F10 50 75
write_fixture solo-ceiling F12 20 92
expect_fail_contains solo-ceiling "solo_claude score 92 > 80" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id solo-ceiling

write_fixture dirty-solo F10 50 75
write_fixture dirty-solo F12 20 70 true
expect_fail_contains dirty-solo "solo_claude timed out" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id dirty-solo

write_fixture missing-artifact F10 50 75
write_fixture missing-artifact F12 20 70
rm "$TMP_DIR/missing-artifact/F12/solo_claude/verify.json"
expect_fail_contains missing-artifact "solo_claude verify.json missing" \
  python3 "$GATE" --results-root "$TMP_DIR" --run-id missing-artifact

echo "✓ test-headroom-gate"
