#!/usr/bin/env bash
# Regression tests for benchmark runner argument parsing.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMP="$(mktemp -d)"
BENCH_ROOT="$ROOT/benchmark/auto-resolve"
trap 'rm -rf "$TMP"; rm -rf "$BENCH_ROOT/results/arg-parse-command-test" "$BENCH_ROOT/results/arg-parse-discovery-test" "$BENCH_ROOT/results/arg-parse-shadow-suite-dry-run" "$BENCH_ROOT/results/arg-parse-shadow-cli-suite-dry-run" "$BENCH_ROOT/results/arg-parse-variant-path" "$BENCH_ROOT/results/arg-parse-headroom-cli-replay" "$BENCH_ROOT/results/arg-parse-pair-cli-replay" "$BENCH_ROOT/results/arg-parse-shadow-judge" "$BENCH_ROOT/results/arg-parse-opus-bad-mapping" "$BENCH_ROOT/results/arg-parse-opus-malformed-mapping" "$BENCH_ROOT/results/arg-parse-opus-malformed-score" "$BENCH_ROOT/results/arg-parse-opus-invalid-generated-score" "$BENCH_ROOT/results/arg-parse-opus-invalid-generated-dq" "$BENCH_ROOT/results/arg-parse-opus-summary-mapping" "$BENCH_ROOT/results/arg-parse-opus-summary-null-margin"; rm -rf /tmp/bench-arg-parse-variant-path-* /tmp/bench-arg-parse-headroom-cli-replay-*' EXIT

expect_fail_contains() {
  local name="$1"
  local expected="$2"
  shift 2
  set +e
  "$@" > "$TMP/$name.out" 2>&1
  local status=$?
  set -e
  [ "$status" -ne 0 ] || {
    echo "expected failure for $name" >&2
    exit 1
  }
  grep -Fq -- "$expected" "$TMP/$name.out" || {
    echo "missing expected output for $name: $expected" >&2
    cat "$TMP/$name.out" >&2
    exit 1
  }
}

expect_fail_contains suite-missing-n "--n requires a value" \
  bash "$ROOT/benchmark/auto-resolve/scripts/run-suite.sh" --n
expect_fail_contains suite-bad-n "error: --n must be an integer" \
  bash "$ROOT/benchmark/auto-resolve/scripts/run-suite.sh" --n abc --dry-run
expect_fail_contains suite-missing-run-id "--run-id requires a value" \
  bash "$ROOT/benchmark/auto-resolve/scripts/run-suite.sh" --judge-only --run-id

bash "$ROOT/benchmark/auto-resolve/scripts/run-suite.sh" --help > "$TMP/run-suite-help.out" 2>&1
grep -Fq 'run-suite.sh --suite shadow --dry-run' "$TMP/run-suite-help.out"
grep -Fq 'shadow suite refuses provider/judge runs' "$TMP/run-suite-help.out"

expect_fail_contains fixture-missing-arm "--arm requires a value" \
  bash "$ROOT/benchmark/auto-resolve/scripts/run-fixture.sh" --fixture F1 --arm
expect_fail_contains fixture-missing-resolve-skill "--resolve-skill requires a value" \
  bash "$ROOT/benchmark/auto-resolve/scripts/run-fixture.sh" \
    --fixture F1 --arm bare --run-id arg-parse --resolve-skill

expect_fail_contains judge-missing-fixture "--fixture requires a value" \
  bash "$ROOT/benchmark/auto-resolve/scripts/judge.sh" --fixture
expect_fail_contains judge-missing-run-id "--run-id requires a value" \
  bash "$ROOT/benchmark/auto-resolve/scripts/judge.sh" --fixture F1 --run-id

grep -Fq 'shadow-fixtures/$FIXTURE' "$ROOT/benchmark/auto-resolve/scripts/judge.sh"

SHADOW_JUDGE_DIR="$BENCH_ROOT/results/arg-parse-shadow-judge/S1-cli-lang-flag"
mkdir -p "$SHADOW_JUDGE_DIR/bare" "$SHADOW_JUDGE_DIR/solo_claude" "$TMP/fakebin"
cat > "$SHADOW_JUDGE_DIR/bare/diff.patch" <<'EOF'
diff --git a/bin/cli.js b/bin/cli.js
--- a/bin/cli.js
+++ b/bin/cli.js
@@ -1 +1 @@
-old
+bare
EOF
cat > "$SHADOW_JUDGE_DIR/solo_claude/diff.patch" <<'EOF'
diff --git a/bin/cli.js b/bin/cli.js
--- a/bin/cli.js
+++ b/bin/cli.js
@@ -1 +1 @@
-old
+solo
EOF
printf '{"arm":"bare","verify_score":0.5}\n' > "$SHADOW_JUDGE_DIR/bare/verify.json"
printf '{"arm":"solo_claude","verify_score":0.75}\n' > "$SHADOW_JUDGE_DIR/solo_claude/verify.json"
cat > "$TMP/fakebin/codex" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = "--version" ]; then
  echo "codex-cli fake"
  exit 0
fi
last=""
while [ $# -gt 0 ]; do
  if [ "$1" = "--output-last-message" ]; then
    last="$2"
    shift 2
    continue
  fi
  shift
done
json='{"a_score":50,"b_score":75,"winner":"B","a_breakdown":{"spec":12,"constraint":13,"scope":12,"quality":13,"notes":"ok"},"b_breakdown":{"spec":19,"constraint":19,"scope":18,"quality":19,"notes":"ok"},"critical_findings":{"A":[],"B":[]},"disqualifiers":{"A":false,"A_reason":"","B":false,"B_reason":""},"overall_reasoning":"fake judge output for shadow fixture resolver regression."}'
[ -z "$last" ] || printf '%s\n' "$json" > "$last"
printf '%s\n' "$json"
EOF
chmod +x "$TMP/fakebin/codex"
PATH="$TMP/fakebin:$PATH" \
  bash "$ROOT/benchmark/auto-resolve/scripts/judge.sh" --fixture S1-cli-lang-flag --run-id arg-parse-shadow-judge \
  > "$TMP/shadow-judge.out" 2>&1
grep -Fq '[judge]' "$TMP/shadow-judge.out"
grep -Fq '"solo_claude"' "$SHADOW_JUDGE_DIR/judge.json"

expect_fail_contains opus-missing-run-id "--run-id requires a value" \
  bash "$ROOT/benchmark/auto-resolve/scripts/judge-opus-pass.sh" --run-id

OPUS_BAD_MAPPING_DIR="$BENCH_ROOT/results/arg-parse-opus-bad-mapping/F9-e2e-ideate-to-resolve"
mkdir -p "$OPUS_BAD_MAPPING_DIR"
: > "$OPUS_BAD_MAPPING_DIR/judge-prompt.txt"
cat > "$OPUS_BAD_MAPPING_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "variant", "B": "bare", "seed": 1},
  "scores_by_arm": {"variant": 70, "bare": 50, "solo_claude": 60}
}
JSON
expect_fail_contains opus-bad-mapping "judge blind mapping missing arm(s): solo_claude" \
  bash "$ROOT/benchmark/auto-resolve/scripts/judge-opus-pass.sh" --run-id arg-parse-opus-bad-mapping

OPUS_MALFORMED_MAPPING_DIR="$BENCH_ROOT/results/arg-parse-opus-malformed-mapping/F9-e2e-ideate-to-resolve"
mkdir -p "$OPUS_MALFORMED_MAPPING_DIR"
: > "$OPUS_MALFORMED_MAPPING_DIR/judge-prompt.txt"
cat > "$OPUS_MALFORMED_MAPPING_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": "not-a-dict",
  "scores_by_arm": {"variant": 70, "bare": 50, "solo_claude": 60}
}
JSON
expect_fail_contains opus-malformed-mapping "judge blind mapping missing" \
  bash "$ROOT/benchmark/auto-resolve/scripts/judge-opus-pass.sh" --run-id arg-parse-opus-malformed-mapping

