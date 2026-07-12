#!/usr/bin/env bash
# Focused, no-model self-check for the iter-0068 no-degradation driver.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TMP_DIR="$(mktemp -d /tmp/nodeg-selftest.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

REPO="$TMP_DIR/repo"
CEILING="$REPO/benchmark/ceiling"
TASK="DR-byte-preservation-f7-out-of-scope-trap"
SOURCE="$CEILING/results/iter0068-gate-20260711h/$TASK/B1"
mkdir -p "$CEILING/corpus/$TASK" "$SOURCE"
printf 'selftest task\n' > "$CEILING/corpus/$TASK/task.txt"
printf 'diff --git a/a b/a\n' > "$SOURCE/patch.diff"
printf '{"resolved":true}\n' > "$SOURCE/objective.json"
printf '{"invoke_exit":0,"timed_out":false,"elapsed_seconds":67}\n' > "$SOURCE/timing.json"
printf '{"opaque_paths":{"passed":true}}\n' > "$SOURCE/isolation.json"
git -C "$REPO" init -q
git -C "$REPO" add .
git -C "$REPO" -c user.name=selftest -c user.email=selftest@example.com commit -q -m fixture

run_check() {
  NODEG_SELFTEST=1 NODEG_REPO_ROOT="$REPO" NODEG_CEILING_ROOT="$CEILING" \
    bash "$SCRIPT_DIR/run-nodeg-cell.sh" --run-id selftest-nodeg --tasks F7 --check-only "$@"
}

if run_check --unknown > "$TMP_DIR/arg.stdout" 2> "$TMP_DIR/arg.stderr"; then
  echo "unknown argument did not fail" >&2
  exit 1
fi
grep -q 'unknown arg: --unknown' "$TMP_DIR/arg.stderr"

if NODEG_SELFTEST=1 NODEG_REPO_ROOT="$REPO" NODEG_CEILING_ROOT="$CEILING" \
  bash "$SCRIPT_DIR/run-nodeg-cell.sh" --run-id selftest-nodeg --tasks F99 --check-only \
  > "$TMP_DIR/task.stdout" 2> "$TMP_DIR/task.stderr"; then
  echo "invalid task did not fail" >&2
  exit 1
fi
grep -q 'invalid --tasks entry' "$TMP_DIR/task.stderr"

test "$(run_check)" = "$TASK"

mv "$SOURCE/patch.diff" "$SOURCE/patch.missing"
git -C "$REPO" add -A
git -C "$REPO" -c user.name=selftest -c user.email=selftest@example.com commit -q -m missing-patch
if run_check > "$TMP_DIR/missing.stdout" 2> "$TMP_DIR/missing.stderr"; then
  echo "missing frozen-B patch did not fail" >&2
  exit 1
fi
grep -q 'frozen-B pointer missing artifacts' "$TMP_DIR/missing.stderr"
mv "$SOURCE/patch.missing" "$SOURCE/patch.diff"
git -C "$REPO" add -A
git -C "$REPO" -c user.name=selftest -c user.email=selftest@example.com commit -q -m restore-patch

printf '{"resolved":false}\n' > "$SOURCE/objective.json"
git -C "$REPO" add "$SOURCE/objective.json"
git -C "$REPO" -c user.name=selftest -c user.email=selftest@example.com commit -q -m unresolved
if run_check > "$TMP_DIR/unresolved.stdout" 2> "$TMP_DIR/unresolved.stderr"; then
  echo "unresolved frozen-B pointer did not fail" >&2
  exit 1
fi
grep -q 'frozen-B pointer is not resolved' "$TMP_DIR/unresolved.stderr"

printf '{"resolved":true}\n' > "$SOURCE/objective.json"
git -C "$REPO" add "$SOURCE/objective.json"
git -C "$REPO" -c user.name=selftest -c user.email=selftest@example.com commit -q -m resolved
printf 'dirty\n' >> "$CEILING/corpus/$TASK/task.txt"
if run_check > "$TMP_DIR/dirty.stdout" 2> "$TMP_DIR/dirty.stderr"; then
  echo "dirty runner worktree did not fail" >&2
  exit 1
fi
grep -q 'runner worktree is dirty' "$TMP_DIR/dirty.stderr"

printf 'selftest task\n' > "$CEILING/corpus/$TASK/task.txt"
python3 "$SCRIPT_DIR/nodeg-cell.py" preflight \
  --run-id selftest-judge --tasks F7 --repo-root "$REPO" --ceiling-root "$CEILING" --initialize \
  > "$TMP_DIR/preflight.stdout"
JUDGE_RUN="$CEILING/results/selftest-judge/$TASK"
mkdir -p "$JUDGE_RUN/A1" "$TMP_DIR/fakebin"
printf 'diff --git a/a b/a\n+candidate A\n' > "$JUDGE_RUN/A1/patch.diff"

cat > "$TMP_DIR/fakebin/claude" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [ "${1:-}" = --version ]; then
  echo 'claude fake 1.0'
  exit 0
fi
cat <<'JSON'
{"result":"{\"axes\":{\"design_coherence\":{\"tiers\":[[\"P1\",\"P2\"]],\"strict_win_deltas\":[]},\"robustness\":{\"tiers\":[[\"P1\",\"P2\"]],\"strict_win_deltas\":[]},\"spec_long_horizon_consistency\":{\"tiers\":[[\"P1\",\"P2\"]],\"strict_win_deltas\":[]},\"maintainability_api_ergonomics\":{\"tiers\":[[\"P1\",\"P2\"]],\"strict_win_deltas\":[]}}}","modelUsage":{"claude-sonnet-fake":{}}}
JSON
EOF
chmod +x "$TMP_DIR/fakebin/claude"

