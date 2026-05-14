#!/usr/bin/env bash
# Regression tests for run-full-pipeline-pair-candidate.sh argument guards.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RUNNER="$SCRIPT_DIR/run-full-pipeline-pair-candidate.sh"
REJECTED="$SCRIPT_DIR/pair-rejected-fixtures.sh"
BENCH_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TMP_DIR="$(mktemp -d /tmp/run-full-pipeline-pair-candidate-test.XXXXXX)"
TEST_RUN="arg-test-$(basename "$TMP_DIR")"
TEST_SHADOW="$BENCH_ROOT/shadow-fixtures/S97-runner-hypothesis"
trap 'rm -rf "$TMP_DIR" "$BENCH_ROOT/results/$TEST_RUN"* "$BENCH_ROOT/results/src-$TEST_RUN" "$TEST_SHADOW"' EXIT

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

bash "$RUNNER" --help > "$TMP_DIR/help.out" 2>&1
grep -Fq 'default: l2_risk_probes' "$TMP_DIR/help.out"
grep -Fq -- '--min-bare-headroom N' "$TMP_DIR/help.out"
grep -Fq -- '--min-solo-headroom N' "$TMP_DIR/help.out"
grep -Fq -- '--max-pair-solo-wall-ratio N  (default: 3)' "$TMP_DIR/help.out"
grep -Fq -- '--allow-rejected-fixtures' "$TMP_DIR/help.out"
grep -Fq -- '--dry-run' "$TMP_DIR/help.out"
grep -Fq 'run_gate_with_report' "$RUNNER"
grep -Fq 'Command: ' "$RUNNER"
grep -Fq 'DEVLYN_BENCHMARK_CLI_SUBCOMMAND' "$RUNNER"
grep -Fq 'cmd=(npx devlyn-cli benchmark pair --run-id "$RUN_ID")' "$RUNNER"
grep -Fq 'cmd=(bash "$0" --run-id "$RUN_ID")' "$RUNNER"
grep -Fq 'cmd+=(--min-bare-headroom "$MIN_BARE_HEADROOM")' "$RUNNER"
grep -Fq 'cmd+=(--min-solo-headroom "$MIN_SOLO_HEADROOM")' "$RUNNER"
grep -Fq 'cmd+=(--allow-rejected-fixtures)' "$RUNNER"
grep -Fq 'cmd+=(--dry-run)' "$RUNNER"
grep -Fq 'baseline evidence-complete' "$RUNNER"
grep -Fq '$PAIR_ARM evidence-clean' "$RUNNER"
grep -Fq 'MAX_PAIR_SOLO_WALL_RATIO=3' "$RUNNER"
grep -Fq 'headroom-gate.md' "$RUNNER"
grep -Fq 'full-pipeline-pair-gate.md' "$RUNNER"
grep -Fq 'cat "$report"' "$RUNNER"
grep -Fq 'headroom gate failed — pair arm not executed' "$RUNNER"
grep -Fq 'headroom gate passed — executing $PAIR_ARM' "$RUNNER"
grep -Fq 'pair gate failed — pair evidence rejected' "$RUNNER"
grep -Fq 'pair gate passed — pair evidence accepted' "$RUNNER"
grep -Fq 'if ! run_gate_with_report \' "$RUNNER"
grep -Fq 'mirror_skills()' "$RUNNER"
grep -Fq 'validate_fixtures' "$RUNNER"
grep -Fq 'fixture_has_solo_ceiling_avoidance_note' "$RUNNER"
grep -Fq 'shadow fixture NOTES.md needs ## Solo ceiling avoidance' "$RUNNER"
grep -Fq 'fixture not found in fixtures/ or shadow-fixtures/' "$RUNNER"
grep -Fq '[FS][0-9]*) FIXTURES+=("$1")' "$RUNNER"
grep -Fq 'retired_fixture_exists' "$RUNNER"
grep -Fq 'fixture is retired and is not rerun by pair-candidate runners' "$RUNNER"
grep -Fq 'fixture_smoke_only' "$RUNNER"
grep -Fq 'fixture is smoke-only and cannot run providers' "$RUNNER"
grep -Fq 'rejected_pair_fixture_reason' "$RUNNER"
grep -Fq 'source "$BENCH_ROOT/scripts/pair-rejected-fixtures.sh"' "$RUNNER"
grep -Fq 'declare -F rejected_pair_fixture_reason' "$RUNNER"
grep -Fq '20260511-f3-http-error-headroom' "$REJECTED"
grep -Fq '20260507-f10-f11-tier1-full-pipeline' "$REJECTED"
grep -Fq '20260511-f12-webhook-headroom' "$REJECTED"
grep -Fq '20260511-f15-concurrency-headroom' "$REJECTED"
grep -Fq '20260511-f28-policy-oraclefix-reverified-pair' "$REJECTED"
grep -Fq '20260511-f30-headroom-v1' "$REJECTED"
grep -Fq '20260513-s2-inventory-headroom' "$REJECTED"
grep -Fq '20260513-s3-ticket-headroom' "$REJECTED"
grep -Fq '20260513-s4-return-headroom' "$REJECTED"
grep -Fq '20260513-s5-credit-headroom' "$REJECTED"
grep -Fq 'Use --allow-rejected-fixtures for diagnostics only' "$RUNNER"
grep -Fq 'if [ -z "$REUSE_CALIBRATED_FROM" ]; then' "$RUNNER"
grep -Fq 'if [ -n "$REUSE_CALIBRATED_FROM" ]; then' "$RUNNER"

