#!/bin/sh
# P3: successful stdout must be exactly one JSON object with the specified
# top-level and merchant-row keys (no unexpected/missing keys), no stderr
# output, and each top-level total equal to the sum of its merchant field.
set -eu
DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/../.." && pwd)"
CLI="$ROOT/bin/cli.js"

set +e
OUT="$(node "$CLI" payout --input "$DIR/P3-single-charge.json" 2>/tmp/p3.err)"
RC=$?
set -e
ERR="$(cat /tmp/p3.err)"
if [ "$RC" -ne 0 ]; then
  echo "FAIL: expected exit 0, got $RC (stderr: $ERR)" >&2
  exit 1
fi
if [ -n "$ERR" ]; then
  echo "FAIL: expected no stderr output, got: $ERR" >&2
  exit 1
fi

printf '%s' "$OUT" > /tmp/p3.out
node "$DIR/P3-check.js" /tmp/p3.out

# --- Error-path shape: the stderr error object must have exactly the
# named keys (error, id) and no others, reusing P1's conflicting-duplicate
# fixture rather than duplicating it. ---
set +e
OUT2="$(node "$CLI" payout --input "$DIR/P1-conflict-dup.json" 2>/tmp/p3b.err)"
RC2=$?
set -e
ERR2="$(cat /tmp/p3b.err)"
if [ "$RC2" -ne 2 ]; then
  echo "FAIL: error-path expected exit 2, got $RC2" >&2
  exit 1
fi
if [ -n "$OUT2" ]; then
  echo "FAIL: error-path expected empty stdout, got: $OUT2" >&2
  exit 1
fi
EXPECTED_ERR='{"error":"conflicting_duplicate","id":"e1"}'
ACTUAL_NORM="$(printf '%s' "$ERR2" | node -e "let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{process.stdout.write(JSON.stringify(JSON.parse(d.trim())))})" 2>/dev/null || echo "UNPARSEABLE")"
if [ "$ACTUAL_NORM" != "$EXPECTED_ERR" ]; then
  echo "FAIL: error-path expected stderr $EXPECTED_ERR (only 'error' and 'id' keys), got: $ERR2 (normalized: $ACTUAL_NORM)" >&2
  exit 1
fi

echo "PASS: shape contract holds for both success and error output"
