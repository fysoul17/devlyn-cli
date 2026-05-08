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
  echo "usage: $0 --fixture <FID> --arm <variant|solo_claude|bare|l2_gated|l2_risk_probes|l2_forced> --run-id <ID> [--resolve-skill new] [--dry-run]"
  exit 1
}

kill_worktree_processes() {
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

FIXTURE=""; ARM=""; RUN_ID=""; DRY_RUN=0
RESOLVE_SKILL="new"
while [ $# -gt 0 ]; do
  case "$1" in
    --fixture)        FIXTURE="$2"; shift 2;;
    --arm)            ARM="$2";     shift 2;;
    --run-id)         RUN_ID="$2";  shift 2;;
    --resolve-skill)  RESOLVE_SKILL="$2"; shift 2;;
    --dry-run)        DRY_RUN=1;    shift;;
    *) usage;;
  esac
done
[ -n "$FIXTURE" ] && [ -n "$ARM" ] && [ -n "$RUN_ID" ] || usage
# iter-0019: original 3 arms — variant (L2-old: Claude orchestrator + Codex BUILD pair via --engine auto),
# solo_claude (L1: Claude orchestrator, codex blocked by shim+wrapper enforcement),
# bare (L0: direct claude -p, no skill, no codex).
# iter-0033c (Codex R0-infra adoption, 2026-05-02): two L2 diagnostic arms for /devlyn:resolve —
# l2_gated (--engine claude, no --pair-verify; pair fires only on natural triggers),
# l2_risk_probes (--engine claude --risk-probes; pair converts visible Verification bullets to executable probes before IMPLEMENT),
# l2_forced (--engine claude --pair-verify; retired because it leaks pair-awareness before IMPLEMENT).
[ "$ARM" = "variant" ] || [ "$ARM" = "solo_claude" ] || [ "$ARM" = "bare" ] \
  || [ "$ARM" = "l2_gated" ] || [ "$ARM" = "l2_risk_probes" ] || [ "$ARM" = "l2_forced" ] || \
  { echo "arm must be variant|solo_claude|bare|l2_gated|l2_risk_probes|l2_forced"; exit 1; }
# iter-0033c (Codex R0-infra Q2): l2_* arms require NEW skill surface (only NEW
# `/devlyn:resolve` honors --pair-verify; OLD `/devlyn:auto-resolve` would silently
# ignore the flag and produce mis-attributed L2 numbers).
if { [ "$ARM" = "l2_gated" ] || [ "$ARM" = "l2_risk_probes" ] || [ "$ARM" = "l2_forced" ]; } && [ "$RESOLVE_SKILL" != "new" ]; then
  echo "l2_* arms require --resolve-skill new (got '$RESOLVE_SKILL')"; exit 1
fi
if [ "$ARM" = "l2_forced" ]; then
  echo "l2_forced is retired: it puts --pair-verify in the initial prompt, so IMPLEMENT can become pair-aware before the diff is frozen. Use scripts/run-frozen-verify-pair.sh for leak-free VERIFY-pair measurement." >&2
  exit 1
fi
# iter-0034 Phase 4 cutover (2026-05-03): OLD `/devlyn:auto-resolve` was
# deleted. Only `new` (= /devlyn:resolve --spec) is supported. The flag stays
# an accepted no-op so historical runners (run-iter-0033c.sh:137) keep working
# unchanged. `old` is hard-errored — silently downgrading to `new` would
# produce mis-attributed results in any pre-cutover replay attempt.
if [ "$RESOLVE_SKILL" = "old" ]; then
  echo "--resolve-skill old is no longer supported: /devlyn:auto-resolve was deleted in the iter-0034 Phase 4 cutover. Use --resolve-skill new (default) or omit the flag." >&2
  exit 1
fi
[ "$RESOLVE_SKILL" = "new" ] || \
  { echo "--resolve-skill must be 'new' (got '$RESOLVE_SKILL')"; exit 1; }

BENCH_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$BENCH_ROOT/../.." && pwd)"

FIX_DIR=""
for candidate in "$BENCH_ROOT/fixtures/$FIXTURE" "$BENCH_ROOT/shadow-fixtures/$FIXTURE"; do
  if [ -d "$candidate" ]; then FIX_DIR="$candidate"; break; fi
