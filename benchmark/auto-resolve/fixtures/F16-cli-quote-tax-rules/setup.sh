#!/usr/bin/env bash
# F16 setup — seed quote pricing rules.
set -e

mkdir -p data

cat > data/pricing.json <<'JSON'
{
  "products": {
    "A": { "unit_cents": 1999, "stock": 3, "tax_code": "standard" },
    "B": { "unit_cents": 250, "stock": 100, "tax_code": "exempt" },
    "C": { "unit_cents": 5000, "stock": 2, "tax_code": "standard" }
  },
  "coupons": {
    "SAVE10": { "percent": 10, "min_subtotal_cents": 2000 },
    "BULK15": { "percent": 15, "min_subtotal_cents": 10000 }
  },
  "tax_rates": {
    "CA": 0.0725,
    "NY": 0.08875,
    "OR": 0
  },
  "taxable_codes": {
    "standard": true,
    "exempt": false
  },
  "shipping_cents": 499,
  "free_shipping_min_cents": 5000
}
JSON

exit 0
