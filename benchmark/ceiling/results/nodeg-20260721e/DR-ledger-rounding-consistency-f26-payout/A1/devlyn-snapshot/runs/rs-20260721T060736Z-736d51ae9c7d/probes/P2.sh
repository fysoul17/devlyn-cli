#!/bin/sh
# P2: all-or-nothing on validation failure — a batch that mixes one
# individually-valid event with one invalid event must abort the whole run
# (exit 2, empty stdout, exactly one JSON error object on stderr), even
# though the other event in the same file would validate on its own.
set -eu
DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/../.." && pwd)"
CLI="$ROOT/bin/cli.js"

check_case() {
  name="$1"
  fixture="$2"
  set +e
  OUT="$(node "$CLI" payout --input "$fixture" 2>/tmp/p2.err)"
  RC=$?
  set -e
  ERR="$(cat /tmp/p2.err)"
  if [ "$RC" -ne 2 ]; then
    echo "FAIL ($name): expected exit 2, got $RC" >&2
    exit 1
  fi
  if [ -n "$OUT" ]; then
    echo "FAIL ($name): expected empty stdout, got: $OUT" >&2
    exit 1
  fi
  ERR_LINES="$(printf '%s\n' "$ERR" | grep -c . || true)"
  if [ "$ERR_LINES" != "1" ]; then
    echo "FAIL ($name): expected exactly one line of stderr output, got $ERR_LINES lines: $ERR" >&2
    exit 1
  fi
  HAS_ERROR_KEY="$(printf '%s' "$ERR" | node -e "let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{try{const j=JSON.parse(d.trim());process.stdout.write(typeof j.error==='string'?'yes':'no')}catch(e){process.stdout.write('unparseable')}})")"
  if [ "$HAS_ERROR_KEY" != "yes" ]; then
    echo "FAIL ($name): expected a single JSON error object with an 'error' key on stderr, got: $ERR" >&2
    exit 1
  fi
}

check_case "unknown_event_type" "$DIR/P2-unknown-type.json"
check_case "missing_merchant_id" "$DIR/P2-missing-merchant-id.json"

# --- Control case: a fully valid batch with distinct ids/merchants must
# still succeed, produce one row per distinct merchant_id in first-seen
# event order, and not be affected by the atomicity check above. ---
set +e
OUT3="$(node "$CLI" payout --input "$DIR/P2-success-batch.json" 2>/tmp/p2c.err)"
RC3=$?
set -e
ERR3="$(cat /tmp/p2c.err)"
if [ "$RC3" -ne 0 ]; then
  echo "FAIL (success_batch): expected exit 0, got $RC3 (stderr: $ERR3)" >&2
  exit 1
fi
ROW_IDS="$(printf '%s' "$OUT3" | node -e "let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{const j=JSON.parse(d);process.stdout.write(j.merchants.map(m=>m.merchant_id).join(','))})")"
if [ "$ROW_IDS" != "m2,m1" ]; then
  echo "FAIL (success_batch): expected 2 distinct merchant rows in first-seen order 'm2,m1', got '$ROW_IDS'" >&2
  exit 1
fi

echo "PASS: all-or-nothing validation failure on mixed valid/invalid batch, success batch unaffected"
