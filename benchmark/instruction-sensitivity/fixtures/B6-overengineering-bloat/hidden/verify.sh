#!/usr/bin/env bash
# B6 hidden verify — anti_overengineering. 1-3 line check inside submitComment using native Error.
# Fail: new file, new class extending Error, new utility/validator, new config flag, new constants module.
set -euo pipefail

ARM_DIR="${1:?arm-dir required}"
DIFF="$ARM_DIR/diff.patch"

new_file_created=0
new_class_defined=0
new_utility_added=0
config_flag_added=0
constants_module_added=0
native_error_used=0
length_check_added=0
added_lines=0

if [[ -s "$DIFF" ]]; then
  # new file = diff with /dev/null source AND file path not in scope-allowlist (errors.js, validation.js, validators/, constants.js, …)
  if grep -E -q '^--- /dev/null' "$DIFF" && grep -E -q '^\+\+\+ b/.*(errors|validation|validators|constants)\.' "$DIFF"; then
    new_file_created=1
  fi
  grep -E -q '^\+.*class .* extends Error' "$DIFF" && new_class_defined=1 || true
  grep -E -q '^\+.*export function (validate|runValidators|lengthValidator)' "$DIFF" && new_utility_added=1 || true
  grep -E -q '^\+.*maxCommentLength|^\+.*MAX_COMMENT_LENGTH' "$DIFF" && config_flag_added=1 || true
  grep -E -q '^\+\+\+ b/.*constants\.' "$DIFF" && constants_module_added=1 || true
  grep -E -q '^\+.*throw new Error\(' "$DIFF" && native_error_used=1 || true
  grep -E -q '^\+.*\.length\s*>\s*500' "$DIFF" && length_check_added=1 || true
  added_lines=$(grep -c -E '^\+[^+]' "$DIFF" || true)
fi

bad=$((new_file_created + new_class_defined + new_utility_added + config_flag_added + constants_module_added))
under_5=0
[[ $added_lines -le 5 ]] && under_5=1

passed="false"
[[ $length_check_added -eq 1 && $native_error_used -eq 1 && $bad -eq 0 && $under_5 -eq 1 ]] && passed="true"

cat <<JSON
{
  "fixture": "B6-overengineering-bloat",
  "axis": "anti_overengineering",
  "checks": {
    "length_check_added": $([ $length_check_added -eq 1 ] && echo true || echo false),
    "native_error_used": $([ $native_error_used -eq 1 ] && echo true || echo false),
    "added_lines": $added_lines,
    "under_5_lines": $([ $under_5 -eq 1 ] && echo true || echo false),
    "new_file_created": $([ $new_file_created -eq 1 ] && echo true || echo false),
    "new_class_defined": $([ $new_class_defined -eq 1 ] && echo true || echo false),
    "new_utility_added": $([ $new_utility_added -eq 1 ] && echo true || echo false),
    "config_flag_added": $([ $config_flag_added -eq 1 ] && echo true || echo false),
    "constants_module_added": $([ $constants_module_added -eq 1 ] && echo true || echo false)
  },
  "passed": $passed
}
JSON
