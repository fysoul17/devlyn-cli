#!/usr/bin/env bash
# Focused offline regression tests for the ceiling harness plumbing.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CEILING_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$CEILING_ROOT/../.." && pwd)"
TMP_DIR="$(mktemp -d /tmp/nx-selftest.XXXXXX)"
RESULT_RUNS=()
cleanup() {
  rm -rf "$TMP_DIR"
  for run in "${RESULT_RUNS[@]:-}"; do
    rm -rf "$CEILING_ROOT/results/$run"
  done
}
trap cleanup EXIT

FAKEBIN="$TMP_DIR/fakebin"
mkdir -p "$FAKEBIN"

cat > "$FAKEBIN/claude" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [ "${1:-}" = "--version" ]; then
  echo "claude fake 1.0"
  exit 0
fi
prompt=""
output_json=0
arm_mode=0
while [ $# -gt 0 ]; do
  case "$1" in
    -p) prompt="$2"; shift 2;;
    --output-format) output_json=1; shift 2;;
    --setting-sources) arm_mode=1; shift 2;;
    *) shift;;
  esac
done
printf '%s' "$prompt" >> "$HOME/fake-claude-prompts.txt"
env | sort > "$HOME/fake-claude-env.txt"
command -v claude > "$HOME/nested-claude-path.txt"
command -v codex > "$HOME/nested-codex-path.txt"
stat -f '%Lp' "$CLAUDE_CONFIG_DIR/.credentials.json" > "$HOME/credentials-mode.txt"
if [ "$arm_mode" = 1 ] && [ -f bin/cli.js ] && [ -f tests/cli.test.js ]; then
  printf '\n// --format yaml\nconst drawReceipt = { status: 1 };\n' >> tests/cli.test.js
  git add tests/cli.test.js
  git -c user.name=selftest -c user.email=selftest@example.com commit -q -m implement-draw
  pre_sha="$(git rev-parse HEAD)"
  mkdir -p .devlyn
  printf 'post-implement patch\n' > .devlyn/surface-close.input.patch
  printf '<!-- devlyn:verification -->\n```json\n{"verification_commands":[{"cmd":"node --test tests/","exit_code":0}]}\n```\n' \
    > .devlyn/criteria.generated.md
  python3 - "$pre_sha" <<'PY'
import datetime as dt
import json
import pathlib
import sys

now = dt.datetime.now(dt.timezone.utc)
stamp = now.isoformat(timespec="milliseconds").replace("+00:00", "Z")
pathlib.Path(".devlyn/pipeline.state.json").write_text(json.dumps({
    "started_at": stamp,
    "phases": {"surface_close": {
        "pre_sha": sys.argv[1], "started_at": stamp, "completed_at": None,
        "duration_ms": None, "verdict": None,
    }},
}) + "\n")
PY
  sleep 30
  exit 9
fi
if [[ "$prompt" == *emit-user-memory-leak* ]]; then
  echo 'Persistent private instruction unique to this isolation selftest.'
  exit 0
fi
if [ "$arm_mode" = 1 ]; then
  printf 'changed by A\n' >> app.txt
  printf 'harness mutation\n' >> CLAUDE.md
  mkdir -p .claude/skills/fake .devlyn
  printf 'harness mutation\n' > .claude/skills/fake/extra.txt
  printf 'state\n' > .devlyn/state.json
  if [ -d .git ]; then python3 - <<'PY'
import datetime as dt
import json
import pathlib

completed = dt.datetime.now(dt.timezone.utc)
started = completed - dt.timedelta(milliseconds=10)
stamp = lambda value: value.isoformat(timespec="milliseconds").replace("+00:00", "Z")
path = pathlib.Path(".devlyn/runs/fake/pipeline.state.json")
path.parent.mkdir(parents=True)
path.write_text(json.dumps({
    "started_at": stamp(started),
    "phases": {"plan": {
        "started_at": stamp(started), "completed_at": stamp(completed),
        "duration_ms": 10, "verdict": "PASS",
    }},
}) + "\n")
PY
  fi
  if [[ "$prompt" == *emit-wrong-model* ]]; then
    echo '{"result":"fake claude done","modelUsage":{"claude-opus-fake":{}}}'
  else
    echo '{"result":"fake claude done","modelUsage":{"claude-sonnet-fake":{}}}'
  fi
  exit 0
fi
if [ "$output_json" = 1 ]; then
  cat <<'JSON'
{"result":"{\"axes\":{\"design_coherence\":{\"tiers\":[[\"P1\",\"P2\",\"P3\"]],\"strict_win_deltas\":[]},\"robustness\":{\"tiers\":[[\"P1\",\"P2\",\"P3\"]],\"strict_win_deltas\":[]},\"spec_long_horizon_consistency\":{\"tiers\":[[\"P1\",\"P2\",\"P3\"]],\"strict_win_deltas\":[]},\"maintainability_api_ergonomics\":{\"tiers\":[[\"P1\",\"P2\",\"P3\"]],\"strict_win_deltas\":[]}}}","modelUsage":{"claude-sonnet-fake":{"inputTokens":1,"outputTokens":1}}}
JSON
  exit 0
fi
printf 'changed by A\n' >> app.txt
printf 'harness mutation\n' >> CLAUDE.md
mkdir -p .claude/skills/fake .devlyn
printf 'harness mutation\n' > .claude/skills/fake/extra.txt
printf 'state\n' > .devlyn/state.json
echo "fake claude done"
EOF
chmod +x "$FAKEBIN/claude"
mkdir -p "$TMP_DIR/claude-versions" "$TMP_DIR/claude-direct"
cp "$FAKEBIN/claude" "$TMP_DIR/claude-versions/2.1.207"
ln -s "$TMP_DIR/claude-versions/2.1.207" "$TMP_DIR/claude-direct/claude"
TEST_CLAUDE_BIN="$TMP_DIR/claude-direct/claude"

