#!/usr/bin/env bash
# run-drift-bait-probe.sh — one probe, one model, one always-loaded instruction variant, fully isolated.
# Probes are drift-bait fixtures (task.txt, starter/, hidden/verify.sh) or EQ3 tasks (task.json .goal,
# visible/, hidden/oracle.py); each is scored by its own hidden oracle.
#
# Usage:
#   MODEL=<exact claude-* ID | sonnet | gpt-*> run-drift-bait-probe.sh --probe-dir <path> --run-id <ID>
#   INSTRUCTION_SRC=<path>|none  (default: repo CLAUDE.md for Claude, repo AGENTS.md for gpt-*)
#   TASK_LANG=<code>             (task.<code>.txt instead of task.txt)
#   PIN_CLAUDE / PIN_CODEX       (snapshot binaries; default: PATH)
# Isolation: fresh HOME with no user memory, skills or plugins. Claude runs through the sealed
# benchmark/ceiling/scripts/claude-isolation.py (exact modelUsage attestation); Codex runs with a fresh
# CODEX_HOME, a render check of the AGENTS.md payload, and rollout model attestation.
# Exit: 0 scored (verdict.json), 3 infra (infra.attempt-N.json, no verdict; at most 2 attempts), 1 misuse.
# A timeout is not infra: the diff at the kill is scored and timing.json records timed_out.
set -euo pipefail

usage() { echo "usage: MODEL=<id> $0 --probe-dir <path> --run-id <ID>" >&2; exit 1; }
PROBE_DIR=""; RUN_ID=""; MODEL="${MODEL:-}"; TASK_LANG="${TASK_LANG:-}"
while [ $# -gt 0 ]; do
  case "$1" in
    --probe-dir) PROBE_DIR="$2"; shift 2;;
    --run-id)    RUN_ID="$2";    shift 2;;
    *) usage;;
  esac
done
[ -n "$PROBE_DIR" ] && [ -n "$RUN_ID" ] && [ -d "$PROBE_DIR" ] || usage
case "$MODEL" in
  claude-*|sonnet) ENGINE=claude; INSTR_NAME=CLAUDE.md;;
  gpt-*)           ENGINE=codex;  INSTR_NAME=AGENTS.md;;
  *) echo "MODEL must be an exact claude-* ID, sonnet, or gpt-* (got '${MODEL}')" >&2; exit 1;;
esac

PROBE_DIR="$(cd "$PROBE_DIR" && pwd)"
PROBE_ID="$(basename "$PROBE_DIR")"
PROBES_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$PROBES_ROOT/../.." && pwd)"
TIMEOUT=1800
if [ -f "$PROBE_DIR/task.json" ]; then SHAPE=eq3; SEED="$PROBE_DIR/visible"; else SHAPE=drift; SEED="$PROBE_DIR/starter"; fi
TASK_FILE="$PROBE_DIR/task${TASK_LANG:+.$TASK_LANG}.txt"
[ "$SHAPE" = eq3 ] || [ -f "$TASK_FILE" ] || { echo "probe missing $TASK_FILE" >&2; exit 1; }
[ -d "$SEED" ] || { echo "probe missing $SEED" >&2; exit 1; }

INSTRUCTION_SRC="${INSTRUCTION_SRC-$REPO_ROOT/$INSTR_NAME}"
if [ "$INSTRUCTION_SRC" = none ]; then INSTR_SHA=none
elif [ -f "$INSTRUCTION_SRC" ]; then INSTR_SHA=$(shasum -a 256 "$INSTRUCTION_SRC" | cut -d' ' -f1)
else echo "INSTRUCTION_SRC not found: $INSTRUCTION_SRC" >&2; exit 1; fi

