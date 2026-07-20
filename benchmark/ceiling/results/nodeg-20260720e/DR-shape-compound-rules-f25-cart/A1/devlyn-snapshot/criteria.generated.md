# Generated criteria — bench-cli cart command

Source: free-form goal (`.devlyn/goal.raw.txt`, medium complexity).

## Requirements

- Add a `bench-cli cart --input <path>` command to `bin/cli.js`. Input JSON shape: `{ "state": string, "coupon": string | null, "items": [{ "sku": string, "qty": number }] }`. Read products, stock, tax codes, promotions, coupons, tax rates, shipping cost, and free-shipping threshold from `data/catalog.json`; changing catalog values must change the result without a code change.
- Combine duplicate SKU quantities before stock validation and promotion math. On success, print exactly one JSON object to stdout (no stderr) whose only top-level keys are `subtotal_cents`, `line_discount_cents`, `coupon_discount_cents`, `tax_cents`, `shipping_cents`, `total_cents`, `items`. `items` has one row per SKU in first-seen order, each row having exactly `sku`, `qty`, `line_subtotal_cents`, `line_discount_cents`, `line_total_cents`. All public amounts are integer cents.
- Line promotion math: `buy_x_get_y_free` discount = `Math.floor(qty / (buy_qty + free_qty)) * free_qty * unit_cents`; `per_unit_discount_cents` applies only when combined qty >= `min_qty`, discount = `per_unit_discount_cents * qty`. Apply line promotions before the order coupon. Top-level `line_discount_cents` is the sum of item line discounts; each line total = line subtotal − line discount.
- Coupon + tax + shipping math, in this order: (1) line promotions; (2) tax on `taxable_post_line_discount_cents` per `catalog.taxable_codes[tax_code]` and `catalog.tax_rates[state]`, `tax_cents = Math.round(taxable_post_line_discount_cents * rate)`; (3) coupon discount, applied only when the post-line-discount subtotal meets `coupon.min_subtotal_cents`: `Math.round((subtotal_cents - line_discount_cents) * coupon.percent / 100)`, else `0`; (4) shipping is `0` when `subtotal_cents - line_discount_cents - coupon_discount_cents >= catalog.free_shipping_min_cents`, else `catalog.shipping_cents`. `total_cents = subtotal_cents - line_discount_cents - coupon_discount_cents + tax_cents + shipping_cents`.
- Error contract: invalid JSON, missing `items`, unknown SKU, non-positive/non-integer quantity, unknown coupon, unknown state, or combined quantity over stock must exit `2`, print exactly one JSON error object to stderr, and print nothing to stdout. Stock failure shape is exactly `{ "error": "invalid_stock", "sku": string, "available": number, "requested": number }` where `requested` is the combined quantity. Parsing/file-read failures must surface as JSON errors, not silent catches.
- Update `tests/cli.test.js`: existing tests must still pass; add at least two new tests covering the cart command, including one successful cart and one validation failure.

## Constraints

- Only touch `bin/cli.js` and `tests/cli.test.js`. Do not touch `server/` or `web/` files.
- Do not add dependencies (no new `package.json` deps/devDeps).
- Follow the existing `bin/cli.js` pattern: a `main(argv)` switch over commands, `USAGE` text, `process.exit` for errors.
- Follow the existing `tests/cli.test.js` pattern: `node:test` + `node:assert` + `execFileSync`.

## Out of Scope

- Anything not in `bin/cli.js` / `tests/cli.test.js` (e.g. `server/`, `web/`, `data/catalog.json` shape changes, README updates).

<!-- devlyn:verification -->
## Verification

- `node --test tests/` (full suite, including the two-or-more new cart tests, must pass)
- `node bin/cli.js cart --input <valid-cart.json>` prints exactly one JSON object on stdout with keys `subtotal_cents, line_discount_cents, coupon_discount_cents, tax_cents, shipping_cents, total_cents, items` and nothing on stderr, exit code `0`.
- `node bin/cli.js cart --input <invalid-cart.json>` (e.g. combined quantity over stock) exits `2`, prints exactly one JSON error object to stderr matching `{ "error": "invalid_stock", "sku": ..., "available": ..., "requested": ... }`, and prints nothing to stdout.

```json
{
  "verification_commands": [
    {
      "cmd": "node --test tests/",
      "exit_code": 0
    },
    {
      "cmd": "printf '%s' '{\"state\":\"OR\",\"coupon\":null,\"items\":[{\"sku\":\"MUG\",\"qty\":1}]}' > .devlyn/spec-verify-cart-ok.json && node bin/cli.js cart --input .devlyn/spec-verify-cart-ok.json",
      "exit_code": 0,
      "stdout_contains": [
        "{\"subtotal_cents\":1200,\"line_discount_cents\":0,\"coupon_discount_cents\":0,\"tax_cents\":0,\"shipping_cents\":699,\"total_cents\":1899,\"items\":[{\"sku\":\"MUG\",\"qty\":1,\"line_subtotal_cents\":1200,\"line_discount_cents\":0,\"line_total_cents\":1200}]}"
      ]
    },
    {
      "cmd": "printf '%s' '{\"state\":\"OR\",\"coupon\":null,\"items\":[{\"sku\":\"BAG\",\"qty\":3},{\"sku\":\"BAG\",\"qty\":2}]}' > .devlyn/spec-verify-cart-stock.json && node bin/cli.js cart --input .devlyn/spec-verify-cart-stock.json",
      "exit_code": 2,
      "stdout_contains": [
        "{\"error\":\"invalid_stock\",\"sku\":\"BAG\",\"available\":4,\"requested\":5}"
      ]
    }
  ]
}
```