done
[ -n "$FIX_DIR" ] || { echo "fixture not found in fixtures/ or shadow-fixtures/: $FIXTURE"; exit 1; }

META="$FIX_DIR/metadata.json"
EXPECTED="$FIX_DIR/expected.json"
SPEC="$FIX_DIR/spec.md"
TASK="$FIX_DIR/task.txt"
SETUP="$FIX_DIR/setup.sh"
for f in "$META" "$EXPECTED" "$SPEC" "$TASK"; do
  [ -f "$f" ] || { echo "fixture missing required file: $f (see SCHEMA.md)"; exit 1; }
done

TIMEOUT=$(python3 -c "import json; print(json.load(open('$META'))['timeout_seconds'])")
if [ "$ARM" = "l2_risk_probes" ]; then
  # This arm adds a bounded Codex probe-derive phase before IMPLEMENT and a
  # bounded Codex pair-JUDGE during VERIFY. The full-pipeline gate still
  # enforces wall-time efficiency by pair/solo ratio; this budget prevents a
  # false timeout before the mandatory second judge can emit its contract line.
  TIMEOUT=$((TIMEOUT + 600))
fi

RESULT_DIR="$BENCH_ROOT/results/$RUN_ID/$FIXTURE/$ARM"
mkdir -p "$RESULT_DIR"

# Fresh copy of test-repo — order matters. We copy arm-env files (skills,
# CLAUDE.md) BEFORE the baseline commit so they do NOT appear in the diff
# the arm produces. That keeps diff.patch focused on the arm's actual code
# changes, so forbidden-pattern scans and judge rubrics see only real work.
WORK_DIR="/tmp/bench-${RUN_ID}-${FIXTURE}-${ARM}"
rm -rf "$WORK_DIR"
cp -R "$BENCH_ROOT/fixtures/test-repo" "$WORK_DIR"

# All skill-driven arms (variant / solo_claude / l2_gated / l2_forced) get
# devlyn skills + project CLAUDE.md pre-baseline + codex shim + monitored
# wrapper. Bare gets nothing (no skill, no shim, no env).
#
# iter-0019: solo_claude (L1) shares variant-arm staging because the L1 arm
# runs the same orchestrator on the same skills — only difference is codex
# is blocked. Shim catches PATH resolution; wrapper catches direct-path
# invocations.
# iter-0033c (Codex R0-infra Q6): l2_gated/l2_forced share variant staging
# (codex unblocked, shim+wrapper routing). Difference vs variant is the
# ENGINE_CLAUSE branch below — l2_* run --engine claude (Claude IMPLEMENT)
# while variant uses --engine auto (Codex IMPLEMENT). Pair-mode in
# /devlyn:resolve VERIFY phase pulls Codex via the OTHER-engine rule.
if [ "$ARM" = "variant" ] || [ "$ARM" = "solo_claude" ] \
   || [ "$ARM" = "l2_gated" ] || [ "$ARM" = "l2_risk_probes" ] || [ "$ARM" = "l2_forced" ]; then
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
    # iter-0019.5 (Codex R1, 2026-04-28): when ARM=solo_claude, OMIT
    # CODEX_REAL_BIN + CODEX_MONITORED_PATH from the env block. Reason: the
    # absolute path to the real codex binary in CODEX_REAL_BIN is itself
    # the bypass weapon — the orchestrator could `Bash("$CODEX_REAL_BIN
    # exec ...")` and reach real codex, defeating both shim (PATH lookup
    # bypassed) and wrapper (codex-monitored.sh not invoked). With the
    # var absent: shim's BLOCKED check fires before it needs CODEX_REAL_BIN
    # so removing it doesn't break the shim path; if CODEX_BLOCKED is
    # somehow unset later, the shim now FAILS CLOSED (no real binary to
    # delegate to) rather than silently delegating. The earlier "diagnostic
    # visibility" justification was inverted — it handed the orchestrator
    # the bypass weapon. Across iter-0019 paid 5-fixture run the bypass
    # was OPEN but never exercised; this closes the surface preemptively
    # before iter-0020's 9-fixture L0/L1/L2 run.
    # iter-0033c (Codex R0-infra Q5): l2_gated/l2_forced are codex-UNBLOCKED
    # (codex must be reachable for VERIFY pair-JUDGE). They take the variant
    # path: ARM_CODEX_BLOCKED=0 → python writer omits CODEX_BLOCKED from env
    # entirely (the shim refuses on any non-empty value, so 0 ≠ unset).
    if [ "$ARM" = "solo_claude" ]; then
      ARM_CODEX_BLOCKED=1
    else
      ARM_CODEX_BLOCKED=0
    fi
    python3 - "$WORK_DIR/.claude/settings.json" \
      "$INJECTED_PATH" "$CODEX_REAL_BIN" "$CODEX_MONITORED_PATH" "$ARM_CODEX_BLOCKED" "$ARM" <<'PY'
