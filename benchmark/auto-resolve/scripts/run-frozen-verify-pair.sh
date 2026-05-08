#!/usr/bin/env bash
# run-frozen-verify-pair.sh — compare solo VERIFY vs pair VERIFY on one frozen diff.
#
# This isolates VERIFY/JUDGE from IMPLEMENT: the implementation diff is applied
# before /devlyn:resolve starts, then both arms run verify-only against the same
# committed code and `.devlyn/external-diff.patch`.

set -euo pipefail

usage() {
  cat >&2 <<EOF
usage: $0 --fixture <FID> --diff <path> [--run-id ID] [--pair-mode forced|gated]
          [--fixtures-root <path>] [--base-repo <path>]
          [--timeout-seconds N] [--prepare-only] [--resume-completed-arms]

Runs two verify-only arms:
  solo  = /devlyn:resolve --verify-only ... --engine claude
  pair  = forced: /devlyn:resolve --verify-only ... --engine claude --pair-verify
          gated:  /devlyn:resolve --verify-only ... --engine claude

By default fixtures come from benchmark/auto-resolve/fixtures and the base repo
is fixtures/test-repo. External corpora such as SWE-bench can pass their own
case root and checked-out base repo.
EOF
  exit "${1:-1}"
}

FIXTURE=""
DIFF_PATH=""
RUN_ID=""
PAIR_MODE="forced"
FIXTURES_ROOT=""
BASE_REPO=""
PREPARE_ONLY=0
TIMEOUT_OVERRIDE=""
RESUME_COMPLETED_ARMS=0
while [ $# -gt 0 ]; do
  case "$1" in
    --fixture) FIXTURE="$2"; shift 2;;
    --diff)    DIFF_PATH="$2"; shift 2;;
    --run-id)  RUN_ID="$2"; shift 2;;
    --pair-mode) PAIR_MODE="$2"; shift 2;;
    --fixtures-root) FIXTURES_ROOT="$2"; shift 2;;
    --base-repo) BASE_REPO="$2"; shift 2;;
    --timeout-seconds) TIMEOUT_OVERRIDE="$2"; shift 2;;
    --prepare-only) PREPARE_ONLY=1; shift;;
    --resume-completed-arms) RESUME_COMPLETED_ARMS=1; shift;;
    -h|--help) usage 0;;
    *) echo "unknown arg: $1" >&2; usage 1;;
  esac
done

[ -n "$FIXTURE" ] && [ -n "$DIFF_PATH" ] || usage 1
[ -f "$DIFF_PATH" ] || { echo "diff not found: $DIFF_PATH" >&2; exit 1; }
[ -s "$DIFF_PATH" ] || { echo "diff is empty: $DIFF_PATH" >&2; exit 1; }
[ "$PAIR_MODE" = "forced" ] || [ "$PAIR_MODE" = "gated" ] || { echo "--pair-mode must be forced|gated (got '$PAIR_MODE')" >&2; exit 1; }

BENCH_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$BENCH_ROOT/../.." && pwd)"
[ -n "$FIXTURES_ROOT" ] || FIXTURES_ROOT="$BENCH_ROOT/fixtures"
[ -n "$BASE_REPO" ] || BASE_REPO="$BENCH_ROOT/fixtures/test-repo"
FIXTURES_ROOT="$(cd "$FIXTURES_ROOT" && pwd)"
BASE_REPO="$(cd "$BASE_REPO" && pwd)"
FIX_DIR="$FIXTURES_ROOT/$FIXTURE"
[ -d "$FIX_DIR" ] || { echo "fixture not found: $FIXTURE" >&2; exit 1; }
[ -d "$BASE_REPO" ] || { echo "base repo not found: $BASE_REPO" >&2; exit 1; }

META="$FIX_DIR/metadata.json"
EXPECTED="$FIX_DIR/expected.json"
SPEC="$FIX_DIR/spec.md"
TASK="$FIX_DIR/task.txt"
SETUP="$FIX_DIR/setup.sh"
for f in "$META" "$EXPECTED" "$SPEC" "$TASK" "$SETUP"; do
  [ -f "$f" ] || { echo "fixture missing required file: $f" >&2; exit 1; }
