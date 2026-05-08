#!/usr/bin/env bash
# Regression test for the SWE-bench frozen VERIFY case importer.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

REPO="$TMP/repo"
mkdir -p "$REPO"
git -C "$REPO" init -q
git -C "$REPO" config user.email bench@example.com
git -C "$REPO" config user.name bench
printf 'hello\n' > "$REPO/app.txt"
git -C "$REPO" add app.txt
git -C "$REPO" commit -q -m base
BASE_SHA="$(git -C "$REPO" rev-parse HEAD)"

printf 'goodbye\n' > "$REPO/app.txt"
git -C "$REPO" diff > "$TMP/model.patch"
git -C "$REPO" checkout -q -- app.txt

cat > "$TMP/instance.json" <<JSON
{
  "instance_id": "local__repo-1",
  "repo": "local/repo",
  "base_commit": "$BASE_SHA",
  "problem_statement": "Change app.txt so it says goodbye instead of hello.",
  "version": "test",
  "issue_url": "https://example.test/issue",
  "pr_url": "https://example.test/pr"
}
JSON

python3 "$ROOT/benchmark/auto-resolve/scripts/prepare-swebench-frozen-case.py" \
  --instance-json "$TMP/instance.json" \
  --model-patch "$TMP/model.patch" \
  --cases-root "$TMP/cases" \
  --repos-root "$TMP/repos" \
  --repo-dir "$REPO" \
  --timeout-seconds 60 > "$TMP/prepare.json"

CASE_DIR="$TMP/cases/local__repo-1"
BASE_REPO="$TMP/repos/local__repo-${BASE_SHA:0:12}"
test -f "$CASE_DIR/spec.md"
test -f "$CASE_DIR/model.patch"
test -x "$CASE_DIR/setup.sh"
grep -q 'SWE-bench local__repo-1' "$CASE_DIR/spec.md"
grep -q -- '--pair-mode gated' "$CASE_DIR/run-command.txt"

python3 "$ROOT/benchmark/auto-resolve/scripts/fetch-swebench-instances.py" \
  --dataset lite \
  --limit 1 \
  --out "$TMP/fetched-lite.jsonl" > "$TMP/fetch.json"
grep -q '"rows_written": 1' "$TMP/fetch.json"
python3 - "$TMP/fetched-lite.jsonl" <<'PY'
import json, pathlib, sys
row = json.loads(pathlib.Path(sys.argv[1]).read_text().splitlines()[0])
for key in ("instance_id", "repo", "base_commit", "problem_statement"):
    assert row.get(key), key
PY

python3 - "$TMP/instance.json" "$TMP/instances.jsonl" "$TMP/model.patch" "$TMP/predictions.jsonl" <<'PY'
import json, pathlib, sys
instance = json.loads(pathlib.Path(sys.argv[1]).read_text())
pathlib.Path(sys.argv[2]).write_text(json.dumps(instance) + "\n")
patch = pathlib.Path(sys.argv[3]).read_text()
pathlib.Path(sys.argv[4]).write_text(json.dumps({
    "instance_id": "local__repo-1",
    "model_name_or_path": "local-test",
    "model_patch": patch,
}) + "\n")
PY

mkdir -p "$TMP/patch-root/local__repo-1"
cp "$TMP/model.patch" "$TMP/patch-root/local__repo-1/patch.diff"
python3 "$ROOT/benchmark/auto-resolve/scripts/collect-swebench-predictions.py" \
  --patch-root "$TMP/patch-root" \
  --instances-jsonl "$TMP/instances.jsonl" \
  --model-name local-patch-root \
  --out "$TMP/collected-predictions.jsonl" > "$TMP/collect.json"
grep -q '"predictions_written": 1' "$TMP/collect.json"
python3 - "$TMP/collected-predictions.jsonl" <<'PY'
import json, pathlib, sys
row = json.loads(pathlib.Path(sys.argv[1]).read_text())
assert row["instance_id"] == "local__repo-1"
assert row["model_name_or_path"] == "local-patch-root"
assert row["model_patch"].endswith("\n")
PY

rm -rf "$TMP/cases-batch" "$TMP/repos-batch"
python3 "$ROOT/benchmark/auto-resolve/scripts/prepare-swebench-frozen-corpus.py" \
  --instances-jsonl "$TMP/instances.jsonl" \
  --predictions-jsonl "$TMP/predictions.jsonl" \
  --cases-root "$TMP/cases-batch" \
  --repos-root "$TMP/repos-batch" \
  --repo-dir "$REPO" \
  --out-manifest "$TMP/manifest.json" > "$TMP/batch.json"