OPUS_MALFORMED_SCORE_DIR="$BENCH_ROOT/results/arg-parse-opus-malformed-score/F9-e2e-ideate-to-resolve"
mkdir -p "$OPUS_MALFORMED_SCORE_DIR"
: > "$OPUS_MALFORMED_SCORE_DIR/judge-prompt.txt"
cat > "$OPUS_MALFORMED_SCORE_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "bare", "B": "solo_claude", "C": "variant", "seed": 1},
  "scores_by_arm": {"bare": 50, "solo_claude": true, "variant": 101}
}
JSON
expect_fail_contains opus-malformed-score "scores_by_arm malformed score(s): solo_claude, variant" \
  bash "$ROOT/benchmark/auto-resolve/scripts/judge-opus-pass.sh" --run-id arg-parse-opus-malformed-score

OPUS_SUMMARY_MAPPING_DIR="$BENCH_ROOT/results/arg-parse-opus-summary-mapping/F99-opus-summary-mapping"
mkdir -p "$OPUS_SUMMARY_MAPPING_DIR"
: > "$OPUS_SUMMARY_MAPPING_DIR/judge-prompt.txt"
cat > "$OPUS_SUMMARY_MAPPING_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "bare", "B": "solo_claude", "seed": 1},
  "scores_by_arm": {"bare": 50, "solo_claude": 60},
  "margins": {"solo_over_bare": 999, "variant_over_bare": 888},
  "winner_arm": "variant",
  "breakdowns_by_arm": {
    "bare": {"spec": 10, "constraint": 10, "scope": 10, "quality": 10},
    "solo_claude": {"spec": 11, "constraint": 11, "scope": 11, "quality": 11}
  }
}
JSON
FAKE_CLAUDE_DIR="$TMP/fake-claude-bin"
mkdir -p "$FAKE_CLAUDE_DIR"
cat > "$FAKE_CLAUDE_DIR/claude" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = "--version" ]; then
  echo "claude fake"
  exit 0
fi
if [ "${FAKE_CLAUDE_INVALID_SCORE:-}" = "1" ]; then
  cat <<'JSON'
{
  "a_score": true,
  "b_score": 101,
  "winner": "B",
  "disqualifiers": {"A": false, "A_reason": "", "B": false, "B_reason": ""},
  "critical_findings": {"A": [], "B": []},
  "a_breakdown": {"spec": 10, "constraint": 10, "scope": 10, "quality": 10},
  "b_breakdown": {"spec": 11, "constraint": 11, "scope": 11, "quality": 11},
  "overall_reasoning": "invalid scores for regression test"
}
JSON
  exit 0
fi
if [ "${FAKE_CLAUDE_INVALID_DQ:-}" = "1" ]; then
  cat <<'JSON'
{
  "a_score": 40,
  "b_score": 70,
  "winner": "B",
  "disqualifiers": {"A": "false", "A_reason": "", "B": false, "B_reason": ""},
  "critical_findings": {"A": [], "B": []},
  "a_breakdown": {"spec": 10, "constraint": 10, "scope": 10, "quality": 10},
  "b_breakdown": {"spec": 11, "constraint": 11, "scope": 11, "quality": 11},
  "overall_reasoning": "invalid disqualifier for regression test"
}
JSON
  exit 0
fi
cat <<'JSON'
{
  "a_score": 40,
  "b_score": 70,
  "winner": "B",
  "disqualifiers": ["not", "a", "dict"],
  "a_breakdown": {"spec": 10, "constraint": 10, "scope": 10, "quality": 10},
  "b_breakdown": {"spec": 11, "constraint": 11, "scope": 11, "quality": 11}
}
JSON
EOF
chmod +x "$FAKE_CLAUDE_DIR/claude"
OPUS_INVALID_GENERATED_SCORE_DIR="$BENCH_ROOT/results/arg-parse-opus-invalid-generated-score/F99-opus-invalid-generated-score"
mkdir -p "$OPUS_INVALID_GENERATED_SCORE_DIR"
: > "$OPUS_INVALID_GENERATED_SCORE_DIR/judge-prompt.txt"
cat > "$OPUS_INVALID_GENERATED_SCORE_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "bare", "B": "solo_claude", "seed": 1},
  "scores_by_arm": {"bare": 50, "solo_claude": 60}
}
JSON
expect_fail_contains opus-invalid-generated-score "invalid opus score value(s): a_score, b_score" \
  env FAKE_CLAUDE_INVALID_SCORE=1 PATH="$FAKE_CLAUDE_DIR:$PATH" \
    bash "$ROOT/benchmark/auto-resolve/scripts/judge-opus-pass.sh" \
      --run-id arg-parse-opus-invalid-generated-score
OPUS_INVALID_GENERATED_DQ_DIR="$BENCH_ROOT/results/arg-parse-opus-invalid-generated-dq/F99-opus-invalid-generated-dq"
mkdir -p "$OPUS_INVALID_GENERATED_DQ_DIR"
: > "$OPUS_INVALID_GENERATED_DQ_DIR/judge-prompt.txt"
cat > "$OPUS_INVALID_GENERATED_DQ_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "bare", "B": "solo_claude", "seed": 1},
  "scores_by_arm": {"bare": 50, "solo_claude": 60}
}
JSON
expect_fail_contains opus-invalid-generated-dq "invalid opus disqualifier value(s): A" \
  env FAKE_CLAUDE_INVALID_DQ=1 PATH="$FAKE_CLAUDE_DIR:$PATH" \
    bash "$ROOT/benchmark/auto-resolve/scripts/judge-opus-pass.sh" \
      --run-id arg-parse-opus-invalid-generated-dq
PATH="$FAKE_CLAUDE_DIR:$PATH" \
  bash "$ROOT/benchmark/auto-resolve/scripts/judge-opus-pass.sh" \
    --run-id arg-parse-opus-summary-mapping > "$TMP/opus-summary-mapping.out" 2>&1
python3 - "$BENCH_ROOT/results/arg-parse-opus-summary-mapping/cross-judge-summary.json" <<'PY'
import json
import pathlib
import sys

summary = json.loads(pathlib.Path(sys.argv[1]).read_text())
row = summary["rows"][0]
assert row["gpt_scores"] == {"bare": 50, "solo_claude": 60}, row
assert row["gpt_margin_l1_l0"] == 10, row
assert row["gpt_margin_v_l0"] is None, row
assert row["gpt_winner"] is None, row
assert row["opus_winner"] == "solo_claude", row
assert row["winner_agree"] is False, row
assert summary["sign_valid_count_variant_over_bare"] == 0, summary
PY

OPUS_SUMMARY_NULL_MARGIN_DIR="$BENCH_ROOT/results/arg-parse-opus-summary-null-margin/F99-opus-summary-null-margin"
mkdir -p "$OPUS_SUMMARY_NULL_MARGIN_DIR"
: > "$OPUS_SUMMARY_NULL_MARGIN_DIR/judge-prompt.txt"
cat > "$OPUS_SUMMARY_NULL_MARGIN_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "bare", "B": "solo_claude", "seed": 1},
  "breakdowns_by_arm": {
    "bare": {"spec": 10, "constraint": 10, "scope": 10, "quality": 10},
    "solo_claude": {"spec": 11, "constraint": 11, "scope": 11, "quality": 11}
  }
}
JSON
PATH="$FAKE_CLAUDE_DIR:$PATH" \
  bash "$ROOT/benchmark/auto-resolve/scripts/judge-opus-pass.sh" \
    --run-id arg-parse-opus-summary-null-margin > "$TMP/opus-summary-null-margin.out" 2>&1
grep -Fq 'gpt_l1_l0_avg=na' "$TMP/opus-summary-null-margin.out"
grep -Fq 'suite_avg_diff=na' "$TMP/opus-summary-null-margin.out"
python3 - "$BENCH_ROOT/results/arg-parse-opus-summary-null-margin/cross-judge-summary.json" <<'PY'
import json
import pathlib
import sys

summary = json.loads(pathlib.Path(sys.argv[1]).read_text())
row = summary["rows"][0]
assert row["gpt_scores"] == {}, row
assert row["gpt_margin_l1_l0"] is None, row
assert summary["suite_avg_l1_l0"]["gpt"] is None, summary
assert summary["suite_avg_l1_l0"]["gpt_valid_count"] == 0, summary
PY