import json, sys
out_path, path_val, real_bin, monitored, codex_blocked, arm = sys.argv[1:7]
env = {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "DISABLE_AUTOUPDATER": "1",
    "PATH": path_val,
}
if codex_blocked == "1":
    # iter-0019.5: solo_claude (L1 arm) — codex blocked at binary layer.
    # Do NOT export CODEX_REAL_BIN / CODEX_MONITORED_PATH to the
    # orchestrator subshell; those vars become bypass weapons under any
    # CODEX_BLOCKED enforcement gap.
    env["CODEX_BLOCKED"] = "1"
else:
    # variant arm (L2) — codex routes through wrapper as part of pair-mode
    # BUILD; both vars are required by the shim/wrapper handshake.
    env["CODEX_REAL_BIN"] = real_bin
    env["CODEX_MONITORED_PATH"] = monitored
    if arm == "l2_risk_probes":
        # Risk-probe derivation is a bounded contract-conversion step. A long
        # Codex run is a harness failure, not useful extra quality signal.
        env["CODEX_MONITORED_TIMEOUT_SEC"] = "300"
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

# iter-0019.6: stage normalized .devlyn/spec-verify.json for BUILD_GATE.
# Only commands safe to reveal before IMPLEMENT may be staged here. Commands
# that reference BENCH_FIXTURE_DIR are hidden post-run oracles; staging their
# path leaks verifier names into the arm and lets agents search for answer-key
# files. Those commands still run in the post-run verifier below.
if [ "$ARM" = "variant" ] || [ "$ARM" = "solo_claude" ] \
   || [ "$ARM" = "l2_gated" ] || [ "$ARM" = "l2_risk_probes" ] || [ "$ARM" = "l2_forced" ]; then
  python3 - "$EXPECTED" "$WORK_DIR/.devlyn/spec-verify.json" <<'PY'
import json, os, sys
expected = json.load(open(sys.argv[1]))
out_path = sys.argv[2]
visible_commands = [
    cmd for cmd in expected.get("verification_commands", [])
    if "BENCH_FIXTURE_DIR" not in str(cmd.get("cmd", ""))
]
normalized = {"verification_commands": visible_commands}
os.makedirs(os.path.dirname(out_path), exist_ok=True)
if not visible_commands:
    raise SystemExit(0)
with open(out_path, "w") as f:
    json.dump(normalized, f, indent=2)
    f.write("\n")
PY
fi

