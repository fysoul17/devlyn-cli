#!/usr/bin/env bash
# run-fixture.sh — run ONE fixture, ONE arm, end-to-end. Self-contained.
#
# Prepares a fresh work dir, applies setup, invokes the arm via `claude -p`
# subprocess (isolated session), then captures artifacts + runs verification.
#
# Usage:
#   run-fixture.sh --fixture <FID> --arm <variant|bare> --run-id <ID>
#   run-fixture.sh --fixture <FID> --arm <variant|bare> --run-id <ID> --dry-run
#
# Outputs to benchmark/auto-resolve/results/<run-id>/<fixture>/<arm>/:
#   input.md, transcript.txt, diff.patch, changed-files.txt, verify.json,
#   timing.json, result.json, setup.log (if setup ran)

set -euo pipefail

usage() {
  echo "usage: $0 --fixture <FID> --arm <variant|bare> --run-id <ID> [--dry-run]"
  exit 1
}

FIXTURE=""; ARM=""; RUN_ID=""; DRY_RUN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --fixture)  FIXTURE="$2"; shift 2;;
    --arm)      ARM="$2";     shift 2;;
    --run-id)   RUN_ID="$2";  shift 2;;
    --dry-run)  DRY_RUN=1;    shift;;
    *) usage;;
  esac
done
[ -n "$FIXTURE" ] && [ -n "$ARM" ] && [ -n "$RUN_ID" ] || usage
# iter-0019: 3 arms — variant (L2: Claude orchestrator + Codex BUILD pair),
# solo_claude (L1: Claude orchestrator, codex blocked by shim+wrapper enforcement),
# bare (L0: direct claude -p, no skill, no codex).
[ "$ARM" = "variant" ] || [ "$ARM" = "solo_claude" ] || [ "$ARM" = "bare" ] || \
  { echo "arm must be variant|solo_claude|bare"; exit 1; }

BENCH_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$BENCH_ROOT/../.." && pwd)"

FIX_DIR="$BENCH_ROOT/fixtures/$FIXTURE"
[ -d "$FIX_DIR" ] || { echo "fixture not found: $FIX_DIR"; exit 1; }

META="$FIX_DIR/metadata.json"
EXPECTED="$FIX_DIR/expected.json"
SPEC="$FIX_DIR/spec.md"
TASK="$FIX_DIR/task.txt"
SETUP="$FIX_DIR/setup.sh"
for f in "$META" "$EXPECTED" "$SPEC" "$TASK"; do
  [ -f "$f" ] || { echo "fixture missing required file: $f (see SCHEMA.md)"; exit 1; }
done

TIMEOUT=$(python3 -c "import json; print(json.load(open('$META'))['timeout_seconds'])")

RESULT_DIR="$BENCH_ROOT/results/$RUN_ID/$FIXTURE/$ARM"
mkdir -p "$RESULT_DIR"

# Fresh copy of test-repo — order matters. We copy arm-env files (skills,
# CLAUDE.md) BEFORE the baseline commit so they do NOT appear in the diff
# the arm produces. That keeps diff.patch focused on the arm's actual code
# changes, so forbidden-pattern scans and judge rubrics see only real work.
WORK_DIR="/tmp/bench-${RUN_ID}-${FIXTURE}-${ARM}"
rm -rf "$WORK_DIR"
cp -R "$BENCH_ROOT/fixtures/test-repo" "$WORK_DIR"