bash "$ROOT/benchmark/auto-resolve/scripts/run-suite.sh" \
  --dry-run \
  --run-id arg-parse-command-test \
  F0 > "$TMP/suite-command.out" 2>&1
grep -Fq 'Command: ' "$TMP/suite-command.out"
grep -Fq -- '--dry-run' "$TMP/suite-command.out"
grep -Fq -- '--run-id arg-parse-command-test' "$TMP/suite-command.out"

bash "$ROOT/benchmark/auto-resolve/scripts/run-suite.sh" \
  --dry-run \
  --judge-only \
  --run-id arg-parse-discovery-test > "$TMP/suite-discovery.out" 2>&1
grep -Fq 'F25-cli-cart-promotion-rules' "$TMP/suite-discovery.out"
if grep -Fq 'F27-cli-subscription-proration' "$TMP/suite-discovery.out"; then
  echo "retired F27 must not be auto-discovered by the golden suite" >&2
  cat "$TMP/suite-discovery.out" >&2
  exit 1
fi
if grep -Fq 'F28-cli-return-authorization' "$TMP/suite-discovery.out"; then
  echo "retired F28 must not be auto-discovered by the golden suite" >&2
  cat "$TMP/suite-discovery.out" >&2
  exit 1
fi

bash "$ROOT/benchmark/auto-resolve/scripts/run-suite.sh" \
  --suite shadow \
  --dry-run \
  --run-id arg-parse-shadow-suite-dry-run > "$TMP/shadow-suite-dry-run.out" 2>&1
grep -Fq 'Suite:         shadow' "$TMP/shadow-suite-dry-run.out"
grep -Fq 'S1-cli-lang-flag' "$TMP/shadow-suite-dry-run.out"
grep -Fq '[suite] DRY RUN complete' "$TMP/shadow-suite-dry-run.out"
grep -Fq 'Use benchmark headroom/pair with explicit S* candidates for real provider measurement.' "$TMP/shadow-suite-dry-run.out"
if grep -Fq 'Run without --dry-run to invoke models.' "$TMP/shadow-suite-dry-run.out"; then
  echo "shadow suite dry-run must not invite a blocked non-dry-run suite invocation" >&2
  cat "$TMP/shadow-suite-dry-run.out" >&2
  exit 1
fi

expect_fail_contains shadow-suite-provider-run \
  "shadow suite run-suite is dry-run only" \
  bash "$ROOT/benchmark/auto-resolve/scripts/run-suite.sh" \
    --suite shadow \
    --run-id arg-parse-shadow-suite-block

expect_fail_contains shadow-suite-judge-only-provider-run \
  "shadow suite run-suite is dry-run only" \
  bash "$ROOT/benchmark/auto-resolve/scripts/run-suite.sh" \
    --suite shadow \
    --judge-only \
    --run-id arg-parse-shadow-suite-judge-only-block

node "$ROOT/bin/devlyn.js" benchmark suite \
  --suite shadow \
  --dry-run \
  --run-id arg-parse-shadow-cli-suite-dry-run > "$TMP/shadow-cli-suite-dry-run.out" 2>&1
grep -Fq 'Suite:         shadow' "$TMP/shadow-cli-suite-dry-run.out"
grep -Fq 'S1-cli-lang-flag' "$TMP/shadow-cli-suite-dry-run.out"
grep -Fq 'Use benchmark headroom/pair with explicit S* candidates for real provider measurement.' "$TMP/shadow-cli-suite-dry-run.out"

node "$ROOT/bin/devlyn.js" --help > "$TMP/devlyn-help.out" 2>&1
grep -Fq 'npx devlyn-cli benchmark    Run the resolve benchmark suite' "$TMP/devlyn-help.out"
grep -Fq 'npx devlyn-cli benchmark recent              Show compact recent benchmark results' "$TMP/devlyn-help.out"
grep -Fq 'npx devlyn-cli benchmark frontier            Show pair candidate frontier scores/triggers without providers' "$TMP/devlyn-help.out"
grep -Fq 'npx devlyn-cli benchmark audit               Audit pair evidence readiness' "$TMP/devlyn-help.out"
grep -Fq 'npx devlyn-cli benchmark audit-headroom      Audit failed headroom results' "$TMP/devlyn-help.out"
grep -Fq 'npx devlyn-cli benchmark headroom <fixtures...>  Score bare vs solo_claude headroom' "$TMP/devlyn-help.out"
grep -Fq 'npx devlyn-cli benchmark pair <fixtures...>      Score solo_claude vs pair path' "$TMP/devlyn-help.out"
if grep -Fq -- '--n 3' "$TMP/devlyn-help.out"; then
  echo "help must not advertise unsupported --n 3 benchmark runs" >&2
  cat "$TMP/devlyn-help.out" >&2
  exit 1
fi
node "$ROOT/bin/devlyn.js" benchmark --help > "$TMP/devlyn-benchmark-help.out" 2>&1
grep -Fq 'npx devlyn-cli benchmark [suite] [options] [fixtures...]' "$TMP/devlyn-benchmark-help.out"
grep -Fq 'npx devlyn-cli benchmark recent [options]' "$TMP/devlyn-benchmark-help.out"
grep -Fq 'npx devlyn-cli benchmark frontier [options]' "$TMP/devlyn-benchmark-help.out"
grep -Fq 'npx devlyn-cli benchmark audit [options]' "$TMP/devlyn-benchmark-help.out"
grep -Fq 'npx devlyn-cli benchmark audit-headroom [options]' "$TMP/devlyn-benchmark-help.out"
grep -Fq 'npx devlyn-cli benchmark suite --suite shadow --dry-run' "$TMP/devlyn-benchmark-help.out"
grep -Fq 'use headroom/pair with explicit S* ids for real measurement' "$TMP/devlyn-benchmark-help.out"
grep -Fq 'Show compact, wrap-safe recent benchmark results' "$TMP/devlyn-benchmark-help.out"
grep -Fq 'npx devlyn-cli benchmark headroom [options] <fixtures...>' "$TMP/devlyn-benchmark-help.out"
grep -Fq 'npx devlyn-cli benchmark pair [options] <fixtures...>' "$TMP/devlyn-benchmark-help.out"
grep -Fq 'Show active rejected/evidence/unmeasured pair candidates, scores, and triggers without providers' "$TMP/devlyn-benchmark-help.out"
grep -Fq 'Fail on unmeasured pair candidates and invalid headroom rejections' "$TMP/devlyn-benchmark-help.out"
grep -Fq 'Prints frontier score rows plus headroom and pair quality handoff rows' "$TMP/devlyn-benchmark-help.out"
grep -Fq 'Fail on active failed or unsupported headroom rejections' "$TMP/devlyn-benchmark-help.out"
grep -Fq 'Score bare vs solo_claude before spending the pair arm' "$TMP/devlyn-benchmark-help.out"
grep -Fq 'Score solo_claude vs the selected pair path and print gate tables' "$TMP/devlyn-benchmark-help.out"
grep -Fq 'npx devlyn-cli benchmark recent --out-md /tmp/devlyn-recent-benchmark.md' "$TMP/devlyn-benchmark-help.out"
grep -Fq 'npx devlyn-cli benchmark pair --min-fixtures 3 --max-pair-solo-wall-ratio 3 F16-cli-quote-tax-rules F23-cli-fulfillment-wave F25-cli-cart-promotion-rules' "$TMP/devlyn-benchmark-help.out"

node "$ROOT/bin/devlyn.js" benchmark recent --help > "$TMP/devlyn-benchmark-recent-help.out" 2>&1
grep -Fq 'npx devlyn-cli benchmark recent [options]' "$TMP/devlyn-benchmark-recent-help.out"
grep -Fq -- '--out-json PATH' "$TMP/devlyn-benchmark-recent-help.out"
grep -Fq -- '--out-md PATH' "$TMP/devlyn-benchmark-recent-help.out"
grep -Fq -- '--fixtures-root PATH' "$TMP/devlyn-benchmark-recent-help.out"
grep -Fq -- '--registry PATH' "$TMP/devlyn-benchmark-recent-help.out"
grep -Fq -- '--results-root PATH' "$TMP/devlyn-benchmark-recent-help.out"
grep -Fq -- '--max-width N  default: 92' "$TMP/devlyn-benchmark-recent-help.out"
grep -Fq 'Prints compact, wrap-safe benchmark status and pair-evidence cards without wide tables' "$TMP/devlyn-benchmark-recent-help.out"
grep -Fq 'npx devlyn-cli benchmark recent --out-md /tmp/devlyn-recent-benchmark.md' "$TMP/devlyn-benchmark-recent-help.out"