RESULT_DIR="$PROBES_ROOT/results/$RUN_ID/drift-bait/$PROBE_ID"
mkdir -p "$RESULT_DIR"
[ -f "$RESULT_DIR/verdict.json" ] && { echo "[run-drift-bait-probe] already scored: $RESULT_DIR"; exit 0; }
ATTEMPT=$(( $(find "$RESULT_DIR" -maxdepth 1 -name 'infra.attempt-*.json' | wc -l) + 1 ))
[ "$ATTEMPT" -le 2 ] || { echo "[run-drift-bait-probe] two infra attempts already recorded: $RESULT_DIR" >&2; exit 3; }
infra() {  # record an infra attempt (the evidence stays), never a verdict
  python3 - "$RESULT_DIR/infra.attempt-$ATTEMPT.json" "$1" "$RESULT_DIR/stderr.log" <<'PY'
import json, pathlib, sys
tail = pathlib.Path(sys.argv[3]).read_text(errors='replace')[-2000:] if pathlib.Path(sys.argv[3]).exists() else ''
pathlib.Path(sys.argv[1]).write_text(json.dumps(dict(reason=sys.argv[2], stderr_tail=tail), indent=2))
PY
  echo "[run-drift-bait-probe] infra: $1 ($RESULT_DIR)" >&2
  exit 3
}

ROOT="$(mktemp -d /tmp/il-XXXXXX)"
trap 'rm -rf "$ROOT"' EXIT
WORK="$ROOT/w"; HOME_DIR="$ROOT/h"; CODEX_DIR="$ROOT/c"
mkdir -p "$WORK" "$HOME_DIR" "$CODEX_DIR"
cp -R "$SEED"/. "$WORK"/
[ "$INSTR_SHA" = none ] || cp "$INSTRUCTION_SRC" "$WORK/$INSTR_NAME"
(cd "$WORK" && git init -q && git add -A && git -c user.email=b@b -c user.name=b commit -q -m baseline)
SCAFFOLD_SHA=$(git -C "$WORK" rev-parse HEAD)
if [ "$SHAPE" = eq3 ]; then python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["goal"], end="")' "$PROBE_DIR/task.json" > "$ROOT/prompt"
else cp "$TASK_FILE" "$ROOT/prompt"; fi

T_START=$(date +%s); RC=0
if [ "$ENGINE" = claude ]; then
  CEILING_TEST_CLAUDE_BIN="${PIN_CLAUDE:-$(command -v claude)}" CEILING_TEST_CODEX_BIN="${PIN_CODEX:-$(command -v codex)}" \
    python3 "$REPO_ROOT/benchmark/ceiling/scripts/claude-isolation.py" launch --mode arm --model "$MODEL" \
      --home "$HOME_DIR" --codex-home "$CODEX_DIR" --workdir "$WORK" --prompt-file "$ROOT/prompt" \
      --debug-file "$RESULT_DIR/claude-debug.log" --metadata-out "$RESULT_DIR/claude-isolation.json" \
      --user-memory-file "$HOME/.claude/CLAUDE.md" --timeout-seconds "$TIMEOUT" \
      > "$RESULT_DIR/transcript.json" 2> "$RESULT_DIR/stderr.log" || RC=$?
else
  CODEX_BIN="${PIN_CODEX:-$(command -v codex)}"
  install -m 600 "$HOME/.codex/auth.json" "$CODEX_DIR/auth.json"
  install -m 600 "$HOME/.codex/models_cache.json" "$CODEX_DIR/models_cache.json"
  grep -q "\"$MODEL\"" "$CODEX_DIR/models_cache.json" || { echo "$MODEL is not in the Codex models cache" >&2; exit 1; }
  SKILLS='skills.config=[{name="imagegen",enabled=false},{name="openai-docs",enabled=false},{name="plugin-creator",enabled=false},{name="skill-creator",enabled=false},{name="skill-installer",enabled=false}]'
  COMMON=(-c 'model_reasoning_effort="xhigh"' -c 'web_search="disabled"' -c "$SKILLS" --disable multi_agent
          --disable apps --disable plugins --disable hooks --disable skill_search --enable skip_host_skill_discovery)
  # prompt-input takes only -c/--enable/--disable; the fresh CODEX_HOME has no user config or rules to ignore.
  RENDER=(-c "model=\"$MODEL\"" -c 'sandbox_mode="workspace-write"' "${COMMON[@]}")
  FLAGS=(--ignore-user-config --strict-config --ignore-rules --sandbox workspace-write
         -c sandbox_workspace_write.network_access=false --model "$MODEL" "${COMMON[@]}")
  ISOLATED=(env -i "PATH=$(dirname "$CODEX_BIN"):$(dirname "$(command -v node)"):/usr/bin:/bin:/usr/sbin:/sbin"
            "HOME=$HOME_DIR" "CODEX_HOME=$CODEX_DIR" "TMPDIR=$HOME_DIR" LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
            TERM=dumb TZ=UTC GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null)
  (cd "$WORK" && "${ISOLATED[@]}" "$CODEX_BIN" debug prompt-input "${RENDER[@]}" "$(cat "$ROOT/prompt")") \
    > "$RESULT_DIR/render.json" 2> "$RESULT_DIR/stderr.log" || infra "codex render failed"
  python3 - "$RESULT_DIR/render.json" "$INSTRUCTION_SRC" <<'PY' || infra "codex render check failed"
