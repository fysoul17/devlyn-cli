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
  "pair": {
    "invoke_exit": 0,
    "timed_out": false,
    "verify_verdict": "$pair_verdict",
    "pair_mode": true,
    "pair_trigger": {"eligible": true, "reasons": ["mode.verify-only"], "skipped_reason": null},
    "elapsed_seconds": 200
  },
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
  --out-md "$TMP_DIR/pass.md" \
  > "$TMP_DIR/pass.out"
grep -Fq '"verdict": "PASS"' "$TMP_DIR/pass.out"
grep -Fq '"avg_pair_solo_wall_ratio": 2.0' "$TMP_DIR/pass.out"
grep -Fq '"pair_solo_wall_ratio": 2.0' "$TMP_DIR/pass.out"
grep -Fq '"pair_trigger_reasons": [' "$TMP_DIR/pass.out"
grep -Fq '"mode.verify-only"' "$TMP_DIR/pass.out"
grep -Fq '"pair_trigger_has_canonical_reason": true' "$TMP_DIR/pass.out"
grep -Fq '| Run | Fixture | Solo VERIFY | Pair VERIFY | Pair mode | Triggers | Wall ratio | External lift | Internal lift | Status | Reason |' "$TMP_DIR/pass.md"
grep -Fq '| pass-a | F10-persist-write-collision | PASS_WITH_ISSUES | NEEDS_WORK | true | mode.verify-only | 2.00x | true | false | PASS | ok |' "$TMP_DIR/pass.md"

expect_fail_contains invalid-min-runs "value must be > 0" \
  python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
    --run-id pass-a --min-runs 0

expect_fail_contains invalid-wall-ratio "value must be > 0" \
  python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
    --run-id pass-a --max-pair-solo-wall-ratio 0

mkdir -p "$TMP_DIR/summary-verdicts/pair"
cat > "$TMP_DIR/summary-verdicts/pair/input.md" <<'EOF'
Use /devlyn:resolve --verify-only --spec docs/roadmap/phase-1/F13-summary-verdict-fallback.md.
EOF
cat > "$TMP_DIR/summary-verdicts/compare.json" <<'EOF'
{
  "solo": {"invoke_exit": 0, "timed_out": false, "verify_verdict": "PASS_WITH_ISSUES", "elapsed_seconds": 100},
  "pair": {
    "invoke_exit": 0,
    "timed_out": false,
    "verify_verdict": "NEEDS_WORK",
    "pair_mode": true,
    "pair_trigger": {"eligible": true, "reasons": ["mode.verify-only"], "skipped_reason": null},
    "elapsed_seconds": 200
  },
  "comparison": {"pair_trigger_missed": false, "pair_verdict_lift": true, "pair_internal_verdict_lift": false}
}
EOF
mkdir -p "$FIXTURES_DIR/F13-summary-verdict-fallback"
python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
  --run-id summary-verdicts --min-runs 1 \
  > "$TMP_DIR/summary-verdicts.out"
grep -Fq '"verdict": "PASS"' "$TMP_DIR/summary-verdicts.out"

mkdir -p "$TMP_DIR/string-pair-mode/pair"
cat > "$TMP_DIR/string-pair-mode/pair/input.md" <<'EOF'
Use /devlyn:resolve --verify-only --spec docs/roadmap/phase-1/F13-string-pair-mode.md.
EOF
cat > "$TMP_DIR/string-pair-mode/compare.json" <<'EOF'
{
  "solo": {"invoke_exit": 0, "timed_out": false, "verify_verdict": "PASS_WITH_ISSUES", "elapsed_seconds": 100},
  "pair": {
    "invoke_exit": 0,
    "timed_out": false,
    "verify_verdict": "NEEDS_WORK",
    "pair_mode": "true",
    "pair_trigger": {"eligible": true, "reasons": ["mode.verify-only"], "skipped_reason": null},
    "elapsed_seconds": 200
  },
  "comparison": {"pair_trigger_missed": false, "pair_verdict_lift": true, "pair_internal_verdict_lift": false}
}
EOF
mkdir -p "$FIXTURES_DIR/F13-string-pair-mode"
expect_fail_contains string-pair-mode "pair_mode false" \
  python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
    --run-id string-pair-mode --min-runs 1

