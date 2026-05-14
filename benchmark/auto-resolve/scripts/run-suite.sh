#!/usr/bin/env bash
# run-suite.sh — the single-command benchmark entry.
#
# Orchestrates: fixture setup + arm invocations + blind judge + report + ship
# gate. Called by `npx devlyn-cli benchmark` as well as directly.
#
# Usage:
#   run-suite.sh                            # all fixtures, n=1 smoke
#   run-suite.sh F2 F5                      # specific fixtures only
#   run-suite.sh --dry-run                  # skip model invocations, validate setup
#   run-suite.sh --judge-only --run-id X    # re-judge an existing run
#   run-suite.sh --label v3.6               # tag this run
#   run-suite.sh --bless                    # if ship-gate PASS, promote to baselines/shipped.json
#   run-suite.sh --resolve-skill new        # invoke /devlyn:resolve --spec (the only supported value post iter-0034 cutover; flag kept as accepted no-op for historical runners)
#   run-suite.sh --suite shadow --dry-run   # list shadow tasks; shadow suite refuses provider/judge runs
#
# Exits 0 on PASS, 1 on FAIL.

set -euo pipefail

BENCH_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$BENCH_ROOT/../.." && pwd)"

N=1
LABEL=""
DRY_RUN=0
JUDGE_ONLY=0
RUN_ID_ARG=""
BLESS=0
ACCEPT_MISSING=0
SUITE="golden"
RESOLVE_SKILL="new"
FIXTURES=()

require_value() {
  local flag="$1"
  local value="${2:-}"
  if [ -z "$value" ] || [[ "$value" == --* ]]; then
    echo "$flag requires a value" >&2
    exit 1
  fi
}

while [ $# -gt 0 ]; do
  case "$1" in
    --n)              require_value "$1" "${2:-}"; N="$2"; shift 2;;
    --label)          require_value "$1" "${2:-}"; LABEL="$2"; shift 2;;
    --dry-run)        DRY_RUN=1; shift;;
    --judge-only)     JUDGE_ONLY=1; shift;;
    --run-id)         require_value "$1" "${2:-}"; RUN_ID_ARG="$2"; shift 2;;
    --bless)          BLESS=1; shift;;
    --accept-missing) ACCEPT_MISSING=1; shift;;
    --suite)          require_value "$1" "${2:-}"; SUITE="$2"; shift 2;;
    --resolve-skill)  require_value "$1" "${2:-}"; RESOLVE_SKILL="$2"; shift 2;;
    -h|--help)
      head -22 "$0" | sed -n '3,22p'; exit 0;;
    [FS][0-9]*)       FIXTURES+=("$1"); shift;;
    *)
      echo "unknown arg: $1" >&2; exit 1;;
  esac
done

# iter-0034 Phase 4 cutover (2026-05-03): OLD `/devlyn:auto-resolve` deleted.
# Only `new` (= /devlyn:resolve --spec) is supported. The flag is retained as
# an accepted no-op so historical runners (e.g. run-iter-0033c.sh) keep working
# without edit. `old` is hard-errored with a pointer at the cutover commit.
if [ "$RESOLVE_SKILL" = "old" ]; then
  echo "--resolve-skill old is no longer supported: /devlyn:auto-resolve was deleted in the iter-0034 Phase 4 cutover. Use --resolve-skill new (default) or omit the flag." >&2
  exit 1
fi
[ "$RESOLVE_SKILL" = "new" ] || \
  { echo "--resolve-skill must be 'new' (got '$RESOLVE_SKILL')" >&2; exit 1; }

# Suite → fixtures directory + discovery prefix.
case "$SUITE" in
  golden)  FIXTURES_DIR="$BENCH_ROOT/fixtures";        FIXTURES_GLOB="F*";;
  shadow)  FIXTURES_DIR="$BENCH_ROOT/shadow-fixtures"; FIXTURES_GLOB="S*";;
  *)       echo "error: --suite must be 'golden' or 'shadow' (got '$SUITE')" >&2; exit 1;;
esac

if [ "$SUITE" = "shadow" ] && [ "$DRY_RUN" -eq 0 ]; then
  echo "shadow suite run-suite is dry-run only. Use benchmark headroom/pair with explicit S* candidates for real provider measurement." >&2
  exit 1