import json, re, sys
text = '\n'.join(block.get('text', '') for message in json.load(open(sys.argv[1]))
                 for block in message.get('content', []) if isinstance(block, dict))
payloads = re.findall(r'# AGENTS\.md instructions[^\n]*\n\n<INSTRUCTIONS>\n(.*?)\n</INSTRUCTIONS>', text, re.S)
expected = [] if sys.argv[2] == 'none' else [open(sys.argv[2]).read().rstrip('\n')]
if [p.rstrip('\n') for p in payloads] != expected or '(file: ' in text or 'Persistent Memory' in text:
    sys.exit(f'render mismatch: {len(payloads)} AGENTS blocks, skill cards or memory present')
PY
  "${ISOLATED[@]}" /bin/sh -c 'cd "$1" && shift && exec "$@"' sh "$WORK" \
    "$(command -v python3)" "$REPO_ROOT/config/skills/_shared/run-bounded.py" "$TIMEOUT" --stdin-file "$ROOT/prompt" -- \
    "$CODEX_BIN" exec "${FLAGS[@]}" --skip-git-repo-check --json --color never - \
    > "$RESULT_DIR/transcript.jsonl" 2>> "$RESULT_DIR/stderr.log" || RC=$?
fi
T_END=$(date +%s)
TIMED_OUT=false
if [ "$ENGINE" = claude ] && [ "$RC" -eq 78 ] && grep -q 'timed out after' "$RESULT_DIR/stderr.log"; then TIMED_OUT=true
elif [ "$ENGINE" = codex ] && [ "$RC" -eq 124 ]; then TIMED_OUT=true
elif [ "$RC" -ne 0 ]; then infra "$ENGINE exit $RC"; fi

# Runtime identity and usage; any error, limit or unattested model is infra, never a verdict.
python3 - "$ENGINE" "$MODEL" "$RESULT_DIR" "$CODEX_DIR" "$TIMED_OUT" > "$ROOT/attest.json" <<'PY' || infra "$(cat "$ROOT/attest.err" 2>/dev/null || echo attestation failed)"
import json, pathlib, re, sys
engine, model, result, codex_home, timed_out = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3]), pathlib.Path(sys.argv[4]), sys.argv[5] == 'true'
limit = re.compile(r'\b(429|529)\b|rate.?limit|usage limit|session limit|overloaded', re.I)
def fail(reason):
    (pathlib.Path(sys.argv[4]).parent / 'attest.err').write_text(reason)
    sys.exit(1)
if engine == 'claude':
    if timed_out:
        print(json.dumps(dict(runtime_model=None, usage='UNKNOWN'))); sys.exit()
    wrapper = json.loads((result / 'transcript.json').read_text())
    if wrapper.get('is_error') or limit.search(str(wrapper.get('result', ''))):
        fail('claude result is_error: ' + str(wrapper.get('subtype')))
    print(json.dumps(dict(runtime_model=sorted(wrapper.get('modelUsage') or {}), usage=wrapper.get('modelUsage'))))