write_run malformed-pair-trigger F13-malformed-pair-trigger PASS_WITH_ISSUES NEEDS_WORK true
mkdir -p "$FIXTURES_DIR/F13-malformed-pair-trigger"
python3 - "$TMP_DIR/malformed-pair-trigger/compare.json" <<'PY'
import json
import sys
path = sys.argv[1]
with open(path) as f:
    data = json.load(f)
data["pair"]["pair_trigger"] = {"eligible": True, "reasons": "forced_pair", "skipped_reason": None}
with open(path, "w") as f:
    json.dump(data, f)
PY
expect_fail_contains malformed-pair-trigger "pair_trigger.reasons malformed" \
  python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
    --run-id malformed-pair-trigger --min-runs 1

write_run unknown-pair-trigger F13-unknown-pair-trigger PASS_WITH_ISSUES NEEDS_WORK true
mkdir -p "$FIXTURES_DIR/F13-unknown-pair-trigger"
python3 - "$TMP_DIR/unknown-pair-trigger/compare.json" <<'PY'
import json
import sys
path = sys.argv[1]
with open(path) as f:
    data = json.load(f)
data["pair"]["pair_trigger"] = {"eligible": True, "reasons": ["looks-hard"], "skipped_reason": None}
with open(path, "w") as f:
    json.dump(data, f)
PY
expect_fail_contains unknown-pair-trigger "pair_trigger reasons missing known trigger reason" \
  python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
    --run-id unknown-pair-trigger --min-runs 1

write_run mixed-unknown-pair-trigger F13-mixed-unknown-pair-trigger PASS_WITH_ISSUES NEEDS_WORK true
mkdir -p "$FIXTURES_DIR/F13-mixed-unknown-pair-trigger"
python3 - "$TMP_DIR/mixed-unknown-pair-trigger/compare.json" <<'PY'
import json
import sys
path = sys.argv[1]
with open(path) as f:
    data = json.load(f)
data["pair"]["pair_trigger"] = {"eligible": True, "reasons": ["mode.verify-only", "looks-hard"], "skipped_reason": None}
with open(path, "w") as f:
    json.dump(data, f)
PY
expect_fail_contains mixed-unknown-pair-trigger "pair_trigger reasons contain unknown trigger reason" \
  python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
    --run-id mixed-unknown-pair-trigger --min-runs 1

write_run normalized-canonical-pair-trigger F13-normalized-canonical-pair-trigger PASS_WITH_ISSUES NEEDS_WORK true
mkdir -p "$FIXTURES_DIR/F13-normalized-canonical-pair-trigger"
python3 - "$TMP_DIR/normalized-canonical-pair-trigger/compare.json" <<'PY'
import json
import sys
path = sys.argv[1]
with open(path) as f:
    data = json.load(f)
data["pair"]["pair_trigger"] = {"eligible": True, "reasons": ["risk high"], "skipped_reason": None}
with open(path, "w") as f:
    json.dump(data, f)
PY
expect_fail_contains normalized-canonical-pair-trigger "pair_trigger reasons missing known trigger reason" \
  python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
    --run-id normalized-canonical-pair-trigger --min-runs 1

write_run historical-only-pair-trigger F13-historical-only-pair-trigger PASS_WITH_ISSUES NEEDS_WORK true
mkdir -p "$FIXTURES_DIR/F13-historical-only-pair-trigger"
python3 - "$TMP_DIR/historical-only-pair-trigger/compare.json" <<'PY'
import json
import sys
path = sys.argv[1]
with open(path) as f:
    data = json.load(f)
data["pair"]["pair_trigger"] = {"eligible": True, "reasons": ["risk_profile.high_risk"], "skipped_reason": None}
with open(path, "w") as f:
    json.dump(data, f)
PY
expect_fail_contains historical-only-pair-trigger "pair_trigger reasons missing canonical trigger reason" \
  python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
    --run-id historical-only-pair-trigger --min-runs 1

write_run missing-hypothesis-trigger F13-missing-hypothesis-trigger PASS_WITH_ISSUES NEEDS_WORK true
mkdir -p "$FIXTURES_DIR/F13-missing-hypothesis-trigger"
cat > "$FIXTURES_DIR/F13-missing-hypothesis-trigger/spec.md" <<'EOF'
## Verification