expect_fail_contains invalid-pair-arm \
  "pair-arm must be l2_risk_probes or l2_gated" \
  bash "$RUNNER" --run-id arg-test --pair-arm variant F21-cli-scheduler-priority

expect_fail_contains retired-pair-arm \
  "pair-arm l2_forced is retired" \
  bash "$RUNNER" --run-id arg-test --pair-arm l2_forced F21-cli-scheduler-priority

expect_fail_contains missing-bare-max-value \
  "--bare-max requires a value" \
  bash "$RUNNER" --bare-max

expect_fail_contains invalid-bare-max \
  "--bare-max must be an integer: nope" \
  bash "$RUNNER" --bare-max nope F21-cli-scheduler-priority

expect_fail_contains invalid-min-fixtures \
  "--min-fixtures must be >= 1" \
  bash "$RUNNER" --min-fixtures 0 F21-cli-scheduler-priority

expect_fail_contains invalid-min-solo-headroom \
  "--min-solo-headroom must be an integer: nope" \
  bash "$RUNNER" --min-solo-headroom nope F21-cli-scheduler-priority

expect_fail_contains negative-min-bare-headroom \
  "--min-bare-headroom must be an integer: -1" \
  bash "$RUNNER" --min-bare-headroom -1 F21-cli-scheduler-priority

expect_fail_contains negative-min-solo-headroom \
  "--min-solo-headroom must be an integer: -1" \
  bash "$RUNNER" --min-solo-headroom -1 F21-cli-scheduler-priority

expect_fail_contains invalid-wall-ratio \
  "--max-pair-solo-wall-ratio must be a positive number: nope" \
  bash "$RUNNER" --max-pair-solo-wall-ratio nope F21-cli-scheduler-priority

expect_fail_contains zero-wall-ratio \
  "--max-pair-solo-wall-ratio must be > 0" \
  bash "$RUNNER" --max-pair-solo-wall-ratio 0 F21-cli-scheduler-priority

expect_fail_contains missing-fixture-fast \
  "fixture not found in fixtures/ or shadow-fixtures/: F999-not-a-fixture" \
  bash "$RUNNER" --run-id "$TEST_RUN-missing-fixture" F999-not-a-fixture