cat > "$FAKEBIN/codex" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [ "${1:-}" = "--version" ]; then
  echo "codex fake 1.0"
  exit 0
fi
[ "${1:-}" = "exec" ] || { echo "unexpected codex args: $*" >&2; exit 2; }
prompt="${@: -1}"
if [ "${FAKE_CODEX_JUDGE:-0}" = "1" ]; then
  cat <<'JSON'
{"axes":{"design_coherence":{"tiers":[["P1","P2","P3"]],"strict_win_deltas":[]},"robustness":{"tiers":[["P1","P2","P3"]],"strict_win_deltas":[]},"spec_long_horizon_consistency":{"tiers":[["P1","P2","P3"]],"strict_win_deltas":[]},"maintainability_api_ergonomics":{"tiers":[["P1","P2","P3"]],"strict_win_deltas":[]}}}
JSON
  exit 0
fi
case "$prompt" in
  "Fix or implement"*) label=B ;;
  *) label=C ;;
esac
printf '%s' "$prompt" > .nx-prompt
env | sort > .nx-env
git remote > .nx-remotes
git log -1 --format='%an <%ae>|%aI|%s' > .nx-log
if [ -d .git/logs ]; then find .git/logs -type f -print | sort > .nx-reflogs; else : > .nx-reflogs; fi
root="$PWD"
for _ in 1 2 3 4 5 6; do root="$(dirname "$root")"; done
find "$root" -name opaque-map.json -print > .nx-map-visible
printf 'changed by %s\n' "$label" >> app.txt
echo "fake codex done"
EOF
chmod +x "$FAKEBIN/codex"

make_repo() {
  local dir="$1"
  rm -rf "$dir"
  mkdir -p "$dir"
  (
    cd "$dir"
    git init -q
    printf 'base\n' > app.txt
    git add app.txt
    git -c user.email=test@example.com -c user.name=test commit -q -m base
  )
}

RUN_ID="selftest-$$"
RESULT_RUNS+=("$RUN_ID")
RUN_OWNED_CODEX_DIR="$TMP_DIR/run-owned-codex/$RUN_ID"
mkdir -p "$RUN_OWNED_CODEX_DIR"
RUN_OWNED_CODEX_DIR="$(cd "$RUN_OWNED_CODEX_DIR" && pwd -P)"
cp "$FAKEBIN/codex" "$RUN_OWNED_CODEX_DIR/codex"
RUN_OWNED_CODEX_BIN="$RUN_OWNED_CODEX_DIR/codex"
PROMPTS="$TMP_DIR/prompts"
mkdir -p "$PROMPTS"
export PATH="$FAKEBIN:$PATH"
case ":$PATH:" in
  *":$RUN_OWNED_CODEX_DIR:"*) echo "run-owned Codex unexpectedly present on exported PATH" >&2; exit 1;;
esac
export FAKE_CODEX_PROMPT_DIR="$PROMPTS"
TEST_EXTERNAL_ROOT="$TMP_DIR/nx01"
TEST_AUTH="$TMP_DIR/auth.json"
printf '{"token":"selftest"}\n' > "$TEST_AUTH"
chmod 0600 "$TEST_AUTH"
TEST_CLAUDE_CREDENTIALS="$TMP_DIR/claude-credentials.json"
printf '{"claudeAiOauth":{"accessToken":"selftest"}}\n' > "$TEST_CLAUDE_CREDENTIALS"
chmod 0600 "$TEST_CLAUDE_CREDENTIALS"

WORK_A="$TEST_EXTERNAL_ROOT/w/rt01/fx01/A1/repo"
make_repo "$WORK_A"
CEILING_EXTERNAL_ROOT="$TEST_EXTERNAL_ROOT" CEILING_TEST_AUTH_JSON="$TEST_AUTH" CEILING_TEST_CLAUDE_CREDENTIALS="$TEST_CLAUDE_CREDENTIALS" CEILING_TEST_CLAUDE_BIN="$TEST_CLAUDE_BIN" CEILING_TEST_CODEX_BIN="$RUN_OWNED_CODEX_BIN" CEILING_TEST_WORKTREE="$WORK_A" bash "$SCRIPT_DIR/run-ceiling-arm.sh" \
  --run-id "$RUN_ID" --task FS1-schedule-max-runs --arm A --attempt 1 --timeout-seconds 30 >/tmp/ceiling-arm-a.log
test -d "$WORK_A/.claude/skills"
test "$(cat "$WORK_A/.devlyn/engines.json")" = '{"executor":"codex"}'
grep -q 'changed by A' "$CEILING_ROOT/results/$RUN_ID/FS1-schedule-max-runs/A1/patch.diff"
! grep -q 'CLAUDE.md' "$CEILING_ROOT/results/$RUN_ID/FS1-schedule-max-runs/A1/patch.diff"
! grep -q '.claude' "$CEILING_ROOT/results/$RUN_ID/FS1-schedule-max-runs/A1/patch.diff"
! grep -q '.devlyn' "$CEILING_ROOT/results/$RUN_ID/FS1-schedule-max-runs/A1/patch.diff"
python3 - "$CEILING_ROOT/results/$RUN_ID/FS1-schedule-max-runs/A1/isolation.json" "$CEILING_ROOT/results/$RUN_ID/FS1-schedule-max-runs/A1/timing.json" "$CEILING_ROOT/results/$RUN_ID/FS1-schedule-max-runs/A1/attribution.json" "$TEST_CLAUDE_BIN" "$RUN_OWNED_CODEX_BIN" <<'PY'
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
timing = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
attribution = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
direct = data["direct_claude"]
expected = Path(sys.argv[4]).parent.resolve() / Path(sys.argv[4]).name
if direct["path"] != str(expected) or direct["superset_wrapper"]:
    raise SystemExit(direct)
if not data["credentials_seeded"] or data["auth_mechanism"] != "test-file":
    raise SystemExit("Claude credential attestation missing")