node "$ROOT/bin/devlyn.js" benchmark audit --help > "$TMP/devlyn-benchmark-audit-help.out" 2>&1
grep -Fq 'npx devlyn-cli benchmark audit [options]' "$TMP/devlyn-benchmark-audit-help.out"
grep -Fq -- '--out-dir PATH' "$TMP/devlyn-benchmark-audit-help.out"
grep -Fq -- '--fixtures-root PATH' "$TMP/devlyn-benchmark-audit-help.out"
grep -Fq -- '--registry PATH' "$TMP/devlyn-benchmark-audit-help.out"
grep -Fq -- '--results-root PATH' "$TMP/devlyn-benchmark-audit-help.out"
grep -Fq -- '--min-pair-evidence N  default: 4' "$TMP/devlyn-benchmark-audit-help.out"
grep -Fq -- '--min-pair-margin N  default: 5' "$TMP/devlyn-benchmark-audit-help.out"
grep -Fq -- '--max-pair-solo-wall-ratio N  default: 3' "$TMP/devlyn-benchmark-audit-help.out"
grep -Fq -- '--require-hypothesis-trigger' "$TMP/devlyn-benchmark-audit-help.out"
grep -Fq 'Prints frontier score rows plus headroom_rejections=PASS/FAIL, pair_evidence_quality=PASS/FAIL, pair_trigger_reasons=PASS/FAIL, pair_evidence_hypotheses=PASS/FAIL, pair_evidence_hypothesis_triggers=PASS/WARN/FAIL, historical-alias, and hypothesis-trigger gap handoff rows' "$TMP/devlyn-benchmark-audit-help.out"
grep -Fq 'npx devlyn-cli benchmark audit --out-dir /tmp/devlyn-benchmark-audit' "$TMP/devlyn-benchmark-audit-help.out"
grep -Fq 'npx devlyn-cli benchmark audit --require-hypothesis-trigger --out-dir /tmp/devlyn-benchmark-audit-strict' "$TMP/devlyn-benchmark-audit-help.out"

node "$ROOT/bin/devlyn.js" benchmark frontier --help > "$TMP/devlyn-benchmark-frontier-help.out" 2>&1
grep -Fq 'npx devlyn-cli benchmark frontier [options]' "$TMP/devlyn-benchmark-frontier-help.out"
grep -Fq -- '--out-json PATH' "$TMP/devlyn-benchmark-frontier-help.out"
grep -Fq -- '--out-md PATH' "$TMP/devlyn-benchmark-frontier-help.out"
grep -Fq -- '--fixtures-root PATH' "$TMP/devlyn-benchmark-frontier-help.out"
grep -Fq -- '--registry PATH' "$TMP/devlyn-benchmark-frontier-help.out"
grep -Fq -- '--results-root PATH' "$TMP/devlyn-benchmark-frontier-help.out"
grep -Fq -- '--fail-on-unmeasured' "$TMP/devlyn-benchmark-frontier-help.out"
grep -Fq -- '--min-pair-margin N  default: 5' "$TMP/devlyn-benchmark-frontier-help.out"
grep -Fq -- '--max-pair-solo-wall-ratio N  default: 3' "$TMP/devlyn-benchmark-frontier-help.out"
grep -Fq 'Prints pair evidence score rows with trigger reasons; --out-md includes a Triggers column' "$TMP/devlyn-benchmark-frontier-help.out"
grep -Fq 'npx devlyn-cli benchmark frontier --out-md /tmp/devlyn-pair-frontier.md' "$TMP/devlyn-benchmark-frontier-help.out"

node "$ROOT/bin/devlyn.js" benchmark audit-headroom --help > "$TMP/devlyn-benchmark-audit-headroom-help.out" 2>&1
grep -Fq 'npx devlyn-cli benchmark audit-headroom [options]' "$TMP/devlyn-benchmark-audit-headroom-help.out"
grep -Fq -- '--out-json PATH' "$TMP/devlyn-benchmark-audit-headroom-help.out"
grep -Fq -- '--fixtures-root PATH' "$TMP/devlyn-benchmark-audit-headroom-help.out"
grep -Fq -- '--registry PATH' "$TMP/devlyn-benchmark-audit-headroom-help.out"
grep -Fq -- '--results-root PATH' "$TMP/devlyn-benchmark-audit-headroom-help.out"
grep -Fq 'npx devlyn-cli benchmark audit-headroom --out-json /tmp/devlyn-headroom-audit.json' "$TMP/devlyn-benchmark-audit-headroom-help.out"

node "$ROOT/bin/devlyn.js" benchmark audit-headroom --out-json "$TMP/headroom-audit.json" > "$TMP/devlyn-benchmark-audit-headroom.out" 2>&1
grep -Fq 'PASS audit-headroom-rejections' "$TMP/devlyn-benchmark-audit-headroom.out"
python3 - "$TMP/headroom-audit.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf8"))
assert report["verdict"] == "PASS"
assert report["unrecorded_failures"] == []
assert report["unsupported_registry_rejections"] == []
PY

node "$ROOT/bin/devlyn.js" benchmark recent \
  --out-json "$TMP/recent.json" \
  --out-md "$TMP/recent.md" \
  --max-width 92 > "$TMP/devlyn-benchmark-recent.out" 2>&1
grep -Fq 'Recent Benchmark Snapshot' "$TMP/devlyn-benchmark-recent.out"
grep -Fq 'Pair evidence rows: 4' "$TMP/devlyn-benchmark-recent.out"
grep -Fq 'Unmeasured candidates: 0' "$TMP/devlyn-benchmark-recent.out"
grep -Fq 'F21 cli scheduler priority' "$TMP/devlyn-benchmark-recent.out"
grep -Fq 'triggers: complexity.high, risk.high, risk_probes.enabled, spec.solo_headroom_hypothesis' "$TMP/devlyn-benchmark-recent.out"
grep -Fq '# Recent Benchmark Snapshot' "$TMP/recent.md"
grep -Fq '## Pair Evidence' "$TMP/recent.md"
if grep -Fq '| Fixture |' "$TMP/recent.md"; then
  echo "recent benchmark markdown must use wrap-safe cards, not a wide table" >&2
  cat "$TMP/recent.md" >&2
  exit 1
fi
python3 - "$TMP/devlyn-benchmark-recent.out" "$TMP/recent.json" <<'PY'
import json
import pathlib
import sys

text = pathlib.Path(sys.argv[1]).read_text(encoding="utf8")
long_lines = [(i, len(line), line) for i, line in enumerate(text.splitlines(), 1) if len(line) > 92]
assert not long_lines, long_lines
report = json.load(open(sys.argv[2], encoding="utf8"))
assert report["verdict"] == "PASS"
assert report["pair_evidence_count"] == 4
assert report["unmeasured_count"] == 0
assert report["pair_margin_avg"] == 27.25
assert report["pair_solo_wall_ratio_max"] == 2.25
PY

