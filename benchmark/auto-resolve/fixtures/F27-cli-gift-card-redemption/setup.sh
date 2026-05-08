#!/usr/bin/env bash
# F27 setup - seed gift card product and balance rules.
set -e

mkdir -p data

cat > data/gift-cards.json <<'JSON'
{
  "products": {
    "TEE": { "unit_cents": 2500 },
    "SOCKS": { "unit_cents": 700 },
    "BAG": { "unit_cents": 3200 }
  },
  "cards": {
    "GC-100": { "balance_cents": 5000, "active": true },
    "GC-200": { "balance_cents": 2500, "active": true },
    "GC-LOCKED": { "balance_cents": 9999, "active": false }
  }
}
JSON

exit 0