if Path(data["claude_config_dir"], ".credentials.json").exists():
    raise SystemExit("Claude credential file survived attempt cleanup")
if data["claude_env_keys"] != sorted(data["claude_env_keys"]):
    raise SystemExit("Claude env keys are not sorted")
shim = Path(data["shim_path"])
target = Path(data["shim_target"])
if not shim.is_symlink() or shim.resolve() != target or target != expected.resolve():
    raise SystemExit("Claude shim target attestation mismatch")
if data["shim_target_sha256"] != direct["sha256"]:
    raise SystemExit("Claude shim sha attestation mismatch")
if Path(data["frozen_path"].split(":")[0]) != shim.parent:
    raise SystemExit("Claude shim is not first on frozen PATH")
command_v = data["command_v_claude"]
if command_v.get("path") != str(shim) or command_v.get("sha256") != direct["sha256"]:
    raise SystemExit("command -v claude attestation mismatch")
path_parts = data["environment"]["keys"]
if "CLAUDE_CONFIG_DIR" not in path_parts or not data["forbidden_transcript_scan"]["passed"]:
    raise SystemExit(data)
if timing.get("schema_version") != 2:
    raise SystemExit(timing)
stamp_pattern = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$")
if not all(stamp_pattern.fullmatch(timing.get(field, "")) for field in ("invoke_started_at", "invoke_completed_at")):
    raise SystemExit(timing)
started = dt.datetime.fromisoformat(timing["invoke_started_at"].replace("Z", "+00:00"))
completed = dt.datetime.fromisoformat(timing["invoke_completed_at"].replace("Z", "+00:00"))
if started.tzinfo is None or completed < started:
    raise SystemExit(timing)
if attribution.get("decomposition_status") != "complete" or abs(attribution.get("conservation_residue_ms", 1001)) > 1000:
    raise SystemExit(attribution)
codex = data["direct_codex"]
codex_path = Path(sys.argv[5]).resolve()
if codex["path"] != str(codex_path) or codex["sha256"] != hashlib.sha256(codex_path.read_bytes()).hexdigest():
    raise SystemExit(codex)
PY
EXPECTED_NESTED_CLAUDE="$(python3 -c 'import pathlib,sys; p=pathlib.Path(sys.argv[1]); print(p.parent.resolve() / p.name)' "$TEST_EXTERNAL_ROOT/claude-homes/r$(printf '%s' "$RUN_ID" | shasum -a 256 | cut -c1-12)/f$(printf '%s' FS1-schedule-max-runs | shasum -a 256 | cut -c1-12)/A1/b/claude")"
test "$(cat "$TEST_EXTERNAL_ROOT/claude-homes/r$(printf '%s' "$RUN_ID" | shasum -a 256 | cut -c1-12)/f$(printf '%s' FS1-schedule-max-runs | shasum -a 256 | cut -c1-12)/A1/nested-claude-path.txt")" = "$EXPECTED_NESTED_CLAUDE"
test "$(cat "$TEST_EXTERNAL_ROOT/claude-homes/r$(printf '%s' "$RUN_ID" | shasum -a 256 | cut -c1-12)/f$(printf '%s' FS1-schedule-max-runs | shasum -a 256 | cut -c1-12)/A1/nested-codex-path.txt")" = "$RUN_OWNED_CODEX_BIN"
test "$(cat "$TEST_EXTERNAL_ROOT/claude-homes/r$(printf '%s' "$RUN_ID" | shasum -a 256 | cut -c1-12)/f$(printf '%s' FS1-schedule-max-runs | shasum -a 256 | cut -c1-12)/A1/credentials-mode.txt")" = 600

DRAW_RESULT="$TEST_EXTERNAL_ROOT/x/rtdraw/fxdraw/A1"
set +e
CEILING_EXTERNAL_ROOT="$TEST_EXTERNAL_ROOT" CEILING_TEST_AUTH_JSON="$TEST_AUTH" CEILING_TEST_CLAUDE_CREDENTIALS="$TEST_CLAUDE_CREDENTIALS" CEILING_TEST_CLAUDE_BIN="$TEST_CLAUDE_BIN" CEILING_TEST_CODEX_BIN="$FAKEBIN/codex" \
  bash "$SCRIPT_DIR/run-ceiling-arm.sh" \
    --run-id selftest-draw --task DR-byte-preservation-f7-out-of-scope-trap \
    --arm A --attempt 1 --opaque-run-id rtdraw --opaque-task-id fxdraw \
    --result-dir "$DRAW_RESULT" --f7-diagnostic-row --timeout-seconds 20 \
    > "$TMP_DIR/draw.stdout" 2> "$TMP_DIR/draw.stderr"
draw_exit=$?
set -e
test "$draw_exit" -eq 86
test -f "$DRAW_RESULT/draw-non-diagnostic.json"
test -d "$DRAW_RESULT/devlyn-snapshot"
python3 - "$DRAW_RESULT/draw-non-diagnostic.json" "$DRAW_RESULT/timing.json" <<'PY'
import json
import sys

marker = json.load(open(sys.argv[1], encoding="utf-8"))
timing = json.load(open(sys.argv[2], encoding="utf-8"))
if marker.get("pre7") is not False or marker.get("pre8") is not True:
    raise SystemExit(marker)
if timing.get("invoke_exit") != 86 or timing.get("draw_non_diagnostic") is not True:
    raise SystemExit(timing)
PY

