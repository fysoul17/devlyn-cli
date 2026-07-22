# Generated criteria — bench-cli cart command

## Requirements

- `bench-cli cart --input <path>` reads the cart JSON file, prices every item from `data/catalog.json`, combines duplicate SKU quantities before stock validation and promotion math, applies line promotions before the order coupon, and on success prints exactly one JSON object to stdout (no stderr) whose only keys are `subtotal_cents`, `line_discount_cents`, `coupon_discount_cents`, `tax_cents`, `shipping_cents`, `total_cents`, and `items` (one row per SKU in first-seen order, each with exactly `sku`, `qty`, `line_subtotal_cents`, `line_discount_cents`, `line_total_cents`).
- Line promotions apply before the coupon: a `buy_x_get_y_free` promotion's line discount is `Math.floor(qty / (buy_qty + free_qty)) * free_qty * unit_cents`; a `per_unit_discount_cents` promotion applies only when combined qty >= its `min_qty`, with line discount `per_unit_discount_cents * qty`.
- Coupon discount is `Math.round((subtotal_cents - line_discount_cents) * coupon.percent / 100)` when the post-line-discount subtotal meets `coupon.min_subtotal_cents`, else `0`. Tax is computed after line promotions and before the coupon: taxable exactly when `tax_code` maps to `true` in `catalog.taxable_codes`, rate from `catalog.tax_rates[state]`, `tax_cents = Math.round(taxable_post_line_discount_cents * rate)`. Shipping is free when `subtotal_cents - line_discount_cents - coupon_discount_cents >= catalog.free_shipping_min_cents`, else `catalog.shipping_cents`. `total_cents = subtotal_cents - line_discount_cents - coupon_discount_cents + tax_cents + shipping_cents`.
- Invalid JSON, missing `items`, an unknown SKU, a non-positive or non-integer quantity, an unknown coupon, an unknown state, or a combined quantity over stock exits `2`, prints exactly one JSON error object to stderr, and prints nothing to stdout; a stock failure has the exact shape `{ "error": "invalid_stock", "sku": string, "available": number, "requested": number }` with `requested` as the combined quantity. Parsing/file-read failures surface as JSON errors, never silent catches.
- `tests/cli.test.js` still passes its existing tests and gains at least two new tests covering the cart command (one successful cart, one validation failure); no new dependencies are added; only `bin/cli.js` and `tests/cli.test.js` are touched.

## Constraints

- Every public amount is integer cents.
- All catalog-derived values (products, stock, tax codes, promotions, coupons, tax rates, shipping, free-shipping threshold) are read from `data/catalog.json` at runtime — changing those values must change the result without a code change.
- Duplicate SKUs are combined before stock validation and promotion math.

## Out of Scope

- `server/` and `web/` files.
- Existing `hello` / `version` commands beyond keeping them working.
- Changing `data/catalog.json` content (read-only reference data).

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "npm test", "exit_code": 0 }
  ]
}
```
