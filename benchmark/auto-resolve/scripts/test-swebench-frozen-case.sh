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

set +e
python3 "$ROOT/benchmark/auto-resolve/scripts/prepare-swebench-frozen-case.py" \
  --instance-json "$TMP/instance.json" \
  --model-patch "$TMP/model.patch" \
  --cases-root "$TMP/cases-bad-timeout" \
  --repos-root "$TMP/repos-bad-timeout" \
  --repo-dir "$REPO" \
  --timeout-seconds 0 > "$TMP/prepare-bad-timeout.log" 2>&1
bad_timeout_status=$?
set -e
[ "$bad_timeout_status" -ne 0 ]
grep -Fq 'must be > 0' "$TMP/prepare-bad-timeout.log"

python3 - "$TMP/instance.json" "$TMP/instance-bad-repo.json" "$TMP/instance-bad-base.json" <<'PY'
import json, pathlib, sys
instance = json.loads(pathlib.Path(sys.argv[1]).read_text())
bad_repo = dict(instance, repo="../bad/repo")
bad_base = dict(instance, base_commit="../bad")
pathlib.Path(sys.argv[2]).write_text(json.dumps(bad_repo) + "\n")
pathlib.Path(sys.argv[3]).write_text(json.dumps(bad_base) + "\n")
PY
set +e
python3 "$ROOT/benchmark/auto-resolve/scripts/prepare-swebench-frozen-case.py" \
  --instance-json "$TMP/instance-bad-repo.json" \
  --model-patch "$TMP/model.patch" \
  --cases-root "$TMP/cases-bad-repo" \
  --repos-root "$TMP/repos-bad-repo" \
  --repo-dir "$REPO" > "$TMP/prepare-bad-repo.log" 2>&1
bad_repo_status=$?
set -e
[ "$bad_repo_status" -ne 0 ]
grep -Fq 'unsafe SWE-bench repo' "$TMP/prepare-bad-repo.log"

set +e
python3 "$ROOT/benchmark/auto-resolve/scripts/prepare-swebench-frozen-case.py" \
  --instance-json "$TMP/instance-bad-base.json" \
  --model-patch "$TMP/model.patch" \
  --cases-root "$TMP/cases-bad-base" \
  --repos-root "$TMP/repos-bad-base" \
  --repo-dir "$REPO" > "$TMP/prepare-bad-base.log" 2>&1
bad_base_status=$?
set -e
[ "$bad_base_status" -ne 0 ]
grep -Fq 'unsafe SWE-bench base_commit' "$TMP/prepare-bad-base.log"

cat > "$TMP/instance-nan-case.json" <<JSON
{
  "instance_id": "local__repo-1",
  "repo": NaN,
  "base_commit": "$BASE_SHA",
  "problem_statement": "Change app.txt."
}
JSON
set +e
python3 "$ROOT/benchmark/auto-resolve/scripts/prepare-swebench-frozen-case.py" \
  --instance-json "$TMP/instance-nan-case.json" \
  --model-patch "$TMP/model.patch" \
  --cases-root "$TMP/cases-nan-case" \
  --repos-root "$TMP/repos-nan-case" \
  --repo-dir "$REPO" > "$TMP/prepare-nan-case.log" 2>&1
prepare_nan_case_status=$?
set -e
[ "$prepare_nan_case_status" -ne 0 ]
grep -Fq 'invalid JSON numeric constant: NaN' "$TMP/prepare-nan-case.log"

set +e
python3 "$ROOT/benchmark/auto-resolve/scripts/prepare-swebench-solver-worktree.py" \
  --instances-jsonl "$TMP/instance-bad-repo.json" \
  --instance-id local__repo-1 \
  --repos-root "$TMP/repos-solver-bad-repo" \
  --worktrees-root "$TMP/worktrees-bad-repo" > "$TMP/solver-bad-repo.log" 2>&1
solver_bad_repo_status=$?
set -e
[ "$solver_bad_repo_status" -ne 0 ]
grep -Fq 'unsafe SWE-bench repo' "$TMP/solver-bad-repo.log"

set +e
python3 "$ROOT/benchmark/auto-resolve/scripts/prepare-swebench-solver-worktree.py" \
  --instances-jsonl "$TMP/instance-bad-base.json" \
  --instance-id local__repo-1 \
  --repos-root "$TMP/repos-solver-bad-base" \
  --worktrees-root "$TMP/worktrees-bad-base" > "$TMP/solver-bad-base.log" 2>&1
solver_bad_base_status=$?
set -e
[ "$solver_bad_base_status" -ne 0 ]
grep -Fq 'unsafe SWE-bench base_commit' "$TMP/solver-bad-base.log"

cat > "$TMP/instance-nan-solver.jsonl" <<'EOF'
{"instance_id": "local__repo-1", "repo": NaN, "base_commit": "abc123", "problem_statement": "Change app.txt."}
EOF
set +e
python3 "$ROOT/benchmark/auto-resolve/scripts/prepare-swebench-solver-worktree.py" \
  --instances-jsonl "$TMP/instance-nan-solver.jsonl" \
  --instance-id local__repo-1 \
  --repos-root "$TMP/repos-solver-nan" \
  --worktrees-root "$TMP/worktrees-nan" > "$TMP/solver-nan.log" 2>&1
solver_nan_status=$?
set -e
[ "$solver_nan_status" -ne 0 ]
grep -Fq 'invalid JSON numeric constant: NaN' "$TMP/solver-nan.log"

python3 - "$ROOT/benchmark/auto-resolve/scripts/fetch-swebench-instances.py" "$TMP/fetched-lite.jsonl" > "$TMP/fetch.json" <<'PY'
import importlib.util
import pathlib
import sys

script = pathlib.Path(sys.argv[1])
out = pathlib.Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("fetch_swebench_instances", script)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.path.insert(0, str(script.parent))
spec.loader.exec_module(module)

def fake_fetch_rows(dataset, split, offset, length):
    assert dataset == "princeton-nlp/SWE-bench_Lite"
    assert split == "test"
    assert offset == 0
    assert length == 1
    return {
        "num_rows_total": 1,
        "rows": [
            {
                "row": {
                    "instance_id": "local__repo-1",
                    "repo": "local/repo",
                    "base_commit": "abc123",
                    "problem_statement": "Change app.txt.",
                }
            }
        ],
    }

module.fetch_rows = fake_fetch_rows
sys.argv = [
    "fetch-swebench-instances.py",
    "--dataset",
    "lite",
    "--limit",
    "1",
    "--out",
    str(out),
]
raise SystemExit(module.main())
PY
grep -q '"rows_written": 1' "$TMP/fetch.json"
python3 - "$TMP/fetched-lite.jsonl" <<'PY'
import json, pathlib, sys
row = json.loads(pathlib.Path(sys.argv[1]).read_text().splitlines()[0])
for key in ("instance_id", "repo", "base_commit", "problem_statement"):
    assert row.get(key), key
PY

