---
id: "F25-cli-cart-promotion-rules"
title: "Cart command with promotion rules"
status: planned
complexity: high
depends-on: []
---

# F25 Cart command with promotion rules

## Context

`bench-cli` currently has greeting and version commands only. The task:
add a `cart` command that reads a cart JSON file, prices it from
`data/catalog.json`, combines duplicate SKU quantities, applies line promotions
before an order coupon, and prints one exact JSON total with cents-based
discounts, tax, shipping, and item rows.

This is checkout promotion math, so every public amount must be integer cents
and stdout must stay machine-readable.

## Requirements

- [ ] `bench-cli cart --input <path>` reads JSON shaped as `{ "state": string, "coupon": string | null, "items": [{ "sku": string, "qty": number }] }`.
- [ ] Catalog, stock, tax codes, line promotions, coupons, tax rates, shipping, and free-shipping threshold come from `data/catalog.json`. Do not hardcode these values in the command implementation.
- [ ] Combine duplicate SKUs before validating stock and before applying line promotions. The output `items` array must contain one row per SKU in first-seen order.
- [ ] Validation happens before any cart total is printed. Invalid JSON, missing `items`, unknown SKU, non-positive or non-integer `qty`, combined quantity over stock, unknown coupon, or unknown state exits `2` and writes exactly one JSON error object to stderr.
- [ ] Combined quantity over stock uses exact error shape `{ "error": "invalid_stock", "sku": string, "available": number, "requested": number }`.
- [ ] On success, write exactly one JSON object to stdout and no stderr. Keys: `subtotal_cents`, `line_discount_cents`, `coupon_discount_cents`, `tax_cents`, `shipping_cents`, `total_cents`, `items`.
- [ ] Each output item row has keys `sku`, `qty`, `line_subtotal_cents`, `line_discount_cents`, and `line_total_cents`.
- [ ] Line promotion `buy_x_get_y_free` applies to the configured SKU as `Math.floor(qty / (buy_qty + free_qty)) * free_qty * unit_cents`.
- [ ] Line promotion `per_unit_discount_cents` applies to the configured SKU only when combined `qty >= min_qty`, and the discount is `per_unit_discount_cents * qty`.
- [ ] `line_discount_cents` is the sum of all item line discounts; each `line_total_cents` is `line_subtotal_cents - line_discount_cents` for that item.
- [ ] `coupon_discount_cents` is `Math.round((subtotal_cents - line_discount_cents) * coupon.percent / 100)` when a coupon is present and the post-line-discount subtotal meets `coupon.min_subtotal_cents`; otherwise `0`.
- [ ] Tax is computed after line promotions and before the order coupon. A product is taxable when its `tax_code` maps to `true` in `catalog.taxable_codes`. Tax rate is `catalog.tax_rates[state]`. Use `Math.round(taxable_post_line_discount_cents * rate)`.
- [ ] `shipping_cents` is `0` when `subtotal_cents - line_discount_cents - coupon_discount_cents >= catalog.free_shipping_min_cents`; otherwise use `catalog.shipping_cents`.
- [ ] `total_cents = subtotal_cents - line_discount_cents - coupon_discount_cents + tax_cents + shipping_cents`.
- [ ] `tests/cli.test.js` is updated. Existing tests still pass AND at least two new tests cover `cart`: one successful cart and one validation failure.

## Constraints

- **No new npm dependencies.**
- **No floating-money output.** All public amounts are integer cents.
- **No silent catches.** If parsing or file reading fails, emit a visible JSON error to stderr and exit `2`.
- **No extra stdout/stderr text** on the success path; downstream tooling parses stdout as JSON.

## Out of Scope

- Inventory mutation or order persistence.
- Adding currencies, locales, or tax jurisdictions beyond `catalog.tax_rates`.
- Adding web UI or server routes.
- Touching `server/`, `web/`, or `tests/server.test.js`.

## Verification

- `node --test tests/cli.test.js` exits 0.
- A cart with duplicate SKUs combines quantities before stock validation and before line promotions.
- A cart with both `buy_x_get_y_free` and `per_unit_discount_cents` line promotions applies those promotions before the order coupon.
- Tax is computed from taxable item totals after line promotions and before the order coupon.
- Shipping uses the subtotal after line discounts and coupon discount to decide whether the free-shipping threshold is met.
- A cart over combined stock exits `2`, prints one JSON error to stderr, and prints no stdout.
- The stock error object includes `sku`, `available`, and `requested`.
- Changing `data/catalog.json` prices or rates changes command output without code changes.
- `git diff --stat` shows only `bin/cli.js` and `tests/cli.test.js` touched (the catalog seed comes from setup, not the arm).