AUTH_FAIL_RESULT="$TEST_EXTERNAL_ROOT/x/rt01/fxauth/A1"
if CEILING_EXTERNAL_ROOT="$TEST_EXTERNAL_ROOT" CEILING_TEST_AUTH_JSON="$TEST_AUTH" CEILING_TEST_CLAUDE_CREDENTIALS="$TMP_DIR/missing-credentials.json" CEILING_TEST_CLAUDE_BIN="$TEST_CLAUDE_BIN" CEILING_TEST_CODEX_BIN="$FAKEBIN/codex" \
  bash "$SCRIPT_DIR/run-ceiling-arm.sh" \
    --run-id "$RUN_ID" --task FS1-schedule-max-runs --arm A --attempt 1 \
    --opaque-run-id rt01 --opaque-task-id fxauth --result-dir "$AUTH_FAIL_RESULT" \
    --timeout-seconds 30 > "$TMP_DIR/a-auth-fail.stdout" 2> "$TMP_DIR/a-auth-fail.stderr"; then
  echo "A-arm missing Claude credentials did not fail closed" >&2
  exit 1
fi
python3 - "$AUTH_FAIL_RESULT/claude-isolation.json" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
if data["credentials_seeded"] is not False:
    raise SystemExit(data)
PY
test ! -e "$TEST_EXTERNAL_ROOT/claude-homes/rt01/fxauth/A1/.claude/.credentials.json"

PURITY_WORK="$TMP_DIR/purity-work"
PURITY_HOME="$TMP_DIR/purity-home"
PURITY_CODEX_HOME="$TMP_DIR/purity-codex"
PURITY_PROMPT="$TMP_DIR/purity-prompt.txt"
PURITY_MEMORY="$TMP_DIR/user-CLAUDE.md"
mkdir -p "$PURITY_WORK"
printf 'Persistent private instruction unique to this isolation selftest.\n' > "$PURITY_MEMORY"
printf 'clean probe\n' > "$PURITY_PROMPT"
CEILING_TEST_AUTH_JSON="$TEST_AUTH" CEILING_TEST_CLAUDE_CREDENTIALS="$TEST_CLAUDE_CREDENTIALS" CEILING_TEST_CLAUDE_BIN="$TEST_CLAUDE_BIN" CEILING_TEST_CODEX_BIN="$FAKEBIN/codex" \
  python3 "$SCRIPT_DIR/claude-isolation.py" launch \
    --mode arm --home "$PURITY_HOME" --codex-home "$PURITY_CODEX_HOME" \
    --workdir "$PURITY_WORK" --prompt-file "$PURITY_PROMPT" \
    --metadata-out "$TMP_DIR/purity-clean.json" --user-memory-file "$PURITY_MEMORY" \
    > "$TMP_DIR/purity-clean.stdout" 2> "$TMP_DIR/purity-clean.stderr"
test -s "$TMP_DIR/purity-clean.stdout"
test ! -e "$PURITY_HOME/.claude/.credentials.json"

printf 'emit-user-memory-leak\n' > "$PURITY_PROMPT"
if CEILING_TEST_AUTH_JSON="$TEST_AUTH" CEILING_TEST_CLAUDE_CREDENTIALS="$TEST_CLAUDE_CREDENTIALS" CEILING_TEST_CLAUDE_BIN="$TEST_CLAUDE_BIN" CEILING_TEST_CODEX_BIN="$FAKEBIN/codex" \
  python3 "$SCRIPT_DIR/claude-isolation.py" launch \
    --mode arm --home "$PURITY_HOME" --codex-home "$PURITY_CODEX_HOME" \
    --workdir "$PURITY_WORK" --prompt-file "$PURITY_PROMPT" \
    --metadata-out "$TMP_DIR/purity-leak.json" --user-memory-file "$PURITY_MEMORY" \
    > "$TMP_DIR/purity-leak.stdout" 2> "$TMP_DIR/purity-leak.stderr"; then
  echo "user-memory-leak transcript was not rejected" >&2
  exit 1
fi
grep -q 'CLAUDE_ISOLATION_ERROR: user-memory-leak:' "$TMP_DIR/purity-leak.stderr"
test ! -e "$PURITY_HOME/.claude/.credentials.json"

printf 'emit-wrong-model\n' > "$PURITY_PROMPT"
if CEILING_TEST_AUTH_JSON="$TEST_AUTH" CEILING_TEST_CLAUDE_CREDENTIALS="$TEST_CLAUDE_CREDENTIALS" CEILING_TEST_CLAUDE_BIN="$TEST_CLAUDE_BIN" CEILING_TEST_CODEX_BIN="$FAKEBIN/codex" \
  python3 "$SCRIPT_DIR/claude-isolation.py" launch \
    --mode arm --home "$PURITY_HOME" --codex-home "$PURITY_CODEX_HOME" \
    --workdir "$PURITY_WORK" --prompt-file "$PURITY_PROMPT" \
    --metadata-out "$TMP_DIR/purity-wrong-model.json" --user-memory-file "$PURITY_MEMORY" \
    > "$TMP_DIR/purity-wrong-model.stdout" 2> "$TMP_DIR/purity-wrong-model.stderr"; then
  echo "wrong Claude runtime model did not fail closed" >&2
  exit 1
fi
grep -q 'CLAUDE_ISOLATION_ERROR: runtime model is not sonnet' "$TMP_DIR/purity-wrong-model.stderr"
test ! -e "$PURITY_HOME/.claude/.credentials.json"

if CEILING_TEST_AUTH_JSON="$TEST_AUTH" CEILING_TEST_CLAUDE_CREDENTIALS="$TMP_DIR/missing-credentials.json" CEILING_TEST_CLAUDE_BIN="$TEST_CLAUDE_BIN" CEILING_TEST_CODEX_BIN="$FAKEBIN/codex" \
  python3 "$SCRIPT_DIR/claude-isolation.py" launch \
    --mode arm --home "$PURITY_HOME" --codex-home "$PURITY_CODEX_HOME" \
    --workdir "$PURITY_WORK" --prompt-file "$PURITY_PROMPT" \
    --metadata-out "$TMP_DIR/purity-auth-fail.json" --user-memory-file "$PURITY_MEMORY" \
    > "$TMP_DIR/purity-auth-fail.stdout" 2> "$TMP_DIR/purity-auth-fail.stderr"; then
  echo "missing Claude credentials did not fail closed" >&2
  exit 1