grep -q '"prepared_count": 1' "$TMP/manifest.json"
test -f "$TMP/cases-batch/local__repo-1/model.patch"

bash "$ROOT/benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh" \
  --fixture local__repo-1 \
  --fixtures-root "$TMP/cases" \
  --base-repo "$BASE_REPO" \
  --diff "$CASE_DIR/model.patch" \
  --run-id swebench-frozen-case-test \
  --pair-mode gated \
  --timeout-seconds 7 \
  --prepare-only > "$TMP/runner.log"

grep -q 'Timeout: 7s per arm' "$TMP/runner.log"
grep -q '^goodbye$' /tmp/bench-swebench-frozen-case-test-local__repo-1-solo/app.txt
grep -q '^goodbye$' /tmp/bench-swebench-frozen-case-test-local__repo-1-pair/app.txt
test ! -e /tmp/bench-swebench-frozen-case-test-local__repo-1-solo/.devlyn/spec-verify.json
test ! -e /tmp/bench-swebench-frozen-case-test-local__repo-1-pair/.devlyn/spec-verify.json

RESULTS_DIR="$ROOT/benchmark/auto-resolve/results"
RESUME_RUN_ID="swebench-resume-arm-test-local__repo-1"
mkdir -p "$RESULTS_DIR/$RESUME_RUN_ID/solo" "$TMP/fakebin"
cat > "$RESULTS_DIR/$RESUME_RUN_ID/solo/summary.json" <<'EOF'
{
  "elapsed_seconds": 1,
  "invoke_exit": 0,
  "timed_out": false,
  "verify_verdict": "PASS",
  "terminal_verdict": "PASS"
}
EOF
cat > "$TMP/fakebin/claude" <<'EOF'
#!/usr/bin/env bash
echo "fake claude invoked"
exit 1
EOF
chmod +x "$TMP/fakebin/claude"
PATH="$TMP/fakebin:$PATH" bash "$ROOT/benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh" \
  --fixture local__repo-1 \
  --fixtures-root "$TMP/cases" \
  --base-repo "$BASE_REPO" \
  --diff "$CASE_DIR/model.patch" \
  --run-id "$RESUME_RUN_ID" \
  --pair-mode gated \
  --timeout-seconds 3 \
  --resume-completed-arms > "$TMP/resume-arm.log" 2>&1
grep -Fq '[frozen-verify] solo: reuse completed summary' "$TMP/resume-arm.log"
grep -Fq 'fake claude invoked' "$RESULTS_DIR/$RESUME_RUN_ID/pair/transcript.txt"
grep -q '"invoke_exit": 0' "$RESULTS_DIR/$RESUME_RUN_ID/solo/summary.json"

bash "$ROOT/benchmark/auto-resolve/scripts/run-swebench-frozen-corpus.sh" \
  --manifest "$TMP/manifest.json" \
  --run-prefix swebench-frozen-corpus-test \
  --timeout-seconds 7 \
  --run-ids-out "$TMP/prepare-run-ids.txt" \
  --out-json "$TMP/gate.json" \
  --out-md "$TMP/gate.md" \
  --prepare-only > "$TMP/corpus-runner.log"
grep -q 'prepare-only complete; gate skipped' "$TMP/corpus-runner.log"
grep -q 'Timeout: 7s per arm' "$TMP/corpus-runner.log"
grep -q '^swebench-frozen-corpus-test-1-local__repo-1$' "$TMP/prepare-run-ids.txt"
grep -q '^goodbye$' /tmp/bench-swebench-frozen-corpus-test-1-local__repo-1-local__repo-1-solo/app.txt
grep -q '^goodbye$' /tmp/bench-swebench-frozen-corpus-test-1-local__repo-1-local__repo-1-pair/app.txt
test ! -e /tmp/bench-swebench-frozen-corpus-test-1-local__repo-1-local__repo-1-solo/.devlyn/spec-verify.json
test ! -e /tmp/bench-swebench-frozen-corpus-test-1-local__repo-1-local__repo-1-pair/.devlyn/spec-verify.json
test ! -e "$TMP/gate.json"
test ! -e "$TMP/gate.md"

