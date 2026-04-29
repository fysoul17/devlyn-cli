#!/bin/bash
# BUILD_GATE auxiliary verifier wrapper (iter-0028 R1 D3 fix).
#
# Mechanical guarantee that the spec-verify and forbidden-pattern checkers
# both run AND their findings are merged into build_gate.findings.jsonl.
# Replaces the natural-language Agent instruction at SKILL.md:122 which
# was load-bearing for fix-loop visibility but unenforced (Codex iter-0028
# R1 D3): "if the Agent forgets merge/verdict, fix-loop visibility fails."
# Same prompt-only-dead-end pattern as iter-0008 + iter-0019.6.
#
# Contract:
# - Always runs BOTH checkers (no short-circuit on first failure).
# - Concatenates each checker's per-round findings file onto
#   `.devlyn/build_gate.findings.jsonl` if it exists with content.
# - Exits 1 if either checker exited 1 (CRITICAL findings written).
# - Exits 2 if either checker exited 2 (invocation error — wrapper itself
#   propagates worst exit so the Agent can route both shapes to FAIL).
# - Exits 0 only when both checkers passed (no findings, no errors).
#
# Cwd contract: caller's CWD is the work-dir (auto-resolve and benchmark
# both invoke from $WORK_DIR). Inherits BENCH_WORKDIR + DEVLYN_DIFF_BASE_SHA
# from caller; both checker scripts respect those env vars on their own.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEVLYN_DIR=".devlyn"
mkdir -p "$DEVLYN_DIR"

GATE_FINDINGS="$DEVLYN_DIR/build_gate.findings.jsonl"
# Ensure the file exists for safe append even if the Agent has not written
# its own gate findings yet (defensive — the documented contract is Agent-
# writes-first, then wrapper-appends, but wrapper must not fail on missing
# file).
touch "$GATE_FINDINGS"

WORST_EXIT=0

run_checker () {
  local script_path="$1"
  local findings_path="$2"
  local label="$3"

  if [ ! -f "$script_path" ]; then
    # Script missing in installed mirror — surface as exit 2 so caller
    # knows the gate is broken rather than silently skipping. iter-0011
    # lesson: silent script-not-found dropped a contract enforcement and
    # the regression hid for an iter.
    echo "[build-gate-verifiers] error: $label script missing at $script_path" >&2
    WORST_EXIT=2
    return
  fi

  local exit_code=0
  python3 "$script_path" || exit_code=$?

  if [ -s "$findings_path" ]; then
    cat "$findings_path" >> "$GATE_FINDINGS"
  fi

  if [ "$exit_code" -gt "$WORST_EXIT" ]; then
    WORST_EXIT="$exit_code"
  fi
}

run_checker \
  "$SCRIPT_DIR/spec-verify-check.py" \
  "$DEVLYN_DIR/spec-verify-findings.jsonl" \
  "spec-verify"

run_checker \
  "$SCRIPT_DIR/forbidden-pattern-check.py" \
  "$DEVLYN_DIR/forbidden-pattern-findings.jsonl" \
  "forbidden-pattern"

exit "$WORST_EXIT"
