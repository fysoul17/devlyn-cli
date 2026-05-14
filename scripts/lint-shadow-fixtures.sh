#!/usr/bin/env bash
# lint-shadow-fixtures.sh — run the standard fixture lint over shadow-fixtures/.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SHADOW_FIXTURES_DIR="${DEVLYN_SHADOW_FIXTURES_DIR:-$REPO_ROOT/benchmark/auto-resolve/shadow-fixtures}"

DEVLYN_FIXTURES_DIR="$SHADOW_FIXTURES_DIR" \
DEVLYN_FIXTURE_GLOB="S*" \
DEVLYN_RETIRED_FIXTURE_GLOB="S*" \
  bash "$REPO_ROOT/scripts/lint-fixtures.sh"

has_actionable_solo_headroom_hypothesis() {
  python3 "$REPO_ROOT/benchmark/auto-resolve/scripts/solo-headroom-hypothesis.py" "$@"
}

has_solo_ceiling_avoidance_note() {
  local notes="$1"
  python3 "$REPO_ROOT/benchmark/auto-resolve/scripts/solo-ceiling-avoidance.py" "$notes"
}

errors=0
for d in "$SHADOW_FIXTURES_DIR"/S*/; do
  [ -d "$d" ] || continue
  fid="$(basename "$d")"
  meta="$d/metadata.json"
  spec="$d/spec.md"
  notes="$d/NOTES.md"
  has_failed_headroom=0
  if [ -f "$notes" ] && grep -Fq 'headroom' "$notes" && grep -Eq '`?FAIL`?' "$notes"; then
    has_failed_headroom=1
  fi
  category="$(
    python3 - "$meta" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as handle:
        print(json.load(handle).get("category", ""))
except FileNotFoundError:
    print("")
PY
  )"
  if [ "$category" = "high-risk" ] && [ "$has_failed_headroom" -eq 0 ]; then
    if ! has_actionable_solo_headroom_hypothesis --expected-json "$d/expected.json" "$spec"; then
      echo "✗ $fid: unmeasured high-risk shadow fixture spec.md must document a solo-headroom hypothesis with solo_claude miss and observable command from expected.json before provider spend"
      errors=$((errors + 1))
    fi
    if ! has_solo_ceiling_avoidance_note "$notes"; then
      echo "✗ $fid: unmeasured high-risk shadow fixture NOTES.md must include ## Solo ceiling avoidance naming how it differs from solo-saturated controls before provider spend"
      errors=$((errors + 1))
    fi
  fi
done

[ "$errors" -eq 0 ] || exit 1