- Solo-headroom hypothesis: `solo_claude` is expected to miss the refund-window defect; observable miss command: `npm test -- --runInBand`.
EOF
expect_fail_contains missing-hypothesis-trigger "pair_trigger missing spec.solo_headroom_hypothesis" \
  python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
    --run-id missing-hypothesis-trigger --min-runs 1 --require-hypothesis-trigger
python3 - "$TMP_DIR/missing-hypothesis-trigger/compare.json" <<'PY'
import json
import sys
path = sys.argv[1]
with open(path) as f:
    data = json.load(f)
data["pair"]["pair_trigger"]["reasons"] = [
    "mode.verify-only",
    "spec.solo_headroom_hypothesis",
]
with open(path, "w") as f:
    json.dump(data, f)
PY
python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
  --run-id missing-hypothesis-trigger --min-runs 1 --require-hypothesis-trigger \
  > "$TMP_DIR/hypothesis-trigger-pass.out"
grep -Fq '"verdict": "PASS"' "$TMP_DIR/hypothesis-trigger-pass.out"

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
  "pair": {
    "invoke_exit": 0,
    "timed_out": false,
    "verify_verdict": "NEEDS_WORK",
    "pair_mode": true,
    "pair_trigger": {"eligible": true, "reasons": ["mode.verify-only"], "skipped_reason": null}
  },
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

mkdir -p "$TMP_DIR/malformed-compare/pair"
cat > "$TMP_DIR/malformed-compare/pair/input.md" <<'EOF'
Use /devlyn:resolve --verify-only --spec docs/roadmap/phase-1/F17-malformed-compare.md.
EOF
printf '["not", "a", "dict"]\n' > "$TMP_DIR/malformed-compare/compare.json"
mkdir -p "$FIXTURES_DIR/F17-malformed-compare"
expect_fail_contains malformed-compare "malformed compare.json for malformed-compare: expected object" \
  python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
    --run-id malformed-compare --min-runs 1

mkdir -p "$TMP_DIR/nan-compare/pair"
cat > "$TMP_DIR/nan-compare/pair/input.md" <<'EOF'
Use /devlyn:resolve --verify-only --spec docs/roadmap/phase-1/F17-nan-compare.md.
EOF
cat > "$TMP_DIR/nan-compare/compare.json" <<'EOF'
{
  "solo": {"invoke_exit": 0, "timed_out": false, "verify_verdict": "PASS_WITH_ISSUES", "elapsed_seconds": 100},
  "pair": {
    "invoke_exit": 0,
    "timed_out": false,
    "verify_verdict": "NEEDS_WORK",
    "pair_mode": true,
    "pair_trigger": {"eligible": true, "reasons": ["mode.verify-only"], "skipped_reason": null},
    "elapsed_seconds": NaN
  },
  "comparison": {"pair_trigger_missed": false, "pair_verdict_lift": true, "pair_internal_verdict_lift": false}
}
EOF
mkdir -p "$FIXTURES_DIR/F17-nan-compare"
expect_fail_contains nan-compare "malformed compare.json for nan-compare: invalid JSON" \
  python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
    --run-id nan-compare --min-runs 1

mkdir -p "$TMP_DIR/malformed-compare-sections/pair"
cat > "$TMP_DIR/malformed-compare-sections/pair/input.md" <<'EOF'
Use /devlyn:resolve --verify-only --spec docs/roadmap/phase-1/F17-malformed-compare-sections.md.
EOF
cat > "$TMP_DIR/malformed-compare-sections/compare.json" <<'EOF'
{
  "solo": ["not", "a", "dict"],
  "pair": ["not", "a", "dict"],
  "comparison": ["not", "a", "dict"]
}
EOF
mkdir -p "$FIXTURES_DIR/F17-malformed-compare-sections"
expect_fail_contains malformed-compare-sections "pair_mode false" \
  python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
    --run-id malformed-compare-sections --min-runs 1

