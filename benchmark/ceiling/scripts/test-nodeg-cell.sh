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
RESUME_SENTINEL="$CEILING/results/selftest-nodeg/tracked.txt"
mkdir -p "$CEILING/corpus/$TASK" "$SOURCE" "$(dirname "$RESUME_SENTINEL")"
printf 'selftest task\n' > "$CEILING/corpus/$TASK/task.txt"
printf 'tracked resume artifact\n' > "$RESUME_SENTINEL"
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
rm "$RESUME_SENTINEL"
test "$(git -C "$REPO" status --porcelain=v1)" = " D benchmark/ceiling/results/selftest-nodeg/tracked.txt"
test "$(run_check --resume)" = "$TASK"
git -C "$REPO" restore "$RESUME_SENTINEL"

python3 "$SCRIPT_DIR/nodeg-cell.py" preflight \
  --run-id selftest-judge --tasks F7 --repo-root "$REPO" --ceiling-root "$CEILING" --initialize \
  > "$TMP_DIR/preflight.stdout"
JUDGE_RUN="$CEILING/results/selftest-judge/$TASK"
mkdir -p "$JUDGE_RUN/A1" "$TMP_DIR/fakebin"
printf 'diff --git a/a b/a\n+candidate A\n' > "$JUDGE_RUN/A1/patch.diff"
printf '{"invoke_exit":0,"timed_out":false,"elapsed_seconds":100}\n' > "$JUDGE_RUN/A1/timing.json"
printf '{"modelUsage":{"claude-sonnet-fake":{}}}\n' > "$JUDGE_RUN/A1/transcript.txt"

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
self_dir="$(cd "$(dirname "$0")" && pwd)"
mode="$(cat "$self_dir/codex-mode" 2>/dev/null || printf valid)"
prompt="${@: -1}"
valid='{"axes":{"design_coherence":{"tiers":[["P1","P2"]],"strict_win_deltas":[]},"robustness":{"tiers":[["P1","P2"]],"strict_win_deltas":[]},"spec_long_horizon_consistency":{"tiers":[["P1","P2"]],"strict_win_deltas":[]},"maintainability_api_ergonomics":{"tiers":[["P1","P2"]],"strict_win_deltas":[]}}}'
case "$mode" in
  retry)
    count_file="$self_dir/codex-count"
    count=0
    [ ! -f "$count_file" ] || read -r count < "$count_file"
    count=$((count + 1))
    printf '%s\n' "$count" > "$count_file"
    if [ "$count" -eq 1 ]; then
      printf '{"axes":"unterminated\n'
    else
      [[ "$prompt" == *'Your previous output was truncated; emit ONLY the JSON, complete.'* ]]
      : > "$self_dir/retry-prompt-ok"
      printf 'startup log\n{"log":"ignore this object"}\n%s\ntrailing log\n' "$valid"
    fi
    ;;
  structural) printf '%s\n' "${valid%?}" ;;
  prose) printf 'leading prose\n%s\ntrailing prose\n' "$valid" ;;
  unrecoverable) printf '{"a":{"b":{"c":{"d":1\n' ;;
  valid) printf '%s\n' "$valid" ;;
  *) echo "unknown fake codex mode: $mode" >&2; exit 2 ;;
esac
EOF
chmod +x "$TMP_DIR/fakebin/codex"
printf 'retry\n' > "$TMP_DIR/fakebin/codex-mode"
rm -f "$TMP_DIR/fakebin/codex-count" "$TMP_DIR/fakebin/retry-prompt-ok"

python3 - "$SCRIPT_DIR/ceiling-judge.py" <<'PY'
import json
import runpy
import sys

module = runpy.run_path(sys.argv[1])
row = {"tiers": [["P1", "P2", "P3"]], "strict_win_deltas": []}
response = {"axes": {axis: row for axis in module["AXES"]}}
raw = json.dumps(response)
extract = module["extract_json_object"]