done

TIMEOUT=$(python3 -c "import json; print(json.load(open('$META'))['timeout_seconds'])")
if [ -n "$TIMEOUT_OVERRIDE" ]; then
  case "$TIMEOUT_OVERRIDE" in ''|*[!0-9]*) echo "--timeout-seconds must be an integer" >&2; exit 1;; esac
  [ "$TIMEOUT_OVERRIDE" -gt 0 ] || { echo "--timeout-seconds must be > 0" >&2; exit 1; }
  TIMEOUT="$TIMEOUT_OVERRIDE"
fi
if [ -z "$RUN_ID" ]; then
  TS=$(date -u +%Y%m%dT%H%M%SZ)
  SHA=$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo nogit)
  RUN_ID="${TS}-${SHA}-frozen-verify"
fi

RESULT_ROOT="$BENCH_ROOT/results/$RUN_ID"
mkdir -p "$RESULT_ROOT"

echo ""
echo "═══ Frozen Verify Pair Run ═══"
echo "Run-id:  $RUN_ID"
echo "Fixture: $FIXTURE"
echo "Cases:   $FIXTURES_ROOT"
echo "Base:    $BASE_REPO"
echo "Diff:    $DIFF_PATH"
echo "Pair:    $PAIR_MODE"
echo "Timeout: ${TIMEOUT}s per arm"
[ "$PREPARE_ONLY" -eq 0 ] || echo "Mode:    prepare-only"
echo ""

mirror_skills() {
  local src_skills="$REPO_ROOT/config/skills"
  local dst_skills="$REPO_ROOT/.claude/skills"
  mkdir -p "$dst_skills"
  local mirrored=0
  for src_dir in "$src_skills"/*/; do
    [ -d "$src_dir" ] || continue
    local name
    name=$(basename "$src_dir")
    case "$name" in
      devlyn:auto-resolve-workspace|devlyn:ideate-workspace|preflight-workspace|roadmap-archival-workspace)
        continue ;;
    esac
    local staging="$dst_skills/.${name}.staging"
    rm -rf "$staging"
    cp -R "$src_dir" "$staging"
    rm -rf "$dst_skills/$name"
    mv "$staging" "$dst_skills/$name"
    mirrored=$((mirrored + 1))
  done
  echo "[frozen-verify] mirrored $mirrored committed skill(s): config/skills/ -> .claude/skills/"
}

stage_codex_env() {
  local work_dir="$1"
  local arm="$2"
  mkdir -p "$work_dir/.claude"
  cp -R "$REPO_ROOT/.claude/skills" "$work_dir/.claude/skills"
  [ -f "$REPO_ROOT/CLAUDE.md" ] && cp "$REPO_ROOT/CLAUDE.md" "$work_dir/CLAUDE.md"

  if ! command -v codex >/dev/null 2>&1; then
    echo "warning: codex not on PATH — pair arm cannot exercise Codex pair-JUDGE" >&2
    return
  fi
  local real_bin shim_src monitored_src monitored_path snapshot_path injected_path blocked
  real_bin="$(command -v codex)"
  shim_src="$REPO_ROOT/scripts/codex-shim/codex"
  monitored_src="$REPO_ROOT/config/skills/_shared/codex-monitored.sh"
  [ -x "$shim_src" ] || { echo "missing codex shim: $shim_src" >&2; exit 1; }
  [ -r "$monitored_src" ] || { echo "missing codex wrapper: $monitored_src" >&2; exit 1; }
  mkdir -p "$work_dir/.devlyn-bin"
  cp "$shim_src" "$work_dir/.devlyn-bin/codex"
  chmod +x "$work_dir/.devlyn-bin/codex"
  monitored_path="$work_dir/.claude/skills/_shared/codex-monitored.sh"
  snapshot_path=$(grep -m1 '^export PATH=' "$HOME/.claude/shell-snapshots/snapshot-zsh-"*.sh 2>/dev/null | head -1 | sed 's/^[^=]*=//' | tr -d '"' || true)
  [ -n "$snapshot_path" ] || snapshot_path="$PATH"
  injected_path="$work_dir/.devlyn-bin:$snapshot_path"
  blocked=0
  [ "$arm" = "solo" ] && blocked=1
  python3 - "$work_dir/.claude/settings.json" "$injected_path" "$real_bin" "$monitored_path" "$blocked" <<'PY'
import json, sys
out_path, path_val, real_bin, monitored, blocked = sys.argv[1:6]
env = {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1", "PATH": path_val}
if blocked == "1":
    env["CODEX_BLOCKED"] = "1"
else:
    env["CODEX_REAL_BIN"] = real_bin
    env["CODEX_MONITORED_PATH"] = monitored
with open(out_path, "w") as f:
    json.dump({"env": env}, f, indent=2)
    f.write("\n")
PY
}

cleanup_workdir_processes() {
  local work_dir="$1"
  local signal="$2"
  local physical_work_dir current_pgid
  physical_work_dir="$(cd "$work_dir" 2>/dev/null && pwd -P || printf '%s' "$work_dir")"
  current_pgid="$(ps -o pgid= -p "$$" | tr -d ' ')"
  ps -axo pid=,pgid=,command= \
    | awk -v p1="$work_dir" -v p2="$physical_work_dir" -v self="$$" -v current_pgid="$current_pgid" '
        $1 != self && $2 != current_pgid && (index($0, p1) || index($0, p2)) { print $2 }
      ' \
    | sort -u \
    | while IFS= read -r pgid; do
        [ -n "$pgid" ] || continue
        kill "-$signal" -- "-$pgid" 2>/dev/null || true
      done
}

archive_ready() {
  local work_dir="$1"
  python3 - "$work_dir" <<'PY'
import pathlib, sys
root = pathlib.Path(sys.argv[1]) / ".devlyn" / "runs"
raise SystemExit(0 if root.is_dir() and any(root.glob("*/pipeline.state.json")) else 1)
PY
}