mkdir -p "$TMP_DIR/malformed-verdict-fields/pair"
cat > "$TMP_DIR/malformed-verdict-fields/pair/input.md" <<'EOF'
Use /devlyn:resolve --verify-only --spec docs/roadmap/phase-1/F17-malformed-verdict-fields.md.
EOF
cat > "$TMP_DIR/malformed-verdict-fields/compare.json" <<'EOF'
{
  "solo": {"invoke_exit": 0, "timed_out": false, "verify_verdict": ["bad"], "elapsed_seconds": 100},
  "pair": {
    "invoke_exit": 0,
    "timed_out": false,
    "verify_verdict": ["bad"],
    "pair_mode": true,
    "pair_trigger": {"eligible": true, "reasons": ["mode.verify-only"], "skipped_reason": null},
    "elapsed_seconds": 200
  },
  "comparison": {
    "pair_trigger_missed": false,
    "pair_verdict_lift": true,
    "pair_internal_verdict_lift": true,
    "solo_verdict": ["bad"],
    "pair_verdict": ["bad"],
    "pair_primary_verdict": ["bad"],
    "pair_judge_verdict": ["bad"]
  }
}
EOF
mkdir -p "$FIXTURES_DIR/F17-malformed-verdict-fields"
expect_fail_contains malformed-verdict-fields "pair verdict missing or malformed" \
  python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
    --run-id malformed-verdict-fields --min-runs 1

mkdir -p "$TMP_DIR/malformed-elapsed-fields/pair"
cat > "$TMP_DIR/malformed-elapsed-fields/pair/input.md" <<'EOF'
Use /devlyn:resolve --verify-only --spec docs/roadmap/phase-1/F17-malformed-elapsed-fields.md.
EOF
cat > "$TMP_DIR/malformed-elapsed-fields/compare.json" <<'EOF'
{
  "solo": {"invoke_exit": 0, "timed_out": false, "verify_verdict": "PASS_WITH_ISSUES", "elapsed_seconds": true},
  "pair": {
    "invoke_exit": 0,
    "timed_out": false,
    "verify_verdict": "NEEDS_WORK",
    "pair_mode": true,
    "pair_trigger": {"eligible": true, "reasons": ["mode.verify-only"], "skipped_reason": null},
    "elapsed_seconds": false
  },
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
mkdir -p "$FIXTURES_DIR/F17-malformed-elapsed-fields"
expect_fail_contains malformed-elapsed-fields "pair/solo wall ratio missing" \
  python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
    --run-id malformed-elapsed-fields --min-runs 1 --max-pair-solo-wall-ratio 3

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

write_run dirty-pair-env F19-dirty-pair-env PASS_WITH_ISSUES NEEDS_WORK true
mkdir -p "$FIXTURES_DIR/F19-dirty-pair-env"
python3 - "$TMP_DIR/dirty-pair-env/compare.json" <<'PY'
import json
import sys
path = sys.argv[1]
with open(path) as f:
    data = json.load(f)
data["pair"]["environment_contamination"] = True
with open(path, "w") as f:
    json.dump(data, f)
PY
expect_fail_contains dirty-pair-env "pair environment contamination" \
  python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
    --run-id dirty-pair-env --min-runs 1

write_run dirty-solo-disqualifier F20-dirty-solo-disqualifier PASS_WITH_ISSUES NEEDS_WORK true
mkdir -p "$FIXTURES_DIR/F20-dirty-solo-disqualifier"
python3 - "$TMP_DIR/dirty-solo-disqualifier/compare.json" <<'PY'
import json
import sys
path = sys.argv[1]
with open(path) as f:
    data = json.load(f)
data["solo"]["disqualifier"] = True
with open(path, "w") as f:
    json.dump(data, f)
PY
expect_fail_contains dirty-solo-disqualifier "solo disqualifier" \
  python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
    --run-id dirty-solo-disqualifier --min-runs 1

write_run dirty-pair-invoke F21-dirty-pair-invoke PASS_WITH_ISSUES NEEDS_WORK true
mkdir -p "$FIXTURES_DIR/F21-dirty-pair-invoke"
python3 - "$TMP_DIR/dirty-pair-invoke/compare.json" <<'PY'
import json
import sys
path = sys.argv[1]
with open(path) as f:
    data = json.load(f)
data["pair"]["invoke_failure"] = True
data["pair"]["invoke_failure_reason"] = "plugin_contamination"
with open(path, "w") as f:
    json.dump(data, f)
PY
expect_fail_contains dirty-pair-invoke "pair invoke failure (plugin_contamination)" \
  python3 "$GATE" --results-root "$TMP_DIR" --fixtures-root "$FIXTURES_DIR" \
    --run-id dirty-pair-invoke --min-runs 1

echo "✓ test-frozen-verify-gate"