# Variant + solo_claude both get devlyn skills + project CLAUDE.md pre-baseline.
# Bare arm gets nothing (no skill, no shim, no env).
#
# iter-0019: solo_claude (L1) shares the variant-arm staging because the L1
# arm is the same orchestrator on the same skills — the only difference is
# that codex is blocked. We stage the shim for both arms; for variant the
# shim transparently routes `codex exec` through codex-monitored.sh (iter-
# 0009 starvation fix), for solo_claude the shim refuses every codex
# invocation under CODEX_BLOCKED=1 (defense in depth: shim catches PATH-
# resolution, wrapper catches direct-path invocations).
if [ "$ARM" = "variant" ] || [ "$ARM" = "solo_claude" ]; then
  mkdir -p "$WORK_DIR/.claude"
  if [ -d "$REPO_ROOT/.claude/skills" ]; then
    cp -R "$REPO_ROOT/.claude/skills" "$WORK_DIR/.claude/skills"
  else
    echo "warning: $REPO_ROOT/.claude/skills missing — $ARM may lack project skills" >&2
  fi
  if [ -f "$REPO_ROOT/CLAUDE.md" ]; then
    cp "$REPO_ROOT/CLAUDE.md" "$WORK_DIR/CLAUDE.md"
  fi
  # Stage the codex PATH shim. Required for both variant (route to monitored
  # wrapper) and solo_claude (CODEX_BLOCKED enforcement at PATH layer).
  if command -v codex >/dev/null 2>&1; then
    CODEX_REAL_BIN="$(command -v codex)"
    SHIM_SRC="$REPO_ROOT/scripts/codex-shim/codex"
    WRAPPER_SRC="$REPO_ROOT/config/skills/_shared/codex-monitored.sh"
    if [ ! -x "$SHIM_SRC" ] || [ ! -r "$WRAPPER_SRC" ]; then
      echo "fatal: iter-0009 shim/wrapper missing at $SHIM_SRC / $WRAPPER_SRC" >&2
      exit 1
    fi
    mkdir -p "$WORK_DIR/.devlyn-bin"
    cp "$SHIM_SRC" "$WORK_DIR/.devlyn-bin/codex"
    chmod +x "$WORK_DIR/.devlyn-bin/codex"
    CODEX_MONITORED_PATH="$WORK_DIR/.claude/skills/_shared/codex-monitored.sh"
    [ -r "$CODEX_MONITORED_PATH" ] || {
      echo "fatal: codex-monitored.sh not present in staged skills at $CODEX_MONITORED_PATH" >&2
      exit 1
    }
    export CODEX_REAL_BIN CODEX_MONITORED_PATH
    SNAPSHOT_PATH=$(grep -m1 '^export PATH=' \
      "$HOME/.claude/shell-snapshots/snapshot-zsh-"*.sh 2>/dev/null \
      | head -1 | sed 's/^[^=]*=//' | tr -d '"' || true)
    [ -n "$SNAPSHOT_PATH" ] || SNAPSHOT_PATH="$PATH"
    INJECTED_PATH="$WORK_DIR/.devlyn-bin:$SNAPSHOT_PATH"
    # iter-0019: arm-specific env. variant gets the codex routing pair;
    # solo_claude gets CODEX_BLOCKED=1 (shim + wrapper both refuse).
    # CODEX_REAL_BIN / CODEX_MONITORED_PATH are still written for solo_claude
    # so that if any code path bypasses BLOCKED check (defense fail), the
    # shim still has the metadata to fail loudly rather than crashing
    # silently — but the BLOCKED check fires first and exits 126.
    if [ "$ARM" = "solo_claude" ]; then
      ARM_CODEX_BLOCKED=1
    else
      ARM_CODEX_BLOCKED=0
    fi
    python3 - "$WORK_DIR/.claude/settings.json" \
      "$INJECTED_PATH" "$CODEX_REAL_BIN" "$CODEX_MONITORED_PATH" "$ARM_CODEX_BLOCKED" <<'PY'
import json, sys
out_path, path_val, real_bin, monitored, codex_blocked = sys.argv[1:6]
env = {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1",
    "PATH": path_val,
    "CODEX_REAL_BIN": real_bin,
    "CODEX_MONITORED_PATH": monitored,
}
if codex_blocked == "1":
    env["CODEX_BLOCKED"] = "1"