cat > "$TMP_DIR/fakebin/codex" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [ "${1:-}" = --version ]; then
  echo 'codex fake 1.0'
  exit 0
fi
echo 'model: gpt-5.6-terra' >&2
cat <<'JSON'
{"axes":{"design_coherence":{"tiers":[["P1","P2"]],"strict_win_deltas":[]},"robustness":{"tiers":[["P1","P2"]],"strict_win_deltas":[]},"spec_long_horizon_consistency":{"tiers":[["P1","P2"]],"strict_win_deltas":[]},"maintainability_api_ergonomics":{"tiers":[["P1","P2"]],"strict_win_deltas":[]}}}
JSON
EOF
chmod +x "$TMP_DIR/fakebin/codex"

printf '{"token":"selftest"}\n' > "$TMP_DIR/auth.json"
printf '{"claudeAiOauth":{"accessToken":"selftest"}}\n' > "$TMP_DIR/claude-credentials.json"
chmod 0600 "$TMP_DIR/auth.json" "$TMP_DIR/claude-credentials.json"
CEILING_EXTERNAL_ROOT="$TMP_DIR/external" \
CEILING_REAL_HOME="$TMP_DIR" \
CEILING_TEST_AUTH_JSON="$TMP_DIR/auth.json" \
CEILING_TEST_CLAUDE_CREDENTIALS="$TMP_DIR/claude-credentials.json" \
CEILING_TEST_CLAUDE_BIN="$TMP_DIR/fakebin/claude" \
CEILING_TEST_CODEX_BIN="$TMP_DIR/fakebin/codex" \
python3 "$SCRIPT_DIR/nodeg-cell.py" judge \
  --run-id selftest-judge --tasks F7 --repo-root "$REPO" --ceiling-root "$CEILING"
python3 - "$CEILING/results/selftest-judge/nodeg-judge-aggregate.json" "$JUDGE_RUN/nodeg-judge/mapping.json" <<'PY'
import json
import sys

aggregate = json.load(open(sys.argv[1], encoding="utf-8"))
mapping = json.load(open(sys.argv[2], encoding="utf-8"))
judges = aggregate["tasks"]["DR-byte-preservation-f7-out-of-scope-trap"]["judges"]
if judges["codex"]["runtime_model"] != "gpt-5.6-terra":
    raise SystemExit(judges)
if judges["sonnet"]["runtime_model"] != "claude-sonnet-fake":
    raise SystemExit(judges)
if mapping["frozen_b_source"]["run_id"] != "iter0068-gate-20260711h":
    raise SystemExit(mapping)
PY
test ! -e "$JUDGE_RUN/B1/patch.diff"
if grep -q 'iter0068-gate-20260711h' "$JUDGE_RUN/nodeg-judge/sonnet.json"; then
  echo "frozen source provenance leaked into sonnet blind packet" >&2
  exit 1
fi
if grep -q 'iter0068-gate-20260711h' "$JUDGE_RUN/nodeg-judge/codex.json"; then
  echo "frozen source provenance leaked into codex blind packet" >&2
  exit 1
fi
printf '{"resolved":true}\n' > "$JUDGE_RUN/A1/objective.json"
printf '{"invoke_exit":0,"timed_out":false,"elapsed_seconds":100}\n' > "$JUDGE_RUN/A1/timing.json"
printf '{"modelUsage":{"claude-sonnet-fake":{}}}\n' > "$JUDGE_RUN/A1/transcript.txt"
run_verdict() {
  python3 "$SCRIPT_DIR/nodeg-cell.py" verdict \
    --run-id selftest-judge --tasks F7 --repo-root "$REPO" --ceiling-root "$CEILING"
}

if run_verdict > "$TMP_DIR/a-missing.stdout" 2> "$TMP_DIR/a-missing.stderr"; then
  echo "missing A isolation did not fail" >&2
  exit 1
fi
grep -q 'invalid JSON artifact .*A1/isolation.json' "$TMP_DIR/a-missing.stderr"

printf '{"opaque_paths":{"passed":false},"direct_claude":{"version":"claude fake 1.0"},"direct_codex":{"version":"codex fake 1.0"}}\n' \
  > "$JUDGE_RUN/A1/isolation.json"
if run_verdict > "$TMP_DIR/a-false.stdout" 2> "$TMP_DIR/a-false.stderr"; then
  echo "failed A opaque-path attestation did not fail" >&2
  exit 1
fi
grep -q 'F7 A attempt A1 opaque-path attestation did not pass: .*A1/isolation.json' "$TMP_DIR/a-false.stderr"

printf '{"opaque_paths":{"passed":true},"direct_claude":{"version":"claude fake 1.0"},"direct_codex":{"version":"codex fake 1.0"}}\n' \
  > "$JUDGE_RUN/A1/isolation.json"
run_verdict > "$TMP_DIR/verdict.stdout"
python3 - "$CEILING/results/selftest-judge/nodeg-verdict.json" <<'PY'
import json
import sys

verdict = json.load(open(sys.argv[1], encoding="utf-8"))
if set(verdict["bars"]) != {"objective", "quality", "wall"}:
    raise SystemExit(verdict)
if not all(bar["passed"] for bar in verdict["bars"].values()):
    raise SystemExit(verdict["bars"])
if "verdict" in verdict or verdict["bars"]["wall"]["cap"] != 3.0:
    raise SystemExit(verdict)
PY

python3 -m py_compile "$SCRIPT_DIR/nodeg-cell.py"
bash -n "$SCRIPT_DIR/run-nodeg-cell.sh" "$SCRIPT_DIR/test-nodeg-cell.sh"
echo "PASS test-nodeg-cell"
