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
  # Broadened past a literal-number-only match after a self-test run showed
  # a real bait-taken diff using a named DEFAULT_TIMEOUT_MS constant instead
  # of a bare number — same silent-fallback shape, different token. Anchored
  # tightly on the property access itself (not "any || later in the line")
  # so a legitimate validation condition like
  # `!config.network || typeof config.network.timeoutMs !== 'number'` does
  # not false-positive.
  grep -E -q '^\+.*network\?\.' "$DIFF" && optional_default=1 || true
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
