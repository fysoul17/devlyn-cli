#!/usr/bin/env bash
# Regression tests for frozen-verify-gate.py evidence guards.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GATE="$SCRIPT_DIR/frozen-verify-gate.py"
TMP_DIR="$(mktemp -d /tmp/frozen-verify-gate-test.XXXXXX)"
FIXTURES_DIR="$TMP_DIR/fixtures"
trap 'rm -rf "$TMP_DIR"' EXIT
mkdir -p "$FIXTURES_DIR"

write_run() {
  local run_id="$1"
  local fixture_id="${2:-}"
  local solo_verdict="$3"
  local pair_verdict="$4"
  local lift="$5"
  local internal_lift="${6:-false}"
  local pair_primary="${7:-$pair_verdict}"
  local pair_judge="${8:-$pair_verdict}"
  mkdir -p "$TMP_DIR/$run_id/pair"
  if [ -n "$fixture_id" ]; then
    cat > "$TMP_DIR/$run_id/pair/input.md" <<EOF
Use /devlyn:resolve --verify-only --spec docs/roadmap/phase-1/$fixture_id.md.
EOF
  fi
  cat > "$TMP_DIR/$run_id/compare.json" <<EOF
{
  "solo": {"invoke_exit": 0, "timed_out": false, "verify_verdict": "$solo_verdict", "elapsed_seconds": 100},
  "pair": {"invoke_exit": 0, "timed_out": false, "verify_verdict": "$pair_verdict", "pair_mode": true, "elapsed_seconds": 200},
  "comparison": {
    "pair_trigger_missed": false,
    "pair_verdict_lift": $lift,
    "pair_internal_verdict_lift": $internal_lift,
    "solo_verdict": "$solo_verdict",
    "pair_verdict": "$pair_verdict",
    "pair_primary_verdict": "$pair_primary",
    "pair_judge_verdict": "$pair_judge"
  }
}
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

write_run pass-a F10-persist-write-collision PASS_WITH_ISSUES NEEDS_WORK true
write_run pass-b F12-webhook-raw-body-signature PASS_WITH_ISSUES NEEDS_WORK true
mkdir -p "$FIXTURES_DIR/F10-persist-write-collision" "$FIXTURES_DIR/F12-webhook-raw-body-signature"
python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
  --run-id pass-a --run-id pass-b --min-runs 2 --max-pair-solo-wall-ratio 3 \
  > "$TMP_DIR/pass.out"
grep -Fq '"verdict": "PASS"' "$TMP_DIR/pass.out"
grep -Fq '"avg_pair_solo_wall_ratio": 2.0' "$TMP_DIR/pass.out"
grep -Fq '"pair_solo_wall_ratio": 2.0' "$TMP_DIR/pass.out"

mkdir -p "$TMP_DIR/summary-verdicts/pair"
cat > "$TMP_DIR/summary-verdicts/pair/input.md" <<'EOF'
Use /devlyn:resolve --verify-only --spec docs/roadmap/phase-1/F13-summary-verdict-fallback.md.
EOF
cat > "$TMP_DIR/summary-verdicts/compare.json" <<'EOF'
{
  "solo": {"invoke_exit": 0, "timed_out": false, "verify_verdict": "PASS_WITH_ISSUES", "elapsed_seconds": 100},
  "pair": {"invoke_exit": 0, "timed_out": false, "verify_verdict": "NEEDS_WORK", "pair_mode": true, "elapsed_seconds": 200},
  "comparison": {"pair_trigger_missed": false, "pair_verdict_lift": true, "pair_internal_verdict_lift": false}
}
EOF
mkdir -p "$FIXTURES_DIR/F13-summary-verdict-fallback"
python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
  --run-id summary-verdicts --min-runs 1 \
  > "$TMP_DIR/summary-verdicts.out"
grep -Fq '"verdict": "PASS"' "$TMP_DIR/summary-verdicts.out"

write_run dup-a F12-webhook-raw-body-signature PASS_WITH_ISSUES NEEDS_WORK true
write_run dup-b F12-webhook-raw-body-signature PASS_WITH_ISSUES NEEDS_WORK true
expect_fail_contains duplicate-fixture "duplicate fixture_id=F12-webhook-raw-body-signature" \
  python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
    --run-id dup-a --run-id dup-b --min-runs 2

write_run missing-fixture "" PASS_WITH_ISSUES NEEDS_WORK true
expect_fail_contains missing-fixture "fixture_id missing" \
  python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
    --run-id missing-fixture --min-runs 1

write_run unknown-fixture F99-not-a-real-fixture PASS_WITH_ISSUES NEEDS_WORK true
expect_fail_contains unknown-fixture "fixture_id not found: F99-not-a-real-fixture" \
  python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
    --run-id unknown-fixture --min-runs 1

write_run recall-only F11-batch-import-all-or-nothing PASS PASS_WITH_ISSUES false
mkdir -p "$FIXTURES_DIR/F11-batch-import-all-or-nothing"
expect_fail_contains recall-only "pair verdict PASS_WITH_ISSUES is not verdict-binding" \
  python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
    --run-id recall-only --min-runs 1

write_run internal-lift F14-internal-pair-lift NEEDS_WORK NEEDS_WORK false true PASS_WITH_ISSUES NEEDS_WORK
mkdir -p "$FIXTURES_DIR/F14-internal-pair-lift"
python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
  --run-id internal-lift --min-runs 1 \
  > "$TMP_DIR/internal-lift.out"
grep -Fq '"verdict": "PASS"' "$TMP_DIR/internal-lift.out"

write_run slow-pair F15-slow-pair PASS_WITH_ISSUES NEEDS_WORK true
mkdir -p "$FIXTURES_DIR/F15-slow-pair"
python3 - "$TMP_DIR/slow-pair/compare.json" <<'PY'
import json
import sys
path = sys.argv[1]
with open(path) as f:
    data = json.load(f)
data["pair"]["elapsed_seconds"] = 401
with open(path, "w") as f:
    json.dump(data, f)
PY
expect_fail_contains slow-pair "pair/solo wall ratio 4.01 exceeds 3.00" \
  python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
    --run-id slow-pair --min-runs 1 --max-pair-solo-wall-ratio 3

mkdir -p "$TMP_DIR/missing-elapsed/pair"
cat > "$TMP_DIR/missing-elapsed/pair/input.md" <<'EOF'
Use /devlyn:resolve --verify-only --spec docs/roadmap/phase-1/F16-missing-elapsed.md.
EOF
cat > "$TMP_DIR/missing-elapsed/compare.json" <<'EOF'
{
  "solo": {"invoke_exit": 0, "timed_out": false, "verify_verdict": "PASS_WITH_ISSUES"},
  "pair": {"invoke_exit": 0, "timed_out": false, "verify_verdict": "NEEDS_WORK", "pair_mode": true},
  "comparison": {
    "pair_trigger_missed": false,
    "pair_verdict_lift": true,
    "pair_internal_verdict_lift": false,
    "solo_verdict": "PASS_WITH_ISSUES",
    "pair_verdict": "NEEDS_WORK",
    "pair_primary_verdict": "NEEDS_WORK",
    "pair_judge_verdict": "NEEDS_WORK"
  }
}
EOF
mkdir -p "$FIXTURES_DIR/F16-missing-elapsed"
expect_fail_contains missing-elapsed "pair/solo wall ratio missing" \
  python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
    --run-id missing-elapsed --min-runs 1 --max-pair-solo-wall-ratio 3

mkdir -p "$TMP_DIR/missing-compare/pair"
cat > "$TMP_DIR/missing-compare/pair/input.md" <<'EOF'
Use /devlyn:resolve --verify-only --spec docs/roadmap/phase-1/F17-missing-compare.md.
EOF
mkdir -p "$FIXTURES_DIR/F17-missing-compare"
expect_fail_contains missing-compare "missing compare.json for missing-compare" \
  python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
    --run-id missing-compare --min-runs 1

mkdir -p "$TMP_DIR/provider-limit/pair"
cat > "$TMP_DIR/provider-limit/pair/input.md" <<'EOF'
Use /devlyn:resolve --verify-only --spec docs/roadmap/phase-1/F18-provider-limit.md.
EOF
cat > "$TMP_DIR/provider-limit/pair/transcript.txt" <<'EOF'
You've hit your limit · resets 3am (Asia/Seoul)
EOF
cat > "$TMP_DIR/provider-limit/compare.json" <<'EOF'
{
  "solo": {"invoke_exit": 0, "timed_out": false, "verify_verdict": "PASS", "elapsed_seconds": 100},
  "pair": {"invoke_exit": 1, "timed_out": false, "verify_verdict": null, "pair_mode": false, "elapsed_seconds": 1},
  "comparison": {
    "pair_trigger_missed": false,
    "pair_verdict_lift": false,
    "pair_internal_verdict_lift": false,
    "solo_verdict": "PASS",
    "pair_verdict": null
  }
}
EOF
mkdir -p "$FIXTURES_DIR/F18-provider-limit"
expect_fail_contains provider-limit "pair provider limit" \
  python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
    --run-id provider-limit --min-runs 1

echo "✓ test-frozen-verify-gate"