data = {"env": env}
with open(out_path, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY
  else
    echo "warning: codex not on PATH — $ARM cannot exercise iter-0009 wrapper / iter-0019 BLOCKED enforcement" >&2
    CODEX_REAL_BIN=""
    CODEX_MONITORED_PATH=""
  fi
fi

(cd "$WORK_DIR" \
   && git init -q \
   && git add -A \
   && git -c user.email=b@b -c user.name=b commit -q -m baseline) \
  || { echo "baseline git init failed"; exit 1; }

# Native security-review Skill expects `refs/remotes/origin/HEAD` to identify
# the diff surface. Fresh `git init` has no remote, which made a prior F8 run
# spend ~56 minutes inside CRITIC recovering this manually. Configure a
# synthetic origin pointing at the work dir itself (no network I/O) and
# wire origin/HEAD → origin/<current-branch> so security-review resolves
# immediately.
(
  cd "$WORK_DIR"
  git remote add origin "$WORK_DIR" 2>/dev/null || true
  BRANCH=$(git branch --show-current 2>/dev/null || echo master)
  git update-ref "refs/remotes/origin/$BRANCH" HEAD 2>/dev/null || true
  git symbolic-ref refs/remotes/origin/HEAD "refs/remotes/origin/$BRANCH" 2>/dev/null || true
) >/dev/null 2>&1 || true

# Fixture-specific setup (applied post-baseline so the diff shows fixture
# framing as part of the arm's environment, not its work product). Commit
# failures here break arm-only diff isolation, so fail loudly.
if [ -f "$SETUP" ] && [ -s "$SETUP" ]; then
  chmod +x "$SETUP"
  if ! (cd "$WORK_DIR" && "$SETUP") > "$RESULT_DIR/setup.log" 2>&1; then
    echo "setup.sh failed; see $RESULT_DIR/setup.log"
    exit 1
  fi
  if ! (cd "$WORK_DIR" \
          && git add -A \
          && git -c user.email=b@b -c user.name=b commit -q --allow-empty -m "fixture-setup"); then
    echo "fixture-setup commit failed — arm diff isolation broken"
    exit 1
  fi
fi

# Build arm-specific prompt + place arm-specific environment files. Anything
# that's "benchmark scaffolding" (spec path placement, prompt wrapper) is
# committed to the work repo as a separate pre-model commit so the model's
# diff shows only its own work.
#
# Per-arm prompt selection is fixture-id-aware only in one case: F9, the
# end-to-end novice fixture. F9's variant arm explicitly chains
# ideate → auto-resolve → preflight from the raw task.txt (as a novice would);
# every other fixture's variant uses the spec-driven auto-resolve path.
PROMPT_FILE="$RESULT_DIR/input.md"
# iter-0019: variant uses --engine auto (codex BUILD + claude critique pair);
# solo_claude uses --engine claude explicitly so the orchestrator routes every
# phase to Claude and never tries to invoke codex. The CODEX_BLOCKED shim
# enforces this at the binary layer if the orchestrator misroutes.
if [ "$ARM" = "variant" ] || [ "$ARM" = "solo_claude" ]; then
  if [ "$ARM" = "solo_claude" ]; then
    ENGINE_CLAUSE="--engine claude"
    ENGINE_PROMPT_HINT="Run with \`--engine claude\` for every phase. Codex must not be invoked — the harness has blocked it at the binary layer for this run."
  else
    ENGINE_CLAUSE=""
    ENGINE_PROMPT_HINT="Let \`--engine auto\` select the route from the spec's complexity and risk signals — do not override it."
  fi
  if [ "$FIXTURE" = "F9-e2e-ideate-to-preflight" ]; then
    # Novice flow — no pre-placed spec. The arm must generate it via ideate.
    cat > "$PROMPT_FILE" <<EOF
You are a first-time devlyn-cli user. You have a vague idea and want the harness to take it from unstructured ask to shipped, verified feature. Run the chain:

1. Invoke \`/devlyn:ideate ${ENGINE_CLAUSE}\` to turn the idea into docs/VISION.md, docs/ROADMAP.md, and a self-contained spec under docs/roadmap/phase-1/.
2. Once ideate emits a spec path (something like docs/roadmap/phase-1/1.1-<slug>.md), invoke \`/devlyn:auto-resolve ${ENGINE_CLAUSE} "Implement per spec at <that-path>"\` to run the full build → evaluate → critic → docs pipeline.
3. Finally, invoke \`/devlyn:preflight ${ENGINE_CLAUSE}\` to audit the implementation against the generated roadmap.

${ENGINE_PROMPT_HINT}

Follow the skills to completion. Do not short-circuit.

After the whole chain, briefly report: (a) the spec path ideate produced, (b) the auto-resolve terminal verdict, (c) whether preflight found any gaps.

RAW IDEA:
$(cat "$TASK")
EOF
  else
    # Standard variant / solo_claude: spec is pre-placed at canonical roadmap path.
    mkdir -p "$WORK_DIR/docs/roadmap/phase-1"
    cp "$SPEC" "$WORK_DIR/docs/roadmap/phase-1/$FIXTURE.md"
    cat > "$PROMPT_FILE" <<EOF
Use the \`/devlyn:auto-resolve ${ENGINE_CLAUSE}\` skill to implement the spec at \`docs/roadmap/phase-1/$FIXTURE.md\`. ${ENGINE_PROMPT_HINT}

After the pipeline finishes, report the terminal verdict and list of files changed so the benchmark runner can capture state.
EOF
  fi
else
  # Bare — same prompt for F9 as any other fixture: task.txt with anti-skill rules.
  cat > "$PROMPT_FILE" <<EOF
You are acting as a smart engineer implementing the following request directly. No skill pipeline.

HARD RULES:
- Do NOT invoke any \`/devlyn:*\` skill (no auto-resolve, evaluate, review, clean, update-docs, team-*, etc.).
- Do NOT invoke native \`simplify\` or \`security-review\` skills.
- Use only direct tools: Read, Write, Edit, Grep, Glob, Bash.
- Write code to satisfy the request. Run the verification commands the user implies. Fix failures until they pass.

REQUEST:
$(cat "$TASK")
EOF
fi

# Commit scaffolding so the upcoming arm-only diff excludes it. A failure
# here means arm work would appear mixed with scaffolding in the diff — fail
# loudly rather than silently producing corrupted data.
if ! (cd "$WORK_DIR" \
        && git add -A \
        && git -c user.email=b@b -c user.name=b commit -q --allow-empty -m "bench-scaffold"); then
  echo "bench-scaffold commit failed — arm diff isolation broken"
  exit 1
fi
# Capture the scaffold commit SHA so the arm-only diff can be computed even
# when the arm makes its own commits internally (e.g. variant's auto-resolve
# pipeline commits after each phase). Diffing against HEAD would miss those.
SCAFFOLD_SHA=$(cd "$WORK_DIR" && git rev-parse HEAD)

# Timing start
T_START=$(date +%s)
cat > "$RESULT_DIR/timing.json" <<EOF
{
  "run_id": "$RUN_ID",
  "fixture": "$FIXTURE",
  "arm": "$ARM",
  "work_dir": "$WORK_DIR",
  "start_epoch": $T_START
}
EOF

# --- Invocation -------------------------------------------------------------
# Exit code is captured so infrastructure failures don't silently look like
# a weak diff. See invoke_exit in result.json.
INVOKE_EXIT=0
# iter-0012: WATCHDOG_FIRED is the truth source for `timed_out` in result.json.
# Set to 1 only when the watchdog flag file existed at post-wait check
# (lines 332-336). Initialized here so the `set -u` `export` below at the
# Python aggregator works in both branches (dry-run never sets it).
WATCHDOG_FIRED=0
if [ $DRY_RUN -eq 1 ]; then
  echo "[run-fixture] DRY RUN — prepared $WORK_DIR, skipping model invocation" \
    > "$RESULT_DIR/transcript.txt"
else
  command -v claude >/dev/null 2>&1 || {
    echo "claude CLI not on PATH — cannot invoke arm"; exit 1;
  }
  # Arm uses real HOME so Claude auth (macOS Keychain + ~/.claude session
  # state) works. Fixtures that need HOME isolation override it inline in
  # their verification commands (e.g. F2 uses `HOME=/nonexistent` per command).
  # Variant-arm skills are resolved from $WORK_DIR/.claude/skills (project
  # scope), so bare-arm runs never see them regardless of HOME.
  #
  # Portable wall-clock watchdog. macOS lacks GNU `timeout` by default; the
  # earlier fallback ran arms unbounded, which produced a multi-hour F7 hang
  # when the inner `codex exec` raced against a lingering codex-mcp-server.
  # We background the arm in its own process group (`set -m` + `exec`) so the
  # watchdog can `kill -- -PGID` and reap codex/codex-mcp-server descendants
  # together with the parent. A flag file disambiguates timeout from natural
  # exit; on timeout we set INVOKE_EXIT=124 (GNU timeout convention) so the
  # downstream `invoke_failure` logic routes the run into BLOCKED. iter-0012:
  # the same flag also flips WATCHDOG_FIRED=1, which is exported and consumed
  # by the Python aggregator below to derive result.json.timed_out — so a
  # natural exit at or past the budget is no longer mislabeled as timeout.
  #
  # MCP/config isolation (iter 0004). The harness's `claude -p` subprocess
  # must not load the operator's user-level MCP plugins (pencil, codex-cli,
  # telegram, vercel, …). Project policy is "MCP is not in the loop"; loading
  # user MCP inside the variant arm is uncontrolled environment leaking into
  # the experiment, and it is the most plausible cause of the F7 0-byte-
  # transcript hang. `--strict-mcp-config` + an empty `mcpServers` object
  # forces a hermetic subprocess. Skills still resolve via `/skill-name`.
  # `--debug-file` records per-arm init/runtime so the next hang has a
  # location, not a guess.
  TIMEOUT_FLAG="$RESULT_DIR/.timed_out"
  rm -f "$TIMEOUT_FLAG"

  set +e
  set -m
  (
    cd "$WORK_DIR"
    # iter-0009 + iter-0019: prepend codex shim PATH for any arm that staged
    # one (variant routes through codex-monitored.sh; solo_claude refuses on
    # CODEX_BLOCKED=1). Bare arm has no shim.
    if { [ "$ARM" = "variant" ] || [ "$ARM" = "solo_claude" ]; } \
       && [ -x "$WORK_DIR/.devlyn-bin/codex" ]; then
      export PATH="$WORK_DIR/.devlyn-bin:$PATH"
      [ "$ARM" = "solo_claude" ] && export CODEX_BLOCKED=1
    fi
    exec claude \
      -p "$(cat "$PROMPT_FILE")" \
      --dangerously-skip-permissions \
      --effort xhigh \
      --strict-mcp-config \
      --mcp-config '{"mcpServers":{}}' \
      --debug-file "$RESULT_DIR/claude-debug.log"
  ) > "$RESULT_DIR/transcript.txt" 2>&1 &
  CHILD_PID=$!
  set +m

  (
    sleep "$TIMEOUT"
    if kill -0 "$CHILD_PID" 2>/dev/null; then
      : > "$TIMEOUT_FLAG"
      kill -TERM -- "-$CHILD_PID" 2>/dev/null
      sleep 5
      kill -KILL -- "-$CHILD_PID" 2>/dev/null
    fi
  ) &
  WATCHDOG_PID=$!

  wait "$CHILD_PID"
  INVOKE_EXIT=$?

  kill -TERM "$WATCHDOG_PID" 2>/dev/null || true
  wait "$WATCHDOG_PID" 2>/dev/null || true

  if [ -f "$TIMEOUT_FLAG" ]; then
    INVOKE_EXIT=124
    WATCHDOG_FIRED=1
    rm -f "$TIMEOUT_FLAG"
    echo "[run-fixture] arm timed out after ${TIMEOUT}s — INVOKE_EXIT=124" >&2
  fi
  set -e
fi

T_END=$(date +%s)
ELAPSED=$((T_END - T_START))

# Capture the ARM-ONLY diff against the scaffold commit. Variant's
# auto-resolve pipeline commits internally after each phase, so diffing
# against HEAD would miss committed work. Diffing against SCAFFOLD_SHA after
# `git add -A` picks up both scaffold..HEAD committed deltas AND any
# staged-but-not-yet-committed leftovers (unstaged or untracked).
(cd "$WORK_DIR" \
   && git add -A 2>/dev/null \
   && git diff "$SCAFFOLD_SHA") > "$RESULT_DIR/diff.patch" 2>&1 || true
(cd "$WORK_DIR" \
   && git diff "$SCAFFOLD_SHA" --name-only) > "$RESULT_DIR/changed-files.txt" 2>&1 || true

# Deterministic oracles (step 1+ of the benchmark-extension plan).
# Findings-only at this stage; scoring integration is step 5.
python3 "$BENCH_ROOT/scripts/oracle-test-fidelity.py" \
  --work "$WORK_DIR" --scaffold "$SCAFFOLD_SHA" \
  > "$RESULT_DIR/oracle-test-fidelity.json" 2>/dev/null || \
  echo '{"oracle":"test-fidelity","findings":[],"error":"oracle invocation failed"}' \
    > "$RESULT_DIR/oracle-test-fidelity.json"

python3 "$BENCH_ROOT/scripts/oracle-scope-tier-a.py" \
  --work "$WORK_DIR" --scaffold "$SCAFFOLD_SHA" --expected "$EXPECTED" \
  > "$RESULT_DIR/oracle-scope-tier-a.json" 2>/dev/null || \
  echo '{"oracle":"scope-tier-a","findings":[],"error":"oracle invocation failed"}' \
    > "$RESULT_DIR/oracle-scope-tier-a.json"

python3 "$BENCH_ROOT/scripts/oracle-scope-tier-b.py" \
  --work "$WORK_DIR" --scaffold "$SCAFFOLD_SHA" --expected "$EXPECTED" \
  > "$RESULT_DIR/oracle-scope-tier-b.json" 2>/dev/null || \
  echo '{"oracle":"scope-tier-b","findings":[],"error":"oracle invocation failed"}' \
    > "$RESULT_DIR/oracle-scope-tier-b.json"

# Run verification commands + forbidden pattern scan + deps check. Uses
# the operator's real HOME (same as the arm saw). Fixtures that need HOME
# isolation override it inline per verification command.
python3 - "$EXPECTED" "$RESULT_DIR" "$WORK_DIR" <<'PY'
import json, os, re, subprocess, sys

expected = json.load(open(sys.argv[1]))
result_dir = sys.argv[2]
work = sys.argv[3]

verify_env = os.environ.copy()
# Expose the work-dir path so fixtures whose verification needs to reference
# the work root can do so portably (e.g. F9's out-of-repo check).
verify_env["BENCH_WORKDIR"] = work

verify = {"commands": [], "forbidden_pattern_hits": [], "deps_added": 0,
          "max_deps_added": expected.get("max_deps_added", 0),
          "missing_required_files": [], "forbidden_files_present": []}

for vc in expected.get("verification_commands", []):
    try:
        proc = subprocess.run(vc["cmd"], cwd=work, shell=True, env=verify_env,
                              capture_output=True, text=True, timeout=60)
        out = (proc.stdout or "") + (proc.stderr or "")
        ok_exit = proc.returncode == vc.get("exit_code", 0)
        ok_contains = all(s in out for s in vc.get("stdout_contains", []))
        ok_not = not any(s in out for s in vc.get("stdout_not_contains", []))
        verify["commands"].append({
            "cmd": vc["cmd"],
            "expected_exit": vc.get("exit_code", 0),
            "actual_exit": proc.returncode,
            "pass": bool(ok_exit and ok_contains and ok_not),
            "reason": None if (ok_exit and ok_contains and ok_not)
                      else ("exit" if not ok_exit
                            else ("missing_contains" if not ok_contains else "unexpected_text")),
            "stdout_tail": out[-500:],
        })
    except subprocess.TimeoutExpired:
        verify["commands"].append({"cmd": vc["cmd"], "pass": False, "reason": "timeout"})
    except Exception as e:
        verify["commands"].append({"cmd": vc["cmd"], "pass": False,
                                    "reason": f"error:{e.__class__.__name__}:{e}"})

# Forbidden pattern scan over diff.patch. Each pattern may declare a `files`
# allowlist; when present, we slice the diff to only those files' hunks.
diff_text = ""
try:
    with open(os.path.join(result_dir, "diff.patch")) as fh:
        diff_text = fh.read()
except Exception:
    pass

def slice_diff_to_files(diff, files):
    """Return the subset of a unified diff touching any of `files`.
    Hunks outside the allowlist are dropped."""
    if not files:
        return diff
    out, keep = [], False
    for line in diff.splitlines(keepends=True):
        if line.startswith("diff --git "):
            keep = any(f in line for f in files)
        if keep:
            out.append(line)
    return "".join(out)

for fp in expected.get("forbidden_patterns", []):
    scope = slice_diff_to_files(diff_text, fp.get("files") or [])
    if re.search(fp["pattern"], scope):
        verify["forbidden_pattern_hits"].append({
            "pattern": fp["pattern"],
            "severity": fp.get("severity", "warning"),
            "description": fp.get("description", ""),
            "scoped_to": fp.get("files") or "all",
        })

# Deps added count (naive: count top-level added lines under dependencies keys)
try:
    proc = subprocess.run(["git", "diff", "HEAD", "--", "package.json"],
                          cwd=work, capture_output=True, text=True)
    in_deps = False
    for line in (proc.stdout or "").splitlines():
        if line.startswith("+ ") or line.startswith("- "):
            continue
        if '"dependencies"' in line or '"devDependencies"' in line:
            in_deps = True
        elif line.strip().startswith("}"):
            in_deps = False
        elif in_deps and line.startswith("+") and not line.startswith("+++"):
            if re.search(r'"[^"]+"\s*:\s*"[^"]+"', line):
                verify["deps_added"] += 1
except Exception:
    pass

# Required / forbidden files
try:
    with open(os.path.join(result_dir, "changed-files.txt")) as fh:
        changed = [l.strip() for l in fh.read().splitlines() if l.strip()]
except Exception:
    changed = []
verify["missing_required_files"] = [
    f for f in expected.get("required_files", [])
    if not os.path.exists(os.path.join(work, f))
]
verify["forbidden_files_present"] = [
    f for f in expected.get("forbidden_files", []) if f in changed
]

total = len(verify["commands"])
passed = sum(1 for r in verify["commands"] if r.get("pass"))
verify["commands_passed"] = passed
verify["commands_total"] = total
verify["verify_score"] = (passed / total) if total else 1.0

verify["disqualifier"] = (
    any(h["severity"] == "disqualifier" for h in verify["forbidden_pattern_hits"])
    or verify["deps_added"] > verify["max_deps_added"]
    or bool(verify["missing_required_files"])
    or bool(verify["forbidden_files_present"])
)

json.dump(verify, open(os.path.join(result_dir, "verify.json"), "w"), indent=2)
PY

# Timing + aggregate
export INVOKE_EXIT WATCHDOG_FIRED
python3 - "$RESULT_DIR" "$FIXTURE" "$ARM" "$RUN_ID" "$T_END" "$ELAPSED" "$TIMEOUT" <<'PY'
import json, os, sys
result_dir, fixture, arm, run_id = sys.argv[1:5]
t_end, elapsed, timeout = int(sys.argv[5]), int(sys.argv[6]), int(sys.argv[7])

timing = json.load(open(os.path.join(result_dir, "timing.json")))
timing["end_epoch"] = t_end
timing["elapsed_seconds"] = elapsed
timing["timeout_seconds"] = timeout
# iter-0012: derive from watchdog signal, not elapsed wall time. Natural
# exits at-or-past the budget (budget == elapsed, or up to ~5s past due to
# SIGTERM grace) are no longer mislabeled as timeouts. Source of truth is
# WATCHDOG_FIRED, set in run-fixture.sh when TIMEOUT_FLAG existed post-wait.
timing["timed_out"] = os.environ.get("WATCHDOG_FIRED", "0") == "1"
json.dump(timing, open(os.path.join(result_dir, "timing.json"), "w"), indent=2)

verify = json.load(open(os.path.join(result_dir, "verify.json")))
try:
    with open(os.path.join(result_dir, "diff.patch")) as f: diff_size = len(f.read())
except Exception: diff_size = 0
try:
    with open(os.path.join(result_dir, "changed-files.txt")) as f:
        changed = [l for l in f.read().splitlines() if l.strip()]
except Exception:
    changed = []

result = {
    "fixture": fixture,
    "arm": arm,
    "run_id": run_id,
    "disqualifier": verify.get("disqualifier", False),
    "verify_score": verify.get("verify_score", 0.0),
    "commands_passed": verify.get("commands_passed", 0),
    "commands_total": verify.get("commands_total", 0),
    "diff_bytes": diff_size,
    "files_changed": len(changed),
    "elapsed_seconds": elapsed,
    "timed_out": timing["timed_out"],
    "invoke_exit": int(os.environ.get("INVOKE_EXIT", "0")),
    "invoke_failure": int(os.environ.get("INVOKE_EXIT", "0")) not in (0,) and not timing["timed_out"],
}
json.dump(result, open(os.path.join(result_dir, "result.json"), "w"), indent=2)
print(json.dumps(result, indent=2))
PY

echo "[run-fixture] done: $RESULT_DIR"
