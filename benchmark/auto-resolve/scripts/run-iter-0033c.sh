#!/usr/bin/env bash
# run-iter-0033c.sh — orchestrate the iter-0033c suite (NEW L2 vs NEW L1).
#
# Codex R0.5-infra design: bypass run-suite.sh + ship-gate.py + compile-report.py
# (those enforce variant/bare semantics that don't apply here). Call run-fixture.sh
# directly per fixture per arm; per-fixture interleaving for fail-early on hard-floor
# violations (Codex R0.5-infra Q4).
#
# Per Mission 1: serial only, no parallel-fleet.
#
# Usage:
#   run-iter-0033c.sh --label <label> [--fixtures F1,F2,...] [--c1-summary <path>] [--f9-judge <path>]
#                     [--manifest-out <path>] [--results-out-dir <path>] [--skip-judge]
#
# Pre-flight: smoke 1b (codex availability) — fail-fast.
# Arms per fixture:
#   - All fixtures: solo_claude (L1 rerun) + l2_gated (L2 natural triggers)
#   - Pair-eligible (per manifest): also l2_forced (L2 diagnostic)
# After arms: judge.sh per fixture; manifest build; iter-0033c-compare.py.
set -euo pipefail

usage() {
  cat >&2 <<EOF
usage: $0 --label <label>
          [--fixtures F1,F2,F3,F4,F5,F6,F7,F8,F9]
          [--c1-summary <path>]   # default: benchmark/auto-resolve/results/3bc86dd-iter0033c1-new-20260501T004229Z/summary.json
          [--f9-judge <path>]     # default: benchmark/auto-resolve/results/4e3d89a-iter-0033a-f9-smoke3-20260430T232747Z/F9-e2e-ideate-to-resolve/judge.json
          [--results-root <path>] # default: benchmark/auto-resolve/results
          [--skip-judge]          # skip judge.sh (re-runnable post-hoc)
EOF
  exit 1
}

LABEL=""
FIXTURES_CSV="F1,F2,F3,F4,F5,F6,F7,F8,F9"
C1_SUMMARY="benchmark/auto-resolve/results/3bc86dd-iter0033c1-new-20260501T004229Z/summary.json"
F9_JUDGE="benchmark/auto-resolve/results/4e3d89a-iter-0033a-f9-smoke3-20260430T232747Z/F9-e2e-ideate-to-resolve/judge.json"
RESULTS_ROOT="benchmark/auto-resolve/results"
SKIP_JUDGE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --label)         LABEL="$2"; shift 2;;
    --fixtures)      FIXTURES_CSV="$2"; shift 2;;
    --c1-summary)    C1_SUMMARY="$2"; shift 2;;
    --f9-judge)      F9_JUDGE="$2"; shift 2;;
    --results-root)  RESULTS_ROOT="$2"; shift 2;;
    --skip-judge)    SKIP_JUDGE=1; shift;;
    *) usage;;
  esac
done
[ -n "$LABEL" ] || usage

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

# --- Smoke 1b: codex availability fail-fast ---
echo "=== Smoke 1b: Codex availability ==="
if ! command -v codex >/dev/null 2>&1; then
  echo "FAIL: codex not on PATH — iter-0033c L2 arms cannot run" >&2
  exit 1
fi
echo "PASS: $(command -v codex) ($(codex --version 2>&1 | head -1))"

# --- Mirror committed skills to .claude/skills (parity with run-suite.sh:111-141) ---
# Iteration commits land in config/skills/; the variant-arm runtime resolves
# from .claude/skills/. Without this step, edits to SKILL.md / phase prompts /
# _shared scripts (e.g. archive_run.py iter-0033c fix) silently run against the
# stale mirror. UNSHIPPED list mirrors bin/devlyn.js:299-304.
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
echo "[run-iter-0033c] mirrored $mirrored committed skill(s): config/skills/ -> .claude/skills/"

# --- Setup ---
HEAD_SHA=$(git rev-parse --short HEAD)
TS=$(date -u +%Y%m%dT%H%M%SZ)
RUN_ID="${HEAD_SHA}-iter0033c-${LABEL}-${TS}"
RESULTS_DIR="$RESULTS_ROOT/$RUN_ID"
mkdir -p "$RESULTS_DIR"
echo "[run-iter-0033c] RUN_ID=$RUN_ID"
echo "[run-iter-0033c] RESULTS_DIR=$RESULTS_DIR"

# --- Determine pair-eligible set from manifest input bundle ---
# Pair eligibility is pre-registered from C1/F9 before any iter-0033c arms run.
# The later L1 rerun summary is archived into the final manifest for provenance;
# it must not change the arm-selection set after execution has begun.
DRAFT_MANIFEST="$RESULTS_DIR/manifest-draft.json"
python3 benchmark/auto-resolve/scripts/build-pair-eligible-manifest.py \
  --c1-summary "$C1_SUMMARY" \
  --f9-judge "$F9_JUDGE" \
  --l1-rerun-summary "$C1_SUMMARY" \
  --output "$DRAFT_MANIFEST"