expect_fail_contains rejected-f1-fixture \
  "fixture rejected for pair-candidate runs: F1-cli-trivial-flag" \
  bash "$RUNNER" --run-id "$TEST_RUN-rejected-f1" --dry-run --min-fixtures 1 F1-cli-trivial-flag

expect_fail_contains rejected-f2-fixture \
  "fixture rejected for pair-candidate runs: F2-cli-medium-subcommand" \
  bash "$RUNNER" --run-id "$TEST_RUN-rejected-f2" --dry-run --min-fixtures 1 F2-cli-medium-subcommand

expect_fail_contains rejected-fixture \
  "fixture rejected for pair-candidate runs: F26-cli-payout-ledger-rules" \
  bash "$RUNNER" --run-id "$TEST_RUN-rejected" --dry-run --min-fixtures 1 F26-cli-payout-ledger-rules

expect_fail_contains rejected-f3-fixture \
  "fixture rejected for pair-candidate runs: F3-backend-contract-risk" \
  bash "$RUNNER" --run-id "$TEST_RUN-rejected-f3" --dry-run --min-fixtures 1 F3-backend-contract-risk

expect_fail_contains rejected-f4-fixture \
  "fixture rejected for pair-candidate runs: F4-web-browser-design" \
  bash "$RUNNER" --run-id "$TEST_RUN-rejected-f4" --dry-run --min-fixtures 1 F4-web-browser-design

expect_fail_contains rejected-f5-fixture \
  "fixture rejected for pair-candidate runs: F5-fix-loop-red-green" \
  bash "$RUNNER" --run-id "$TEST_RUN-rejected-f5" --dry-run --min-fixtures 1 F5-fix-loop-red-green

expect_fail_contains rejected-f6-fixture \
  "fixture rejected for pair-candidate runs: F6-dep-audit-native-module" \
  bash "$RUNNER" --run-id "$TEST_RUN-rejected-f6" --dry-run --min-fixtures 1 F6-dep-audit-native-module

expect_fail_contains rejected-f7-fixture \
  "fixture rejected for pair-candidate runs: F7-out-of-scope-trap" \
  bash "$RUNNER" --run-id "$TEST_RUN-rejected-f7" --dry-run --min-fixtures 1 F7-out-of-scope-trap

expect_fail_contains rejected-f8-fixture \
  "fixture rejected for pair-candidate runs: F8-known-limit-ambiguous" \
  bash "$RUNNER" --run-id "$TEST_RUN-rejected-f8" --dry-run --min-fixtures 1 F8-known-limit-ambiguous

expect_fail_contains rejected-f9-fixture \
  "fixture rejected for pair-candidate runs: F9-e2e-ideate-to-resolve" \
  bash "$RUNNER" --run-id "$TEST_RUN-rejected-f9" --dry-run --min-fixtures 1 F9-e2e-ideate-to-resolve

expect_fail_contains rejected-f10-fixture \
  "fixture rejected for pair-candidate runs: F10-persist-write-collision" \
  bash "$RUNNER" --run-id "$TEST_RUN-rejected-f10" --dry-run --min-fixtures 1 F10-persist-write-collision

expect_fail_contains rejected-f11-fixture \
  "fixture rejected for pair-candidate runs: F11-batch-import-all-or-nothing" \
  bash "$RUNNER" --run-id "$TEST_RUN-rejected-f11" --dry-run --min-fixtures 1 F11-batch-import-all-or-nothing

expect_fail_contains rejected-f12-fixture \
  "fixture rejected for pair-candidate runs: F12-webhook-raw-body-signature" \
  bash "$RUNNER" --run-id "$TEST_RUN-rejected-f12" --dry-run --min-fixtures 1 F12-webhook-raw-body-signature

expect_fail_contains rejected-f15-fixture \
  "fixture rejected for pair-candidate runs: F15-frozen-diff-race-review" \
  bash "$RUNNER" --run-id "$TEST_RUN-rejected-f15" --dry-run --min-fixtures 1 F15-frozen-diff-race-review