for missing in (1, 2, 3):
    metadata = {}
    if extract(raw[:-missing], structural_completion=True, parse_metadata=metadata) != response:
        raise SystemExit(f"{missing}-brace structural completion failed")
    if metadata != {"structural_completion": missing}:
        raise SystemExit(metadata)
refused = {
    "depth-4": '{"a":{"b":{"c":' + raw[:-1],
    "trailing-garbage": raw[:-1] + " trailing",
    "in-string": '{"axes":"unterminated',
    "missing-bracket": raw.replace("]]", "]", 1)[:-1],
    "missing-content": '{"axes":',
}
for name, candidate in refused.items():
    metadata = {}
    if extract(candidate, structural_completion=True, parse_metadata=metadata) is not None:
        raise SystemExit(f"{name} structural completion was accepted")
    if metadata:
        raise SystemExit({name: metadata})
PY

printf '{"token":"selftest"}\n' > "$TMP_DIR/auth.json"
printf '{"claudeAiOauth":{"accessToken":"selftest"}}\n' > "$TMP_DIR/claude-credentials.json"
chmod 0600 "$TMP_DIR/auth.json" "$TMP_DIR/claude-credentials.json"
ATTEMPT_RUNNER_SHA="$(git -C "$REPO" rev-parse HEAD)"
printf 'judge runner\n' > "$REPO/judge-runner.txt"
git -C "$REPO" add judge-runner.txt
git -C "$REPO" -c user.name=selftest -c user.email=selftest@example.com commit -q -m judge-runner
JUDGE_RUNNER_SHA="$(git -C "$REPO" rev-parse HEAD)"
printf '{"opaque_paths":{"passed":false},"direct_claude":{"version":"claude fake 1.0"},"direct_codex":{"version":"codex fake 1.0"}}\n' \
  > "$JUDGE_RUN/A1/isolation.json"
DEVIATIONS="$TMP_DIR/deviations.json"
printf '{"deviations":[{"type":"judge-runner-sha","attempt_runner_sha":"%s","judge_runner_sha":"%s","reason":"dated instrument repair","decision_ref":"autoresearch/DECISIONS.md:0068.9"},{"type":"opaque-paths-artifact-dir","driver_line":"run-nodeg-cell.sh:75","prompt_grep_hits":0,"other_checks":"all-true","materiality":"attestation-layer"}]}\n' \
  "$ATTEMPT_RUNNER_SHA" "$JUDGE_RUNNER_SHA" > "$DEVIATIONS"

manifest_command=(
  python3 "$SCRIPT_DIR/nodeg-cell.py" manifest
  --run-id selftest-judge --tasks F7 --repo-root "$REPO" --ceiling-root "$CEILING"
)
CEILING_TEST_CLAUDE_BIN="$TMP_DIR/fakebin/claude" \
CEILING_TEST_CODEX_BIN="$TMP_DIR/fakebin/codex" \
  "${manifest_command[@]}" > "$TMP_DIR/manifest.stdout"
python3 - "$CEILING/results/selftest-judge/replay-binding-manifest.json" "$ATTEMPT_RUNNER_SHA" "$JUDGE_RUNNER_SHA" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1], encoding="utf-8"))
control = manifest["controls"]["F7"]
if set(control["frozen_b"]) != {"patch_sha256", "objective_sha256", "timing_sha256"}:
    raise SystemExit(control)
if manifest["attempt_runner_sha"] != sys.argv[2] or manifest["judge_runner_sha"] != sys.argv[3]:
    raise SystemExit(manifest)
if manifest["judge_engines"]["sonnet"]["cli_version"] != "claude fake 1.0":
    raise SystemExit(manifest["judge_engines"])
if manifest["judge_engines"]["codex"]["model"] != "gpt-5.6-terra":
    raise SystemExit(manifest["judge_engines"])
for binding in (manifest["judge_module"], manifest["judge_prompt_builder"]):
    if len(binding["sha256"]) != 64:
        raise SystemExit(binding)