fi
python3 - "$TMP_DIR/purity-auth-fail.json" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
if data["credentials_seeded"] is not False:
    raise SystemExit(data)
PY
test ! -e "$PURITY_HOME/.claude/.credentials.json"

WORK_B="$TEST_EXTERNAL_ROOT/w/rt01/fx01/B1/repo"
RESULT_B="$TEST_EXTERNAL_ROOT/x/rt01/fx01/B1"
make_repo "$WORK_B"
CEILING_EXTERNAL_ROOT="$TEST_EXTERNAL_ROOT" CEILING_TEST_AUTH_JSON="$TEST_AUTH" CEILING_TEST_CODEX_BIN="$FAKEBIN/codex" CEILING_TEST_WORKTREE="$WORK_B" bash "$SCRIPT_DIR/run-ceiling-arm.sh" \
  --run-id "$RUN_ID" --task FS1-schedule-max-runs --arm B --attempt 1 --opaque-run-id rt01 --opaque-task-id fx01 --result-dir "$RESULT_B" --timeout-seconds 30 >/tmp/ceiling-arm-b.log
python3 - "$CEILING_ROOT/corpus/FS1-schedule-max-runs/task.txt" "$WORK_B/.nx-prompt" <<'PY'
import sys
from pathlib import Path
expected = "Fix or implement the following in this repository. Verify your work before finishing.\n\n" + Path(sys.argv[1]).read_text(encoding="utf-8").rstrip("\n")
actual = Path(sys.argv[2]).read_text(encoding="utf-8")
if actual != expected:
    raise SystemExit("B prompt mismatch")
PY
grep -q '^HOME=.*/h/rt01/fx01/B1$' "$WORK_B/.nx-env"
grep -q '^CODEX_HOME=.*/d/rt01/fx01/B1$' "$WORK_B/.nx-env"
grep -q '^GIT_CONFIG_GLOBAL=/dev/null$' "$WORK_B/.nx-env"
grep -q '^TZ=UTC$' "$WORK_B/.nx-env"
! grep -Eiq 'CLAUDE|SUPERSET|DEVLYN|CODEX_COMPANION|SSH_AUTH_SOCK|FAKE_CODEX|ZDOTDIR' "$WORK_B/.nx-env"
test ! -s "$WORK_B/.nx-remotes"
test ! -s "$WORK_B/.nx-reflogs"
test ! -s "$WORK_B/.nx-map-visible"
test "$(cat "$WORK_B/.nx-log")" = 'Project Maintainer <maintainer@example.com>|2000-01-01T00:00:00Z|Initial project snapshot'
test ! -L "$TEST_EXTERNAL_ROOT/d/rt01/fx01/B1/auth.json"
test "$(stat -f '%Lp' "$TEST_EXTERNAL_ROOT/d/rt01/fx01/B1/auth.json")" = 600
python3 - "$RESULT_B/isolation.json" "$FAKEBIN/codex" <<'PY'
import hashlib, json, sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text())
expected = sorted(["PATH","HOME","CODEX_HOME","TERM","LANG","LC_ALL","TZ","TMPDIR","GIT_CONFIG_NOSYSTEM","GIT_CONFIG_GLOBAL","NPM_CONFIG_USERCONFIG","NPM_CONFIG_CACHE"])
if data["environment"]["keys"] != expected or not data["environment"]["forbidden_values_absent"]:
    raise SystemExit(data["environment"])
if not data["opaque_paths"]["passed"] or not data["shell_startup_canary"]["passed"]:
    raise SystemExit(data)
if data["direct_codex"]["path"] != str(Path(sys.argv[2]).resolve()) or data["direct_codex"]["superset_wrapper"]:
    raise SystemExit(data["direct_codex"])
if data["direct_codex"]["sha256"] != hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest():
    raise SystemExit(data["direct_codex"])
if data["auth"]["is_symlink"] or data["auth"]["mode"] != "0600":
    raise SystemExit(data["auth"])
if not data["forbidden_transcript_scan"]["passed"]:
    raise SystemExit(data["forbidden_transcript_scan"])
PY

WORK_C="$TEST_EXTERNAL_ROOT/w/rt01/fx02/C1/repo"
RESULT_C="$TEST_EXTERNAL_ROOT/x/rt01/fx02/C1"
make_repo "$WORK_C"
CEILING_EXTERNAL_ROOT="$TEST_EXTERNAL_ROOT" CEILING_TEST_AUTH_JSON="$TEST_AUTH" CEILING_TEST_CODEX_BIN="$FAKEBIN/codex" CEILING_TEST_WORKTREE="$WORK_C" bash "$SCRIPT_DIR/run-ceiling-arm.sh" \
  --run-id "$RUN_ID" --task FS1-schedule-max-runs --arm C --attempt 1 --opaque-run-id rt01 --opaque-task-id fx02 --result-dir "$RESULT_C" --timeout-seconds 30 >/tmp/ceiling-arm-c.log
python3 - "$CEILING_ROOT/corpus/copycat-doc.md" "$CEILING_ROOT/corpus/FS1-schedule-max-runs/task.txt" "$WORK_C/.nx-prompt" <<'PY'
import sys
from pathlib import Path
expected = (
    Path(sys.argv[1]).read_text(encoding="utf-8")
    + "\n\nFollow the methodology above end-to-end yourself (plan, implement, build gate, cleanup, then a fresh-eyes verification pass) while completing this task:\n\n"
    + Path(sys.argv[2]).read_text(encoding="utf-8").rstrip("\n")
)
actual = Path(sys.argv[3]).read_text(encoding="utf-8")
if actual != expected:
    raise SystemExit("C prompt mismatch")
PY