expect_fail_contains rejected-f31-fixture \
  "fixture rejected for pair-candidate runs: F31-cli-seat-rebalance" \
  bash "$RUNNER" --run-id "$TEST_RUN-rejected-f31" --dry-run --min-fixtures 1 F31-cli-seat-rebalance

expect_fail_contains rejected-f32-fixture \
  "fixture rejected for pair-candidate runs: F32-cli-subscription-renewal" \
  bash "$RUNNER" --run-id "$TEST_RUN-rejected-f32" --dry-run --min-fixtures 1 F32-cli-subscription-renewal

expect_fail_contains rejected-s2-shadow-fixture \
  "fixture rejected for pair-candidate runs: S2-cli-inventory-reservation" \
  bash "$RUNNER" --run-id "$TEST_RUN-rejected-s2" --dry-run --min-fixtures 1 S2-cli-inventory-reservation

expect_fail_contains rejected-s3-shadow-fixture \
  "fixture rejected for pair-candidate runs: S3-cli-ticket-assignment" \
  bash "$RUNNER" --run-id "$TEST_RUN-rejected-s3" --dry-run --min-fixtures 1 S3-cli-ticket-assignment

expect_fail_contains rejected-s4-shadow-fixture \
  "fixture rejected for pair-candidate runs: S4-cli-return-routing" \
  bash "$RUNNER" --run-id "$TEST_RUN-rejected-s4" --dry-run --min-fixtures 1 S4-cli-return-routing

expect_fail_contains rejected-s5-shadow-fixture \
  "fixture rejected for pair-candidate runs: S5-cli-credit-grant-ledger" \
  bash "$RUNNER" --run-id "$TEST_RUN-rejected-s5" --dry-run --min-fixtures 1 S5-cli-credit-grant-ledger

expect_fail_contains rejected-s6-shadow-fixture \
  "fixture rejected for pair-candidate runs: S6-cli-refund-window-ledger" \
  bash "$RUNNER" --run-id "$TEST_RUN-rejected-s6" --dry-run --min-fixtures 1 S6-cli-refund-window-ledger

expect_fail_contains retired-fixture \
  "fixture is retired and is not rerun by pair-candidate runners: F28-cli-return-authorization" \
  bash "$RUNNER" --run-id "$TEST_RUN-retired" --dry-run --min-fixtures 1 F28-cli-return-authorization

expect_fail_contains smoke-only-s1-provider-run \
  "fixture is smoke-only and cannot run providers: S1-cli-lang-flag" \
  bash "$RUNNER" --run-id "$TEST_RUN-smoke-only" --min-fixtures 1 S1-cli-lang-flag

expect_fail_contains reuse-source-missing \
  "reuse source missing" \
  bash "$RUNNER" --run-id "$TEST_RUN-source-missing" \
    --reuse-calibrated-from "src-$TEST_RUN-missing" \
    F21-cli-scheduler-priority

expect_fail_contains cli-replay-command \
  "Command: npx devlyn-cli benchmark pair --run-id $TEST_RUN-cli-replay" \
  env DEVLYN_BENCHMARK_CLI_SUBCOMMAND=pair \
    bash "$RUNNER" --run-id "$TEST_RUN-cli-replay" \
      --reuse-calibrated-from "src-$TEST_RUN-missing" \
      F21-cli-scheduler-priority

expect_fail_contains dry-run-min-fixtures \
  '[full-pipeline-pair] DRY RUN failed' \
  bash "$RUNNER" --run-id "$TEST_RUN-dry-run-fail" --dry-run F21-cli-scheduler-priority

bash "$RUNNER" --run-id "$TEST_RUN-dry-run" --dry-run --min-fixtures 1 F21-cli-scheduler-priority \
  > "$TMP_DIR/dry-run.out" 2>&1
