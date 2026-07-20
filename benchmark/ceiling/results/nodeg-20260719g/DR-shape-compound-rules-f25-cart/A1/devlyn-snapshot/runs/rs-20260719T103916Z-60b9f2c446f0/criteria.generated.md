# Generated criteria — bench-cli cart command

Source: `.devlyn/goal.raw.txt` (free-form goal, complexity: medium).

## Context anchors

- `bin/cli.js` is a single-file CLI: `main(argv)` destructures `[command, ...rest]` and
  switches on `command`, each case doing its own arg parsing then `console.log`/`process.exit`.
  The new `cart` case follows this same shape — no new dependencies, no new files.
- `tests/cli.test.js` uses `node:test` + `execFileSync('node', [CLI, ...args], {encoding:'utf8'})`
  and asserts on stdout via `assert.match`. Failure-path tests will need `execFileSync` wrapped to
  catch/inspect a non-zero exit (`error.status`, `error.stdout`, `error.stderr`) rather than assert.match alone.
- `data/catalog.json` already exists with `products`, `line_promotions`, `coupons`, `tax_rates`,
  `taxable_codes`, `shipping_cents`, `free_shipping_min_cents` — matches the goal's schema exactly;
  no catalog changes are required or in scope.

## Requirements

- Add a `cart --input <path>` subcommand to `bin/cli.js` that reads a cart JSON file
  (`{ state, coupon, items: [{ sku, qty }] }`), reads pricing/stock/promotion/coupon/tax/shipping
  data from `data/catalog.json`, and prints one exact JSON object to stdout on success with keys
  `subtotal_cents, line_discount_cents, coupon_discount_cents, tax_cents, shipping_cents, total_cents, items`
  (no stderr output). Every `items` row has exactly `sku, qty, line_subtotal_cents, line_discount_cents, line_total_cents`,
  one row per SKU in first-seen order.
- Combine duplicate SKU quantities before stock validation and before promotion math.
- Implement `buy_x_get_y_free` line discount as `Math.floor(qty / (buy_qty + free_qty)) * free_qty * unit_cents`,
  and `per_unit_discount_cents` (gated on `qty >= min_qty`) as `per_unit_discount_cents * qty`; apply
  line promotions before the coupon.
- Implement the order coupon: when present and `subtotal_cents - line_discount_cents >= coupon.min_subtotal_cents`,
  `coupon_discount_cents = Math.round((subtotal_cents - line_discount_cents) * coupon.percent / 100)`, else `0`.
- Implement tax (computed after line promotions, before the coupon) as `Math.round(taxable_post_line_discount_cents * rate)`
  where a product is taxable iff `catalog.taxable_codes[tax_code] === true` and `rate = catalog.tax_rates[state]`.
  Implement shipping as free (`0`) when `subtotal_cents - line_discount_cents - coupon_discount_cents >= catalog.free_shipping_min_cents`,
  else `catalog.shipping_cents`. Compute `total_cents = subtotal_cents - line_discount_cents - coupon_discount_cents + tax_cents + shipping_cents`.
- On invalid JSON, missing `items`, unknown SKU, non-positive/non-integer quantity, unknown coupon, unknown state,
  or combined quantity over stock: exit `2`, print exactly one JSON error object to stderr, print nothing to stdout.
  The combined-stock failure must have the exact shape `{ "error": "invalid_stock", "sku": string, "available": number, "requested": number }`
  where `requested` is the combined quantity. Parsing/file-read failures must surface as JSON errors, not silent catches.
- Update `tests/cli.test.js` with at least two new tests covering the cart command: one successful cart, one
  validation failure — without breaking the existing `hello`/`version` tests.

## Constraints

- Only touch `bin/cli.js` and `tests/cli.test.js`. Do not touch `server/`, `web/`, or `data/catalog.json`.
- Do not add dependencies (`package.json` `dependencies`/`devDependencies` stay unchanged).
- All public amounts are integer cents; changing `data/catalog.json` values must change the result without a code change.

## Out of Scope

- Any change to `server/` or `web/` files.
- Any change to `data/catalog.json` contents or schema.
- New CLI commands beyond `cart`.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "npm test",
      "exit_code": 0,
      "stdout_contains": ["# fail 0"],
      "stdout_not_contains": []
    },
    {
      "cmd": "printf '{\"state\":\"CA\",\"coupon\":null,\"items\":[{\"sku\":\"MUG\",\"qty\":1}]}' > /tmp/devlyn-cart-verify-success.json && node bin/cli.js cart --input /tmp/devlyn-cart-verify-success.json",
      "exit_code": 0,
      "stdout_contains": ["subtotal_cents", "1200", "total_cents", "1899", "shipping_cents", "699"],
      "stdout_not_contains": []
    },
    {
      "cmd": "printf '{\"state\":\"CA\",\"coupon\":null,\"items\":[{\"sku\":\"BAG\",\"qty\":5}]}' > /tmp/devlyn-cart-verify-stock.json && node bin/cli.js cart --input /tmp/devlyn-cart-verify-stock.json",
      "exit_code": 2,
      "stdout_contains": ["invalid_stock", "BAG", "available", "requested"],
      "stdout_not_contains": []
    }
  ]
}
```