# Build arm-specific prompt + place arm-specific environment files. Anything
# that's "benchmark scaffolding" (spec path placement, prompt wrapper) is
# committed to the work repo as a separate pre-model commit so the model's
# diff shows only its own work.
#
# Per-arm prompt selection is:
#   1. Fixture-id-aware for F9 (end-to-end novice fixture, no pre-placed spec).
#   2. Spec-mode `/devlyn:resolve --spec <path>` for the rest (post iter-0034
#      Phase 4 cutover the OLD `/devlyn:auto-resolve` route was deleted).
PROMPT_FILE="$RESULT_DIR/input.md"
# Variant uses --engine auto (experimental dual-engine: codex BUILD + claude
# critique pair); solo_claude uses --engine claude explicitly so the orchestrator
# routes every phase to Claude and never tries to invoke codex. The CODEX_BLOCKED
# shim enforces this at the binary layer if the orchestrator misroutes. Both
# arms pass the engine flag explicitly so they survive future runtime-default
# changes (post iter-0020 close-out: default flipped to claude).
if [ "$ARM" = "variant" ] || [ "$ARM" = "solo_claude" ] \
   || [ "$ARM" = "l2_gated" ] || [ "$ARM" = "l2_risk_probes" ] || [ "$ARM" = "l2_forced" ]; then
  case "$ARM" in
    solo_claude)
      ENGINE_CLAUSE="--engine claude"
      ENGINE_PROMPT_HINT="Run with \`--engine claude\` for every phase. Codex must not be invoked — the harness has blocked it at the binary layer for this run."
      ;;
    variant)
      ENGINE_CLAUSE="--engine auto"
      ENGINE_PROMPT_HINT="Run with \`--engine auto\` so the experimental dual-engine routing fires (Codex BUILD/FIX, Claude EVAL/CRITIC) — do not override it."
      ;;
    l2_gated)
      # NEW L2 with natural pair-mode triggers. Claude does IMPLEMENT;
      # pair-JUDGE in VERIFY fires per /devlyn:resolve PHASE 5 policy
      # (high complexity, coverage_failed, or warning-level mechanical
      # findings; never after HIGH/CRITICAL mechanical blockers). Codex
      # remains available as the OTHER-engine pair-JUDGE candidate.
      ENGINE_CLAUSE="--engine claude"
      ENGINE_PROMPT_HINT="Run with \`--engine claude\` and let the orchestrator's pair-mode (VERIFY) trigger naturally per its policy. Codex is available as the OTHER-engine pair-JUDGE — the harness has not blocked it. Do NOT pass \`--pair-verify\`; this arm measures gated triggering."
      ;;
    l2_risk_probes)
      # NEW L2 probe-derive arm. Claude plans/implements; Codex is used before
      # IMPLEMENT only to derive bounded executable probes from visible
      # Verification bullets. BUILD_GATE and VERIFY execute those probes
      # mechanically via spec-verify-check.py.
      ENGINE_CLAUSE="--engine claude --risk-probes"
      ENGINE_PROMPT_HINT="Run with \`--engine claude --risk-probes\`. Codex is available as the OTHER-engine probe derivation and pair-JUDGE engine. The probe phase may only derive executable checks from visible \`## Verification\` text; it must not read hidden fixture/verifier paths."
      ;;
    l2_forced)
      # iter-0033c: NEW L2 forced — pair-JUDGE always fires. Diagnostic arm
      # for Gate 6 fixture-level cross-check + Gate 7 attribution causality.
      ENGINE_CLAUSE="--engine claude --pair-verify"
      ENGINE_PROMPT_HINT="Run with \`--engine claude --pair-verify\` so VERIFY pair-mode fires unconditionally. Codex is the OTHER-engine pair-JUDGE."
      ;;
  esac
  if [ "$FIXTURE" = "F9-e2e-ideate-to-resolve" ]; then
    # F9 NEW chain (iter-0033a): /devlyn:ideate --quick → /devlyn:resolve
    # --spec <emitted-path>. No pre-placed spec; the variant arm generates it
    # via ideate. No preflight (folded into resolve's VERIFY phase).
    #
    # --quick is mandatory in autonomous (claude -p) mode: default ideate
    # invokes interactive Q&A which has no human to answer in a benchmark
    # subprocess — the agent asks questions and stops. --quick uses
    # single-turn assume-and-confirm: AI synthesizes the spec from the goal
    # plus an explicit assumptions block, so the chain proceeds end-to-end
    # without user input. Smoke 3 (iter-0033a, 2026-04-30) caught this:
    # default-mode F9 produced empty diffs after 54s of Q&A waiting.
    cat > "$PROMPT_FILE" <<EOF
You are a first-time devlyn-cli user. You have a vague idea and want the 2-skill harness to take it from unstructured ask to shipped, verified feature. Run the chain:

1. Invoke \`/devlyn:ideate --quick ${ENGINE_CLAUSE}\` to turn the idea into a verifiable spec. \`--quick\` is mandatory: this is an autonomous run with no human to answer interactive questions, so ideate must synthesize the spec single-turn from the goal text and emit assumptions explicitly. The skill announces \`spec ready — /devlyn:resolve --spec <emitted-path>\` when done. The emitted spec lives at \`docs/specs/<id>-<slug>/spec.md\` with a sibling \`spec.expected.json\`.
2. Take the emitted spec path verbatim from the announce line and invoke \`/devlyn:resolve --spec <that-path> ${ENGINE_CLAUSE}\` to run PLAN → IMPLEMENT → BUILD_GATE → CLEANUP → VERIFY (VERIFY is the fresh-subagent final phase — there is no separate preflight skill in the 2-skill design).

${ENGINE_PROMPT_HINT}

Follow the skills to completion. Do not short-circuit. Do not invoke \`/devlyn:auto-resolve\` or \`/devlyn:preflight\` — they are not part of the 2-skill chain. Do not stop after ideate; the chain only counts as complete after \`/devlyn:resolve\` returns a terminal verdict.

After the whole chain, briefly report: (a) the spec path ideate produced, (b) the resolve terminal verdict, (c) whether VERIFY surfaced any findings.

RAW IDEA:
$(cat "$TASK")
EOF
  else
    # Spec-mode /devlyn:resolve: spec pre-placed at the canonical roadmap path
    # the harness has used since iter-0019. Pre-Phase-4 this branch shared
    # staging with the OLD /devlyn:auto-resolve route; iter-0034 deleted the
    # OLD branch and this is now the only non-F9 path.
    mkdir -p "$WORK_DIR/docs/roadmap/phase-1"
    cp "$SPEC" "$WORK_DIR/docs/roadmap/phase-1/$FIXTURE.md"
    cat > "$PROMPT_FILE" <<EOF
Use the \`/devlyn:resolve --spec docs/roadmap/phase-1/$FIXTURE.md ${ENGINE_CLAUSE}\` skill to implement the spec. ${ENGINE_PROMPT_HINT}

The 2-skill design folds verification into resolve's VERIFY phase — there is no separate \`/devlyn:preflight\`, \`/devlyn:auto-resolve\`, or other 3-skill orchestrator at HEAD.

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
  # must not load the operator's user-level MCP/plugins/settings (pencil,
  # codex-cli, telegram, vercel, ...). Project policy is "MCP/plugins are not in
  # the loop"; loading user config inside the arm is uncontrolled environment
  # leaking into the experiment. `--setting-sources project,local` keeps user
  # plugin enablement out of the run but Claude Code still reads the installed
  # plugin registry for autoupdate. Official Claude Code settings document
  # `DISABLE_AUTOUPDATER=1` / `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` as the
  # supported way to disable that background traffic, while preserving OAuth
  # auth from the real HOME. `--strict-mcp-config` + an empty `mcpServers` object
  # forces a hermetic MCP set. Skills still resolve via the project
  # `.claude/skills` staged into the worktree.
  # `--debug-file` records per-arm init/runtime so the next hang has a
  # location, not a guess.
  TIMEOUT_FLAG="$RESULT_DIR/.timed_out"
  rm -f "$TIMEOUT_FLAG"

  set +e
  set -m
  (
    cd "$WORK_DIR"
    # iter-0009 + iter-0019: prepend codex shim PATH for any arm that staged
    # one. variant routes through codex-monitored.sh; solo_claude refuses on
    # CODEX_BLOCKED=1; bare has no shim.
    # iter-0033c (Codex R0-infra Q6): l2_gated/l2_forced ALSO need the shim
    # PATH — they route Claude IMPLEMENT but Codex pair-JUDGE in VERIFY hits
    # `codex exec` through the wrapper for starvation safety.
    if { [ "$ARM" = "variant" ] || [ "$ARM" = "solo_claude" ] \
         || [ "$ARM" = "l2_gated" ] || [ "$ARM" = "l2_risk_probes" ] || [ "$ARM" = "l2_forced" ]; } \
       && [ -x "$WORK_DIR/.devlyn-bin/codex" ]; then
      export PATH="$WORK_DIR/.devlyn-bin:$PATH"
      [ "$ARM" = "solo_claude" ] && export CODEX_BLOCKED=1
    fi
    # iter-0019.6: BUILD_GATE's spec-verify-check.py uses BENCH_WORKDIR for
    # commands that escape the work-dir (e.g. F9's outside-repo check via
    # `cd /tmp && node $BENCH_WORKDIR/bin/cli.js gitstats`). Mirror exactly
    # what the post-run verifier (run-fixture.sh:431-434) sets so the gate
    # sees the same environment shape.
    export BENCH_WORKDIR="$WORK_DIR"
    # Python helper scripts run inside the benchmark worktree. Do not let them
    # rewrite tracked __pycache__ artifacts and pollute the arm-only diff.
    export PYTHONDONTWRITEBYTECODE=1
    # Official Claude Code setting: disable background plugin/autoupdate traffic
    # before process startup. Project settings env is not early enough for all
    # startup paths.
    export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
    export DISABLE_AUTOUPDATER=1
    exec claude \
      -p "$(cat "$PROMPT_FILE")" \
      --dangerously-skip-permissions \
      --effort xhigh \
      --setting-sources project,local \
      --strict-mcp-config \
      --mcp-config '{"mcpServers":{}}' \
      --debug-file "$RESULT_DIR/claude-debug.log"
  ) > "$RESULT_DIR/transcript.txt" 2>&1 &
  CHILD_PID=$!
  set +m

  (
    deadline=$((T_START + TIMEOUT))
    while kill -0 "$CHILD_PID" 2>/dev/null; do
      now=$(date +%s)
      if [ "$now" -ge "$deadline" ]; then
        : > "$TIMEOUT_FLAG"
        kill -TERM -- "-$CHILD_PID" 2>/dev/null
        kill_worktree_processes "$WORK_DIR" TERM
        sleep 5
        kill -KILL -- "-$CHILD_PID" 2>/dev/null
        kill_worktree_processes "$WORK_DIR" KILL
        exit 0
      fi
      remaining=$((deadline - now))
      [ "$remaining" -gt 30 ] && sleep 30 || sleep "$remaining"
    done
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
    kill_worktree_processes "$WORK_DIR" TERM
    sleep 1
    kill_worktree_processes "$WORK_DIR" KILL
    echo "[run-fixture] arm timed out after ${TIMEOUT}s — INVOKE_EXIT=124" >&2
  else
    # A clean `claude -p` exit can still leave OTHER-engine pair-JUDGE
    # descendants alive; reap any process group rooted in this arm worktree.
    kill_worktree_processes "$WORK_DIR" TERM
    sleep 1
    kill_worktree_processes "$WORK_DIR" KILL
  fi
  set -e
fi

T_END=$(date +%s)
ELAPSED=$((T_END - T_START))

# Restore tracked Python bytecode to the scaffold commit and remove only
# untracked bytecode. Helper invocations must not count as model work, but
# deleting tracked scaffold files would also pollute changed-files.txt.
(cd "$WORK_DIR" \
  && git restore --source "$SCAFFOLD_SHA" -- .claude/skills/_shared/__pycache__ 2>/dev/null || true)
cleanup_roots=()
[ -d "$WORK_DIR/.claude" ] && cleanup_roots+=("$WORK_DIR/.claude")
[ -d "$WORK_DIR/.devlyn" ] && cleanup_roots+=("$WORK_DIR/.devlyn")
if [ ${#cleanup_roots[@]} -gt 0 ]; then
  find "${cleanup_roots[@]}" -type f \( -name '*.pyc' -o -name '*.pyo' \) -print0 \
    | while IFS= read -r -d '' py_file; do
        rel="${py_file#$WORK_DIR/}"
        if ! (cd "$WORK_DIR" && git ls-files --error-unmatch "$rel" >/dev/null 2>&1); then
          rm -f "$py_file"
        fi
      done
  find "${cleanup_roots[@]}" -type d -name __pycache__ -empty -delete || true
fi

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

if { [ "$ARM" = "variant" ] || [ "$ARM" = "solo_claude" ] \
     || [ "$ARM" = "l2_gated" ] || [ "$ARM" = "l2_risk_probes" ]; } \
   && [ -f "$WORK_DIR/.devlyn/pipeline.state.json" ] \
   && [ -f "$WORK_DIR/.claude/skills/_shared/verify-merge-findings.py" ]; then
  if [ -f "$WORK_DIR/.devlyn/codex-judge.stdout" ] \
     && [ -f "$WORK_DIR/.claude/skills/_shared/collect-codex-findings.py" ]; then
    if ! python3 "$WORK_DIR/.claude/skills/_shared/collect-codex-findings.py" \
        --devlyn-dir "$WORK_DIR/.devlyn" \
        > "$RESULT_DIR/collect-codex-findings.log" 2>&1; then
      echo "[run-fixture] Codex pair findings collection failed; see $RESULT_DIR/collect-codex-findings.log" >&2
    fi
  fi
  if ! python3 "$WORK_DIR/.claude/skills/_shared/verify-merge-findings.py" \
      --devlyn-dir "$WORK_DIR/.devlyn" --write-state \
      > "$RESULT_DIR/verify-merge-normalize.log" 2>&1; then
    echo "[run-fixture] verify merge normalization failed; see $RESULT_DIR/verify-merge-normalize.log" >&2
  fi
fi

if { [ "$ARM" = "variant" ] || [ "$ARM" = "solo_claude" ] \
     || [ "$ARM" = "l2_gated" ] || [ "$ARM" = "l2_risk_probes" ]; } && [ -d "$WORK_DIR/.devlyn" ]; then
  run_dir=$(find "$WORK_DIR/.devlyn/runs" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort | tail -1 || true)
  if [ -n "$run_dir" ]; then
    rm -rf "$RESULT_DIR/run-archive"
    cp -R "$run_dir" "$RESULT_DIR/run-archive"
    [ -f "$RESULT_DIR/run-archive/pipeline.state.json" ] \
      || [ ! -f "$WORK_DIR/.devlyn/pipeline.state.json" ] \
      || cp "$WORK_DIR/.devlyn/pipeline.state.json" "$RESULT_DIR/run-archive/pipeline.state.json"
  else
    rm -rf "$RESULT_DIR/run-archive"
    mkdir -p "$RESULT_DIR/run-archive"
    find "$WORK_DIR/.devlyn" -maxdepth 1 -type f -exec cp {} "$RESULT_DIR/run-archive/" \;
  fi
fi

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
# Hidden benchmark verifiers live in the fixture directory, outside the arm's
# work tree. This keeps oracle code from becoming implementation context.
verify_env["BENCH_FIXTURE_DIR"] = os.path.dirname(os.path.abspath(sys.argv[1]))

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

state = {}
state_path = os.path.join(result_dir, "run-archive", "pipeline.state.json")
if os.path.isfile(state_path):
    with open(state_path) as f:
        state = json.load(f)
verify_phase = (state.get("phases") or {}).get("verify") or {}
sub_verdicts = verify_phase.get("sub_verdicts")
pair_trigger = verify_phase.get("pair_trigger") or ((state.get("verify") or {}).get("pair_trigger"))
pair_mode = bool(
    isinstance(sub_verdicts, dict)
    and (sub_verdicts.get("judge_codex") is not None or sub_verdicts.get("pair_judge") is not None)
) or bool(verify_phase.get("pair_mode"))

invoke_exit = int(os.environ.get("INVOKE_EXIT", "0"))
plugin_contamination = False
plugin_contamination_reason = None
debug_path = os.path.join(result_dir, "claude-debug.log")
try:
    with open(debug_path, errors="replace") as f:
        debug_text = f.read()
except OSError:
    debug_text = ""
if (
    "Plugin autoupdate: checking installed plugins" in debug_text
    or "Caching plugin from source:" in debug_text
    or "Cloned repository from " in debug_text
    or "Successfully cached plugin " in debug_text
    or "Found 8 plugins (8 enabled" in debug_text
):
    if "Plugin autoupdate: skipped (auto-updater disabled)" not in debug_text:
        plugin_contamination = True
        plugin_contamination_reason = "plugin_contamination"

invoke_failure = (
    (invoke_exit not in (0,) and not timing["timed_out"])
    or plugin_contamination
)
invoke_failure_reason = None
if plugin_contamination:
    invoke_failure_reason = plugin_contamination_reason
elif invoke_failure:
    transcript_path = os.path.join(result_dir, "transcript.txt")
    haystack = ""
    for path in (transcript_path, debug_path):
        try:
            with open(path, errors="replace") as f:
                haystack += "\n" + f.read()
        except OSError:
            pass
    if "You've hit your limit" in haystack or "rate_limit_error" in haystack:
        invoke_failure_reason = "provider_limit"

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
    "environment_contamination": plugin_contamination,
    "environment_contamination_reason": plugin_contamination_reason,
    "invoke_exit": invoke_exit,
    "invoke_failure": invoke_failure,
    "invoke_failure_reason": invoke_failure_reason,
    "terminal_verdict": ((state.get("phases") or {}).get("final_report") or {}).get("verdict"),
    "verify_verdict": verify_phase.get("verdict"),
    "pair_trigger": pair_trigger,
    "pair_mode": pair_mode,
}
json.dump(result, open(os.path.join(result_dir, "result.json"), "w"), indent=2)
print(json.dumps(result, indent=2))
PY

echo "[run-fixture] done: $RESULT_DIR"