PY
if CEILING_TEST_CLAUDE_BIN="$TMP_DIR/fakebin/claude" \
  CEILING_TEST_CODEX_BIN="$TMP_DIR/fakebin/codex" \
  "${manifest_command[@]}" > "$TMP_DIR/manifest-overwrite.stdout" 2> "$TMP_DIR/manifest-overwrite.stderr"; then
  echo "binding manifest overwrite did not fail" >&2
  exit 1
fi
grep -q 'replay binding manifest already exists' "$TMP_DIR/manifest-overwrite.stderr"

if CEILING_EXTERNAL_ROOT="$TMP_DIR/external" \
  CEILING_REAL_HOME="$TMP_DIR" \
  CEILING_TEST_AUTH_JSON="$TMP_DIR/auth.json" \
  CEILING_TEST_CLAUDE_CREDENTIALS="$TMP_DIR/claude-credentials.json" \
  CEILING_TEST_CLAUDE_BIN="$TMP_DIR/fakebin/claude" \
  CEILING_TEST_CODEX_BIN="$TMP_DIR/fakebin/codex" \
  python3 "$SCRIPT_DIR/nodeg-cell.py" judge \
    --run-id selftest-judge --tasks F7 --repo-root "$REPO" --ceiling-root "$CEILING" \
    > "$TMP_DIR/judge-no-deviation.stdout" 2> "$TMP_DIR/judge-no-deviation.stderr"; then
  echo "judge accepted changed runner without deviations" >&2
  exit 1
fi
grep -q 'runner commit changed after cell initialization' "$TMP_DIR/judge-no-deviation.stderr"

CEILING_EXTERNAL_ROOT="$TMP_DIR/external" \
CEILING_REAL_HOME="$TMP_DIR" \
CEILING_TEST_AUTH_JSON="$TMP_DIR/auth.json" \
CEILING_TEST_CLAUDE_CREDENTIALS="$TMP_DIR/claude-credentials.json" \
CEILING_TEST_CLAUDE_BIN="$TMP_DIR/fakebin/claude" \
CEILING_TEST_CODEX_BIN="$TMP_DIR/fakebin/codex" \
python3 "$SCRIPT_DIR/nodeg-cell.py" judge \
  --run-id selftest-judge --tasks F7 --repo-root "$REPO" --ceiling-root "$CEILING" \
  --deviations "$DEVIATIONS"
python3 - "$CEILING/results/selftest-judge/nodeg-judge-aggregate.json" "$JUDGE_RUN/nodeg-judge/mapping.json" <<'PY'
import json
import sys

aggregate = json.load(open(sys.argv[1], encoding="utf-8"))
mapping = json.load(open(sys.argv[2], encoding="utf-8"))
judges = aggregate["tasks"]["DR-byte-preservation-f7-out-of-scope-trap"]["judges"]
if {entry["type"] for entry in aggregate["deviations"]} != {
    "judge-runner-sha",
    "opaque-paths-artifact-dir",
}:
    raise SystemExit(aggregate["deviations"])
if judges["codex"]["runtime_model"] != "gpt-5.6-terra":
    raise SystemExit(judges)
if judges["sonnet"]["runtime_model"] != "claude-sonnet-fake":
    raise SystemExit(judges)
if mapping["frozen_b_source"]["run_id"] != "iter0068-gate-20260711h":
    raise SystemExit(mapping)
raw = json.load(open(sys.argv[2].replace("mapping.json", "codex.json"), encoding="utf-8"))
if len(raw["attempts"]) != 2 or not raw["attempts"][0]["error"].startswith("parse_error: incomplete_json"):
    raise SystemExit(raw["attempts"])
PY
test -f "$TMP_DIR/fakebin/retry-prompt-ok"

rm "$JUDGE_RUN/nodeg-judge/codex.json"
printf 'structural\n' > "$TMP_DIR/fakebin/codex-mode"
CEILING_EXTERNAL_ROOT="$TMP_DIR/external" \
CEILING_REAL_HOME="$TMP_DIR" \
CEILING_TEST_AUTH_JSON="$TMP_DIR/auth.json" \
CEILING_TEST_CLAUDE_CREDENTIALS="$TMP_DIR/claude-credentials.json" \
CEILING_TEST_CLAUDE_BIN="$TMP_DIR/fakebin/claude" \
CEILING_TEST_CODEX_BIN="$TMP_DIR/fakebin/codex" \
  python3 "$SCRIPT_DIR/nodeg-cell.py" judge \
    --run-id selftest-judge --tasks F7 --repo-root "$REPO" --ceiling-root "$CEILING" --resume \
    --deviations "$DEVIATIONS"
