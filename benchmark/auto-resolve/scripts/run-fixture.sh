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
[ "$ARM" = "variant" ] || [ "$ARM" = "bare" ] || { echo "arm must be variant|bare"; exit 1; }

BENCH_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$BENCH_ROOT/../.." && pwd)"

# Portable timeout: GNU `timeout` on Linux, `gtimeout` via coreutils on macOS.
if command -v gtimeout >/dev/null 2>&1; then
  TIMEOUT_CMD="gtimeout"
elif command -v timeout >/dev/null 2>&1; then
  TIMEOUT_CMD="timeout"
else
  TIMEOUT_CMD=""  # no timeout available — we still run, but can't wall off runaway invocations
fi
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

# Variant gets devlyn skills + project CLAUDE.md pre-baseline
if [ "$ARM" = "variant" ]; then
  mkdir -p "$WORK_DIR/.claude"
  if [ -d "$REPO_ROOT/.claude/skills" ]; then
    cp -R "$REPO_ROOT/.claude/skills" "$WORK_DIR/.claude/skills"
  else
    echo "warning: $REPO_ROOT/.claude/skills missing — variant may lack project skills" >&2
  fi
  if [ -f "$REPO_ROOT/CLAUDE.md" ]; then
    cp "$REPO_ROOT/CLAUDE.md" "$WORK_DIR/CLAUDE.md"
  fi
fi

(cd "$WORK_DIR" \
   && git init -q \
   && git add -A \
   && git -c user.email=b@b -c user.name=b commit -q -m baseline) \
  || { echo "baseline git init failed"; exit 1; }

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
if [ "$ARM" = "variant" ]; then
  if [ "$FIXTURE" = "F9-e2e-ideate-to-preflight" ]; then
    # Novice flow — no pre-placed spec. The arm must generate it via ideate.
    cat > "$PROMPT_FILE" <<EOF
You are a first-time devlyn-cli user. You have a vague idea and want the harness to take it from unstructured ask to shipped, verified feature. Run the chain:

1. Invoke \`/devlyn:ideate\` to turn the idea into docs/VISION.md, docs/ROADMAP.md, and a self-contained spec under docs/roadmap/phase-1/.
2. Once ideate emits a spec path (something like docs/roadmap/phase-1/1.1-<slug>.md), invoke \`/devlyn:auto-resolve "Implement per spec at <that-path>"\` to run the full build → evaluate → critic → docs pipeline.
3. Finally, invoke \`/devlyn:preflight\` to audit the implementation against the generated roadmap.

Follow the skills to completion. Do not short-circuit.

After the whole chain, briefly report: (a) the spec path ideate produced, (b) the auto-resolve terminal verdict, (c) whether preflight found any gaps.

RAW IDEA:
$(cat "$TASK")
EOF
  else
    # Standard variant: spec is pre-placed at canonical roadmap path.
    mkdir -p "$WORK_DIR/docs/roadmap/phase-1"
    cp "$SPEC" "$WORK_DIR/docs/roadmap/phase-1/$FIXTURE.md"
    cat > "$PROMPT_FILE" <<EOF
Use the \`/devlyn:auto-resolve\` skill to implement the spec at \`docs/roadmap/phase-1/$FIXTURE.md\`. Let \`--engine auto\` select the route from the spec's complexity and risk signals — do not override it.

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
  set +e
  if [ -n "$TIMEOUT_CMD" ]; then
    (
      cd "$WORK_DIR"
      "$TIMEOUT_CMD" "$TIMEOUT" claude \
        -p "$(cat "$PROMPT_FILE")" \
        --dangerously-skip-permissions \
        --effort xhigh \
        2>&1
    ) > "$RESULT_DIR/transcript.txt" 2>&1
    INVOKE_EXIT=$?
  else
    (
      cd "$WORK_DIR"
      claude \
        -p "$(cat "$PROMPT_FILE")" \
        --dangerously-skip-permissions \
        --effort xhigh \
        2>&1
    ) > "$RESULT_DIR/transcript.txt" 2>&1
    INVOKE_EXIT=$?
    echo "[run-fixture] warning: no timeout utility on PATH — arm ran without wall clock limit" >&2
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
export INVOKE_EXIT
python3 - "$RESULT_DIR" "$FIXTURE" "$ARM" "$RUN_ID" "$T_END" "$ELAPSED" "$TIMEOUT" <<'PY'
import json, os, sys
result_dir, fixture, arm, run_id = sys.argv[1:5]
t_end, elapsed, timeout = int(sys.argv[5]), int(sys.argv[6]), int(sys.argv[7])

timing = json.load(open(os.path.join(result_dir, "timing.json")))
timing["end_epoch"] = t_end
timing["elapsed_seconds"] = elapsed
timing["timeout_seconds"] = timeout
timing["timed_out"] = elapsed >= timeout
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