grep -Fq 'Mode:     DRY RUN (no model/provider invocations)' "$TMP_DIR/dry-run.out"
grep -Fq 'Command: ' "$TMP_DIR/dry-run.out"
grep -Fq -- '--dry-run' "$TMP_DIR/dry-run.out"
grep -Fq -- '--min-bare-headroom 5' "$TMP_DIR/dry-run.out"
grep -Fq -- '--min-solo-headroom 5' "$TMP_DIR/dry-run.out"
grep -Fq -- '--min-fixtures 1' "$TMP_DIR/dry-run.out"
grep -Fq -- '--max-pair-solo-wall-ratio 3' "$TMP_DIR/dry-run.out"
grep -Fq 'Pair:     l2_risk_probes evidence-clean, canonical trigger, margin >= +5, wall ratio <= 3' "$TMP_DIR/dry-run.out"
grep -Fq '[full-pipeline-pair] DRY RUN complete' "$TMP_DIR/dry-run.out"

bash "$RUNNER" --run-id "$TEST_RUN-shadow-dry-run" --dry-run --min-fixtures 1 S1-cli-lang-flag \
  > "$TMP_DIR/shadow-dry-run.out" 2>&1
grep -Fq 'Fixtures: S1-cli-lang-flag' "$TMP_DIR/shadow-dry-run.out"
grep -Fq '[full-pipeline-pair] DRY RUN complete' "$TMP_DIR/shadow-dry-run.out"

mkdir -p "$TEST_SHADOW"
cat > "$TEST_SHADOW/metadata.json" <<'EOF'
{
  "id": "S97-runner-hypothesis",
  "category": "high-risk"
}
EOF
cat > "$TEST_SHADOW/spec.md" <<'EOF'
# Runner hypothesis fixture

Add idempotency handling for duplicate requests.
EOF
cat > "$TEST_SHADOW/expected.json" <<'EOF'
{
  "verification_commands": [
    {
      "cmd": "node -e \"process.exit(0)\"",
      "exit_code": 0
    }
  ]
}
EOF
cat > "$TEST_SHADOW/NOTES.md" <<'EOF'
# Notes

Synthetic runner guard fixture.
EOF
expect_fail_contains missing-solo-headroom-hypothesis \
  'fixture spec.md needs a solo-headroom hypothesis with solo_claude miss and observable command from expected.json before provider spend: S97-runner-hypothesis' \
  bash "$RUNNER" --run-id "$TEST_RUN-missing-hypothesis" --dry-run --min-fixtures 1 S97-runner-hypothesis
cat >> "$TEST_SHADOW/spec.md" <<'EOF'

## Solo-headroom hypothesis

A capable solo_claude baseline is expected to miss duplicate idempotency ordering.
EOF
expect_fail_contains weak-solo-headroom-hypothesis \
  'fixture spec.md needs a solo-headroom hypothesis with solo_claude miss and observable command from expected.json before provider spend: S97-runner-hypothesis' \
  bash "$RUNNER" --run-id "$TEST_RUN-weak-hypothesis" --dry-run --min-fixtures 1 S97-runner-hypothesis
cat >> "$TEST_SHADOW/spec.md" <<'EOF'

Implementation marker: `duplicate-idempotency`.
EOF
expect_fail_contains unrelated-backtick-solo-headroom-hypothesis \
  'fixture spec.md needs a solo-headroom hypothesis with solo_claude miss and observable command from expected.json before provider spend: S97-runner-hypothesis' \
  bash "$RUNNER" --run-id "$TEST_RUN-unrelated-backtick-hypothesis" --dry-run --min-fixtures 1 S97-runner-hypothesis
cat >> "$TEST_SHADOW/spec.md" <<'EOF'

Observable command: `node -e "process.exit(0)"` exposes behavior.
EOF
expect_fail_contains observable-without-miss-solo-headroom-hypothesis \
  'fixture spec.md needs a solo-headroom hypothesis with solo_claude miss and observable command from expected.json before provider spend: S97-runner-hypothesis' \
  bash "$RUNNER" --run-id "$TEST_RUN-observable-without-miss-hypothesis" --dry-run --min-fixtures 1 S97-runner-hypothesis