python3 - "$ROOT/benchmark/auto-resolve/scripts/fetch-swebench-instances.py" <<'PY'
import importlib.util
import pathlib
import sys

script = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("fetch_swebench_instances", script)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.path.insert(0, str(script.parent))
spec.loader.exec_module(module)

def fake_fetch_rows(dataset, split, offset, length):
    return {
        "num_rows_total": 1,
        "rows": [{"row": ["not", "an", "object"]}],
    }

module.fetch_rows = fake_fetch_rows
sys.argv = [
    "fetch-swebench-instances.py",
    "--dataset",
    "lite",
    "--limit",
    "1",
    "--out",
    "/tmp/fetch-malformed-row.jsonl",
]
try:
    module.main()
except ValueError as exc:
    assert "malformed fetched row 1: row must be object" in str(exc), str(exc)
else:
    raise AssertionError("malformed fetched row was accepted")
PY

set +e
python3 "$ROOT/benchmark/auto-resolve/scripts/fetch-swebench-instances.py" \
  --dataset lite \
  --limit 0 \
  --out "$TMP/fetched-empty-limit.jsonl" > "$TMP/fetch-empty-limit.log" 2>&1
fetch_empty_limit_status=$?
set -e
[ "$fetch_empty_limit_status" -ne 0 ]
grep -Fq 'must be > 0' "$TMP/fetch-empty-limit.log"

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

python3 - "$TMP/instance.json" "$TMP/instances-with-missing.jsonl" <<'PY'
import json, pathlib, sys
instance = json.loads(pathlib.Path(sys.argv[1]).read_text())
missing = dict(instance, instance_id="local__repo-missing")
pathlib.Path(sys.argv[2]).write_text(json.dumps(instance) + "\n" + json.dumps(missing) + "\n")
PY
set +e
python3 "$ROOT/benchmark/auto-resolve/scripts/collect-swebench-predictions.py" \
  --patch-root "$TMP/patch-root" \
  --instances-jsonl "$TMP/instances-with-missing.jsonl" \
  --model-name local-patch-root \
  --out "$TMP/collected-missing-predictions.jsonl" > "$TMP/collect-missing.log" 2>&1
collect_missing_status=$?
set -e
[ "$collect_missing_status" -ne 0 ]
grep -q 'missing patch.diff for instance ids: local__repo-missing' "$TMP/collect-missing.log"

mkdir -p "$TMP/patch-root-empty/local__repo-1"
: > "$TMP/patch-root-empty/local__repo-1/patch.diff"
set +e
python3 "$ROOT/benchmark/auto-resolve/scripts/collect-swebench-predictions.py" \
  --patch-root "$TMP/patch-root-empty" \
  --instances-jsonl "$TMP/instances.jsonl" \
  --model-name local-patch-root \
  --out "$TMP/collected-empty-predictions.jsonl" \
  --allow-empty > "$TMP/collect-empty.log" 2>&1
collect_empty_status=$?
set -e
[ "$collect_empty_status" -ne 0 ]
grep -q 'no non-empty patches collected' "$TMP/collect-empty.log"

cat > "$TMP/instances-nan.jsonl" <<'EOF'
{"instance_id": NaN, "repo": "local/repo", "base_commit": "abc123", "problem_statement": "Change app.txt."}
EOF
set +e
python3 "$ROOT/benchmark/auto-resolve/scripts/collect-swebench-predictions.py" \
  --patch-root "$TMP/patch-root" \
  --instances-jsonl "$TMP/instances-nan.jsonl" \
  --model-name local-patch-root \
  --out "$TMP/collected-nan-instances.jsonl" > "$TMP/collect-nan-instances.log" 2>&1
collect_nan_instances_status=$?
set -e
[ "$collect_nan_instances_status" -ne 0 ]
grep -Fq 'invalid JSON numeric constant: NaN' "$TMP/collect-nan-instances.log"

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

set +e
python3 "$ROOT/benchmark/auto-resolve/scripts/prepare-swebench-frozen-corpus.py" \
  --instances-jsonl "$TMP/instances.jsonl" \
  --predictions-jsonl "$TMP/predictions.jsonl" \
  --cases-root "$TMP/cases-batch-empty-limit" \
  --repos-root "$TMP/repos-batch-empty-limit" \
  --repo-dir "$REPO" \
  --limit 0 > "$TMP/batch-empty-limit.log" 2>&1
batch_empty_limit_status=$?
set -e
[ "$batch_empty_limit_status" -ne 0 ]
grep -Fq 'must be > 0' "$TMP/batch-empty-limit.log"

touch "$TMP/empty-predictions.jsonl"
set +e
python3 "$ROOT/benchmark/auto-resolve/scripts/prepare-swebench-frozen-corpus.py" \
  --instances-jsonl "$TMP/instances.jsonl" \
  --predictions-jsonl "$TMP/empty-predictions.jsonl" \
  --cases-root "$TMP/cases-batch-empty-predictions" \
  --repos-root "$TMP/repos-batch-empty-predictions" \
  --repo-dir "$REPO" > "$TMP/batch-empty-predictions.log" 2>&1
batch_empty_predictions_status=$?
set -e
[ "$batch_empty_predictions_status" -ne 0 ]
grep -q 'no prediction instances selected' "$TMP/batch-empty-predictions.log"

set +e
python3 "$ROOT/benchmark/auto-resolve/scripts/prepare-swebench-frozen-corpus.py" \
  --instances-jsonl "$TMP/instances.jsonl" \
  --predictions-jsonl "$TMP/predictions.jsonl" \
  --cases-root "$TMP/cases-batch-bad-timeout" \
  --repos-root "$TMP/repos-batch-bad-timeout" \
  --repo-dir "$REPO" \
  --timeout-seconds 0 > "$TMP/batch-bad-timeout.log" 2>&1
batch_bad_timeout_status=$?
set -e
[ "$batch_bad_timeout_status" -ne 0 ]
grep -Fq 'must be > 0' "$TMP/batch-bad-timeout.log"

cat > "$TMP/predictions-nan.jsonl" <<'EOF'
{"instance_id": "local__repo-1", "model_name_or_path": "local-test", "model_patch": NaN}
EOF
set +e
python3 "$ROOT/benchmark/auto-resolve/scripts/prepare-swebench-frozen-corpus.py" \
  --instances-jsonl "$TMP/instances.jsonl" \
  --predictions-jsonl "$TMP/predictions-nan.jsonl" \
  --cases-root "$TMP/cases-batch-nan-predictions" \
  --repos-root "$TMP/repos-batch-nan-predictions" \
  --repo-dir "$REPO" > "$TMP/batch-nan-predictions.log" 2>&1
batch_nan_predictions_status=$?
set -e
[ "$batch_nan_predictions_status" -ne 0 ]
grep -Fq 'invalid JSON numeric constant: NaN' "$TMP/batch-nan-predictions.log"

