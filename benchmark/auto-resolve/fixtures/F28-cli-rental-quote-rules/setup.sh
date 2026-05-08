#!/usr/bin/env bash
# F28 setup - seed rental quote rules.
set -e

mkdir -p data

cat > data/rental-rules.json <<'JSON'
{
  "items": {
    "CAM": { "daily_cents": 1200, "stock": 2, "deposit_cents": 5000 },
    "LIGHT": { "daily_cents": 700, "stock": 3, "deposit_cents": 2000 },
    "TRIPOD": { "daily_cents": 400, "stock": 5, "deposit_cents": 1000 }
  },
  "weekend_surcharge_percent": 25,
  "protection_daily_cents": 300,
  "coupons": {
    "LONG3": { "percent": 10, "min_rental_days": 3 },
    "NONE": { "percent": 0, "min_rental_days": 1 }
  }
}
JSON

exit 0
