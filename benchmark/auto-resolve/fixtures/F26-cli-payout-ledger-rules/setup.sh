#!/usr/bin/env bash
# F26 setup — seed payout ledger rules.
set -e

mkdir -p data

cat > data/payout-rules.json <<'JSON'
{
  "processing_fee_percent": 2.9,
  "fixed_fee_cents": 30,
  "dispute_fee_cents": 1500,
  "reserve_percent": 10,
  "minimum_payout_cents": 1000
}
JSON

exit 0
