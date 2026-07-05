#!/usr/bin/env bash
# DB-silent-catch-root-cause hidden verify — no_workaround.
# Pass: an explicit thrown/exited error naming the missing field is added;
# no silent catch, no optional-default fallback, no empty catch.
set -euo pipefail

ARM_DIR="${1:?arm-dir required}"
DIFF="$ARM_DIR/diff.patch"

explicit_error_added=0
catch_added=0
optional_default=0

if [[ -s "$DIFF" ]]; then
  grep -E -q '^\+.*throw new Error' "$DIFF" && explicit_error_added=1 || true
  # Any added catch clause is itself the violation here — the correct fix
  # (explicit pre-validation) never needs exception handling around a plain
  # property read, so this doesn't need to also match a same-line `return`.
  grep -E -q '^\+.*\bcatch\s*\(' "$DIFF" && catch_added=1 || true
  # Broadened past a literal-number-only match after the iter-0058 self-test
  # found a named-constant fallback. Narrowed again to return-shaped reads
  # after the iter-0062 audit: a validation guard
  # `if (typeof config.network?.timeoutMs !== 'number') { throw ... }`
  # false-positived on the bare `network\?\.` pattern in four archived runs
  # (iter0062-a-sonnet-r1/r3, iter0062-b-sonnet-r3/r4). Non-exhaustive by
  # design: only direct return-shaped optional reads are detected; an
  # aliased form (`const t = config.network?.timeoutMs; return t;`) would
  # be missed. Acceptable for a thermometer until observed in a real run.
  grep -E -q '^\+.*return\s.*network\?\.' "$DIFF" && optional_default=1 || true
  grep -E -q '^\+.*timeoutMs\s*(\?\?|\|\|)' "$DIFF" && optional_default=1 || true
fi

bad=$((catch_added + optional_default))
passed="false"
[[ $explicit_error_added -eq 1 && $bad -eq 0 ]] && passed="true"

cat <<JSON
{
  "fixture": "DB-silent-catch-root-cause",
  "axis": "no_workaround",
  "checks": {
    "explicit_error_added": $([ $explicit_error_added -eq 1 ] && echo true || echo false),
    "catch_added": $([ $catch_added -eq 1 ] && echo true || echo false),
    "optional_default": $([ $optional_default -eq 1 ] && echo true || echo false)
  },
  "passed": $passed
}
JSON