BUNDLE="$CEILING_ROOT/corpus/DR-byte-preservation-f7-out-of-scope-trap/source.bundle"
BUNDLE_SHA_BEFORE="$(shasum -a 256 "$BUNDLE" | awk '{print $1}')"
NEUTRAL_ONE="$TMP_DIR/n1"
NEUTRAL_TWO="$TMP_DIR/n2"
git clone -q "$BUNDLE" "$NEUTRAL_ONE"
git clone -q "$BUNDLE" "$NEUTRAL_TWO"
python3 "$SCRIPT_DIR/neutralize-workspace.py" --workspace "$NEUTRAL_ONE" --seed-derived --report "$TMP_DIR/n1.json" >/dev/null
python3 "$SCRIPT_DIR/neutralize-workspace.py" --workspace "$NEUTRAL_TWO" --seed-derived --report "$TMP_DIR/n2.json" >/dev/null
python3 - "$TMP_DIR/n1.json" "$TMP_DIR/n2.json" <<'PY'
import json, sys
a, b = (json.load(open(path)) for path in sys.argv[1:])
for key in ("neutralization_diff_sha256", "neutral_baseline_sha"):
    if a[key] != b[key]:
        raise SystemExit(f"non-deterministic {key}: {a[key]} != {b[key]}")
PY
grep -q 'TODO(devlyn)' "$NEUTRAL_ONE/bin/cli.js"
! rg -i 'devlyn-cli|auto-resolve benchmark|benchmark fixture|bench-test-repo' "$NEUTRAL_ONE/README.md" "$NEUTRAL_ONE/package.json" "$NEUTRAL_ONE/package-lock.json" "$NEUTRAL_ONE/bin/cli.js" "$NEUTRAL_ONE/playwright.config.js" "$NEUTRAL_ONE/server/index.js" "$NEUTRAL_ONE/web/index.html"
test -z "$(git -C "$NEUTRAL_ONE" remote)"
test ! -d "$NEUTRAL_ONE/.git/logs"
test "$BUNDLE_SHA_BEFORE" = "$(shasum -a 256 "$BUNDLE" | awk '{print $1}')"

PATCH_SOURCE="$TMP_DIR/patch-source"
ORIGINAL_PATCH="$TMP_DIR/original-context.patch"
TRANSPORTED_PATCH="$TMP_DIR/transported.patch"
TRANSPORTED_TWICE_PATCH="$TMP_DIR/transported-twice.patch"
git clone -q "$BUNDLE" "$PATCH_SOURCE"
python3 - "$PATCH_SOURCE" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])
server = root / "server/index.js"
server_text = server.read_text(encoding="utf-8")
server_identity = "// Tiny Express server used by backend-contract fixtures. Intentionally small."
server.write_text(
    server_text.replace(server_identity, server_identity + "\n// transported server change", 1),
    encoding="utf-8",
)

cli = root / "bin/cli.js"
cli_text = cli.read_text(encoding="utf-8")
cli_identity = "// Fixtures extend or modify this file; keep the baseline minimal and obvious."
cli_text = cli_text.replace(
    cli_identity,
    cli_identity + "\n// transported CLI change",
    1,
)
cli_text = cli_text.replace(
    "function parseGreetingFormat(_argv) {",
    "function parseGreetingFormat(argv) {",
    1,
)
cli.write_text(cli_text, encoding="utf-8")
PY
git -C "$PATCH_SOURCE" diff --binary --no-ext-diff HEAD -- . > "$ORIGINAL_PATCH"
grep -Fq '// Tiny Express server used by backend-contract fixtures. Intentionally small.' "$ORIGINAL_PATCH"
grep -Fq '// bench-test-repo — tiny CLI used as the deterministic base for benchmark fixtures.' "$ORIGINAL_PATCH"
grep -Fq '// Fixtures extend or modify this file; keep the baseline minimal and obvious.' "$ORIGINAL_PATCH"
grep -Fq '// TODO(devlyn): this helper is unused — leftover from an abandoned refactor.' "$ORIGINAL_PATCH"
if git -C "$NEUTRAL_ONE" apply --check "$ORIGINAL_PATCH" >/dev/null 2>&1; then
  echo "original identity-context patch unexpectedly applied to neutralized tree" >&2
  exit 1
fi
python3 "$SCRIPT_DIR/neutralize-workspace.py" \
  --transform-patch "$ORIGINAL_PATCH" "$TRANSPORTED_PATCH"
git -C "$NEUTRAL_ONE" apply --check "$TRANSPORTED_PATCH"
git -C "$NEUTRAL_ONE" apply "$TRANSPORTED_PATCH"
grep -Fq '// transported server change' "$NEUTRAL_ONE/server/index.js"
grep -Fq '// transported CLI change' "$NEUTRAL_ONE/bin/cli.js"
grep -Fq 'function parseGreetingFormat(argv) {' "$NEUTRAL_ONE/bin/cli.js"
python3 "$SCRIPT_DIR/neutralize-workspace.py" \
  --transform-patch "$TRANSPORTED_PATCH" "$TRANSPORTED_TWICE_PATCH"
cmp "$TRANSPORTED_PATCH" "$TRANSPORTED_TWICE_PATCH"
python3 - "$ORIGINAL_PATCH" "$TRANSPORTED_PATCH" <<'PY'
import sys
from pathlib import Path

todo = "// TODO(devlyn): this helper is unused — leftover from an abandoned refactor.".encode()
original, transported = (Path(path).read_bytes() for path in sys.argv[1:])
if original.count(todo) != 1 or transported.count(todo) != 1:
    raise SystemExit("TODO(devlyn) patch context did not pass through exactly")
PY
test "$BUNDLE_SHA_BEFORE" = "$(shasum -a 256 "$BUNDLE" | awk '{print $1}')"