fi

# n must be 1 while iteration semantics aren't wired through judge/report.
# Remove this block when compile-report.py gains multi-iter aggregation.
case "$N" in ''|*[!0-9]*) echo "error: --n must be an integer" >&2; exit 1;; esac
[ "$N" -gt 0 ] || { echo "error: --n must be > 0" >&2; exit 1; }
if [ "$N" -ne 1 ]; then
  echo "error: --n $N not yet supported — judge/report currently expect a single iteration per fixture." >&2
  echo "       Track progress in benchmark/auto-resolve/BENCHMARK-DESIGN.md (#multi-iter-roadmap)." >&2
  exit 2
fi

# Auto-discover fixtures if none specified
if [ ${#FIXTURES[@]} -eq 0 ]; then
  for d in "$FIXTURES_DIR"/$FIXTURES_GLOB/; do
    [ -d "$d" ] && FIXTURES+=("$(basename "$d")")
  done
fi

if [ ${#FIXTURES[@]} -eq 0 ]; then
  echo "no fixtures found in $FIXTURES_DIR/ — build the suite first" >&2
  exit 1
fi

# RUN_ID
if [ -n "$RUN_ID_ARG" ]; then
  RUN_ID="$RUN_ID_ARG"
else
  TS=$(date -u +%Y%m%dT%H%M%SZ)
  SHA=$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo nogit)
  RUN_ID="${TS}-${SHA}${LABEL:+-$LABEL}"
fi

RES_DIR="$BENCH_ROOT/results/$RUN_ID"
mkdir -p "$RES_DIR"

print_command() {
  local cmd=(bash "$0" --n "$N" --suite "$SUITE" --resolve-skill "$RESOLVE_SKILL")
  [ -z "$LABEL" ] || cmd+=(--label "$LABEL")
  cmd+=(--run-id "$RUN_ID")
  [ $DRY_RUN -eq 0 ] || cmd+=(--dry-run)
  [ $JUDGE_ONLY -eq 0 ] || cmd+=(--judge-only)
  [ $BLESS -eq 0 ] || cmd+=(--bless)
  [ $ACCEPT_MISSING -eq 0 ] || cmd+=(--accept-missing)
  if [ ${#FIXTURES[@]} -gt 0 ]; then
    cmd+=("${FIXTURES[@]}")
  fi
  printf 'Command: '
  printf '%q ' "${cmd[@]}"
  printf '\n'
}

echo ""
echo "═══ Benchmark Suite Run ═══"
echo "Run-id:        $RUN_ID"
echo "Label:         ${LABEL:-(unlabeled)}"
echo "Suite:         $SUITE ($FIXTURES_DIR)"
echo "Fixtures:      ${FIXTURES[*]}"
echo "n:             $N"
echo "Resolve skill: $RESOLVE_SKILL"
[ $DRY_RUN -eq 1 ] && echo "Mode:          DRY RUN (no model invocations)"
[ $JUDGE_ONLY -eq 1 ] && echo "Mode:          JUDGE ONLY (re-judging existing artifacts)"
print_command
echo ""

# ---- Mirror committed skills into .claude/skills (iter-0017) --------------
# The variant arm reads $REPO_ROOT/.claude/skills/, but iteration commits land
# in config/skills/. Without this step every checkout/revert that touches
# SKILL.md or phase prompts requires a manual `node bin/devlyn.js -y` or
# surgical cp; forgetting it silently runs the suite against stale skills.
# Replicates the clean-then-copy semantics of bin/devlyn.js
# (cleanManagedSkillDirs ~L313 + copyRecursive ~L274). Per-skill staging dir
# + atomic mv keeps a Ctrl-C window from leaving a managed skill missing.
# UNSHIPPED list mirrors bin/devlyn.js:299-304 — keep them in sync.
# Skipped only in --judge-only (no model invocations); runs in --dry-run.
if [ $JUDGE_ONLY -eq 0 ]; then
  SRC_SKILLS="$REPO_ROOT/config/skills"
  DST_SKILLS="$REPO_ROOT/.claude/skills"
  mkdir -p "$DST_SKILLS"
  mirrored=0
  for src_dir in "$SRC_SKILLS"/*/; do
    [ -d "$src_dir" ] || continue
    name=$(basename "$src_dir")
    case "$name" in
      devlyn:auto-resolve-workspace|devlyn:ideate-workspace|preflight-workspace|roadmap-archival-workspace)
        continue ;;
    esac
    staging="$DST_SKILLS/.${name}.staging"
    rm -rf "$staging"
    cp -R "$src_dir" "$staging"
    rm -rf "$DST_SKILLS/$name"
    mv "$staging" "$DST_SKILLS/$name"
    mirrored=$((mirrored + 1))
  done
  echo "[suite] mirrored $mirrored committed skill(s): config/skills/ -> .claude/skills/"
fi

# Prereq checks
if [ $DRY_RUN -eq 0 ] && [ $JUDGE_ONLY -eq 0 ]; then
  command -v claude >/dev/null 2>&1 || { echo "claude CLI missing; install Claude Code first"; exit 1; }
fi
if [ $JUDGE_ONLY -eq 0 ]; then
  command -v codex  >/dev/null 2>&1 || echo "warning: codex CLI missing — judge will fail"
fi
command -v python3 >/dev/null 2>&1 || { echo "python3 missing"; exit 1; }

# Install test-repo deps once per suite run (shared cache)
if [ $DRY_RUN -eq 0 ] && [ $JUDGE_ONLY -eq 0 ]; then
  TEST_REPO="$BENCH_ROOT/fixtures/test-repo"
  if [ ! -d "$TEST_REPO/node_modules" ]; then
    echo "[suite] installing test-repo deps (one-time)"
    if ! (cd "$TEST_REPO" && npm install --no-audit --no-fund --loglevel=error); then
      echo "[suite] ✗ npm install in test-repo failed — check network/npm auth. Aborting." >&2
      exit 1
    fi
  fi
fi

# ---- Run arms ---------------------------------------------------------------
if [ $JUDGE_ONLY -eq 0 ]; then
  for fid in "${FIXTURES[@]}"; do
    [ -d "$FIXTURES_DIR/$fid" ] || { echo "[suite] skip $fid (missing)"; continue; }
    for arm in variant solo_claude bare; do
      echo "[suite] ► $fid / $arm (resolve-skill=$RESOLVE_SKILL)"
      extra=""
      [ $DRY_RUN -eq 1 ] && extra="--dry-run"
      bash "$BENCH_ROOT/scripts/run-fixture.sh" \
        --fixture "$fid" --arm "$arm" --run-id "$RUN_ID" \
        --resolve-skill "$RESOLVE_SKILL" $extra \
        || echo "[suite] ✗ $fid / $arm (arm failure tolerated; artifacts still captured)"
    done
  done
fi

# ---- Judge ------------------------------------------------------------------
for fid in "${FIXTURES[@]}"; do
  if [ ! -d "$BENCH_ROOT/results/$RUN_ID/$fid" ]; then
    echo "[suite] skip judge for $fid (no results)"
    continue
  fi
  if [ $DRY_RUN -eq 1 ]; then
    echo "[suite] DRY RUN — skipping judge for $fid"
    continue
  fi
  echo "[suite] ► judge $fid"
  bash "$BENCH_ROOT/scripts/judge.sh" --fixture "$fid" --run-id "$RUN_ID" \
    || echo "[suite] ✗ judge failed for $fid (will appear as NO_JUDGE in report)"
done

# ---- Compile report + ship gate --------------------------------------------
if [ $DRY_RUN -eq 1 ]; then
  echo ""
  echo "[suite] DRY RUN complete — results in $RES_DIR"
  if [ "$SUITE" = "shadow" ]; then
    echo "Use benchmark headroom/pair with explicit S* candidates for real provider measurement."
  else
    echo "Run without --dry-run to invoke models."
  fi
  exit 0
fi

echo ""
python3 "$BENCH_ROOT/scripts/compile-report.py" --run-id "$RUN_ID" ${LABEL:+--label "$LABEL"}

extra_flag=""
[ $BLESS -eq 1 ] && extra_flag="$extra_flag --bless"
[ $ACCEPT_MISSING -eq 1 ] && extra_flag="$extra_flag --accept-missing"
python3 "$BENCH_ROOT/scripts/ship-gate.py" --run-id "$RUN_ID" $extra_flag