cat >> "$TEST_SHADOW/spec.md" <<'EOF'

Observable command: `node -e "process.exit(0)"` exposes the miss.
EOF
expect_fail_contains missing-solo-ceiling-avoidance \
  'shadow fixture NOTES.md needs ## Solo ceiling avoidance with solo_claude, a rejected/solo-saturated control comparison, and headroom reasoning before provider spend: S97-runner-hypothesis' \
  bash "$RUNNER" --run-id "$TEST_RUN-missing-ceiling" --dry-run --min-fixtures 1 S97-runner-hypothesis
cat >> "$TEST_SHADOW/NOTES.md" <<'EOF'

## Solo ceiling avoidance

This candidate mentions solo_claude but gives no control comparison.
EOF
expect_fail_contains weak-solo-ceiling-avoidance \
  'shadow fixture NOTES.md needs ## Solo ceiling avoidance with solo_claude, a rejected/solo-saturated control comparison, and headroom reasoning before provider spend: S97-runner-hypothesis' \
  bash "$RUNNER" --run-id "$TEST_RUN-weak-ceiling" --dry-run --min-fixtures 1 S97-runner-hypothesis
cat >> "$TEST_SHADOW/NOTES.md" <<'EOF'

Unlike solo-saturated S2-S6 controls, this fixture should preserve
solo_claude headroom because it targets a multi-run state dependency.
EOF
bash "$RUNNER" --run-id "$TEST_RUN-hypothesis" --dry-run --min-fixtures 1 S97-runner-hypothesis \
  > "$TMP_DIR/hypothesis.out" 2>&1
grep -Fq '[full-pipeline-pair] DRY RUN complete' "$TMP_DIR/hypothesis.out"

bash "$RUNNER" --run-id "$TEST_RUN-shadow-rejected-override" --dry-run --min-fixtures 1 \
  --allow-rejected-fixtures S3-cli-ticket-assignment \
  > "$TMP_DIR/shadow-rejected-override.out" 2>&1
grep -Fq -- '--allow-rejected-fixtures' "$TMP_DIR/shadow-rejected-override.out"
grep -Fq '[full-pipeline-pair] DRY RUN complete' "$TMP_DIR/shadow-rejected-override.out"

bash "$RUNNER" --run-id "$TEST_RUN-rejected-override" --dry-run --min-fixtures 1 \
  --allow-rejected-fixtures F26-cli-payout-ledger-rules \
  > "$TMP_DIR/rejected-override.out" 2>&1
grep -Fq -- '--allow-rejected-fixtures' "$TMP_DIR/rejected-override.out"
grep -Fq '[full-pipeline-pair] DRY RUN complete' "$TMP_DIR/rejected-override.out"

STUB_REPO="$TMP_DIR/stub-repo"
STUB_BENCH="$STUB_REPO/benchmark/auto-resolve"
mkdir -p \
  "$STUB_BENCH/scripts" \
  "$STUB_BENCH/fixtures/F21-cli-scheduler-priority" \
  "$STUB_REPO/config/skills/devlyn:resolve"
cp "$RUNNER" "$STUB_BENCH/scripts/run-full-pipeline-pair-candidate.sh"
cp "$REJECTED" "$STUB_BENCH/scripts/pair-rejected-fixtures.sh"
chmod +x "$STUB_BENCH/scripts/run-full-pipeline-pair-candidate.sh"
chmod +x "$STUB_BENCH/scripts/pair-rejected-fixtures.sh"
printf -- '---\nname: devlyn:resolve\n---\n' > "$STUB_REPO/config/skills/devlyn:resolve/SKILL.md"
cat > "$STUB_BENCH/scripts/run-fixture.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
echo "[stub-run-fixture] $*"
EOF
chmod +x "$STUB_BENCH/scripts/run-fixture.sh"
cat > "$STUB_BENCH/scripts/judge.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
echo "[stub-judge] $*"
EOF
chmod +x "$STUB_BENCH/scripts/judge.sh"
cat > "$STUB_BENCH/scripts/headroom-gate.py" <<'PY'
#!/usr/bin/env python3
import json
import os
import pathlib
import sys