python3 - "$JUDGE_RUN/nodeg-judge/codex.json" "$CEILING/results/selftest-judge/nodeg-judge-aggregate.json" <<'PY'
import json
import sys

raw = json.load(open(sys.argv[1], encoding="utf-8"))
if len(raw["attempts"]) != 1 or raw["meta"].get("structural_completion") != 1:
    raise SystemExit(raw)
aggregate = json.load(open(sys.argv[2], encoding="utf-8"))
metadata = aggregate["tasks"][raw["task"]]["judges"]["codex"]["parse_metadata"]
if metadata != {"structural_completion": 1}:
    raise SystemExit(metadata)
PY

rm "$JUDGE_RUN/nodeg-judge/codex.json"
printf 'prose\n' > "$TMP_DIR/fakebin/codex-mode"
CEILING_EXTERNAL_ROOT="$TMP_DIR/external" \
CEILING_REAL_HOME="$TMP_DIR" \
CEILING_TEST_AUTH_JSON="$TMP_DIR/auth.json" \
CEILING_TEST_CLAUDE_CREDENTIALS="$TMP_DIR/claude-credentials.json" \
CEILING_TEST_CLAUDE_BIN="$TMP_DIR/fakebin/claude" \
CEILING_TEST_CODEX_BIN="$TMP_DIR/fakebin/codex" \
  python3 "$SCRIPT_DIR/nodeg-cell.py" judge \
    --run-id selftest-judge --tasks F7 --repo-root "$REPO" --ceiling-root "$CEILING" --resume \
    --deviations "$DEVIATIONS"
python3 - "$JUDGE_RUN/nodeg-judge/codex.json" <<'PY'
import json
import sys

raw = json.load(open(sys.argv[1], encoding="utf-8"))
if len(raw["attempts"]) != 1 or raw["parsed"] is None:
    raise SystemExit(raw)
PY

rm "$JUDGE_RUN/nodeg-judge/codex.json"
printf 'unrecoverable\n' > "$TMP_DIR/fakebin/codex-mode"
if CEILING_EXTERNAL_ROOT="$TMP_DIR/external" \
  CEILING_REAL_HOME="$TMP_DIR" \
  CEILING_TEST_AUTH_JSON="$TMP_DIR/auth.json" \
  CEILING_TEST_CLAUDE_CREDENTIALS="$TMP_DIR/claude-credentials.json" \
  CEILING_TEST_CLAUDE_BIN="$TMP_DIR/fakebin/claude" \
  CEILING_TEST_CODEX_BIN="$TMP_DIR/fakebin/codex" \
  python3 "$SCRIPT_DIR/nodeg-cell.py" judge \
    --run-id selftest-judge --tasks F7 --repo-root "$REPO" --ceiling-root "$CEILING" --resume \
    --deviations "$DEVIATIONS" \
    > "$TMP_DIR/unrecoverable.stdout" 2> "$TMP_DIR/unrecoverable.stderr"; then
  echo "unrecoverable judge JSON did not fail closed" >&2
  exit 1
fi
grep -Eq 'failed after retries: parse_error: incomplete_json; raw_length=[0-9]+ tail=' "$TMP_DIR/unrecoverable.stderr"
test -s "$JUDGE_RUN/nodeg-judge/judge-codex-attempt1.stdout.txt"
test -s "$JUDGE_RUN/nodeg-judge/judge-codex-attempt2.stdout.txt"

