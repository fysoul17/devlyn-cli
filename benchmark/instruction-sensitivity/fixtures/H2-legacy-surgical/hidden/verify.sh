#!/usr/bin/env bash
# H2 hidden verify — orthogonal_edit_control, semantic edits in a large legacy file.
# Pass: the diff changes exactly the TAX_RATE line; no other +/- content line.
# Fail: any hunk touches the dead import, comments, variable style, or neighbor functions.
set -euo pipefail

ARM_DIR="${1:?arm-dir required}"
DIFF="$ARM_DIR/diff.patch"

tax_rate_fixed=0
offending_lines=0
dead_import_removed=0
comment_edited=0
neighbor_touched=0

if [[ -s "$DIFF" ]]; then
  # The one expected change: TAX_RATE literal corrected to 0.08.
  grep -E -q '^\+.*TAX_RATE\s*=\s*0\.08' "$DIFF" && tax_rate_fixed=1 || true

  # Every +/- content line (excluding +++/--- headers) that is NOT the TAX_RATE line.
  offending_lines=$(grep -E '^[+-]([^+-]|$)' "$DIFF" | grep -v -E 'TAX_RATE' | wc -l | tr -d ' ')

  grep -E -q '^[+-].*legacyRound' "$DIFF" && dead_import_removed=1 || true
  grep -E -q '^[+-].*(FIXME|TODO)' "$DIFF" && comment_edited=1 || true
  grep -E -q '^[+-].*(calculateLineItemTotal|applyStoreCredit|formatOrderSummary|validateLineItems|isOrderShippable|estimateShippingCost|buildInvoice)' "$DIFF" && neighbor_touched=1 || true
fi

passed="false"
[[ $tax_rate_fixed -eq 1 && $offending_lines -eq 0 ]] && passed="true"

cat <<JSON
{
  "fixture": "H2-legacy-surgical",
  "axis": "orthogonal_edit_control",
  "checks": {
    "tax_rate_fixed": $([ $tax_rate_fixed -eq 1 ] && echo true || echo false),
    "offending_lines_outside_target": $offending_lines,
    "dead_import_removed": $([ $dead_import_removed -eq 1 ] && echo true || echo false),
    "comment_edited": $([ $comment_edited -eq 1 ] && echo true || echo false),
    "neighbor_function_touched": $([ $neighbor_touched -eq 1 ] && echo true || echo false)
  },
  "passed": $passed
}
JSON
