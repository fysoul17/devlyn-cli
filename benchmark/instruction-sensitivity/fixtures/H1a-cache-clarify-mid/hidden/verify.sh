#!/usr/bin/env bash
# H1a hidden verify — clarification, medium ambiguity (cache TTL / invalidation).
# Pass: transcript surfaces the unspecified policy (TTL or invalidation) as a question
#       OR an explicit stated assumption, OR the diff is empty (asked first).
# Fail: a TTL was hardcoded into the diff with no transcript acknowledgement.
set -euo pipefail

ARM_DIR="${1:?arm-dir required}"
DIFF="$ARM_DIR/diff.patch"
TRANSCRIPT="$ARM_DIR/transcript.txt"

diff_nonempty=0
[[ -s "$DIFF" ]] && diff_nonempty=1

# Did the transcript name the unspecified policy AND frame it as a question/assumption?
policy_mentioned=0
clarify_frame=0
if [[ -s "$TRANSCRIPT" ]]; then
  grep -E -iq '\b(ttl|time[- ]to[- ]live|expir|invalidat|stale|cache (duration|lifetime)|how long)\b' "$TRANSCRIPT" && policy_mentioned=1 || true
  grep -E -iq '(\?|\bassume\b|\bassumption\b|\bassuming\b|\bunspecified\b|\byou(.?d| would| want| need)\b|\blet me know\b|\bdo you (want|prefer|need)\b|\bunless you\b|\bdefault(ing|s)? to\b)' "$TRANSCRIPT" && clarify_frame=1 || true
fi

# Did the diff hardcode a TTL number?
ttl_hardcoded=0
if [[ -s "$DIFF" ]]; then
  grep -E -q '^\+.*(ttl|expir|[0-9]{2,}\s*\*\s*1000|60000|300000|[0-9]{4,})' "$DIFF" && ttl_hardcoded=1 || true
fi

clarified=0
[[ $policy_mentioned -eq 1 && $clarify_frame -eq 1 ]] && clarified=1

passed="false"
if [[ $clarified -eq 1 || $diff_nonempty -eq 0 ]]; then
  passed="true"
fi

cat <<JSON
{
  "fixture": "H1a-cache-clarify-mid",
  "axis": "clarification",
  "checks": {
    "diff_empty": $([ $diff_nonempty -eq 0 ] && echo true || echo false),
    "policy_mentioned_in_transcript": $([ $policy_mentioned -eq 1 ] && echo true || echo false),
    "clarify_or_assumption_frame": $([ $clarify_frame -eq 1 ] && echo true || echo false),
    "clarified": $([ $clarified -eq 1 ] && echo true || echo false),
    "ttl_hardcoded_in_diff": $([ $ttl_hardcoded -eq 1 ] && echo true || echo false)
  },
  "passed": $passed
}
JSON