python3 - "$ROOT/benchmark/auto-resolve/scripts/prepare-swebench-frozen-corpus.py" <<'PY'
import importlib.util
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(path.parent))
spec = importlib.util.spec_from_file_location("prepare_swebench_frozen_corpus", path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

for stdout, expected in [
    ("[]", "expected JSON object"),
    ('{"instance_id": NaN}', "invalid JSON numeric constant: NaN"),
    ('{"instance_id":"x","case_dir":"c","repo_dir":"r","run_command":[]}', "missing non-empty 'run_command'"),
]:
    try:
        module.parse_prepared_case(stdout, "child")
    except ValueError as exc:
        assert expected in str(exc), str(exc)
    else:
        raise AssertionError(f"expected ValueError for {stdout}")
PY

bash "$ROOT/benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh" \
  --fixture local__repo-1 \
  --fixtures-root "$TMP/cases" \
  --base-repo "$BASE_REPO" \
  --diff "$CASE_DIR/model.patch" \
  --run-id swebench-frozen-case-test \
  --pair-mode gated \
  --timeout-seconds 7 \
  --prepare-only > "$TMP/runner.log"

grep -Fq 'Command: ' "$TMP/runner.log"
grep -Fq '# Frozen VERIFY Pair Summary' "$TMP/runner.log"
grep -q 'Timeout: 7s per arm' "$TMP/runner.log"
test -f "$ROOT/benchmark/auto-resolve/results/swebench-frozen-case-test/compare.md"
grep -Fq '| Arm | Verdict | Pair mode | Triggers | Findings | Elapsed | Invoke exit | Failure |' \
  "$ROOT/benchmark/auto-resolve/results/swebench-frozen-case-test/compare.md"
grep -Fq '| pair |' "$ROOT/benchmark/auto-resolve/results/swebench-frozen-case-test/compare.md"
grep -q '^goodbye$' /tmp/bench-swebench-frozen-case-test-local__repo-1-solo/app.txt
grep -q '^goodbye$' /tmp/bench-swebench-frozen-case-test-local__repo-1-pair/app.txt
test ! -e /tmp/bench-swebench-frozen-case-test-local__repo-1-solo/.devlyn/spec-verify.json
test ! -e /tmp/bench-swebench-frozen-case-test-local__repo-1-pair/.devlyn/spec-verify.json

cp -R "$CASE_DIR" "$TMP/cases/local__repo-1-nan-metadata"
cat > "$TMP/cases/local__repo-1-nan-metadata/metadata.json" <<'EOF'
{"timeout_seconds": NaN}
EOF
set +e
bash "$ROOT/benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh" \
  --fixture local__repo-1-nan-metadata \
  --fixtures-root "$TMP/cases" \
  --base-repo "$BASE_REPO" \
  --diff "$CASE_DIR/model.patch" \
  --prepare-only > "$TMP/runner-nan-metadata.log" 2>&1
runner_nan_metadata_status=$?
set -e
[ "$runner_nan_metadata_status" -ne 0 ]
grep -Fq 'invalid JSON numeric constant: NaN' "$TMP/runner-nan-metadata.log"

cp -R "$CASE_DIR" "$TMP/cases/local__repo-1-nan-expected"
cat > "$TMP/cases/local__repo-1-nan-expected/expected.json" <<'EOF'
{"verification_commands": NaN}
EOF
set +e
bash "$ROOT/benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh" \
  --fixture local__repo-1-nan-expected \
  --fixtures-root "$TMP/cases" \
  --base-repo "$BASE_REPO" \
  --diff "$CASE_DIR/model.patch" \
  --prepare-only > "$TMP/runner-nan-expected.log" 2>&1
runner_nan_expected_status=$?
set -e
[ "$runner_nan_expected_status" -ne 0 ]
grep -Fq 'invalid JSON numeric constant: NaN' "$TMP/runner-nan-expected.log"

set +e
bash "$ROOT/benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh" \
  --fixture > "$TMP/runner-missing-value.log" 2>&1
runner_missing_value_status=$?
set -e
[ "$runner_missing_value_status" -ne 0 ]
grep -Fq -- '--fixture requires a value' "$TMP/runner-missing-value.log"

set +e
bash "$ROOT/benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh" \
  --fixture '../bad' \
  --fixtures-root "$TMP/cases" \
  --base-repo "$BASE_REPO" \
  --diff "$CASE_DIR/model.patch" \
  --prepare-only > "$TMP/runner-unsafe-fixture.log" 2>&1
runner_unsafe_fixture_status=$?
set -e
[ "$runner_unsafe_fixture_status" -ne 0 ]
grep -Fq -- '--fixture must match [A-Za-z0-9_.-]+' "$TMP/runner-unsafe-fixture.log"

set +e
bash "$ROOT/benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh" \
  --fixture local__repo-1 \
  --fixtures-root "$TMP/cases" \
  --base-repo "$BASE_REPO" \
  --diff "$CASE_DIR/model.patch" \
  --run-id '../bad-run' \
  --prepare-only > "$TMP/runner-unsafe-run-id.log" 2>&1
runner_unsafe_run_id_status=$?
set -e
[ "$runner_unsafe_run_id_status" -ne 0 ]
grep -Fq -- '--run-id must match [A-Za-z0-9_.-]+' "$TMP/runner-unsafe-run-id.log"

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

BOOL_ELAPSED_RUN_ID="swebench-bool-elapsed-test-local__repo-1"
mkdir -p "$RESULTS_DIR/$BOOL_ELAPSED_RUN_ID/solo" "$RESULTS_DIR/$BOOL_ELAPSED_RUN_ID/pair"
cat > "$RESULTS_DIR/$BOOL_ELAPSED_RUN_ID/solo/summary.json" <<'EOF'
{
  "elapsed_seconds": true,
  "invoke_exit": 0,
  "timed_out": false,
  "verify_verdict": "PASS_WITH_ISSUES",
  "terminal_verdict": "PASS"
}
EOF
cat > "$RESULTS_DIR/$BOOL_ELAPSED_RUN_ID/pair/summary.json" <<'EOF'
{
  "elapsed_seconds": false,
  "invoke_exit": 0,
  "timed_out": false,
  "verify_verdict": "NEEDS_WORK",
  "terminal_verdict": "PASS",
  "pair_mode": true,
  "sub_verdicts": {"judge": "PASS_WITH_ISSUES", "pair_judge": "NEEDS_WORK"}
}
EOF
bash "$ROOT/benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh" \
  --fixture local__repo-1 \
  --fixtures-root "$TMP/cases" \
  --base-repo "$BASE_REPO" \
  --diff "$CASE_DIR/model.patch" \
  --run-id "$BOOL_ELAPSED_RUN_ID" \
  --pair-mode gated \
  --timeout-seconds 3 \
  --resume-completed-arms > "$TMP/bool-elapsed-runner.log" 2>&1
grep -Fq '[frozen-verify] solo: reuse completed summary' "$TMP/bool-elapsed-runner.log"
grep -q '"pair_solo_wall_ratio": null' "$RESULTS_DIR/$BOOL_ELAPSED_RUN_ID/compare.json"
grep -Fq '| n/a |' "$RESULTS_DIR/$BOOL_ELAPSED_RUN_ID/compare.md"

MALFORMED_PAIR_JUDGE_RUN_ID="swebench-malformed-pair-judge-test-local__repo-1"
mkdir -p "$RESULTS_DIR/$MALFORMED_PAIR_JUDGE_RUN_ID/solo" "$RESULTS_DIR/$MALFORMED_PAIR_JUDGE_RUN_ID/pair"
cat > "$RESULTS_DIR/$MALFORMED_PAIR_JUDGE_RUN_ID/solo/summary.json" <<'EOF'
{
  "elapsed_seconds": 100,
  "invoke_exit": 0,
  "timed_out": false,
  "verify_verdict": "PASS_WITH_ISSUES",
  "terminal_verdict": "PASS"
}
EOF
cat > "$RESULTS_DIR/$MALFORMED_PAIR_JUDGE_RUN_ID/pair/summary.json" <<'EOF'
{
  "elapsed_seconds": 150,
  "invoke_exit": 0,
  "timed_out": false,
  "verify_verdict": "NEEDS_WORK",
  "terminal_verdict": "PASS",
  "pair_mode": false,
  "sub_verdicts": {"judge": "PASS_WITH_ISSUES", "pair_judge": ""}
}
EOF
bash "$ROOT/benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh" \
  --fixture local__repo-1 \
  --fixtures-root "$TMP/cases" \
  --base-repo "$BASE_REPO" \
  --diff "$CASE_DIR/model.patch" \
  --run-id "$MALFORMED_PAIR_JUDGE_RUN_ID" \
  --pair-mode gated \
  --timeout-seconds 3 \
  --resume-completed-arms > "$TMP/malformed-pair-judge-runner.log" 2>&1
grep -q '"pair_mode": false' "$RESULTS_DIR/$MALFORMED_PAIR_JUDGE_RUN_ID/compare.json"
grep -q '"pair_verdict_lift": false' "$RESULTS_DIR/$MALFORMED_PAIR_JUDGE_RUN_ID/compare.json"
grep -q '"pair_internal_verdict_lift": false' "$RESULTS_DIR/$MALFORMED_PAIR_JUDGE_RUN_ID/compare.json"

MALFORMED_PAIR_TRIGGER_RUN_ID="swebench-malformed-pair-trigger-test-local__repo-1"
mkdir -p "$RESULTS_DIR/$MALFORMED_PAIR_TRIGGER_RUN_ID/solo" "$RESULTS_DIR/$MALFORMED_PAIR_TRIGGER_RUN_ID/pair"
cat > "$RESULTS_DIR/$MALFORMED_PAIR_TRIGGER_RUN_ID/solo/summary.json" <<'EOF'
{
  "elapsed_seconds": 100,
  "invoke_exit": 0,
  "timed_out": false,
  "verify_verdict": "PASS_WITH_ISSUES",
  "terminal_verdict": "PASS",
  "verify_findings_count": 1,
  "severity_counts": {"LOW": 1, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
}
EOF
cat > "$RESULTS_DIR/$MALFORMED_PAIR_TRIGGER_RUN_ID/pair/summary.json" <<'EOF'
{
  "elapsed_seconds": 150,
  "invoke_exit": 0,
  "timed_out": false,
  "verify_verdict": "PASS_WITH_ISSUES",
  "terminal_verdict": "PASS",
  "pair_mode": false,
  "pair_trigger": "eligible",
  "verify_findings_count": "2",
  "severity_counts": "bad"
}
EOF
bash "$ROOT/benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh" \
  --fixture local__repo-1 \
  --fixtures-root "$TMP/cases" \
  --base-repo "$BASE_REPO" \
  --diff "$CASE_DIR/model.patch" \
  --run-id "$MALFORMED_PAIR_TRIGGER_RUN_ID" \
  --pair-mode gated \
  --timeout-seconds 3 \
  --resume-completed-arms > "$TMP/malformed-pair-trigger-runner.log" 2>&1
grep -q '"pair_trigger_missed": false' "$RESULTS_DIR/$MALFORMED_PAIR_TRIGGER_RUN_ID/compare.json"
grep -q '"pair_found_more_findings": false' "$RESULTS_DIR/$MALFORMED_PAIR_TRIGGER_RUN_ID/compare.json"
grep -q '"pair_found_more_low_or_worse": false' "$RESULTS_DIR/$MALFORMED_PAIR_TRIGGER_RUN_ID/compare.json"
python3 "$ROOT/benchmark/auto-resolve/scripts/swebench-frozen-matrix.py" \
  --results-root "$RESULTS_DIR" \
  --title "Malformed Trigger Matrix" \
  --verdict FAIL \
  --run-id "$MALFORMED_PAIR_TRIGGER_RUN_ID" \
  --out-json "$TMP/malformed-trigger-matrix.json" \
  --out-md "$TMP/malformed-trigger-matrix.md" > "$TMP/malformed-trigger-matrix.log"
grep -q '"pair_trigger_eligible": false' "$TMP/malformed-trigger-matrix.json"
grep -Fq '"pair_trigger_failures": [' "$TMP/malformed-trigger-matrix.json"
grep -q '"pair_trigger missing or malformed"' "$TMP/malformed-trigger-matrix.json"
grep -q '"classification": "failed attempt: pair trigger contract: pair_trigger missing or malformed"' "$TMP/malformed-trigger-matrix.json"
grep -Fq '| Fixture | Solo VERIFY | Pair VERIFY | Pair mode | Pair trigger | Triggers | Wall ratio | External lift | Internal lift | Included | Classification |' "$TMP/malformed-trigger-matrix.md"
grep -Fq '| unknown | PASS_WITH_ISSUES | PASS_WITH_ISSUES | false | malformed |' "$TMP/malformed-trigger-matrix.md"

UNKNOWN_PAIR_TRIGGER_RUN_ID="swebench-unknown-pair-trigger-test-local__repo-1"
mkdir -p "$RESULTS_DIR/$UNKNOWN_PAIR_TRIGGER_RUN_ID/pair"
cat > "$RESULTS_DIR/$UNKNOWN_PAIR_TRIGGER_RUN_ID/pair/input.md" <<'EOF'
Use /devlyn:resolve --verify-only --spec docs/roadmap/phase-1/local__repo-1.md.
EOF
cat > "$RESULTS_DIR/$UNKNOWN_PAIR_TRIGGER_RUN_ID/compare.json" <<'EOF'
{
  "solo": {"invoke_exit": 0, "timed_out": false, "verify_verdict": "PASS_WITH_ISSUES", "elapsed_seconds": 100},
  "pair": {
    "invoke_exit": 0,
    "timed_out": false,
    "verify_verdict": "NEEDS_WORK",
    "pair_mode": true,
    "pair_trigger": {"eligible": true, "reasons": ["looks-hard"], "skipped_reason": null},
    "elapsed_seconds": 200
  },
  "comparison": {
    "pair_trigger_missed": false,
    "pair_verdict_lift": true,
    "solo_verdict": "PASS_WITH_ISSUES",
    "pair_verdict": "NEEDS_WORK"
  }
}
EOF
python3 "$ROOT/benchmark/auto-resolve/scripts/swebench-frozen-matrix.py" \
  --results-root "$RESULTS_DIR" \
  --title "Unknown Trigger Matrix" \
  --verdict FAIL \
  --run-id "$UNKNOWN_PAIR_TRIGGER_RUN_ID" \
  --out-json "$TMP/unknown-trigger-matrix.json" \
  --out-md "$TMP/unknown-trigger-matrix.md" > "$TMP/unknown-trigger-matrix.log"
grep -q '"pair_trigger_eligible": false' "$TMP/unknown-trigger-matrix.json"
grep -q '"pair_trigger reasons missing known trigger reason"' "$TMP/unknown-trigger-matrix.json"
grep -q '"classification": "failed attempt: pair trigger contract: pair_trigger reasons missing known trigger reason"' "$TMP/unknown-trigger-matrix.json"
grep -Fq '| local__repo-1 | PASS_WITH_ISSUES | NEEDS_WORK | true | malformed |' "$TMP/unknown-trigger-matrix.md"

NORMALIZED_PAIR_TRIGGER_RUN_ID="swebench-normalized-pair-trigger-test-local__repo-1"
mkdir -p "$RESULTS_DIR/$NORMALIZED_PAIR_TRIGGER_RUN_ID/pair"
cat > "$RESULTS_DIR/$NORMALIZED_PAIR_TRIGGER_RUN_ID/pair/input.md" <<'EOF'
Use /devlyn:resolve --verify-only --spec docs/roadmap/phase-1/local__repo-1.md.
EOF
cat > "$RESULTS_DIR/$NORMALIZED_PAIR_TRIGGER_RUN_ID/compare.json" <<'EOF'
{
  "solo": {"invoke_exit": 0, "timed_out": false, "verify_verdict": "PASS_WITH_ISSUES", "elapsed_seconds": 100},
  "pair": {
    "invoke_exit": 0,
    "timed_out": false,
    "verify_verdict": "NEEDS_WORK",
    "pair_mode": true,
    "pair_trigger": {"eligible": true, "reasons": ["risk high"], "skipped_reason": null},
    "elapsed_seconds": 200
  },
  "comparison": {
    "pair_trigger_missed": false,
    "pair_verdict_lift": true,
    "solo_verdict": "PASS_WITH_ISSUES",
    "pair_verdict": "NEEDS_WORK"
  }
}
EOF
python3 "$ROOT/benchmark/auto-resolve/scripts/swebench-frozen-matrix.py" \
  --results-root "$RESULTS_DIR" \
  --title "Normalized Trigger Matrix" \
  --verdict FAIL \
  --run-id "$NORMALIZED_PAIR_TRIGGER_RUN_ID" \
  --out-json "$TMP/normalized-trigger-matrix.json" \
  --out-md "$TMP/normalized-trigger-matrix.md" > "$TMP/normalized-trigger-matrix.log"
grep -q '"pair_trigger_eligible": false' "$TMP/normalized-trigger-matrix.json"
grep -q '"pair_trigger reasons missing known trigger reason"' "$TMP/normalized-trigger-matrix.json"
grep -q '"classification": "failed attempt: pair trigger contract: pair_trigger reasons missing known trigger reason"' "$TMP/normalized-trigger-matrix.json"
grep -Fq '| local__repo-1 | PASS_WITH_ISSUES | NEEDS_WORK | true | malformed |' "$TMP/normalized-trigger-matrix.md"

MIXED_UNKNOWN_PAIR_TRIGGER_RUN_ID="swebench-mixed-unknown-pair-trigger-test-local__repo-1"
mkdir -p "$RESULTS_DIR/$MIXED_UNKNOWN_PAIR_TRIGGER_RUN_ID/pair"
cat > "$RESULTS_DIR/$MIXED_UNKNOWN_PAIR_TRIGGER_RUN_ID/pair/input.md" <<'EOF'
Use /devlyn:resolve --verify-only --spec docs/roadmap/phase-1/local__repo-1.md.
EOF
cat > "$RESULTS_DIR/$MIXED_UNKNOWN_PAIR_TRIGGER_RUN_ID/compare.json" <<'EOF'
{
  "solo": {"invoke_exit": 0, "timed_out": false, "verify_verdict": "PASS_WITH_ISSUES", "elapsed_seconds": 100},
  "pair": {
    "invoke_exit": 0,
    "timed_out": false,
    "verify_verdict": "NEEDS_WORK",
    "pair_mode": true,
    "pair_trigger": {"eligible": true, "reasons": ["mode.verify-only", "looks-hard"], "skipped_reason": null},
    "elapsed_seconds": 200
  },
  "comparison": {
    "pair_trigger_missed": false,
    "pair_verdict_lift": true,
    "solo_verdict": "PASS_WITH_ISSUES",
    "pair_verdict": "NEEDS_WORK"
  }
}
EOF
python3 "$ROOT/benchmark/auto-resolve/scripts/swebench-frozen-matrix.py" \
  --results-root "$RESULTS_DIR" \
  --title "Mixed Unknown Trigger Matrix" \
  --verdict FAIL \
  --run-id "$MIXED_UNKNOWN_PAIR_TRIGGER_RUN_ID" \
  --out-json "$TMP/mixed-unknown-trigger-matrix.json" \
  --out-md "$TMP/mixed-unknown-trigger-matrix.md" > "$TMP/mixed-unknown-trigger-matrix.log"
grep -q '"pair_trigger_eligible": false' "$TMP/mixed-unknown-trigger-matrix.json"
grep -q '"pair_trigger reasons contain unknown trigger reason"' "$TMP/mixed-unknown-trigger-matrix.json"
grep -q '"classification": "failed attempt: pair trigger contract: pair_trigger reasons contain unknown trigger reason"' "$TMP/mixed-unknown-trigger-matrix.json"
grep -Fq '| local__repo-1 | PASS_WITH_ISSUES | NEEDS_WORK | true | malformed |' "$TMP/mixed-unknown-trigger-matrix.md"

HISTORICAL_ONLY_TRIGGER_RUN_ID="swebench-historical-only-pair-trigger-test-local__repo-1"
mkdir -p "$RESULTS_DIR/$HISTORICAL_ONLY_TRIGGER_RUN_ID/pair"
cat > "$RESULTS_DIR/$HISTORICAL_ONLY_TRIGGER_RUN_ID/pair/input.md" <<'EOF'
Use /devlyn:resolve --verify-only --spec docs/roadmap/phase-1/local__repo-1.md.
EOF
cat > "$RESULTS_DIR/$HISTORICAL_ONLY_TRIGGER_RUN_ID/compare.json" <<'EOF'
{
  "solo": {"invoke_exit": 0, "timed_out": false, "verify_verdict": "PASS_WITH_ISSUES", "elapsed_seconds": 100},
  "pair": {
    "invoke_exit": 0,
    "timed_out": false,
    "verify_verdict": "NEEDS_WORK",
    "pair_mode": true,
    "pair_trigger": {"eligible": true, "reasons": ["risk_profile.high_risk"], "skipped_reason": null},
    "elapsed_seconds": 200
  },
  "comparison": {
    "pair_trigger_missed": false,
    "pair_verdict_lift": true,
    "solo_verdict": "PASS_WITH_ISSUES",
    "pair_verdict": "NEEDS_WORK"
  }
}
EOF
python3 "$ROOT/benchmark/auto-resolve/scripts/swebench-frozen-matrix.py" \
  --results-root "$RESULTS_DIR" \
  --title "Historical Trigger Matrix" \
  --verdict FAIL \
  --run-id "$HISTORICAL_ONLY_TRIGGER_RUN_ID" \
  --out-json "$TMP/historical-trigger-matrix.json" \
  --out-md "$TMP/historical-trigger-matrix.md" > "$TMP/historical-trigger-matrix.log"
grep -q '"pair_trigger_eligible": false' "$TMP/historical-trigger-matrix.json"
grep -q '"pair_trigger reasons missing canonical trigger reason"' "$TMP/historical-trigger-matrix.json"
grep -q '"classification": "failed attempt: pair trigger contract: pair_trigger reasons missing canonical trigger reason"' "$TMP/historical-trigger-matrix.json"
grep -Fq '| local__repo-1 | PASS_WITH_ISSUES | NEEDS_WORK | true | malformed |' "$TMP/historical-trigger-matrix.md"

HYPOTHESIS_TRIGGER_RUN_ID="swebench-missing-hypothesis-trigger-test-local__repo-hypothesis"
mkdir -p "$TMP/cases/local__repo-hypothesis" "$RESULTS_DIR/$HYPOTHESIS_TRIGGER_RUN_ID/pair"
cat > "$TMP/cases/local__repo-hypothesis/spec.md" <<'EOF'
## Verification

- Solo-headroom hypothesis: `solo_claude` is expected to miss the frozen review defect; observable miss command: `python -m pytest tests/test_review.py`.
EOF
cat > "$RESULTS_DIR/$HYPOTHESIS_TRIGGER_RUN_ID/pair/input.md" <<'EOF'
Use /devlyn:resolve --verify-only --spec docs/roadmap/phase-1/local__repo-hypothesis.md.
EOF
cat > "$RESULTS_DIR/$HYPOTHESIS_TRIGGER_RUN_ID/compare.json" <<'EOF'
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
  "comparison": {
    "pair_trigger_missed": false,
    "pair_verdict_lift": true,
    "solo_verdict": "PASS_WITH_ISSUES",
    "pair_verdict": "NEEDS_WORK"
  }
}
EOF
set +e
python3 "$ROOT/benchmark/auto-resolve/scripts/swebench-frozen-matrix.py" \
  --results-root "$RESULTS_DIR" \
  --title "Hypothesis Trigger Matrix" \
  --verdict FAIL \
  --run-id "$HYPOTHESIS_TRIGGER_RUN_ID" \
  --require-hypothesis-trigger \
  --out-json "$TMP/hypothesis-trigger-missing-root.json" \
  --out-md "$TMP/hypothesis-trigger-missing-root.md" > "$TMP/hypothesis-trigger-missing-root.log" 2>&1
missing_root_status=$?
set -e
[ "$missing_root_status" -ne 0 ]
grep -Fq -- '--require-hypothesis-trigger requires --fixtures-root' "$TMP/hypothesis-trigger-missing-root.log"
python3 "$ROOT/benchmark/auto-resolve/scripts/swebench-frozen-matrix.py" \
  --results-root "$RESULTS_DIR" \
  --fixtures-root "$TMP/cases" \
  --title "Hypothesis Trigger Matrix" \
  --verdict FAIL \
  --run-id "$HYPOTHESIS_TRIGGER_RUN_ID" \
  --require-hypothesis-trigger \
  --out-json "$TMP/hypothesis-trigger-matrix.json" \
  --out-md "$TMP/hypothesis-trigger-matrix.md" > "$TMP/hypothesis-trigger-matrix.log"
grep -q '"pair_trigger missing spec.solo_headroom_hypothesis"' "$TMP/hypothesis-trigger-matrix.json"
grep -q '"classification": "failed attempt: pair trigger contract: pair_trigger missing spec.solo_headroom_hypothesis"' "$TMP/hypothesis-trigger-matrix.json"
grep -Fq '| local__repo-hypothesis | PASS_WITH_ISSUES | NEEDS_WORK | true | malformed |' "$TMP/hypothesis-trigger-matrix.md"

set +e
bash "$ROOT/benchmark/auto-resolve/scripts/run-swebench-frozen-corpus.sh" \
  --manifest "$TMP/manifest.json" \
  --min-runs > "$TMP/corpus-missing-value.log" 2>&1
missing_value_status=$?
set -e
[ "$missing_value_status" -ne 0 ]
grep -Fq -- '--min-runs requires a value' "$TMP/corpus-missing-value.log"

cat > "$TMP/manifest-non-object.json" <<'EOF'
[]
EOF
set +e
bash "$ROOT/benchmark/auto-resolve/scripts/run-swebench-frozen-corpus.sh" \
  --manifest "$TMP/manifest-non-object.json" \
  --prepare-only > "$TMP/corpus-manifest-non-object.log" 2>&1
manifest_non_object_status=$?
set -e
[ "$manifest_non_object_status" -ne 0 ]
grep -Fq 'manifest malformed: expected JSON object' "$TMP/corpus-manifest-non-object.log"

cat > "$TMP/manifest-nan.json" <<'EOF'
{
  "cases_root": NaN,
  "prepared": []
}
EOF
set +e
bash "$ROOT/benchmark/auto-resolve/scripts/run-swebench-frozen-corpus.sh" \
  --manifest "$TMP/manifest-nan.json" \
  --prepare-only > "$TMP/corpus-manifest-nan.log" 2>&1
manifest_nan_status=$?
set -e
[ "$manifest_nan_status" -ne 0 ]
grep -Fq 'invalid JSON numeric constant: NaN' "$TMP/corpus-manifest-nan.log"

cat > "$TMP/manifest-empty-prepared.json" <<EOF
{
  "cases_root": "$TMP/cases-batch",
  "prepared": []
}
EOF
set +e
bash "$ROOT/benchmark/auto-resolve/scripts/run-swebench-frozen-corpus.sh" \
  --manifest "$TMP/manifest-empty-prepared.json" \
  --prepare-only > "$TMP/corpus-manifest-empty-prepared.log" 2>&1
manifest_empty_prepared_status=$?
set -e
[ "$manifest_empty_prepared_status" -ne 0 ]
grep -Fq 'manifest malformed: prepared must be a non-empty array' "$TMP/corpus-manifest-empty-prepared.log"

cat > "$TMP/manifest-bad-row.json" <<EOF
{
  "cases_root": "$TMP/cases-batch",
  "prepared": ["not an object"]
}
EOF
set +e
bash "$ROOT/benchmark/auto-resolve/scripts/run-swebench-frozen-corpus.sh" \
  --manifest "$TMP/manifest-bad-row.json" \
  --prepare-only > "$TMP/corpus-manifest-bad-row.log" 2>&1
manifest_bad_row_status=$?
set -e
[ "$manifest_bad_row_status" -ne 0 ]
grep -Fq 'manifest malformed: prepared[1] expected JSON object' "$TMP/corpus-manifest-bad-row.log"

bash "$ROOT/benchmark/auto-resolve/scripts/run-swebench-frozen-corpus.sh" \
  --manifest "$TMP/manifest.json" \
  --run-prefix swebench-frozen-corpus-test \
  --timeout-seconds 7 \
  --run-ids-out "$TMP/prepare-run-ids.txt" \
  --out-json "$TMP/gate.json" \
  --out-md "$TMP/gate.md" \
  --prepare-only > "$TMP/corpus-runner.log"
grep -Fq 'Command: ' "$TMP/corpus-runner.log"
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

DIRTY_MATRIX_RUN_ID="swebench-dirty-matrix-test-local__repo-1"
mkdir -p "$RESULTS_DIR/$DIRTY_MATRIX_RUN_ID/solo" "$RESULTS_DIR/$DIRTY_MATRIX_RUN_ID/pair"
cat > "$RESULTS_DIR/$DIRTY_MATRIX_RUN_ID/solo/input.md" <<'EOF'
Use /devlyn:resolve --verify-only --spec docs/roadmap/phase-1/local__repo-1.md.
EOF
cat > "$RESULTS_DIR/$DIRTY_MATRIX_RUN_ID/compare.json" <<'EOF'
{
  "solo": {"invoke_exit": 0, "timed_out": false, "verify_verdict": "PASS_WITH_ISSUES", "elapsed_seconds": 100},
  "pair": {"invoke_exit": 0, "timed_out": false, "verify_verdict": "NEEDS_WORK", "pair_mode": true, "elapsed_seconds": 200, "environment_contamination": true},
  "comparison": {
    "pair_trigger_missed": false,
    "pair_verdict_lift": true,
    "solo_verdict": "PASS_WITH_ISSUES",
    "pair_verdict": "NEEDS_WORK"
  }
}
EOF
python3 "$ROOT/benchmark/auto-resolve/scripts/swebench-frozen-matrix.py" \
  --title "Local SWE-bench Dirty Matrix" \
  --verdict FAIL \
  --run-id "$DIRTY_MATRIX_RUN_ID" \
  --out-json "$TMP/dirty-matrix.json" \
  --out-md "$TMP/dirty-matrix.md" > "$TMP/dirty-matrix.log"
grep -q '"classification": "failed attempt: environment contamination"' "$TMP/dirty-matrix.json"
grep -Fq 'failed attempt: environment contamination' "$TMP/dirty-matrix.md"

MALFORMED_MATRIX_RUN_ID="swebench-malformed-matrix-test-local__repo-1"
mkdir -p "$RESULTS_DIR/$MALFORMED_MATRIX_RUN_ID/solo" "$RESULTS_DIR/$MALFORMED_MATRIX_RUN_ID/pair"
cat > "$RESULTS_DIR/$MALFORMED_MATRIX_RUN_ID/solo/input.md" <<'EOF'
Use /devlyn:resolve --verify-only --spec docs/roadmap/phase-1/local__repo-1.md.
EOF
cat > "$RESULTS_DIR/$MALFORMED_MATRIX_RUN_ID/compare.json" <<'EOF'
{
  "solo": ["not", "a", "dict"],
  "pair": {"invoke_exit": 0, "timed_out": false, "verify_verdict": ["bad"], "pair_mode": true, "elapsed_seconds": true},
  "comparison": {"pair_verdict_lift": true, "solo_verdict": ["bad"], "pair_verdict": ["bad"]}
}
EOF
python3 "$ROOT/benchmark/auto-resolve/scripts/swebench-frozen-matrix.py" \
  --title "Local SWE-bench Malformed Matrix" \
  --verdict FAIL \
  --run-id "$MALFORMED_MATRIX_RUN_ID" \
  --out-json "$TMP/malformed-matrix.json" \
  --out-md "$TMP/malformed-matrix.md" > "$TMP/malformed-matrix.log"
grep -q '"classification": "failed attempt: malformed compare"' "$TMP/malformed-matrix.json"
grep -q '"solo_verdict": null' "$TMP/malformed-matrix.json"
grep -q '"pair_solo_wall_ratio": null' "$TMP/malformed-matrix.json"
grep -Fq 'failed attempt: malformed compare' "$TMP/malformed-matrix.md"

NAN_MATRIX_RUN_ID="swebench-nan-matrix-test-local__repo-1"
mkdir -p "$RESULTS_DIR/$NAN_MATRIX_RUN_ID/solo" "$RESULTS_DIR/$NAN_MATRIX_RUN_ID/pair"
cat > "$RESULTS_DIR/$NAN_MATRIX_RUN_ID/solo/input.md" <<'EOF'
Use /devlyn:resolve --verify-only --spec docs/roadmap/phase-1/local__repo-1.md.
EOF
cat > "$RESULTS_DIR/$NAN_MATRIX_RUN_ID/compare.json" <<'EOF'
{
  "solo": {"invoke_exit": 0, "timed_out": false, "verify_verdict": "PASS_WITH_ISSUES", "elapsed_seconds": 100},
  "pair": {"invoke_exit": 0, "timed_out": false, "verify_verdict": "NEEDS_WORK", "pair_mode": true, "elapsed_seconds": NaN},
  "comparison": {"pair_verdict_lift": true, "solo_verdict": "PASS_WITH_ISSUES", "pair_verdict": "NEEDS_WORK"}
}
EOF
python3 "$ROOT/benchmark/auto-resolve/scripts/swebench-frozen-matrix.py" \
  --title "Local SWE-bench NaN Matrix" \
  --verdict FAIL \
  --run-id "$NAN_MATRIX_RUN_ID" \
  --out-json "$TMP/nan-matrix.json" \
  --out-md "$TMP/nan-matrix.md" > "$TMP/nan-matrix.log"
grep -q '"classification": "failed attempt: malformed compare"' "$TMP/nan-matrix.json"
grep -q '"malformed_compare": true' "$TMP/nan-matrix.json"
grep -Fq 'failed attempt: malformed compare' "$TMP/nan-matrix.md"

STRING_BOOL_MATRIX_RUN_ID="swebench-string-bool-matrix-test-local__repo-1"
mkdir -p "$RESULTS_DIR/$STRING_BOOL_MATRIX_RUN_ID/solo" "$RESULTS_DIR/$STRING_BOOL_MATRIX_RUN_ID/pair"
cat > "$RESULTS_DIR/$STRING_BOOL_MATRIX_RUN_ID/solo/input.md" <<'EOF'
Use /devlyn:resolve --verify-only --spec docs/roadmap/phase-1/local__repo-1.md.
EOF
cat > "$RESULTS_DIR/$STRING_BOOL_MATRIX_RUN_ID/compare.json" <<'EOF'
{
  "solo": {"invoke_exit": 0, "timed_out": "true", "verify_verdict": "PASS_WITH_ISSUES", "elapsed_seconds": 100},
  "pair": {"invoke_exit": 0, "timed_out": "false", "verify_verdict": "NEEDS_WORK", "pair_mode": "true", "elapsed_seconds": 200, "environment_contamination": "true"},
  "comparison": {
    "pair_trigger_missed": "false",
    "pair_verdict_lift": "true",
    "pair_internal_verdict_lift": "true",
    "solo_verdict": "PASS_WITH_ISSUES",
    "pair_verdict": "NEEDS_WORK"
  }
}
EOF
python3 "$ROOT/benchmark/auto-resolve/scripts/swebench-frozen-matrix.py" \
  --title "Local SWE-bench String Bool Matrix" \
  --verdict FAIL \
  --run-id "$STRING_BOOL_MATRIX_RUN_ID" \
  --out-json "$TMP/string-bool-matrix.json" \
  --out-md "$TMP/string-bool-matrix.md" > "$TMP/string-bool-matrix.log"
grep -q '"pair_mode": false' "$TMP/string-bool-matrix.json"
grep -q '"external_lift": false' "$TMP/string-bool-matrix.json"
grep -q '"internal_lift": false' "$TMP/string-bool-matrix.json"
grep -q '"pair_environment_contamination": false' "$TMP/string-bool-matrix.json"

touch "$TMP/empty-run-ids.txt"
set +e
bash "$ROOT/benchmark/auto-resolve/scripts/run-swebench-frozen-corpus.sh" \
  --manifest "$TMP/manifest.json" \
  --gate-only-run-ids "$TMP/empty-run-ids.txt" > "$TMP/gate-empty-run-ids.log" 2>&1
empty_run_ids_status=$?
set -e
[ "$empty_run_ids_status" -ne 0 ]
grep -Fq 'run ids malformed: no run ids' "$TMP/gate-empty-run-ids.log"

printf 'valid-run\n\n' > "$TMP/blank-run-ids.txt"
set +e
bash "$ROOT/benchmark/auto-resolve/scripts/run-swebench-frozen-corpus.sh" \
  --manifest "$TMP/manifest.json" \
  --gate-only-run-ids "$TMP/blank-run-ids.txt" > "$TMP/gate-blank-run-ids.log" 2>&1
blank_run_ids_status=$?
set -e
[ "$blank_run_ids_status" -ne 0 ]
grep -Fq 'run ids malformed: line 2 is empty' "$TMP/gate-blank-run-ids.log"

printf 'bad/run\n' > "$TMP/unsafe-run-ids.txt"
set +e
bash "$ROOT/benchmark/auto-resolve/scripts/run-swebench-frozen-corpus.sh" \
  --manifest "$TMP/manifest.json" \
  --gate-only-run-ids "$TMP/unsafe-run-ids.txt" > "$TMP/gate-unsafe-run-ids.log" 2>&1
unsafe_run_ids_status=$?
set -e
[ "$unsafe_run_ids_status" -ne 0 ]
grep -Fq 'run ids malformed: line 1 has unsafe run id' "$TMP/gate-unsafe-run-ids.log"

RUN_ID="swebench-gate-only-test-local__repo-1"
mkdir -p "$RESULTS_DIR/$RUN_ID/pair"
cat > "$RESULTS_DIR/$RUN_ID/pair/input.md" <<'EOF'
Use /devlyn:resolve --verify-only --spec docs/roadmap/phase-1/local__repo-1.md.
EOF
cat > "$RESULTS_DIR/$RUN_ID/compare.json" <<'EOF'
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
grep -q '"pair_trigger_reasons": \[' "$TMP/matrix.json"
grep -q '"mode.verify-only"' "$TMP/matrix.json"
grep -q '"pair_trigger_has_canonical_reason": true' "$TMP/matrix.json"
grep -Fq 'Local SWE-bench Matrix' "$TMP/matrix.md"
grep -Fq 'Gate rate: 1.000' "$TMP/matrix.md"
grep -Fq 'Yield verdict: **PASS**' "$TMP/matrix.md"
grep -Fq '| Fixture | Solo VERIFY | Pair VERIFY | Pair mode | Pair trigger | Triggers | Wall ratio | External lift | Internal lift | Included | Classification |' "$TMP/matrix.md"
grep -Fq '| local__repo-1 | PASS_WITH_ISSUES | NEEDS_WORK | true | eligible | mode.verify-only | 2.00x | true | false | true | gate: external lift |' "$TMP/matrix.md"

rm -rf /tmp/bench-swebench-frozen-case-test-local__repo-1-solo
rm -rf /tmp/bench-swebench-frozen-case-test-local__repo-1-pair
rm -rf /tmp/bench-swebench-frozen-corpus-test-1-local__repo-1-local__repo-1-solo
rm -rf /tmp/bench-swebench-frozen-corpus-test-1-local__repo-1-local__repo-1-pair
rm -rf "$ROOT/benchmark/auto-resolve/results/swebench-frozen-case-test"
rm -rf "$ROOT/benchmark/auto-resolve/results/swebench-frozen-corpus-test-1-local__repo-1"
rm -rf "$ROOT/benchmark/auto-resolve/results/swebench-frozen-corpus-fail-test-1-local__repo-1"
rm -rf "$RESULTS_DIR/$RESUME_RUN_ID"
rm -rf "$RESULTS_DIR/$BOOL_ELAPSED_RUN_ID"
rm -rf "$RESULTS_DIR/$MALFORMED_PAIR_JUDGE_RUN_ID"
rm -rf "$RESULTS_DIR/$MALFORMED_PAIR_TRIGGER_RUN_ID"
rm -rf "$RESULTS_DIR/$PROVIDER_LIMIT_RUN_ID"
rm -rf "$RESULTS_DIR/$DIRTY_MATRIX_RUN_ID"
rm -rf "$RESULTS_DIR/$MALFORMED_MATRIX_RUN_ID"
rm -rf "$RESULTS_DIR/$NAN_MATRIX_RUN_ID"
rm -rf "$RESULTS_DIR/$STRING_BOOL_MATRIX_RUN_ID"
rm -rf "$RESULTS_DIR/$RUN_ID"

echo "PASS test-swebench-frozen-case"
