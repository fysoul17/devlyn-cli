# Plan — `cart` subcommand for harbor-tools CLI

<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` — edit — add a `cart` case to the existing `switch (command)` in `main(argv)` (same shape as the `hello`/`version` cases: parse `rest` for `--input <path>`, do the work, `console.log`/`process.exit`). Implements all Requirements: reading `--input`, reading `data/catalog.json`, combine/validate/price/tax/coupon/shipping math, the single success JSON object to stdout, and the single error JSON object to stderr with exit `2`.
- `tests/cli.test.js` — edit — add at least two new `test()` blocks (one successful `cart` run asserting on the parsed stdout JSON, one validation-failure run using a wrapped `execFileSync` that catches the non-zero exit and asserts on `error.status`/`error.stdout`/`error.stderr`), appended after the existing three tests without modifying them. Implements Requirement: "Update `tests/cli.test.js` with at least two new tests covering the cart command... without breaking the existing `hello`/`version` tests."

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

- **Ambiguous validation order.** The criteria lists failure conditions ("invalid JSON, missing `items`, unknown SKU, non-positive/non-integer quantity, unknown coupon, unknown state, or combined quantity over stock") without stating a strict check order, beyond the explicit constraint that combining happens *before* stock validation and promotion math. Interpretation to implement, strictly and consistently: (1) JSON parse the file — `invalid_json`; (2) `items` must be a non-empty array — `missing_items`; (3) per raw item, validate `sku` exists in `catalog.products` (`invalid_sku`) and `qty` is a positive integer via `typeof qty === 'number' && Number.isInteger(qty) && qty > 0` (`invalid_quantity`), while accumulating combined quantities per SKU in first-seen order; (4) if `coupon` is non-null, it must exist in `catalog.coupons` (`invalid_coupon`); (5) `state` must exist in `catalog.tax_rates` (`invalid_state`); (6) only after all of the above pass, check each combined SKU quantity against `catalog.products[sku].stock` (`invalid_stock`, first offending SKU in first-seen order). No output (stdout or stderr) is written until every validation passes or the first failure is found — the success object must never be partially printed.
- **Exact error JSON shape is pinned down only for `invalid_stock`**: `{ "error": "invalid_stock", "sku": string, "available": number, "requested": number }` where `requested` is the *combined* quantity for that SKU. For every other failure (`invalid_json`, `missing_items`, `invalid_sku`, `invalid_quantity`, `invalid_coupon`, `invalid_state`), the criteria only requires "exactly one JSON error object" — plan is to use the same `{ "error": "<code>" }` family (adding minimal identifying context like `sku` where natural) for consistency, since the criteria does not fully specify these shapes. Do not invent stdout output or additional stderr lines for these paths.
- **Tax base is computed once, then rounded once.** "`Math.round(taxable_post_line_discount_cents * rate)`" means: sum `(line_subtotal_cents - line_discount_cents)` across only the lines whose product's `tax_code` maps to `taxable_codes[tax_code] === true`, THEN apply a single `Math.round(... * rate)` on that aggregate. Do not round per-line and sum the rounded values — that produces different (wrong) totals due to floating-point/rounding drift across multiple `Math.round` calls versus one.
- **Coupon and tax are order-level, not allocated back into `items` rows.** Each `items` row only needs `sku, qty, line_subtotal_cents, line_discount_cents, line_total_cents` — `line_total_cents = line_subtotal_cents - line_discount_cents` (promotions only; the coupon and tax are never subtracted into a line's total). Do not invent a per-line coupon/tax share.
- **Line promotion lookup is 1:1 by SKU.** `catalog.line_promotions` has at most one entry per SKU (`buy_x_get_y_free` or `per_unit_discount_cents`); a SKU with no matching entry has `line_discount_cents = 0`. Implement `buy_x_get_y_free` literally as `Math.floor(qty / (buy_qty + free_qty)) * free_qty * unit_cents`, and `per_unit_discount_cents` literally as `qty >= min_qty ? per_unit_discount_cents * qty : 0` — do not use `Math.round`/`Math.ceil` in place of the specified `Math.floor`.
- **Floating-point tax rates** (`0.0825`, `0.08875`) multiplied by integer cents can produce a non-integer float before `Math.round` (e.g. `98.99999999999999`); `Math.round` handles this correctly as specified — no extra epsilon/toFixed workaround is needed or in scope.
- **Scope discipline**: `data/catalog.json`, `server/`, `web/` are out of scope per Constraints — no reads of `data/catalog.json` will be cached/copied into `bin/cli.js`; the command reads the file fresh each invocation via `fs.readFileSync` + `JSON.parse`, same pattern as `readPackageVersion()`. No new dependencies — only `fs`/`path`, already imported.
- **Existing tests are contract.** New tests append after the three existing tests; `hello`/`version` cases and tests are untouched.
- **Verification block's field naming is not a contradiction to resolve here.** The third verification command (stock failure) labels its assertions `stdout_contains` even though the Requirements section is explicit that errors print "to stderr... print nothing to stdout." Treat `stdout_contains` in that verification entry as the harness's generic "process output contains" label (it will run the command through a shell that can see both streams), not as a license to write the error JSON to stdout. IMPLEMENT must keep the error object on stderr exactly as Requirements specify; do not switch streams to satisfy the label literally.

## Acceptance restatement

Verbatim copy of the criteria's `## Verification` block:

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