PAIR_ELIGIBLE=$(python3 - "$DRAFT_MANIFEST" "$REPO_ROOT/benchmark/auto-resolve/scripts" <<'PY'
import pathlib
import sys

sys.path.insert(0, sys.argv[2])
from pair_evidence_contract import loads_strict_json_object

manifest = loads_strict_json_object(pathlib.Path(sys.argv[1]).read_text())
fixtures = manifest.get("fixtures_pair_eligible")
if not isinstance(fixtures, list) or not all(isinstance(item, str) for item in fixtures):
    raise SystemExit("manifest fixtures_pair_eligible must be a string array")
print(" ".join(fixtures))
PY
)
echo "[run-iter-0033c] pair-eligible: $PAIR_ELIGIBLE"

# --- Per-fixture interleaved arm loop ---
IFS=',' read -ra FIXTURES <<< "$FIXTURES_CSV"
declare -a TIMINGS=()
for short in "${FIXTURES[@]}"; do
  # Resolve short ID to canonical fixture dir name.
  case "$short" in
    F1) fx="F1-cli-trivial-flag";;
    F2) fx="F2-cli-medium-subcommand";;
    F3) fx="F3-backend-contract-risk";;
    F4) fx="F4-web-browser-design";;
    F5) fx="F5-fix-loop-red-green";;
    F6) fx="F6-dep-audit-native-module";;
    F7) fx="F7-out-of-scope-trap";;
    F8) fx="F8-known-limit-ambiguous";;
    F9) fx="F9-e2e-ideate-to-resolve";;
    *) echo "[run-iter-0033c] unknown fixture short id: $short" >&2; exit 1;;
  esac
  echo ""
  echo "=== Fixture $fx ==="
  ARMS=("solo_claude" "l2_gated")
  if [[ " $PAIR_ELIGIBLE " =~ " $short " ]]; then
    ARMS+=("l2_forced")
  fi
  for arm in "${ARMS[@]}"; do
    echo "[run-iter-0033c] $fx :: $arm START $(date -u +%FT%TZ)"
    arm_t0=$(date +%s)
    if ! bash benchmark/auto-resolve/scripts/run-fixture.sh \
         --fixture "$fx" --arm "$arm" \
         --run-id "$RUN_ID" --resolve-skill new \
         > "$RESULTS_DIR/${fx}-${arm}.log" 2>&1; then
      echo "[run-iter-0033c] $fx :: $arm FAILED — see $RESULTS_DIR/${fx}-${arm}.log"
      # Continue to next arm; full failure surface goes through compare.py gates.
    fi
    arm_t1=$(date +%s)
    elapsed=$((arm_t1 - arm_t0))
    TIMINGS+=("$fx:$arm:${elapsed}s")
    echo "[run-iter-0033c] $fx :: $arm END elapsed=${elapsed}s"
  done

  # Per-fixture judge (graded across ARMS_PRESENT)
  if [ "$SKIP_JUDGE" -eq 0 ]; then
    echo "[run-iter-0033c] $fx :: judge START"
    if ! bash benchmark/auto-resolve/scripts/judge.sh \
         --fixture "$fx" --run-id "$RUN_ID" \
         > "$RESULTS_DIR/${fx}-judge.log" 2>&1; then
      echo "[run-iter-0033c] $fx :: judge FAILED — see $RESULTS_DIR/${fx}-judge.log"
    fi
    echo "[run-iter-0033c] $fx :: judge END"
  fi
done

# --- Build L1 rerun summary from solo_claude arm result.json + judge.json ---
L1_RERUN_SUMMARY="$RESULTS_DIR/l1-rerun-summary.json"
python3 benchmark/auto-resolve/scripts/iter-0033c-l1-summary.py \
  --results-dir "$RESULTS_DIR" \
  --out "$L1_RERUN_SUMMARY" \
  --run-id "$RUN_ID" \
  --git-sha "$HEAD_SHA"

# --- Build final manifest with real L1 rerun summary ---
FINAL_MANIFEST="$RESULTS_DIR/iter-0033c-pair-eligible.json"
python3 benchmark/auto-resolve/scripts/build-pair-eligible-manifest.py \
  --c1-summary "$C1_SUMMARY" \
  --f9-judge "$F9_JUDGE" \
  --l1-rerun-summary "$L1_RERUN_SUMMARY" \
  --output "$FINAL_MANIFEST"

# --- Run iter-0033c gate compare ---
GATES_JSON="$RESULTS_DIR/gates.json"
GATES_MD="$RESULTS_DIR/gates.md"
python3 benchmark/auto-resolve/scripts/iter-0033c-compare.py \
  --manifest "$FINAL_MANIFEST" \
  --results-dir "$RESULTS_DIR" \
  --work-dir-root /tmp \
  --run-id "$RUN_ID" \
  --out-json "$GATES_JSON" \
  --out-md "$GATES_MD" \
  || true  # gates may FAIL — exit non-zero handled by inspecting gates.json

echo ""
echo "=== iter-0033c done ==="
echo "RESULTS_DIR=$RESULTS_DIR"
echo "MANIFEST=$FINAL_MANIFEST"
echo "GATES=$GATES_MD"
printf '\n--- per-arm wall ---\n%s\n' "$(printf '%s\n' "${TIMINGS[@]}")"