printf 'valid\n' > "$TMP_DIR/fakebin/codex-mode"
CEILING_EXTERNAL_ROOT="$TMP_DIR/external" \
CEILING_REAL_HOME="$TMP_DIR" \
CEILING_TEST_AUTH_JSON="$TMP_DIR/auth.json" \
CEILING_TEST_CLAUDE_CREDENTIALS="$TMP_DIR/claude-credentials.json" \
CEILING_TEST_CLAUDE_BIN="$TMP_DIR/fakebin/claude" \
CEILING_TEST_CODEX_BIN="$TMP_DIR/fakebin/codex" \
python3 "$SCRIPT_DIR/nodeg-cell.py" judge \
  --run-id selftest-judge --tasks F7 --repo-root "$REPO" --ceiling-root "$CEILING" --resume \
  --deviations "$DEVIATIONS"
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
    --run-id selftest-judge --tasks F7 --repo-root "$REPO" --ceiling-root "$CEILING" "$@"
}

if run_verdict > "$TMP_DIR/verdict-no-deviation.stdout" 2> "$TMP_DIR/verdict-no-deviation.stderr"; then
  echo "verdict accepted changed runner without deviations" >&2
  exit 1
fi
grep -q 'runner commit changed after cell initialization' "$TMP_DIR/verdict-no-deviation.stderr"

run_verdict --deviations "$DEVIATIONS" > "$TMP_DIR/verdict.stdout"
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
if verdict["bars"]["quality"]["quality_label"] != "post-hoc instrument-repaired":
    raise SystemExit(verdict["bars"]["quality"])
if {entry["type"] for entry in verdict["deviations"]} != {
    "judge-runner-sha",
    "opaque-paths-artifact-dir",
}:
    raise SystemExit(verdict["deviations"])
PY

RUNTIME_DEVIATIONS="$TMP_DIR/runtime-deviations.json"
python3 - "$DEVIATIONS" "$RUNTIME_DEVIATIONS" "$TASK" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
payload["deviations"].append(
    {
        "type": "a-runtime-attestation-source",
        "task": sys.argv[3],
        "reason": "timed-out A attempt has no stream-json summary",
    }
)
with open(sys.argv[2], "w", encoding="utf-8") as handle:
    json.dump(payload, handle)
    handle.write("\n")
PY
if run_verdict --deviations "$RUNTIME_DEVIATIONS" \
  > "$TMP_DIR/runtime-healthy.stdout" 2> "$TMP_DIR/runtime-healthy.stderr"; then
  echo "runtime attestation deviation was accepted for a healthy row" >&2
  exit 1
fi
grep -q 'deviation provided but transcript/timing checks do not match' "$TMP_DIR/runtime-healthy.stderr"

printf '{"invoke_exit":124,"timed_out":true,"elapsed_seconds":100}\n' > "$JUDGE_RUN/A1/timing.json"
: > "$JUDGE_RUN/A1/transcript.txt"
printf 'path=/tmp/claude-homes\nmodel=claude-sonnet-fake\nretry model=claude-sonnet-fake\n' \
  > "$JUDGE_RUN/A1/claude-debug.log"
if run_verdict --deviations "$DEVIATIONS" \
  > "$TMP_DIR/runtime-missing.stdout" 2> "$TMP_DIR/runtime-missing.stderr"; then
  echo "empty timed-out transcript was accepted without runtime attestation deviation" >&2
  exit 1
fi
grep -q 'requires a-runtime-attestation-source deviation' "$TMP_DIR/runtime-missing.stderr"

run_verdict --deviations "$RUNTIME_DEVIATIONS" > "$TMP_DIR/runtime-verdict.stdout"
python3 - "$CEILING/results/selftest-judge/nodeg-verdict.json" "$TASK" <<'PY'
import json
import sys

verdict = json.load(open(sys.argv[1], encoding="utf-8"))
attestation = verdict["a_runtime_attestations"][sys.argv[2]]
if attestation["scan"] != {"hits": 2, "distinct_models": ["claude-sonnet-fake"]}:
    raise SystemExit(attestation)
if attestation["deviation"] != {
    "type": "a-runtime-attestation-source",
    "task": sys.argv[2],
    "reason": "timed-out A attempt has no stream-json summary",
}:
    raise SystemExit(attestation)
