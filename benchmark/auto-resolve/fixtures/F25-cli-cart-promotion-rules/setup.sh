#!/usr/bin/env bash
# F25 setup — seed cart catalog and promotion rules.
set -e

mkdir -p data

cat > data/catalog.json <<'JSON'
{
  "products": {
    "TEE": { "unit_cents": 2500, "stock": 10, "tax_code": "standard" },
    "BAG": { "unit_cents": 3200, "stock": 4, "tax_code": "standard" },
    "MUG": { "unit_cents": 1200, "stock": 20, "tax_code": "exempt" }
  },
  "line_promotions": [
    { "sku": "TEE", "type": "buy_x_get_y_free", "buy_qty": 2, "free_qty": 1 },
    { "sku": "BAG", "type": "per_unit_discount_cents", "min_qty": 2, "per_unit_discount_cents": 500 }
  ],
  "coupons": {
    "ORDER10": { "percent": 10, "min_subtotal_cents": 8000 },
    "SMALL5": { "percent": 5, "min_subtotal_cents": 2000 }
  },
  "tax_rates": {
    "CA": 0.0825,
    "OR": 0,
    "NY": 0.08875
  },
  "taxable_codes": {
    "standard": true,
    "exempt": false
  },
  "shipping_cents": 699,
  "free_shipping_min_cents": 9000
}
JSON

exit 0
