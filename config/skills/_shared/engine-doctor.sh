#!/usr/bin/env bash
# engine-doctor.sh — read-only detection for /devlyn:engines' no-arg output.
#
# WHY (iter-0050): users need to see what's actually on the machine, not
# just what's pinned. This script never writes .devlyn/engines.json, never
# installs anything, never changes pin validation — it only reports.
#
# CATALOG NOTE: `pi` (bin/devlyn.js's Pi/earendil-works install target) has
# no verified CLI binary name anywhere in this repo — its own installer
# detect() only checks project marker files, never shells out to a binary.
# Fabricating a `command -v pi` check would be a guess this repo's evidence
# rule forbids, so its binary column reports "unknown" rather than "no".
#
# macOS-safe bash 3.2: no associative arrays, no mapfile/readarray.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
ADAPTERS_DIR="$SCRIPT_DIR/adapters"

TARGETS=(claude codex omp pi)
KINDS=(cli-engine cli-engine cli-engine orchestrator-only)
BINARIES=(claude codex omp "")
INSTALL_HINTS=(
  "see https://docs.anthropic.com/en/docs/claude-code"
  "npm install -g @openai/codex"
  "brew install can1357/tap/omp"
  ""
)

check_binary() {
  # $1 = binary name, "" means no known binary to probe
  [ -n "$1" ] || { printf 'unknown'; return; }
  if command -v "$1" >/dev/null 2>&1; then printf 'yes'; else printf 'no'; fi
}

check_adapter() {
  # $1 = target name
  if [ -f "$ADAPTERS_DIR/$1.md" ]; then printf 'yes'; else printf 'no'; fi
}

check_role() {
  # $1 = adapter file path. Reads the optional `## Role eligibility` fixed
  # ASCII fields (_shared/adapters/README.md); absent file or section = both
  # roles eligible by default (every adapter shipped before iter-0051).
  [ -f "$1" ] || { printf 'n/a'; return; }
  local exec_ok='yes' judge_ok='yes'
  grep -q '^executor: no' "$1" 2>/dev/null && exec_ok='no'
  grep -q '^pair_judge: no' "$1" 2>/dev/null && judge_ok='no'
  if [ "$exec_ok" = 'yes' ] && [ "$judge_ok" = 'yes' ]; then printf 'executor+judge'
  elif [ "$judge_ok" = 'yes' ]; then printf 'judge-only'
  elif [ "$exec_ok" = 'yes' ]; then printf 'executor-only'
  else printf 'none'
  fi
}

printf '%-8s %-17s %-8s %-8s %-14s %-12s %s\n' \
  'target' 'kind' 'binary' 'adapter' 'role' 'pin_eligible' 'note'

pin_eligible_count=0
missing_hints=()

for i in "${!TARGETS[@]}"; do
  target="${TARGETS[$i]}"
  kind="${KINDS[$i]}"
  binary="$(check_binary "${BINARIES[$i]}")"
  adapter="$(check_adapter "$target")"
  role="$(check_role "$ADAPTERS_DIR/$target.md")"

  pin_eligible='no'
  case "$kind" in
    cli-engine) [ "$binary" = 'yes' ] && [ "$adapter" = 'yes' ] && pin_eligible='yes' ;;
  esac

  note='-'
  case "$kind" in
    cli-engine)
      if [ "$pin_eligible" = 'yes' ]; then
        pin_eligible_count=$((pin_eligible_count + 1))
      elif [ "$binary" = 'no' ]; then
        note="not installed; ${INSTALL_HINTS[$i]}"
        missing_hints+=("$target: ${INSTALL_HINTS[$i]}")
      else
        note="binary present, no adapter — ship _shared/adapters/$target.md"
      fi
      ;;
    orchestrator-only)
      note='informational only; not a routable role engine — no verified CLI binary or adapter'
      ;;
  esac

  printf '%-8s %-17s %-8s %-8s %-14s %-12s %s\n' \
    "$target" "$kind" "$binary" "$adapter" "$role" "$pin_eligible" "$note"
done

printf '\n'
if [ "$pin_eligible_count" -lt 2 ]; then
  printf 'Recommendation: only %d adapter-valid engine(s) available. VERIFY pair-judge and\n' "$pin_eligible_count"
  printf 'risk-probe escalation need a second, genuinely different model to check against —\n'
  printf 'iter-0045 found different model tiers hit different failure-mode blind spots (not\n'
  printf 'that any arbitrary second model helps); with fewer than 2, those routes can never\n'
  printf 'fire and every run stays solo. Add one of:\n'
  for hint in "${missing_hints[@]}"; do
    printf '  - %s\n' "$hint"
  done
else
  printf 'Pair-judge diversity: %d adapter-valid engines available.\n' "$pin_eligible_count"
fi