EVAL_ATTEMPT="$TEST_EXTERNAL_ROOT/x/rt02/fx03/A1"
mkdir -p "$EVAL_ATTEMPT"
cp "$CEILING_ROOT/corpus/DR-byte-preservation-f7-out-of-scope-trap/hidden/reference.patch" "$EVAL_ATTEMPT/patch.diff"
python3 - "$TMP_DIR/n1.json" "$EVAL_ATTEMPT/isolation.json" <<'PY'
import json, sys
json.dump({"neutralization": json.load(open(sys.argv[1]))}, open(sys.argv[2], "w"))
PY
CEILING_EXTERNAL_ROOT="$TEST_EXTERNAL_ROOT" bash "$SCRIPT_DIR/ceiling-eval.sh" \
  --run-id selftest --task DR-byte-preservation-f7-out-of-scope-trap \
  --arm-attempt A1 --opaque-run-id rt02 --opaque-task-id fx03 \
  --attempt-dir "$EVAL_ATTEMPT" >/tmp/ceiling-eval-neutral.log
python3 - "$EVAL_ATTEMPT/objective.json" "$TMP_DIR/n1.json" <<'PY'
import json, sys
objective, neutral = (json.load(open(path)) for path in sys.argv[1:])
if not objective["resolved"]:
    raise SystemExit(objective)
if objective["neutral_baseline_sha"] != neutral["neutral_baseline_sha"]:
    raise SystemExit("evaluator neutral baseline mismatch")
PY

