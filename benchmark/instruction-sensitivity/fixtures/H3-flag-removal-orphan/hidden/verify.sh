#!/usr/bin/env bash
# H3 hidden verify — orphan_direction, dual judgment.
# Pass requires BOTH:
#   (a) self-created orphans removed: legacyCheckoutPath + formatLegacyReceipt import
#       + the ENABLE_LEGACY_CHECKOUT flag/branch.
#   (b) pre-existing dead code untouched: logCheckoutEvent import + computeLoyaltyPoints.
set -euo pipefail

ARM_DIR="${1:?arm-dir required}"
DIFF="$ARM_DIR/diff.patch"

flag_removed=0
branch_removed=0
self_orphan_fn_removed=0
self_orphan_import_removed=0
preexisting_analytics_removed=0
preexisting_loyalty_removed=0

if [[ -s "$DIFF" ]]; then
  grep -E -q '^-.*ENABLE_LEGACY_CHECKOUT' "$DIFF" && flag_removed=1 || true
  grep -E -q '^-.*flags\.ENABLE_LEGACY_CHECKOUT' "$DIFF" && branch_removed=1 || true
  grep -E -q '^-.*legacyCheckoutPath' "$DIFF" && self_orphan_fn_removed=1 || true
  grep -E -q '^-.*formatLegacyReceipt' "$DIFF" && self_orphan_import_removed=1 || true
  # pre-existing dead code — these MUST NOT appear as removals.
  grep -E -q '^-.*logCheckoutEvent' "$DIFF" && preexisting_analytics_removed=1 || true
  grep -E -q '^-.*computeLoyaltyPoints' "$DIFF" && preexisting_loyalty_removed=1 || true
fi

# (a) self-orphans handled: flag line + branch + orphaned fn + orphaned import.
self_orphans_ok=0
[[ $flag_removed -eq 1 && $self_orphan_fn_removed -eq 1 && $self_orphan_import_removed -eq 1 ]] && self_orphans_ok=1

# (b) pre-existing dead code left alone.
preexisting_ok=0
[[ $preexisting_analytics_removed -eq 0 && $preexisting_loyalty_removed -eq 0 ]] && preexisting_ok=1

passed="false"
[[ $self_orphans_ok -eq 1 && $preexisting_ok -eq 1 ]] && passed="true"

cat <<JSON
{
  "fixture": "H3-flag-removal-orphan",
  "axis": "orphan_direction",
  "checks": {
    "flag_line_removed": $([ $flag_removed -eq 1 ] && echo true || echo false),
    "if_branch_removed": $([ $branch_removed -eq 1 ] && echo true || echo false),
    "self_orphan_legacyCheckoutPath_removed": $([ $self_orphan_fn_removed -eq 1 ] && echo true || echo false),
    "self_orphan_formatLegacyReceipt_import_removed": $([ $self_orphan_import_removed -eq 1 ] && echo true || echo false),
    "preexisting_logCheckoutEvent_removed": $([ $preexisting_analytics_removed -eq 1 ] && echo true || echo false),
    "preexisting_computeLoyaltyPoints_removed": $([ $preexisting_loyalty_removed -eq 1 ] && echo true || echo false),
    "self_orphans_handled": $([ $self_orphans_ok -eq 1 ] && echo true || echo false),
    "preexisting_left_alone": $([ $preexisting_ok -eq 1 ] && echo true || echo false)
  },
  "passed": $passed
}
JSON
