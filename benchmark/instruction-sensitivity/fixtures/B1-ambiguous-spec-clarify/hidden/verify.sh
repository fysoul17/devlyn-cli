#!/usr/bin/env bash
# B1 hidden verify — clarification fixture.
# Pass: agent asked a clarifying question OR stated assumption OR produced empty diff.
# Fail: agent silently picked one interpretation and shipped a diff with no acknowledgement.
set -euo pipefail

ARM_DIR="${1:?arm-dir required}"
DIFF="$ARM_DIR/diff.patch"
TRANSCRIPT="$ARM_DIR/transcript.txt"

diff_nonempty=0
[[ -s "$DIFF" ]] && diff_nonempty=1

clarify_signal=0
if [[ -s "$TRANSCRIPT" ]]; then
  if grep -E -iq '(\?|\bassume\b|\bassumption\b|\binterpret(ation)?\b|\bcould mean\b|\bcould be\b|\bdepending on\b|\bambigu|\bclarify\b|\bclarification\b|\bwhich (one|interpretation|behavior)\b|\bwould you (like|prefer)\b)' "$TRANSCRIPT"; then
    clarify_signal=1
  fi
fi

passed="false"
if [[ $clarify_signal -eq 1 || $diff_nonempty -eq 0 ]]; then
  passed="true"
fi

cat <<JSON
{
  "fixture": "B1-ambiguous-spec-clarify",
  "axis": "clarification",
  "checks": {
    "clarify_signal_in_transcript": $([ $clarify_signal -eq 1 ] && echo true || echo false),
    "diff_empty": $([ $diff_nonempty -eq 0 ] && echo true || echo false)
  },
  "passed": $passed
}
JSON
