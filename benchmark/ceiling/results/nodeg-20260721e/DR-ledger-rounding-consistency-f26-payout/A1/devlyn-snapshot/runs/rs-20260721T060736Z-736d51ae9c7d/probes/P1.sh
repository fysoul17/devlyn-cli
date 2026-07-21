#!/bin/sh
# P1: idempotent replay of a byte-identical duplicate id vs. a conflicting
# duplicate id (same id, different content) — the same-id case must branch
# on content equality, not merely on id.
set -eu
DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/../.." && pwd)"
CLI="$ROOT/bin/cli.js"

# --- Case A: byte-identical duplicate id must be applied only once ---
set +e
OUT="$(node "$CLI" payout --input "$DIR/P1-dedup-same.json" 2>/tmp/p1a.err)"
RC=$?
set -e
ERR="$(cat /tmp/p1a.err)"
if [ "$RC" -ne 0 ]; then
  echo "FAIL: dedup case expected exit 0, got $RC" >&2
  exit 1
fi
if [ -n "$ERR" ]; then
  echo "FAIL: dedup case expected empty stderr, got: $ERR" >&2
  exit 1
fi
MERCHANT_COUNT="$(printf '%s' "$OUT" | node -e "let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{const j=JSON.parse(d);process.stdout.write(String(j.merchants.length))})")"
GROSS="$(printf '%s' "$OUT" | node -e "let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{const j=JSON.parse(d);process.stdout.write(String(j.merchants[0].gross_charge_cents))})")"
if [ "$MERCHANT_COUNT" != "1" ]; then
  echo "FAIL: dedup case expected exactly 1 merchant row, got $MERCHANT_COUNT" >&2
  exit 1
fi
if [ "$GROSS" != "1000" ]; then
  echo "FAIL: dedup case expected the duplicate applied once (gross_charge_cents=1000), got $GROSS" >&2
  exit 1
fi

# --- Case B: same id, different content is a conflicting duplicate ---
set +e
OUT2="$(node "$CLI" payout --input "$DIR/P1-conflict-dup.json" 2>/tmp/p1b.err)"
RC2=$?
set -e
ERR2="$(cat /tmp/p1b.err)"
if [ "$RC2" -ne 2 ]; then
  echo "FAIL: conflicting duplicate expected exit 2, got $RC2" >&2
  exit 1
fi
if [ -n "$OUT2" ]; then
  echo "FAIL: conflicting duplicate expected empty stdout, got: $OUT2" >&2
  exit 1
fi
EXPECTED_ERR='{"error":"conflicting_duplicate","id":"e1"}'
ACTUAL_NORM="$(printf '%s' "$ERR2" | node -e "let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{process.stdout.write(JSON.stringify(JSON.parse(d.trim())))})" 2>/dev/null || echo "UNPARSEABLE")"
if [ "$ACTUAL_NORM" != "$EXPECTED_ERR" ]; then
  echo "FAIL: conflicting duplicate expected stderr $EXPECTED_ERR, got: $ERR2 (normalized: $ACTUAL_NORM)" >&2
  exit 1
fi

echo "PASS: idempotent replay + conflicting duplicate contract"
