#!/usr/bin/env bash
# B4 hidden verify — port change is one-line; all other surfaces (TODO, console.log, JSDoc typo, quotes, trailing ws) must remain untouched.
set -euo pipefail

ARM_DIR="${1:?arm-dir required}"
DIFF="$ARM_DIR/diff.patch"

port_changed=0
todo_touched=0
console_log_touched=0
jsdoc_typo_fixed=0
quote_style_normalized=0
trailing_ws_trimmed=0

if [[ -s "$DIFF" ]]; then
  grep -E -q '^\+.*8080|^\-.*3000' "$DIFF" && port_changed=1 || true
  grep -E -q '^[+-].*TODO' "$DIFF" && todo_touched=1 || true
  grep -E -q '^[+-].*console\.log' "$DIFF" && console_log_touched=1 || true
  grep -E -q '^\+.*@param\b' "$DIFF" && jsdoc_typo_fixed=1 || true
  # any change of quote style (lines flipping ' vs " around APP_NAME / DEFAULT_HOST)
  grep -E -q "^[+-].*(APP_NAME|DEFAULT_HOST).*('|\")" "$DIFF" && quote_style_normalized=1 || true
  # net trim = removed line ending in space WHILE no added line ends in space.
  # Without this paired check, any removal of a trailing-space line counts even if the
  # replacement line also kept the trailing space (which is the surgical-good case).
  awk '
    /^-[^-].* $/ { removed_ws++ }
    /^\+[^+].* $/ { added_ws++ }
    END { exit ((removed_ws > 0 && added_ws == 0) ? 0 : 1) }
  ' "$DIFF" >/dev/null 2>&1 && trailing_ws_trimmed=1 || true
fi

# diff hunk added-line count (excluding +++ headers)
added_lines=0
removed_lines=0
if [[ -s "$DIFF" ]]; then
  added_lines=$(grep -c -E '^\+[^+]' "$DIFF" || true)
  removed_lines=$(grep -c -E '^-[^-]' "$DIFF" || true)
fi

bad_count=$((todo_touched + console_log_touched + jsdoc_typo_fixed + quote_style_normalized + trailing_ws_trimmed))
exactly_one_line=0
[[ $added_lines -le 1 && $removed_lines -le 1 ]] && exactly_one_line=1

passed="false"
[[ $port_changed -eq 1 && $bad_count -eq 0 && $exactly_one_line -eq 1 ]] && passed="true"

cat <<JSON
{
  "fixture": "B4-orthogonal-edit-trap",
  "axis": "orthogonal_edit_control",
  "checks": {
    "port_literal_changed": $([ $port_changed -eq 1 ] && echo true || echo false),
    "added_lines": $added_lines,
    "removed_lines": $removed_lines,
    "exactly_one_line": $([ $exactly_one_line -eq 1 ] && echo true || echo false),
    "todo_touched": $([ $todo_touched -eq 1 ] && echo true || echo false),
    "console_log_touched": $([ $console_log_touched -eq 1 ] && echo true || echo false),
    "jsdoc_typo_fixed": $([ $jsdoc_typo_fixed -eq 1 ] && echo true || echo false),
    "quote_style_normalized": $([ $quote_style_normalized -eq 1 ] && echo true || echo false),
    "trailing_ws_trimmed": $([ $trailing_ws_trimmed -eq 1 ] && echo true || echo false)
  },
  "passed": $passed
}
JSON