out_json = None
out_md = None
args = sys.argv[1:]
for index, arg in enumerate(args):
    if arg == "--out-json":
        out_json = pathlib.Path(args[index + 1])
    if arg == "--out-md":
        out_md = pathlib.Path(args[index + 1])
payload = {"verdict": "PASS" if os.environ.get("STUB_HEADROOM_EXIT", "0") == "0" else "FAIL"}
if out_json:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload) + "\n", encoding="utf8")
if out_md:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(
        "# stub headroom\n\n"
        "Verdict: **%s**\n\n"
        "| fixture | bare | solo_claude | solo_claude-bare |\n"
        "| --- | ---: | ---: | ---: |\n"
        "| F21-cli-scheduler-priority | 50 | 75 | 25 |\n"
        % payload["verdict"],
        encoding="utf8",
    )
sys.exit(int(os.environ.get("STUB_HEADROOM_EXIT", "0")))
PY
cat > "$STUB_BENCH/scripts/full-pipeline-pair-gate.py" <<'PY'
#!/usr/bin/env python3
import json
import os
import pathlib
import sys

out_json = None
out_md = None
args = sys.argv[1:]
for index, arg in enumerate(args):
    if arg == "--out-json":
        out_json = pathlib.Path(args[index + 1])
    if arg == "--out-md":
        out_md = pathlib.Path(args[index + 1])
payload = {"verdict": "PASS" if os.environ.get("STUB_PAIR_EXIT", "0") == "0" else "FAIL"}
print("stub-pair-gate args: " + " ".join(args))
if out_json:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload) + "\n", encoding="utf8")
if out_md:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(
        "# stub pair\n\n"
        "Verdict: **%s**\n\n"
        "| fixture | bare | solo_claude | pair | pair-solo_claude |\n"
        "| --- | ---: | ---: | ---: | ---: |\n"
        "| F21-cli-scheduler-priority | 50 | 75 | 96 | 21 |\n"
        % payload["verdict"],
        encoding="utf8",
    )
sys.exit(int(os.environ.get("STUB_PAIR_EXIT", "0")))
PY

STUB_RUNNER="$STUB_BENCH/scripts/run-full-pipeline-pair-candidate.sh"
STUB_HEADROOM_EXIT=0 STUB_PAIR_EXIT=0 \
  bash "$STUB_RUNNER" --run-id "$TEST_RUN-stub-success" --min-fixtures 1 F21-cli-scheduler-priority \
  > "$TMP_DIR/stub-success.out" 2>&1
grep -Fq '[full-pipeline-pair] headroom gate passed — executing l2_risk_probes.' "$TMP_DIR/stub-success.out"
grep -Fq '[full-pipeline-pair] pair gate passed — pair evidence accepted.' "$TMP_DIR/stub-success.out"
grep -Fq '[full-pipeline-pair] release audit: npx devlyn-cli benchmark audit --require-hypothesis-trigger --out-dir /tmp/devlyn-benchmark-audit-strict' "$TMP_DIR/stub-success.out"
grep -Fq '| F21-cli-scheduler-priority | 50 | 75 | 25 |' "$TMP_DIR/stub-success.out"
grep -Fq '| F21-cli-scheduler-priority | 50 | 75 | 96 | 21 |' "$TMP_DIR/stub-success.out"
grep -Fq '[stub-run-fixture] --fixture F21-cli-scheduler-priority --arm l2_risk_probes' "$TMP_DIR/stub-success.out"
grep -Fq -- '--require-hypothesis-trigger' "$TMP_DIR/stub-success.out"