python3 - "$TMP/manifest.json" "$TMP/manifest-bad-diff.json" <<'PY'
import json, pathlib, sys
manifest = json.loads(pathlib.Path(sys.argv[1]).read_text())
manifest["prepared"][0]["case_dir"] = str(pathlib.Path(manifest["prepared"][0]["case_dir"]).parent / "missing-case")
pathlib.Path(sys.argv[2]).write_text(json.dumps(manifest, indent=2) + "\n")
PY
set +e
bash "$ROOT/benchmark/auto-resolve/scripts/run-swebench-frozen-corpus.sh" \
  --manifest "$TMP/manifest-bad-diff.json" \
  --run-prefix swebench-frozen-corpus-fail-test \
  --run-ids-out "$TMP/fail-run-ids.txt" \
  --prepare-only > "$TMP/corpus-fail.log" 2>&1
fail_status=$?
set -e
[ "$fail_status" -ne 0 ]
grep -q 'row failed: swebench-frozen-corpus-fail-test-1-local__repo-1' "$TMP/corpus-fail.log"
grep -q '^swebench-frozen-corpus-fail-test-1-local__repo-1$' "$TMP/fail-run-ids.txt"
test -f "$ROOT/benchmark/auto-resolve/results/swebench-frozen-corpus-fail-test-1-local__repo-1/compare.json"

python3 "$ROOT/benchmark/auto-resolve/scripts/swebench-frozen-matrix.py" \
  --title "Local SWE-bench Failed Matrix" \
  --verdict FAIL \
  --run-id swebench-frozen-corpus-fail-test-1-local__repo-1 \
  --out-json "$TMP/fail-matrix.json" \
  --out-md "$TMP/fail-matrix.md" > "$TMP/fail-matrix.log"
grep -q '"classification": "failed attempt: row runner exit=1"' "$TMP/fail-matrix.json"
grep -q '"trailing_non_gate_rows": 1' "$TMP/fail-matrix.json"
grep -q '"failed attempt: row runner exit=1": 1' "$TMP/fail-matrix.json"
grep -Fq 'failed attempt: row runner exit=1' "$TMP/fail-matrix.md"
grep -Fq 'Trailing non-gate rows: 1' "$TMP/fail-matrix.md"
set +e
python3 "$ROOT/benchmark/auto-resolve/scripts/swebench-frozen-matrix.py" \
  --title "Local SWE-bench Failed Matrix" \
  --verdict FAIL \
  --run-id swebench-frozen-corpus-fail-test-1-local__repo-1 \
  --max-trailing-non-gate 0 \
  --out-json "$TMP/fail-yield-matrix.json" \
  --out-md "$TMP/fail-yield-matrix.md" > "$TMP/fail-yield-matrix.log"
yield_status=$?
set -e
[ "$yield_status" -eq 2 ]
grep -q '"yield_verdict": "FAIL"' "$TMP/fail-yield-matrix.json"
grep -q '"trailing non-gate rows 1 > maximum 0"' "$TMP/fail-yield-matrix.json"
grep -Fq 'Yield verdict: **FAIL**' "$TMP/fail-yield-matrix.md"

PROVIDER_LIMIT_RUN_ID="swebench-provider-limit-test-local__repo-1"
mkdir -p "$RESULTS_DIR/$PROVIDER_LIMIT_RUN_ID/solo" "$RESULTS_DIR/$PROVIDER_LIMIT_RUN_ID/pair"
cat > "$RESULTS_DIR/$PROVIDER_LIMIT_RUN_ID/solo/input.md" <<'EOF'
Use /devlyn:resolve --verify-only --spec docs/roadmap/phase-1/local__repo-1.md.
EOF
cat > "$RESULTS_DIR/$PROVIDER_LIMIT_RUN_ID/pair/transcript.txt" <<'EOF'
You've hit your limit · resets 3am (Asia/Seoul)
EOF
cat > "$RESULTS_DIR/$PROVIDER_LIMIT_RUN_ID/compare.json" <<'EOF'
{
  "solo": {"invoke_exit": 0, "timed_out": false, "verify_verdict": "PASS", "elapsed_seconds": 1},
  "pair": {"invoke_exit": 1, "timed_out": false, "verify_verdict": null, "elapsed_seconds": 1},
  "comparison": {
    "pair_trigger_missed": false,
    "pair_verdict_lift": false,
    "solo_verdict": "PASS",
    "pair_verdict": null
  }
}
EOF
python3 "$ROOT/benchmark/auto-resolve/scripts/swebench-frozen-matrix.py" \
  --title "Local SWE-bench Provider Limit Matrix" \
  --verdict FAIL \
  --run-id "$PROVIDER_LIMIT_RUN_ID" \
  --out-json "$TMP/provider-limit-matrix.json" \
  --out-md "$TMP/provider-limit-matrix.md" > "$TMP/provider-limit-matrix.log"