summarize_arm() {
  local result_dir="$1"
  local elapsed="$2"
  local invoke_exit="$3"
  python3 - "$result_dir" "$elapsed" "$invoke_exit" <<'PY'
import json, pathlib, sys
result_dir = pathlib.Path(sys.argv[1])
elapsed = int(sys.argv[2])
invoke_exit = int(sys.argv[3])
archive = result_dir / "run-archive"
state_path = archive / "pipeline.state.json"
state = json.loads(state_path.read_text()) if state_path.is_file() else {}
verify = ((state.get("phases") or {}).get("verify") or {})
sub_verdicts = verify.get("sub_verdicts")
pair_trigger = verify.get("pair_trigger") or ((state.get("verify") or {}).get("pair_trigger"))
findings = []
finding_paths = []
merged_path = archive / "verify-merged.findings.jsonl"
if merged_path.is_file():
    finding_paths.append(merged_path)
else:
    candidates = []
    for name in ("verify.findings.jsonl", "verify.pair-judge.findings.jsonl"):
        candidates.append(archive / name)
    candidates.extend(sorted(archive.glob("verify.findings*.jsonl")))
    candidates.extend(sorted(archive.glob("verify.*findings*.jsonl")))
    seen = set()
    for candidate_path in candidates:
        if candidate_path.name == "verify-mechanical.findings.jsonl":
            continue
        if candidate_path in seen or not candidate_path.is_file():
            continue
        seen.add(candidate_path)
        finding_paths.append(candidate_path)
findings_source = "+".join(path.name for path in finding_paths) if finding_paths else "missing"
finding_severities = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
for findings_path in finding_paths:
    for line in findings_path.read_text().splitlines():
        if line.strip():
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(parsed, dict):
                continue
            sev = str(parsed.get("severity") or parsed.get("level") or "").upper()
            if sev not in finding_severities:
                continue
            findings.append(parsed)
merged = verify.get("merged") if isinstance(verify.get("merged"), dict) else {}
merged_findings_count = sum(
    int(merged.get(k) or 0) for k in ("critical", "high", "medium", "low")
)
findings_count = len(findings) if findings else merged_findings_count
severity_counts = {}
for finding in findings:
    if isinstance(finding, dict):
        sev = str(finding.get("severity") or finding.get("level") or "unknown").upper()
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
transcript_path = result_dir / "transcript.txt"
transcript = transcript_path.read_text(errors="replace") if transcript_path.is_file() else ""
invoke_failure_reason = None
if invoke_exit == 124:
    invoke_failure_reason = "timeout"
elif "You've hit your limit" in transcript:
    invoke_failure_reason = "provider_limit"
summary = {
    "elapsed_seconds": elapsed,
    "invoke_exit": invoke_exit,
    "timed_out": invoke_exit == 124,
    "invoke_failure_reason": invoke_failure_reason,
    "terminal_verdict": ((state.get("phases") or {}).get("final_report") or {}).get("verdict"),
    "verify_verdict": verify.get("verdict"),
    "sub_verdicts": sub_verdicts,
    "pair_trigger": pair_trigger,
    "pair_mode": bool(isinstance(sub_verdicts, dict) and (
        sub_verdicts.get("judge_codex") is not None
        or sub_verdicts.get("pair_judge") is not None
    ))
        or bool(verify.get("pair_mode")),
    "verify_findings_count": findings_count,
    "verify_findings_source": findings_source if finding_paths else (
        "state.merged" if merged_findings_count else "missing"
    ),
    "merged_findings_counts": merged,
    "severity_counts": severity_counts,
    "verify_findings_severities": [f.get("severity") for f in findings if isinstance(f, dict)],
}
(result_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
PY
}

copy_base_repo() {
  local work_dir="$1"
  rm -rf "$work_dir"
  mkdir -p "$work_dir"
  if [ -d "$BASE_REPO/.git" ]; then
    git -C "$BASE_REPO" archive --format=tar HEAD | (cd "$work_dir" && LC_ALL=C tar -xf -)
  else
    cp -R "$BASE_REPO"/. "$work_dir"/
    rm -rf "$work_dir/.git"
  fi
}

run_arm() {
  local arm="$1"
  local pair_flag="$2"
  local result_dir="$RESULT_ROOT/$arm"
  local work_dir="/tmp/bench-${RUN_ID}-${FIXTURE}-${arm}"
  if [ "$RESUME_COMPLETED_ARMS" -eq 1 ] && [ "$PREPARE_ONLY" -eq 0 ] && [ -f "$result_dir/summary.json" ]; then
    if python3 - "$result_dir/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1]))
raise SystemExit(0 if summary.get("invoke_exit") == 0 else 1)
PY
    then
      echo "[frozen-verify] $arm: reuse completed summary"
      return 0
    fi
  fi
  mkdir -p "$result_dir"
  copy_base_repo "$work_dir"

  stage_codex_env "$work_dir" "$arm"

  (cd "$work_dir" && git init -q && git add -A && git -c user.email=b@b -c user.name=b commit -q -m baseline)

  if [ -s "$SETUP" ]; then
    chmod +x "$SETUP"
    (cd "$work_dir" && "$SETUP") > "$result_dir/setup.log" 2>&1
    (cd "$work_dir" && git add -A && git -c user.email=b@b -c user.name=b commit -q --allow-empty -m fixture-setup)
  fi

  mkdir -p "$work_dir/docs/roadmap/phase-1" "$work_dir/.devlyn"
  cp "$SPEC" "$work_dir/docs/roadmap/phase-1/$FIXTURE.md"
  cp "$DIFF_PATH" "$work_dir/.devlyn/external-diff.patch"
  python3 - "$EXPECTED" "$work_dir/.devlyn/spec-verify.json" <<'PY'
import json, os, sys
expected = json.load(open(sys.argv[1]))
out_path = sys.argv[2]
commands = expected.get("verification_commands", [])
if not commands:
    raise SystemExit(0)
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, "w") as f:
    json.dump({"verification_commands": commands}, f, indent=2)
    f.write("\n")
PY

  if ! (cd "$work_dir" && git apply .devlyn/external-diff.patch); then
    echo "[frozen-verify] $arm: diff failed to apply" >&2
    return 1
  fi
  (cd "$work_dir" && git add -A && git -c user.email=b@b -c user.name=b commit -q -m external-implementation)

  cat > "$result_dir/input.md" <<EOF
Use the \`/devlyn:resolve --verify-only .devlyn/external-diff.patch --spec docs/roadmap/phase-1/$FIXTURE.md --engine claude ${pair_flag}\` skill to run VERIFY-ONLY mode.

The diff at .devlyn/external-diff.patch represents an external implementation already applied to the work tree. Run PHASE 5 (VERIFY) only — skip PLAN, IMPLEMENT, BUILD_GATE, CLEANUP per the skill's verify-only mode contract.

Important: \`--engine claude\` selects the primary VERIFY judge only. It must not suppress gated VERIFY pair-mode. If the spec/phase trigger makes pair-mode eligible with non-empty reasons, the skill must spawn the OTHER-engine judge unless Codex is blocked/unavailable at the invocation layer.

Report the terminal verdict, list of files in the diff, and any findings.
EOF

  if [ "$PREPARE_ONLY" -eq 1 ]; then
    echo "[frozen-verify] $arm prepared at $work_dir"
    return 0
  fi

  local start end elapsed invoke_exit watchdog timeout_flag complete_flag
  start=$(date +%s)
  timeout_flag="$result_dir/.timed_out"
  complete_flag="$result_dir/.completed"
  rm -f "$timeout_flag" "$complete_flag"
  set +e
  set -m
  (
    cd "$work_dir"
    export PATH="$work_dir/.devlyn-bin:$PATH"
    [ "$arm" = "solo" ] && export CODEX_BLOCKED=1
    export BENCH_WORKDIR="$work_dir"
    export BENCH_FIXTURE_DIR="$FIX_DIR"
    exec claude \
      -p "$(cat "$result_dir/input.md")" \
      --dangerously-skip-permissions \
      --effort xhigh \
      --strict-mcp-config \
      --mcp-config '{"mcpServers":{}}' \
      --debug-file "$result_dir/claude-debug.log" \
      </dev/null
  ) > "$result_dir/transcript.txt" 2>&1 &
  local child_pid=$!
  set +m
  (
    local deadline now
    deadline=$(($(date +%s) + TIMEOUT))
    while kill -0 "$child_pid" 2>/dev/null; do
      if archive_ready "$work_dir"; then
        : > "$complete_flag"
        kill -TERM -- "-$child_pid" 2>/dev/null
        cleanup_workdir_processes "$work_dir" TERM
        sleep 2
        kill -KILL -- "-$child_pid" 2>/dev/null
        cleanup_workdir_processes "$work_dir" KILL
        exit 0
      fi
      now=$(date +%s)
      [ "$now" -lt "$deadline" ] || break
      sleep 5
    done
    if kill -0 "$child_pid" 2>/dev/null; then
      : > "$timeout_flag"
      kill -TERM -- "-$child_pid" 2>/dev/null
      cleanup_workdir_processes "$work_dir" TERM
      sleep 5
      kill -KILL -- "-$child_pid" 2>/dev/null
      cleanup_workdir_processes "$work_dir" KILL
    fi
  ) &
  watchdog=$!
  wait "$child_pid"
  invoke_exit=$?
  kill -TERM "$watchdog" 2>/dev/null || true
  wait "$watchdog" 2>/dev/null || true
  if [ -f "$timeout_flag" ]; then
    invoke_exit=124
    rm -f "$timeout_flag"
  elif [ -f "$complete_flag" ]; then
    invoke_exit=0
    rm -f "$complete_flag"
  fi
  set -e
  end=$(date +%s)
  elapsed=$((end - start))

  local run_dir
  run_dir=$(find "$work_dir/.devlyn/runs" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort | tail -1 || true)
  if [ -n "$run_dir" ]; then
    rm -rf "$result_dir/run-archive"
    cp -R "$run_dir" "$result_dir/run-archive"
    [ -f "$result_dir/run-archive/pipeline.state.json" ] \
      || [ ! -f "$work_dir/.devlyn/pipeline.state.json" ] \
      || cp "$work_dir/.devlyn/pipeline.state.json" "$result_dir/run-archive/pipeline.state.json"
  elif [ -d "$work_dir/.devlyn" ]; then
    rm -rf "$result_dir/run-archive"
    mkdir -p "$result_dir/run-archive"
    find "$work_dir/.devlyn" -maxdepth 1 -type f -exec cp {} "$result_dir/run-archive/" \;
  fi
  if [ -d "$work_dir/.devlyn" ] && [ -d "$result_dir/run-archive" ]; then
    find "$work_dir/.devlyn" -maxdepth 1 -type f \
      \( -name 'verify.findings*.jsonl' -o -name 'verify.*findings*.jsonl' -o -name 'verify-merged.findings.jsonl' \) \
      ! -name 'verify-mechanical.findings.jsonl' \
      -exec cp {} "$result_dir/run-archive/" \;
  fi
  summarize_arm "$result_dir" "$elapsed" "$invoke_exit"
}

mirror_skills
echo "[frozen-verify] ► solo"
run_arm solo ""
echo "[frozen-verify] ► pair"
if [ "$PAIR_MODE" = "forced" ]; then
  run_arm pair "--pair-verify"
else
  run_arm pair ""
fi

python3 - "$RESULT_ROOT" "$PAIR_MODE" <<'PY'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
pair_mode_requested = sys.argv[2]
out = {}
for arm in ("solo", "pair"):
    path = root / arm / "summary.json"
    out[arm] = json.loads(path.read_text()) if path.is_file() else {"missing": True}
solo = out.get("solo", {})
pair = out.get("pair", {})
rank = {
    None: 0,
    "PASS": 0,
    "PASS_WITH_ISSUES": 1,
    "NEEDS_WORK": 2,
    "BLOCKED": 3,
}
solo_rank = rank.get(solo.get("verify_verdict"), 0)
pair_rank = rank.get(pair.get("verify_verdict"), 0)
pair_sub = pair.get("sub_verdicts") or {}
pair_primary_verdict = pair_sub.get("judge")
pair_judge_verdict = pair_sub.get("pair_judge")
pair_primary_rank = rank.get(pair_primary_verdict, 0)
pair_judge_rank = rank.get(pair_judge_verdict, 0)
out["comparison"] = {
    "pair_mode_requested": pair_mode_requested,
    "pair_trigger_missed": bool(
        pair_mode_requested == "gated"
        and (pair.get("pair_trigger") or {}).get("eligible") is True
        and (pair.get("pair_trigger") or {}).get("reasons")
        and not pair.get("pair_mode")
    ),
    "pair_found_more_findings": (pair.get("verify_findings_count") or 0) > (solo.get("verify_findings_count") or 0),
    "pair_found_more_low_or_worse": sum((pair.get("severity_counts") or {}).get(k, 0) for k in ("LOW", "MEDIUM", "HIGH", "CRITICAL"))
        > sum((solo.get("severity_counts") or {}).get(k, 0) for k in ("LOW", "MEDIUM", "HIGH", "CRITICAL")),
    "pair_verdict_lift": bool(pair.get("pair_mode")) and pair_rank > solo_rank and pair_rank >= rank["NEEDS_WORK"],
    "pair_internal_verdict_lift": bool(pair.get("pair_mode"))
        and pair_judge_rank > pair_primary_rank
        and pair_rank >= rank["NEEDS_WORK"],
    "solo_verdict": solo.get("verify_verdict"),
    "pair_verdict": pair.get("verify_verdict"),
    "pair_primary_verdict": pair_primary_verdict,
    "pair_judge_verdict": pair_judge_verdict,
}
(root / "compare.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
PY