make_judge_quality() {
  local root="$1"
  local certified="${2:-sonnet}"
  mkdir -p "$root/cases" "$root/results/sonnet" "$root/results/codex"
  for case in WD1 WD2 WD3 WD4 SC1 SC2 SC3 SC4; do
    axis="no_workaround"
    [[ "$case" == SC* ]] && axis="scope_discipline"
    cat > "$root/cases/$case.json" <<JSON
{"id":"$case","ground_truth":{"type":"defect","class":"$axis","file":"x"}}
JSON
  done
  for case in WD1-CLEAN WD3-CLEAN SC1-CLEAN SC3-CLEAN; do
    cat > "$root/cases/$case.json" <<JSON
{"id":"$case","ground_truth":{"type":"clean"}}
JSON
  done
  for judge in sonnet codex; do
    mkdir -p "$root/results/$judge"
    if [ "$judge" = "$certified" ]; then
      echo '{"cli_version":"fake","model_id_or_alias":"fake","recorded_at_run_id":"selftest"}' > "$root/results/$judge/identity.json"
    else
      echo '{"cli_version":null,"model_id_or_alias":"fake","recorded_at_run_id":"selftest"}' > "$root/results/$judge/identity.json"
    fi
    for case_file in "$root"/cases/*.json; do
      case_id="$(basename "$case_file" .json)"
      for rep in 1 2; do
        if [[ "$case_id" == *CLEAN ]]; then
          echo '{"false_positive":false}' > "$root/results/$judge/$case_id-rep$rep.json"
        else
          echo '{"hit":true}' > "$root/results/$judge/$case_id-rep$rep.json"
        fi
      done
    done
  done
}

write_attempt() {
  local run="$1" task="$2" attempt="$3" elapsed="$4" exit_code="$5" timed_out="$6" resolved="$7" reg="${8:-0}"
  local dir="$CEILING_ROOT/results/$run/$task/$attempt"
  mkdir -p "$dir"
  cat > "$dir/timing.json" <<JSON
{"task":"$task","arm":"${attempt:0:1}","attempt":${attempt:1},"elapsed_seconds":$elapsed,"invoke_exit":$exit_code,"timed_out":$timed_out}
JSON
  cat > "$dir/objective.json" <<JSON
{"task":"$task","arm_attempt":"$attempt","resolved":$resolved,"f2p_passed":0,"f2p_total":1,"p2p_regressions":$reg,"tests_passed":0,"tests_total":1,"hidden_test_failures":$reg}
JSON
  printf 'diff --git a/app.txt b/app.txt\n+candidate change\n' > "$dir/patch.diff"
}

JQ="$TMP_DIR/jq"
make_judge_quality "$JQ" sonnet
export CEILING_JUDGE_QUALITY_CASES="$JQ/cases"
export CEILING_JUDGE_QUALITY_RESULTS="$JQ/results"
CEILING_TASKS="$(python3 - "$SCRIPT_DIR/ceiling-gate.py" <<'PY'
import runpy
import sys

gate = runpy.run_path(sys.argv[1])
print("\n".join(gate["task_ids"](None)))
PY
)"
CEILING_TASKS_CSV="$(printf '%s\n' "$CEILING_TASKS" | paste -sd, -)"

N_RUN="selftest-n-$$"
RESULT_RUNS+=("$N_RUN")
for task in $CEILING_TASKS; do
  write_attempt "$N_RUN" "$task" A1 100 0 false true
  write_attempt "$N_RUN" "$task" B1 10 0 false true
  write_attempt "$N_RUN" "$task" C1 10 0 false false
done
write_attempt "$N_RUN" SW1-django-13230 B1 9 1 false false
write_attempt "$N_RUN" SW1-django-13230 B2 49 0 false true
python3 "$SCRIPT_DIR/ceiling-gate.py" --run-id "$N_RUN" --phase select >/tmp/ceiling-select.log
python3 - "$CEILING_ROOT/results/$N_RUN/ceiling-selection.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
row = data["tasks"]["SW1-django-13230"]["n_rule"]
if row["status"] != "VALID" or row["denominator_attempt"] != "B2" or row["n"] != 2:
    raise SystemExit(row)
PY

INVALID_RUN="selftest-invalid-$$"
RESULT_RUNS+=("$INVALID_RUN")
for task in $CEILING_TASKS; do
  write_attempt "$INVALID_RUN" "$task" A1 10 0 false true
  write_attempt "$INVALID_RUN" "$task" B1 10 0 false true
  write_attempt "$INVALID_RUN" "$task" C1 10 0 false true
done
write_attempt "$INVALID_RUN" SW2-django-13265 B1 10 1 false false
write_attempt "$INVALID_RUN" SW2-django-13265 B2 10 124 true false
python3 "$SCRIPT_DIR/ceiling-gate.py" --run-id "$INVALID_RUN" --phase select >/tmp/ceiling-invalid-select.log
python3 - "$CEILING_ROOT/results/$INVALID_RUN/ceiling-selection.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
if data["tasks"]["SW2-django-13265"]["row_status"] != "INVALID-infra":
    raise SystemExit(data["tasks"]["SW2-django-13265"])
PY

TIE_RUN="selftest-tie-$$"
RESULT_RUNS+=("$TIE_RUN")
for task in $CEILING_TASKS; do
  write_attempt "$TIE_RUN" "$task" A1 20 0 false true
  write_attempt "$TIE_RUN" "$task" B1 10 0 false true
  write_attempt "$TIE_RUN" "$task" C1 10 0 false false
done
cat > "$CEILING_ROOT/results/$TIE_RUN/ceiling-judge-aggregate.json" <<'JSON'
{"run_id":"selftest","tasks":{}}
JSON
python3 "$SCRIPT_DIR/ceiling-gate.py" --run-id "$TIE_RUN" --phase verdict --tasks "$CEILING_TASKS_CSV" >/tmp/ceiling-tie.log
python3 - "$CEILING_ROOT/results/$TIE_RUN/ceiling-verdict.json" "$CEILING_ROOT/results/$TIE_RUN/ceiling-verdict.md" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
if data["verdict"] != "BARE-LIFT-NOT-SHOWN":
    raise SystemExit(data)
md = open(sys.argv[2], encoding="utf-8").read()
if "Excluding FS1-schedule-max-runs" not in md:
    raise SystemExit("missing FS1 leave-one-out note")
PY

MOAT_RUN="selftest-moat-$$"
RESULT_RUNS+=("$MOAT_RUN")
for task in $CEILING_TASKS; do
  write_attempt "$MOAT_RUN" "$task" A1 20 0 false true
  write_attempt "$MOAT_RUN" "$task" B1 10 0 false false
  write_attempt "$MOAT_RUN" "$task" C1 10 0 false true
done
python3 - "$CEILING_ROOT/results/$MOAT_RUN/ceiling-judge-aggregate.json" "$CEILING_TASKS_CSV" <<'PY'
import json, sys
axes = ["design_coherence","robustness","spec_long_horizon_consistency","maintainability_api_ergonomics"]
tasks = {}
for task in sys.argv[2].split(","):
    tasks[task] = {"axes": {}}
    for axis in axes:
        tasks[task]["axes"][axis] = {"per_judge":{"sonnet":{"a_vs_c":"A_win"}}}
json.dump({"run_id":"selftest","tasks":tasks}, open(sys.argv[1], "w"), indent=2)
PY
python3 "$SCRIPT_DIR/ceiling-gate.py" --run-id "$MOAT_RUN" --phase verdict --tasks "$CEILING_TASKS_CSV" >/tmp/ceiling-moat.log
python3 - "$CEILING_ROOT/results/$MOAT_RUN/ceiling-verdict.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
lc2 = data["loss_conditions"]["LC2_moat"]
if data["verdict"] != "MOAT-NOT-SHOWN" or lc2["ranked_axes_mode"] != "low-confidence-annex":
    raise SystemExit(data)
PY

JUDGE_RUN="selftest-judge-$$"
RESULT_RUNS+=("$JUDGE_RUN")
for task in SW1-django-13230; do
  write_attempt "$JUDGE_RUN" "$task" A1 10 0 false true
  write_attempt "$JUDGE_RUN" "$task" B1 10 0 false true
  write_attempt "$JUDGE_RUN" "$task" C1 10 0 false true
done
export FAKE_CODEX_JUDGE=1
HOME="$TMP_DIR" CEILING_REAL_HOME="$TMP_DIR" CEILING_EXTERNAL_ROOT="$TEST_EXTERNAL_ROOT" CEILING_TEST_AUTH_JSON="$TEST_AUTH" CEILING_TEST_CLAUDE_CREDENTIALS="$TEST_CLAUDE_CREDENTIALS" CEILING_TEST_CLAUDE_BIN="$TEST_CLAUDE_BIN" CEILING_TEST_CODEX_BIN="$FAKEBIN/codex" FAKE_CODEX_LABEL=judge python3 "$SCRIPT_DIR/ceiling-judge.py" \
  --run-id "$JUDGE_RUN" --judges sonnet,codex --codex-command "$FAKEBIN/codex" \
  --select SW1-django-13230=B1 --select SW1-django-13230=C1 >/tmp/ceiling-judge.log
if grep -E 'A1|B1|C1|arm A|arm B|arm C' "$CEILING_ROOT/results/$JUDGE_RUN/SW1-django-13230/judge-sonnet.json"; then
  echo "arm attempt leaked into sonnet judge packet/prompt" >&2
  exit 1
fi
if grep -E 'A1|B1|C1|arm A|arm B|arm C' "$CEILING_ROOT/results/$JUDGE_RUN/SW1-django-13230/judge-codex.json"; then
  echo "arm attempt leaked into codex judge packet/prompt" >&2
  exit 1
fi
grep -q 'A1' "$CEILING_ROOT/results/$JUDGE_RUN/SW1-django-13230/judge-mapping.json"

python3 -m py_compile "$SCRIPT_DIR/claude-isolation.py" "$SCRIPT_DIR/ceiling-judge.py" "$SCRIPT_DIR/ceiling-gate.py"
bash -n "$SCRIPT_DIR/claude-purity-canary.sh" "$SCRIPT_DIR/run-ceiling-arm.sh" "$SCRIPT_DIR/ceiling-eval.sh" "$SCRIPT_DIR/run-ceiling-tranche.sh" "$SCRIPT_DIR/test-ceiling-harness.sh"

echo "PASS test-ceiling-harness"