node "$ROOT/bin/devlyn.js" benchmark audit --out-dir "$TMP/audit" > "$TMP/devlyn-benchmark-audit.out" 2>&1
grep -Fq '[audit] frontier' "$TMP/devlyn-benchmark-audit.out"
grep -Fq 'fixtures=21 rejected=17 candidates=4 pair_evidence=4 unmeasured=0 verdict=PASS' "$TMP/devlyn-benchmark-audit.out"
grep -Fq 'F16-cli-quote-tax-rules: bare=50 solo_claude=75 pair=96 arm=l2_risk_probes margin=+21' "$TMP/devlyn-benchmark-audit.out"
grep -Fq 'verdict=pair_evidence_passed' "$TMP/devlyn-benchmark-audit.out"
grep -Fq 'headroom_rejections=PASS verdict=PASS unrecorded=0 unsupported=0' "$TMP/devlyn-benchmark-audit.out"
grep -Fq 'pair_evidence_quality=PASS min_pair_margin_actual=+21 min_pair_margin_required=+5 max_wall_actual=2.25x max_wall_allowed=3.00x' "$TMP/devlyn-benchmark-audit.out"
grep -Fq 'pair_trigger_reasons=PASS canonical=4 historical_alias=0 exposed=4 total=4 summary=4 rows_match=true' "$TMP/devlyn-benchmark-audit.out"
grep -Fq 'pair_evidence_hypothesis_triggers=PASS matched=4 documented=4 total=4' "$TMP/devlyn-benchmark-audit.out"
if grep -Fq 'pair_trigger_historical_aliases=' "$TMP/devlyn-benchmark-audit.out" \
  || grep -Fq 'pair_evidence_hypothesis_trigger_gaps=' "$TMP/devlyn-benchmark-audit.out"; then
  echo "current benchmark audit must not report historical aliases or hypothesis-trigger gaps" >&2
  cat "$TMP/devlyn-benchmark-audit.out" >&2
  exit 1
fi
grep -Fq 'PASS audit-pair-evidence' "$TMP/devlyn-benchmark-audit.out"
test -f "$TMP/audit/frontier.json"
test -f "$TMP/audit/frontier.stdout"
test -f "$TMP/audit/frontier.stderr"
test -f "$TMP/audit/headroom-audit.json"
test -f "$TMP/audit/headroom-rejections.stdout"
test -f "$TMP/audit/headroom-rejections.stderr"
test -f "$TMP/audit/audit.json"
grep -Fq 'F16-cli-quote-tax-rules: bare=50 solo_claude=75 pair=96 arm=l2_risk_probes margin=+21' "$TMP/audit/frontier.stdout"
grep -Fq 'verdict=pair_evidence_passed' "$TMP/audit/frontier.stdout"
python3 - "$TMP/audit/audit.json" "$TMP/audit/frontier.json" <<'PY'
import json
import sys

audit = json.load(open(sys.argv[1], encoding="utf8"))
frontier = json.load(open(sys.argv[2], encoding="utf8"))
assert audit["verdict"] == "PASS"
assert audit["min_pair_evidence"] == 4
assert audit["min_pair_margin"] == 5
assert audit["max_pair_solo_wall_ratio"] == 3.0
assert audit["checks"]["frontier"]["status"] == "PASS"
assert audit["checks"]["headroom_rejections"]["status"] == "PASS"
assert audit["checks"]["headroom_rejections"]["exit_code"] == 0
assert audit["checks"]["headroom_rejections"]["report_check_exit_code"] == 0
assert audit["checks"]["headroom_rejections"]["verdict"] == "PASS"
assert audit["checks"]["headroom_rejections"]["unrecorded_failure_count"] == 0
assert audit["checks"]["headroom_rejections"]["unsupported_registry_rejection_count"] == 0
assert audit["checks"]["frontier_report"]["status"] == "PASS"
assert audit["checks"]["frontier_report"]["verdict"] == frontier["verdict"]
assert audit["checks"]["frontier_report"]["unmeasured_count"] == frontier["unmeasured_count"]
assert audit["checks"]["frontier_stdout"]["status"] == "PASS"
assert audit["checks"]["frontier_stdout"]["summary_rows"] == 1
assert audit["checks"]["frontier_stdout"]["aggregate_rows"] == 1
assert audit["checks"]["frontier_stdout"]["final_verdict_rows"] == 1
assert audit["checks"]["frontier_stdout"]["expected_rows"] == len(audit["pair_evidence_rows"])
assert audit["checks"]["frontier_stdout"]["stdout_rows"] == len(audit["pair_evidence_rows"])
assert audit["checks"]["frontier_stdout"]["trigger_rows"] == len(audit["pair_evidence_rows"])
assert audit["checks"]["frontier_stdout"]["hypothesis_trigger_rows"] == len(audit["pair_evidence_rows"])
assert audit["checks"]["frontier_stdout"]["rows_match_count"] is True
assert audit["checks"]["frontier_stdout"]["trigger_rows_match_count"] is True
assert audit["checks"]["frontier_stdout"]["hypothesis_trigger_rows_match_count"] is True
assert audit["checks"]["min_pair_evidence"]["status"] == "PASS"
assert audit["checks"]["min_pair_evidence"]["actual_rows"] == len(audit["pair_evidence_rows"])
assert audit["checks"]["min_pair_evidence"]["actual_rows"] >= audit["min_pair_evidence"]
assert audit["checks"]["pair_evidence_quality"]["status"] == "PASS"
assert audit["checks"]["pair_evidence_quality"]["min_pair_margin_actual"] == frontier["pair_margin_min"]
assert audit["checks"]["pair_evidence_quality"]["max_pair_solo_wall_ratio_actual"] == frontier["pair_solo_wall_ratio_max"]
assert audit["checks"]["pair_trigger_reasons"]["status"] == "PASS"
assert audit["checks"]["pair_trigger_reasons"]["summary_pair_evidence_count"] == 4
assert audit["checks"]["pair_trigger_reasons"]["canonical_rows"] == 4
assert audit["checks"]["pair_trigger_reasons"]["historical_alias_rows"] == 0
assert audit["checks"]["pair_trigger_reasons"]["historical_alias_details"] == []
assert audit["checks"]["pair_trigger_reasons"]["exposed_rows"] == 4
assert audit["checks"]["pair_trigger_reasons"]["total_rows"] == 4
assert audit["checks"]["pair_trigger_reasons"]["rows_match_count"] is True
assert audit["checks"]["pair_evidence_hypothesis_triggers"]["status"] == "PASS"
assert audit["checks"]["pair_evidence_hypothesis_triggers"]["exit_code"] == 0
assert audit["checks"]["pair_evidence_hypothesis_triggers"]["required"] is False
assert audit["checks"]["pair_evidence_hypothesis_triggers"]["matched_rows"] == 4
assert audit["checks"]["pair_evidence_hypothesis_triggers"]["documented_rows"] == 4
assert audit["checks"]["pair_evidence_hypothesis_triggers"]["total_rows"] == 4
assert audit["checks"]["pair_evidence_hypothesis_triggers"]["gap_details"] == []
assert audit["artifacts"]["frontier_stdout"] == "frontier.stdout"
assert audit["artifacts"]["headroom_rejections_stdout"] == "headroom-rejections.stdout"
assert audit["frontier_summary"]["pair_margin_avg"] == frontier["pair_margin_avg"]
assert audit["frontier_summary"]["unmeasured_count"] == frontier["unmeasured_count"]
assert len(audit["pair_evidence_rows"]) == frontier["pair_evidence_count"]
for row in audit["pair_evidence_rows"]:
    assert isinstance(row["fixture"], str) and row["fixture"]
    assert row["verdict"] == "pair_evidence_passed"
    assert isinstance(row["run_id"], str) and row["run_id"]
    assert isinstance(row["pair_arm"], str) and row["pair_arm"]
    assert isinstance(row["bare_score"], int) and not isinstance(row["bare_score"], bool)
    assert isinstance(row["solo_score"], int) and not isinstance(row["solo_score"], bool)
    assert isinstance(row["pair_score"], int) and not isinstance(row["pair_score"], bool)
    assert isinstance(row["pair_margin"], int) and not isinstance(row["pair_margin"], bool)
    assert row["pair_mode"] is True
    assert row["pair_trigger_eligible"] is True
    assert isinstance(row["pair_solo_wall_ratio"], (int, float))
    assert not isinstance(row["pair_solo_wall_ratio"], bool)
assert frontier["verdict"] == "PASS"
assert frontier["min_pair_margin"] == 5
assert frontier["max_pair_solo_wall_ratio"] == 3.0
assert frontier["unmeasured_count"] == 0
assert frontier["pair_margin_avg"] is not None
assert frontier["pair_margin_min"] is not None
PY