if {entry["type"] for entry in verdict["deviations"]} != {
    "judge-runner-sha",
    "opaque-paths-artifact-dir",
    "a-runtime-attestation-source",
}:
    raise SystemExit(verdict["deviations"])
PY

printf 'model=claude-sonnet-fake\nmodel=claude-opus-fake\n' > "$JUDGE_RUN/A1/claude-debug.log"
if run_verdict --deviations "$RUNTIME_DEVIATIONS" \
  > "$TMP_DIR/runtime-wrong.stdout" 2> "$TMP_DIR/runtime-wrong.stderr"; then
  echo "anchored non-sonnet runtime model was accepted" >&2
  exit 1
fi
grep -q 'debug model attestation missing or not sonnet' "$TMP_DIR/runtime-wrong.stderr"

printf 'requested_model=claude-sonnet-fake\n' > "$JUDGE_RUN/A1/claude-debug.log"
if run_verdict --deviations "$RUNTIME_DEVIATIONS" \
  > "$TMP_DIR/runtime-zero.stdout" 2> "$TMP_DIR/runtime-zero.stderr"; then
  echo "debug log with zero anchored runtime model hits was accepted" >&2
  exit 1
fi
grep -q 'debug model attestation missing or not sonnet' "$TMP_DIR/runtime-zero.stderr"

printf '{"deviations":{}}\n' > "$TMP_DIR/malformed-deviations.json"
if run_verdict --deviations "$TMP_DIR/malformed-deviations.json" \
  > "$TMP_DIR/malformed.stdout" 2> "$TMP_DIR/malformed.stderr"; then
  echo "malformed deviations did not fail" >&2
  exit 1
fi
grep -q 'deviations file must be an object containing only a deviations array' "$TMP_DIR/malformed.stderr"

printf '{"deviations":[{"type":"unregistered"}]}\n' > "$TMP_DIR/unknown-deviations.json"
if run_verdict --deviations "$TMP_DIR/unknown-deviations.json" \
  > "$TMP_DIR/unknown.stdout" 2> "$TMP_DIR/unknown.stderr"; then
  echo "unknown deviation type did not fail" >&2
  exit 1
fi
grep -q 'unknown deviation type' "$TMP_DIR/unknown.stderr"

printf '{"opaque_paths":{"passed":true}}\n' > "$JUDGE_RUN/A1/isolation.json"
sed -i.bak "s/$ATTEMPT_RUNNER_SHA/$JUDGE_RUNNER_SHA/" \
  "$CEILING/results/selftest-judge/nodeg-cohort.json"
rm "$CEILING/results/selftest-judge/nodeg-cohort.json.bak"
printf '{"deviations":[{"type":"judge-runner-sha","attempt_runner_sha":"%s","judge_runner_sha":"%s","reason":"should fail","decision_ref":"selftest"},{"type":"opaque-paths-artifact-dir","driver_line":"run-nodeg-cell.sh:75","prompt_grep_hits":0,"other_checks":"all-true","materiality":"attestation-layer"}]}\n' \
  "$JUDGE_RUNNER_SHA" "$JUDGE_RUNNER_SHA" > "$TMP_DIR/unneeded-deviations.json"
if python3 "$SCRIPT_DIR/nodeg-cell.py" judge \
  --run-id selftest-judge --tasks F7 --repo-root "$REPO" --ceiling-root "$CEILING" \
  --deviations "$TMP_DIR/unneeded-deviations.json" \
  > "$TMP_DIR/unneeded.stdout" 2> "$TMP_DIR/unneeded.stderr"; then
  echo "deviations were accepted while checks passed" >&2
  exit 1
fi
grep -q 'deviation provided but runner SHA check passes' "$TMP_DIR/unneeded.stderr"

python3 -m py_compile "$SCRIPT_DIR/nodeg-cell.py"
bash -n "$SCRIPT_DIR/run-nodeg-cell.sh" "$SCRIPT_DIR/test-nodeg-cell.sh"
echo "PASS test-nodeg-cell"