else:
    events = []
    for line in (result / 'transcript.jsonl').read_text(errors='replace').splitlines():
        try: events.append(json.loads(line))
        except ValueError: pass
    if not timed_out and any(e.get('type') in ('turn.failed', 'error') for e in events):
        fail('codex turn failed: ' + json.dumps([e for e in events if e.get('type') in ('turn.failed', 'error')])[:300])
    models, reroute = set(), False
    for path in (codex_home / 'sessions').rglob('*.jsonl'):
        for line in path.read_text(errors='replace').splitlines():
            try: e = json.loads(line)
            except ValueError: continue
            if e.get('type') == 'turn_context': models.add(e['payload'].get('model'))
            if e.get('type') == 'event_msg' and (e.get('payload') or {}).get('type') == 'model_reroute': reroute = True
    if reroute or (models and models != {model}) or (not models and not timed_out):
        fail(f'codex runtime model {sorted(models)} (reroute={reroute}) is not {model}')
    turns = [e['usage'] for e in events if e.get('type') == 'turn.completed']
    usage = {k: sum(t.get(k, 0) for t in turns) for k in ('input_tokens', 'cached_input_tokens', 'output_tokens')} if turns else 'UNKNOWN'
    print(json.dumps(dict(runtime_model=sorted(models), usage=usage)))
PY

(cd "$WORK" && git add -A && git diff "$SCAFFOLD_SHA") > "$RESULT_DIR/diff.patch" 2>/dev/null || true
git -C "$WORK" diff "$SCAFFOLD_SHA" --name-only > "$RESULT_DIR/changed-files.txt" 2>/dev/null || true
if [ "$ENGINE" = claude ]; then VERSION=$("${PIN_CLAUDE:-claude}" --version 2>/dev/null | head -1); else VERSION=$("${PIN_CODEX:-codex}" --version 2>/dev/null | head -1); fi
python3 - "$RESULT_DIR/timing.json" "$ROOT/attest.json" <<PY
import json, sys
attest = json.load(open(sys.argv[2]))
json.dump(dict(probe="$PROBE_ID", engine="$ENGINE", model="$MODEL", task_lang="${TASK_LANG:-en}", cli_version="$VERSION",
               instruction_sha256="$INSTR_SHA", elapsed_seconds=$((T_END - T_START)), timed_out="$TIMED_OUT" == 'true',
               commits_after_baseline=int("$(git -C "$WORK" rev-list --count "$SCAFFOLD_SHA"..HEAD)"), **attest),
          open(sys.argv[1], 'w'), indent=2)
PY

if [ "$SHAPE" = drift ]; then
  bash "$PROBE_DIR/hidden/verify.sh" "$RESULT_DIR" > "$RESULT_DIR/verdict.json" 2> "$RESULT_DIR/verify-sh.stderr.log" || true
else  # EQ3: an oracle crash counts every manifestation as failed
  python3 - "$PROBE_DIR" "$WORK" "$RESULT_DIR/verdict.json" <<'PY'
import json, pathlib, subprocess, sys
task, work, out = pathlib.Path(sys.argv[1]), sys.argv[2], pathlib.Path(sys.argv[3])
total = len(json.loads((task / 'hidden/manifests.json').read_text())['manifestations'])
try:
    done = subprocess.run([sys.executable, str(task / 'hidden/oracle.py'), work], capture_output=True, text=True, timeout=60)
    rows = json.loads(done.stdout)['manifestations'] if done.returncode == 0 else None
except (subprocess.TimeoutExpired, ValueError, KeyError):
    rows = None
failed = total if rows is None else sum(1 for row in rows if not isinstance(row, dict) or row.get('passed') is not True)
out.write_text(json.dumps(dict(passed=failed == 0, manifestations_failed=failed, manifestations_total=total,
                               oracle_crashed=rows is None, manifestations=rows), indent=2))
PY
fi
[ -s "$RESULT_DIR/verdict.json" ] || infra "oracle wrote no verdict"
cat "$RESULT_DIR/verdict.json"
echo "[run-drift-bait-probe] done: $RESULT_DIR"