actual_pair_evidence=$(python3 - "$TMP/audit/audit.json" <<'PY'
import json
import sys

audit = json.load(open(sys.argv[1], encoding="utf8"))
actual = audit["checks"]["min_pair_evidence"]["actual_rows"]
assert isinstance(actual, int) and not isinstance(actual, bool)
print(actual)
PY
)
required_pair_evidence=$((actual_pair_evidence + 1))
if node "$ROOT/bin/devlyn.js" benchmark audit \
  --min-pair-evidence "$required_pair_evidence" \
  --out-dir "$TMP/audit-fail" \
  > "$TMP/devlyn-benchmark-audit-fail.out" 2>&1; then
  echo "benchmark audit must fail when min pair evidence exceeds current evidence rows" >&2
  cat "$TMP/devlyn-benchmark-audit-fail.out" >&2
  exit 1
fi
grep -Fq "pair evidence count ${actual_pair_evidence} below required minimum ${required_pair_evidence}" "$TMP/devlyn-benchmark-audit-fail.out"
grep -Fq 'pair_margin_avg=+27.25 pair_margin_min=+21 wall_avg=1.66x wall_max=2.25x' "$TMP/devlyn-benchmark-audit-fail.out"
grep -Fq 'F16-cli-quote-tax-rules: bare=50 solo_claude=75 pair=96 arm=l2_risk_probes margin=+21' "$TMP/devlyn-benchmark-audit-fail.out"
grep -Fq 'headroom_rejections=PASS verdict=PASS unrecorded=0 unsupported=0' "$TMP/devlyn-benchmark-audit-fail.out"
grep -Fq 'pair_evidence_quality=PASS min_pair_margin_actual=+21 min_pair_margin_required=+5 max_wall_actual=2.25x max_wall_allowed=3.00x' "$TMP/devlyn-benchmark-audit-fail.out"
grep -Fq 'pair_trigger_reasons=PASS canonical=4 historical_alias=0 exposed=4 total=4 summary=4 rows_match=true' "$TMP/devlyn-benchmark-audit-fail.out"
grep -Fq 'pair_evidence_hypothesis_triggers=PASS matched=4 documented=4 total=4' "$TMP/devlyn-benchmark-audit-fail.out"
grep -Fq 'FAIL audit-pair-evidence' "$TMP/devlyn-benchmark-audit-fail.out"
python3 - "$TMP/audit-fail/audit.json" "$actual_pair_evidence" "$required_pair_evidence" <<'PY'
import json
import sys

audit = json.load(open(sys.argv[1], encoding="utf8"))
actual = int(sys.argv[2])
required = int(sys.argv[3])
assert audit["verdict"] == "FAIL"
assert audit["checks"]["frontier"]["status"] == "PASS"
assert audit["checks"]["headroom_rejections"]["status"] == "PASS"
assert audit["checks"]["headroom_rejections"]["report_check_exit_code"] == 0
assert audit["checks"]["headroom_rejections"]["verdict"] == "PASS"
assert audit["checks"]["headroom_rejections"]["unrecorded_failure_count"] == 0
assert audit["checks"]["headroom_rejections"]["unsupported_registry_rejection_count"] == 0
assert audit["checks"]["min_pair_evidence"]["status"] == "FAIL"
assert audit["checks"]["min_pair_evidence"]["required"] == required
assert audit["checks"]["min_pair_evidence"]["actual_rows"] == actual
assert audit["checks"]["pair_evidence_quality"]["status"] == "PASS"
assert audit["checks"]["pair_trigger_reasons"]["status"] == "PASS"
assert audit["checks"]["pair_trigger_reasons"]["summary_pair_evidence_count"] == actual
assert audit["checks"]["pair_trigger_reasons"]["historical_alias_rows"] == 0
assert audit["checks"]["pair_trigger_reasons"]["rows_match_count"] is True
assert audit["checks"]["pair_evidence_hypothesis_triggers"]["status"] == "PASS"
assert audit["checks"]["pair_evidence_hypothesis_triggers"]["matched_rows"] == actual
PY

node "$ROOT/bin/devlyn.js" benchmark audit \
  --require-hypothesis-trigger \
  --out-dir "$TMP/audit-strict-trigger" \
  > "$TMP/devlyn-benchmark-audit-strict-trigger.out" 2>&1
grep -Fq 'pair_evidence_hypothesis_triggers=PASS matched=4 documented=4 total=4' "$TMP/devlyn-benchmark-audit-strict-trigger.out"
grep -Fq 'PASS audit-pair-evidence' "$TMP/devlyn-benchmark-audit-strict-trigger.out"
if grep -Fq 'pair_evidence_hypothesis_trigger_gaps=' "$TMP/devlyn-benchmark-audit-strict-trigger.out"; then
  echo "strict benchmark audit must not report current hypothesis-trigger gaps" >&2
  cat "$TMP/devlyn-benchmark-audit-strict-trigger.out" >&2
  exit 1
fi
python3 - "$TMP/audit-strict-trigger/audit.json" <<'PY'
import json
import sys

audit = json.load(open(sys.argv[1], encoding="utf8"))
assert audit["verdict"] == "PASS"
assert audit["checks"]["pair_evidence_hypothesis_triggers"]["status"] == "PASS"
assert audit["checks"]["pair_evidence_hypothesis_triggers"]["exit_code"] == 0
assert audit["checks"]["pair_evidence_hypothesis_triggers"]["required"] is True
assert audit["checks"]["pair_evidence_hypothesis_triggers"]["matched_rows"] == 4
assert audit["checks"]["pair_evidence_hypothesis_triggers"]["documented_rows"] == 4
assert audit["checks"]["pair_evidence_hypothesis_triggers"]["total_rows"] == 4
assert audit["checks"]["pair_evidence_hypothesis_triggers"]["gap_details"] == []
PY

node "$ROOT/bin/devlyn.js" benchmark frontier --out-json "$TMP/frontier.json" > "$TMP/devlyn-benchmark-frontier.out" 2>&1
grep -Fq 'fixtures=' "$TMP/devlyn-benchmark-frontier.out"
grep -Fq 'rejected=' "$TMP/devlyn-benchmark-frontier.out"
grep -Fq 'candidates=' "$TMP/devlyn-benchmark-frontier.out"
grep -Fq 'pair_evidence=' "$TMP/devlyn-benchmark-frontier.out"
grep -Fq 'pair_margin_avg=' "$TMP/devlyn-benchmark-frontier.out"
grep -Fq 'PASS pair-candidate-frontier' "$TMP/devlyn-benchmark-frontier.out"
python3 - "$TMP/frontier.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf8"))
assert report["verdict"] in {"PASS", "FAIL"}
assert report["fixtures_total"] >= 1
assert "unmeasured_count" in report
assert "pair_margin_avg" in report
assert "rows" in report
PY

frontier_fail_fixtures="$TMP/frontier-fail-fixtures"
frontier_fail_results="$TMP/frontier-fail-results"
frontier_fail_registry="$TMP/frontier-fail-rejected.sh"
mkdir -p "$frontier_fail_fixtures/F21-cli-scheduler-priority" "$frontier_fail_results"
cat > "$frontier_fail_registry" <<'SH'
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
if node "$ROOT/bin/devlyn.js" benchmark frontier \
  --fixtures-root "$frontier_fail_fixtures" \
  --registry "$frontier_fail_registry" \
  --results-root "$frontier_fail_results" \
  --fail-on-unmeasured \
  --out-json "$TMP/frontier-fail.json" \
  > "$TMP/devlyn-benchmark-frontier-fail.out" 2>&1; then
  echo "benchmark frontier must fail when active unmeasured candidates remain" >&2
  cat "$TMP/devlyn-benchmark-frontier-fail.out" >&2
  exit 1
fi
grep -Fq 'fixtures=1 rejected=0 candidates=1 pair_evidence=0 unmeasured=1 verdict=FAIL' "$TMP/devlyn-benchmark-frontier-fail.out"
grep -Fq 'unmeasured candidate fixture(s): F21-cli-scheduler-priority' "$TMP/devlyn-benchmark-frontier-fail.out"
grep -Fq 'FAIL pair-candidate-frontier' "$TMP/devlyn-benchmark-frontier-fail.out"
python3 - "$TMP/frontier-fail.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf8"))
assert report["verdict"] == "FAIL"
assert report["fixtures_total"] == 1
assert report["candidate_count"] == 1
assert report["unmeasured_count"] == 1
assert report["rows"][0]["status"] == "candidate_unmeasured"
PY