grep -q '"classification": "failed attempt: provider limit"' "$TMP/provider-limit-matrix.json"
grep -Fq 'failed attempt: provider limit' "$TMP/provider-limit-matrix.md"

RUN_ID="swebench-gate-only-test-local__repo-1"
mkdir -p "$RESULTS_DIR/$RUN_ID/pair"
cat > "$RESULTS_DIR/$RUN_ID/pair/input.md" <<'EOF'
Use /devlyn:resolve --verify-only --spec docs/roadmap/phase-1/local__repo-1.md.
EOF
cat > "$RESULTS_DIR/$RUN_ID/compare.json" <<'EOF'
{
  "solo": {"invoke_exit": 0, "timed_out": false, "verify_verdict": "PASS_WITH_ISSUES", "elapsed_seconds": 100},
  "pair": {"invoke_exit": 0, "timed_out": false, "verify_verdict": "NEEDS_WORK", "pair_mode": true, "elapsed_seconds": 200},
  "comparison": {
    "pair_trigger_missed": false,
    "pair_verdict_lift": true,
    "solo_verdict": "PASS_WITH_ISSUES",
    "pair_verdict": "NEEDS_WORK"
  }
}
EOF
printf '%s\n' "$RUN_ID" > "$TMP/run-ids.txt"
bash "$ROOT/benchmark/auto-resolve/scripts/run-swebench-frozen-corpus.sh" \
  --manifest "$TMP/manifest.json" \
  --gate-only-run-ids "$TMP/run-ids.txt" \
  --min-runs 1 \
  --max-pair-solo-wall-ratio 3 \
  --run-ids-out "$TMP/gate-run-ids.txt" \
  --out-json "$TMP/gate.json" \
  --out-md "$TMP/gate.md" > "$TMP/gate-only.log"
grep -q '"verdict": "PASS"' "$TMP/gate.json"
grep -q '"avg_pair_solo_wall_ratio": 2.0' "$TMP/gate.json"
grep -Fq 'Verdict: **PASS**' "$TMP/gate.md"
grep -Fq 'Max pair/solo wall ratio: 3.00x' "$TMP/gate.md"
cmp "$TMP/run-ids.txt" "$TMP/gate-run-ids.txt"

python3 "$ROOT/benchmark/auto-resolve/scripts/swebench-frozen-matrix.py" \
  --title "Local SWE-bench Matrix" \
  --verdict PASS \
  --gate-json "$TMP/gate.json" \
  --run-id "$RUN_ID" \
  --min-gate-rate 1 \
  --max-trailing-non-gate 0 \
  --out-json "$TMP/matrix.json" \
  --out-md "$TMP/matrix.md" > "$TMP/matrix.log"
grep -q '"runs_total": 1' "$TMP/matrix.json"
grep -q '"gate_rows": 1' "$TMP/matrix.json"
grep -q '"gate_rate": 1.0' "$TMP/matrix.json"
grep -q '"trailing_non_gate_rows": 0' "$TMP/matrix.json"
grep -q '"yield_verdict": "PASS"' "$TMP/matrix.json"
grep -Fq 'Local SWE-bench Matrix' "$TMP/matrix.md"
grep -Fq 'Gate rate: 1.000' "$TMP/matrix.md"
grep -Fq 'Yield verdict: **PASS**' "$TMP/matrix.md"

rm -rf /tmp/bench-swebench-frozen-case-test-local__repo-1-solo
rm -rf /tmp/bench-swebench-frozen-case-test-local__repo-1-pair
rm -rf /tmp/bench-swebench-frozen-corpus-test-1-local__repo-1-local__repo-1-solo
rm -rf /tmp/bench-swebench-frozen-corpus-test-1-local__repo-1-local__repo-1-pair
rm -rf "$ROOT/benchmark/auto-resolve/results/swebench-frozen-case-test"
rm -rf "$ROOT/benchmark/auto-resolve/results/swebench-frozen-corpus-test-1-local__repo-1"
rm -rf "$ROOT/benchmark/auto-resolve/results/swebench-frozen-corpus-fail-test-1-local__repo-1"
rm -rf "$RESULTS_DIR/$RESUME_RUN_ID"
rm -rf "$RESULTS_DIR/$PROVIDER_LIMIT_RUN_ID"
rm -rf "$RESULTS_DIR/$RUN_ID"

echo "PASS test-swebench-frozen-case"
