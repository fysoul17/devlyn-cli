#!/usr/bin/env bash
# engine-doctor.sh — read-only detection for /devlyn-engines' no-arg output.
#
# WHY (iter-0050): users need to see what's actually on the machine, not
# just what's pinned. This script never writes .devlyn/engines.json, never
# installs anything, never changes pin validation — it only reports.
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

check_executor() {
  # $1 = adapter file path. An adapter may declare the fixed ASCII field
  # `executor: no` under `## Role eligibility`; otherwise it can execute.
  [ -f "$1" ] || { printf 'n/a'; return; }
  if grep -q '^executor: no' "$1" 2>/dev/null; then printf 'no'; else printf 'yes'; fi
}

printf '%-8s %-17s %-8s %-8s %-9s %s\n' \
  'target' 'kind' 'binary' 'adapter' 'executor' 'note'

for i in "${!TARGETS[@]}"; do
  target="${TARGETS[$i]}"
  kind="${KINDS[$i]}"
  binary="$(check_binary "${BINARIES[$i]}")"
  adapter="$(check_adapter "$target")"
  executor="$(check_executor "$ADAPTERS_DIR/$target.md")"

  note='-'
  case "$kind" in
    cli-engine)
      if [ "$binary" = 'no' ]; then
        note="not installed; ${INSTALL_HINTS[$i]}"
      elif [ "$adapter" = 'no' ]; then
        note="binary present, no adapter — reinstall devlyn-cli, whose releases ship the adapters"
      elif [ "$executor" = 'no' ]; then
        note='adapter declares executor: no'
      fi
      ;;
    orchestrator-only)
      note='informational only; not a routable engine — no verified CLI binary or adapter'
      ;;
  esac

  printf '%-8s %-17s %-8s %-8s %-9s %s\n' \
    "$target" "$kind" "$binary" "$adapter" "$executor" "$note"
done