set +e
node "$ROOT/bin/devlyn.js" benchmark frontier \
  --fixtures-root "$frontier_fail_fixtures" \
  --registry "$frontier_fail_registry" \
  --results-root "$frontier_fail_results" \
  --fail-on-unmeasured \
  > "$TMP/devlyn-benchmark-frontier-json-fail.json" \
  2> "$TMP/devlyn-benchmark-frontier-json-fail.stderr"
frontier_json_fail_status=$?
set -e
if [ "$frontier_json_fail_status" -eq 0 ]; then
  echo "benchmark frontier pure JSON failure path must fail" >&2
  exit 1
fi
grep -Fq 'unmeasured candidate fixture(s): F21-cli-scheduler-priority' "$TMP/devlyn-benchmark-frontier-json-fail.stderr"
grep -Fq 'FAIL pair-candidate-frontier' "$TMP/devlyn-benchmark-frontier-json-fail.stderr"
if grep -Fq 'FAIL pair-candidate-frontier' "$TMP/devlyn-benchmark-frontier-json-fail.json"; then
  echo "benchmark frontier pure JSON stdout must not include final text verdict" >&2
  cat "$TMP/devlyn-benchmark-frontier-json-fail.json" >&2
  exit 1
fi
python3 - "$TMP/devlyn-benchmark-frontier-json-fail.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf8"))
assert report["verdict"] == "FAIL"
assert report["fixtures_total"] == 1
assert report["unmeasured_count"] == 1
assert report["rows"][0]["status"] == "candidate_unmeasured"
PY

node "$ROOT/bin/devlyn.js" benchmark suite --dry-run --run-id arg-parse-command-test F0 \
  > "$TMP/devlyn-benchmark-suite.out" 2>&1
grep -Fq '═══ Benchmark Suite Run ═══' "$TMP/devlyn-benchmark-suite.out"
grep -Fq -- '--run-id arg-parse-command-test' "$TMP/devlyn-benchmark-suite.out"

node "$ROOT/bin/devlyn.js" benchmark headroom --help > "$TMP/devlyn-benchmark-headroom-help.out" 2>&1
grep -Fq 'npx devlyn-cli benchmark headroom [options] <fixtures...>' "$TMP/devlyn-benchmark-headroom-help.out"
grep -Fq 'use 3 for F16/F23/F25 proof reruns; audit requires 4 passing evidence rows' "$TMP/devlyn-benchmark-headroom-help.out"
grep -Fq 'npx devlyn-cli benchmark headroom --min-fixtures 3 F16-cli-quote-tax-rules F23-cli-fulfillment-wave F25-cli-cart-promotion-rules' "$TMP/devlyn-benchmark-headroom-help.out"
grep -Fq -- '--min-bare-headroom N' "$TMP/devlyn-benchmark-headroom-help.out"
grep -Fq -- '--min-solo-headroom N' "$TMP/devlyn-benchmark-headroom-help.out"
grep -Fq -- '--allow-rejected-fixtures' "$TMP/devlyn-benchmark-headroom-help.out"
grep -Fq -- '--dry-run' "$TMP/devlyn-benchmark-headroom-help.out"
if grep -Fq 'run-headroom-candidate.sh' "$TMP/devlyn-benchmark-headroom-help.out"; then
  echo "headroom CLI help must not expose internal runner name" >&2
  cat "$TMP/devlyn-benchmark-headroom-help.out" >&2
  exit 1
fi
node "$ROOT/bin/devlyn.js" benchmark pair --help > "$TMP/devlyn-benchmark-pair-help.out" 2>&1
grep -Fq 'npx devlyn-cli benchmark pair [options] <fixtures...>' "$TMP/devlyn-benchmark-pair-help.out"
grep -Fq 'use 3 for F16/F23/F25 proof reruns; audit requires 4 passing evidence rows' "$TMP/devlyn-benchmark-pair-help.out"
grep -Fq 'default: l2_risk_probes; l2_gated is diagnostic' "$TMP/devlyn-benchmark-pair-help.out"
grep -Fq -- '--min-bare-headroom N' "$TMP/devlyn-benchmark-pair-help.out"
grep -Fq -- '--min-solo-headroom N' "$TMP/devlyn-benchmark-pair-help.out"
grep -Fq -- '--max-pair-solo-wall-ratio N  default: 3' "$TMP/devlyn-benchmark-pair-help.out"
grep -Fq -- '--allow-rejected-fixtures' "$TMP/devlyn-benchmark-pair-help.out"
grep -Fq 'npx devlyn-cli benchmark pair --min-fixtures 3 --max-pair-solo-wall-ratio 3 F16-cli-quote-tax-rules F23-cli-fulfillment-wave F25-cli-cart-promotion-rules' "$TMP/devlyn-benchmark-pair-help.out"
grep -Fq -- '--dry-run' "$TMP/devlyn-benchmark-pair-help.out"
if grep -Fq 'run-full-pipeline-pair-candidate.sh' "$TMP/devlyn-benchmark-pair-help.out"; then
  echo "pair CLI help must not expose internal runner name" >&2
  cat "$TMP/devlyn-benchmark-pair-help.out" >&2
  exit 1
fi
grep -Fq 'DEVLYN_BENCHMARK_CLI_SUBCOMMAND: benchmarkMode' "$ROOT/bin/devlyn.js"

expect_fail_contains devlyn-headroom-cli-replay \
  'Command: npx devlyn-cli benchmark headroom --run-id arg-parse-headroom-cli-replay' \
  node "$ROOT/bin/devlyn.js" benchmark headroom \
    --run-id arg-parse-headroom-cli-replay \
    --min-fixtures 2 \
    F999-not-a-fixture

expect_fail_contains devlyn-pair-cli-replay \
  'Command: npx devlyn-cli benchmark pair --run-id arg-parse-pair-cli-replay' \
  node "$ROOT/bin/devlyn.js" benchmark pair \
    --run-id arg-parse-pair-cli-replay \
    --reuse-calibrated-from arg-parse-missing-calibration \
    F21-cli-scheduler-priority

node "$ROOT/bin/devlyn.js" benchmark headroom \
  --run-id arg-parse-headroom-dry-run \
  --dry-run \
  --min-fixtures 1 \
  F21-cli-scheduler-priority > "$TMP/devlyn-headroom-dry-run.out" 2>&1
grep -Fq 'Command: npx devlyn-cli benchmark headroom --run-id arg-parse-headroom-dry-run' "$TMP/devlyn-headroom-dry-run.out"
grep -Fq -- '--min-bare-headroom 5' "$TMP/devlyn-headroom-dry-run.out"
grep -Fq -- '--min-solo-headroom 5' "$TMP/devlyn-headroom-dry-run.out"
grep -Fq -- '--dry-run' "$TMP/devlyn-headroom-dry-run.out"
grep -Fq '[headroom] DRY RUN complete' "$TMP/devlyn-headroom-dry-run.out"

node "$ROOT/bin/devlyn.js" benchmark headroom \
  --run-id arg-parse-shadow-headroom-dry-run \
  --dry-run \
  --min-fixtures 1 \
  S1-cli-lang-flag > "$TMP/devlyn-shadow-headroom-dry-run.out" 2>&1
grep -Fq 'Fixtures: S1-cli-lang-flag' "$TMP/devlyn-shadow-headroom-dry-run.out"
grep -Fq '[headroom] DRY RUN complete' "$TMP/devlyn-shadow-headroom-dry-run.out"

expect_fail_contains smoke-only-s1-cli-headroom \
  "fixture is smoke-only and cannot run providers: S1-cli-lang-flag" \
  node "$ROOT/bin/devlyn.js" benchmark headroom \
    --run-id arg-parse-shadow-headroom-block \
    --min-fixtures 1 \
    S1-cli-lang-flag

node "$ROOT/bin/devlyn.js" benchmark pair \
  --run-id arg-parse-pair-dry-run \
  --dry-run \
  --min-fixtures 1 \
  F21-cli-scheduler-priority > "$TMP/devlyn-pair-dry-run.out" 2>&1