if STUB_HEADROOM_EXIT=1 STUB_PAIR_EXIT=0 \
  bash "$STUB_RUNNER" --run-id "$TEST_RUN-stub-headroom-fail" --min-fixtures 1 F21-cli-scheduler-priority \
  > "$TMP_DIR/stub-headroom-fail.out" 2>&1; then
  echo "expected stub headroom failure" >&2
  cat "$TMP_DIR/stub-headroom-fail.out" >&2
  exit 1
fi
grep -Fq '[full-pipeline-pair] headroom gate failed — pair arm not executed.' "$TMP_DIR/stub-headroom-fail.out"
grep -Fq '| F21-cli-scheduler-priority | 50 | 75 | 25 |' "$TMP_DIR/stub-headroom-fail.out"
if grep -Fq '[stub-run-fixture] --fixture F21-cli-scheduler-priority --arm l2_risk_probes' "$TMP_DIR/stub-headroom-fail.out"; then
  echo "pair arm must not run after headroom failure" >&2
  cat "$TMP_DIR/stub-headroom-fail.out" >&2
  exit 1
fi

if STUB_HEADROOM_EXIT=0 STUB_PAIR_EXIT=1 \
  bash "$STUB_RUNNER" --run-id "$TEST_RUN-stub-pair-fail" --min-fixtures 1 F21-cli-scheduler-priority \
  > "$TMP_DIR/stub-pair-fail.out" 2>&1; then
  echo "expected stub pair gate failure" >&2
  cat "$TMP_DIR/stub-pair-fail.out" >&2
  exit 1
fi
grep -Fq '[full-pipeline-pair] headroom gate passed — executing l2_risk_probes.' "$TMP_DIR/stub-pair-fail.out"
grep -Fq '[full-pipeline-pair] pair gate failed — pair evidence rejected.' "$TMP_DIR/stub-pair-fail.out"
grep -Fq '| F21-cli-scheduler-priority | 50 | 75 | 25 |' "$TMP_DIR/stub-pair-fail.out"
grep -Fq '| F21-cli-scheduler-priority | 50 | 75 | 96 | 21 |' "$TMP_DIR/stub-pair-fail.out"
if grep -Fq '[full-pipeline-pair] pair gate passed — pair evidence accepted.' "$TMP_DIR/stub-pair-fail.out"; then
  echo "pair accepted message must not print after pair gate failure" >&2
  cat "$TMP_DIR/stub-pair-fail.out" >&2
  exit 1
fi

mkdir -p "$BENCH_ROOT/results/src-$TEST_RUN/F21-cli-scheduler-priority/bare"
printf '{}\n' > "$BENCH_ROOT/results/src-$TEST_RUN/F21-cli-scheduler-priority/bare/result.json"
printf '{}\n' > "$BENCH_ROOT/results/src-$TEST_RUN/F21-cli-scheduler-priority/bare/verify.json"
expect_fail_contains reuse-source-incomplete \
  "reuse source missing diff.patch" \
  bash "$RUNNER" --run-id "$TEST_RUN-source-incomplete" \
    --reuse-calibrated-from "src-$TEST_RUN" \
    F21-cli-scheduler-priority

mkdir -p "$BENCH_ROOT/results/$TEST_RUN-destination-incomplete/F21-cli-scheduler-priority/bare"
printf '{}\n' > "$BENCH_ROOT/results/$TEST_RUN-destination-incomplete/F21-cli-scheduler-priority/bare/result.json"
printf '{}\n' > "$BENCH_ROOT/results/$TEST_RUN-destination-incomplete/F21-cli-scheduler-priority/bare/verify.json"
expect_fail_contains reuse-destination-incomplete \
  "reuse destination incomplete diff.patch" \
  bash "$RUNNER" --run-id "$TEST_RUN-destination-incomplete" \
    --reuse-calibrated-from "src-$TEST_RUN" \
    F21-cli-scheduler-priority

echo "PASS test-run-full-pipeline-pair-candidate"