grep -Fq 'Command: npx devlyn-cli benchmark pair --run-id arg-parse-pair-dry-run' "$TMP/devlyn-pair-dry-run.out"
grep -Fq -- '--min-bare-headroom 5' "$TMP/devlyn-pair-dry-run.out"
grep -Fq -- '--min-solo-headroom 5' "$TMP/devlyn-pair-dry-run.out"
grep -Fq -- '--max-pair-solo-wall-ratio 3' "$TMP/devlyn-pair-dry-run.out"
grep -Fq -- '--dry-run' "$TMP/devlyn-pair-dry-run.out"
grep -Fq '[full-pipeline-pair] DRY RUN complete' "$TMP/devlyn-pair-dry-run.out"

node "$ROOT/bin/devlyn.js" benchmark pair \
  --run-id arg-parse-shadow-pair-dry-run \
  --dry-run \
  --min-fixtures 1 \
  S1-cli-lang-flag > "$TMP/devlyn-shadow-pair-dry-run.out" 2>&1
grep -Fq 'Fixtures: S1-cli-lang-flag' "$TMP/devlyn-shadow-pair-dry-run.out"
grep -Fq '[full-pipeline-pair] DRY RUN complete' "$TMP/devlyn-shadow-pair-dry-run.out"

expect_fail_contains smoke-only-s1-cli-pair \
  "fixture is smoke-only and cannot run providers: S1-cli-lang-flag" \
  node "$ROOT/bin/devlyn.js" benchmark pair \
    --run-id arg-parse-shadow-pair-block \
    --min-fixtures 1 \
    S1-cli-lang-flag

bash "$ROOT/benchmark/auto-resolve/scripts/run-fixture.sh" \
  --fixture F1-cli-trivial-flag \
  --arm variant \
  --run-id arg-parse-variant-path \
  --dry-run > "$TMP/variant-dry-run.out" 2>&1
grep -Fq -- '--engine claude --risk-probes' \
  "$BENCH_ROOT/results/arg-parse-variant-path/F1-cli-trivial-flag/variant/input.md"
if grep -Fq -- '--engine auto' \
  "$BENCH_ROOT/results/arg-parse-variant-path/F1-cli-trivial-flag/variant/input.md"; then
  echo "variant arm must not use retired --engine auto route" >&2
  cat "$BENCH_ROOT/results/arg-parse-variant-path/F1-cli-trivial-flag/variant/input.md" >&2
  exit 1
fi
mkdir -p "$BENCH_ROOT/shadow-fixtures"
rm -rf "$BENCH_ROOT/shadow-fixtures/arg-parse-nan-metadata" \
  "$BENCH_ROOT/shadow-fixtures/arg-parse-nan-expected" \
  "$BENCH_ROOT/results/arg-parse-nan-metadata" \
  "$BENCH_ROOT/results/arg-parse-nan-expected"
cp -R "$BENCH_ROOT/fixtures/F1-cli-trivial-flag" "$BENCH_ROOT/shadow-fixtures/arg-parse-nan-metadata"
printf '{"timeout_seconds": NaN}\n' > "$BENCH_ROOT/shadow-fixtures/arg-parse-nan-metadata/metadata.json"
expect_fail_contains fixture-nan-metadata "invalid JSON numeric constant: NaN" \
  bash "$ROOT/benchmark/auto-resolve/scripts/run-fixture.sh" \
    --fixture arg-parse-nan-metadata \
    --arm bare \
    --run-id arg-parse-nan-metadata \
    --dry-run
cp -R "$BENCH_ROOT/fixtures/F1-cli-trivial-flag" "$BENCH_ROOT/shadow-fixtures/arg-parse-nan-expected"
printf '{"verification_commands": NaN}\n' > "$BENCH_ROOT/shadow-fixtures/arg-parse-nan-expected/expected.json"
expect_fail_contains fixture-nan-expected "invalid JSON numeric constant: NaN" \
  bash "$ROOT/benchmark/auto-resolve/scripts/run-fixture.sh" \
    --fixture arg-parse-nan-expected \
    --arm variant \
    --run-id arg-parse-nan-expected \
    --dry-run
rm -rf "$BENCH_ROOT/shadow-fixtures/arg-parse-nan-metadata" \
  "$BENCH_ROOT/shadow-fixtures/arg-parse-nan-expected" \
  "$BENCH_ROOT/results/arg-parse-nan-metadata" \
  "$BENCH_ROOT/results/arg-parse-nan-expected"
grep -Fq 'data = raw_oracle' \
  "$ROOT/benchmark/auto-resolve/scripts/run-fixture.sh"
grep -Fq 'expected = loads_strict_json_object(pathlib.Path(sys.argv[1]).read_text())' \
  "$ROOT/benchmark/auto-resolve/scripts/run-fixture.sh"
grep -Fq 'oracle artifact malformed or unreadable' \
  "$ROOT/benchmark/auto-resolve/scripts/run-fixture.sh"
grep -Fq 'findings = raw_findings if isinstance(raw_findings, list) else []' \
  "$ROOT/benchmark/auto-resolve/scripts/run-fixture.sh"
grep -Fq 'if not isinstance(finding, dict):' \
  "$ROOT/benchmark/auto-resolve/scripts/run-fixture.sh"
grep -Fq 'loads_strict_json_object(pathlib.Path(result_dir, "timing.json").read_text())' \
  "$ROOT/benchmark/auto-resolve/scripts/run-fixture.sh"
grep -Fq 'loads_strict_json_object(pathlib.Path(result_dir, "verify.json").read_text())' \
  "$ROOT/benchmark/auto-resolve/scripts/run-fixture.sh"
grep -Fq 'loads_strict_json_object(pathlib.Path(state_path).read_text())' \
  "$ROOT/benchmark/auto-resolve/scripts/run-fixture.sh"
grep -Fq '"type": "oracle-error"' \
  "$ROOT/benchmark/auto-resolve/scripts/run-fixture.sh"
grep -Fq 'verify["oracle_disqualifier"] = True' \
  "$ROOT/benchmark/auto-resolve/scripts/run-fixture.sh"

SCOPE_REPO="$TMP/scope-repo"
mkdir -p "$SCOPE_REPO"
git -C "$SCOPE_REPO" init -q
git -C "$SCOPE_REPO" config user.email bench@example.com
git -C "$SCOPE_REPO" config user.name bench
printf 'console.log("ok")\n' > "$SCOPE_REPO/app.js"
git -C "$SCOPE_REPO" add app.js
git -C "$SCOPE_REPO" commit -q -m base
SCOPE_SHA="$(git -C "$SCOPE_REPO" rev-parse HEAD)"

cat > "$TMP/expected-nan.json" <<'JSON'
{"tier_a_waivers": NaN, "spec_output_files": ["app.js"]}
JSON
python3 "$ROOT/benchmark/auto-resolve/scripts/oracle-scope-tier-a.py" \
  --work "$SCOPE_REPO" \
  --scaffold "$SCOPE_SHA" \
  --expected "$TMP/expected-nan.json" > "$TMP/scope-tier-a-nan.json"
grep -Fq '"error": "expected.json unreadable: invalid JSON numeric constant: NaN"' \
  "$TMP/scope-tier-a-nan.json"
python3 "$ROOT/benchmark/auto-resolve/scripts/oracle-scope-tier-b.py" \
  --work "$SCOPE_REPO" \
  --scaffold "$SCOPE_SHA" \
  --expected "$TMP/expected-nan.json" > "$TMP/scope-tier-b-nan.json"
grep -Fq '"error": "expected.json unreadable: invalid JSON numeric constant: NaN"' \
  "$TMP/scope-tier-b-nan.json"

cat > "$TMP/expected-bad-tier-c.json" <<'JSON'
{"tier_a_waivers": [], "spec_output_files": "app.js"}
JSON
python3 "$ROOT/benchmark/auto-resolve/scripts/oracle-scope-tier-b.py" \
  --work "$SCOPE_REPO" \
  --scaffold "$SCOPE_SHA" \
  --expected "$TMP/expected-bad-tier-c.json" > "$TMP/scope-tier-b-bad-tier-c.json"
grep -Fq '"error": "expected.json malformed: spec_output_files must be a string array"' \
  "$TMP/scope-tier-b-bad-tier-c.json"

echo "PASS test-benchmark-arg-parsing"
