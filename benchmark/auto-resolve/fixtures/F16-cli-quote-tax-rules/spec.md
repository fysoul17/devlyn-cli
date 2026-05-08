---
id: "F16-cli-quote-tax-rules"
title: "Quote command with tax rules"
status: planned
complexity: high
depends-on: []
---

# F16 Quote command with tax rules

## Context

`bench-cli` currently has greeting and version commands only. The task:
add a `quote` command that reads an order JSON file, prices it from
`data/pricing.json`, validates duplicate SKU quantities before quoting,
and prints one exact JSON quote with cents-based discount, tax, shipping,
and total fields.

This is checkout math, so every calculation must use integer cents and
the output must be machine-readable.

## Requirements

- [ ] `bench-cli quote --input <path>` reads JSON shaped as `{ "state": string, "coupon": string | null, "items": [{ "sku": string, "qty": number }] }`.
- [ ] Pricing comes from `data/pricing.json`. Do not hardcode product prices, stock, tax codes, coupons, or tax rates in the command implementation.
- [ ] Combine duplicate SKUs before validating stock and before computing line totals. The output `items` array must contain one row per SKU in first-seen order.
- [ ] Validation happens before any quote is printed. Invalid JSON, missing `items`, unknown SKU, non-positive or non-integer `qty`, combined quantity over stock, unknown coupon, or unknown state exits `2` and writes exactly one JSON error object to stderr.
- [ ] Combined quantity over stock uses exact error shape `{ "error": "invalid_stock", "sku": string, "available": number, "requested": number }`.
- [ ] On success, write exactly one JSON object to stdout and no stderr. Keys: `subtotal_cents`, `discount_cents`, `tax_cents`, `shipping_cents`, `total_cents`, `items`.
- [ ] Each output item row has keys `sku`, `qty`, `line_cents`. `line_cents` is `unit_cents * combined_qty`.
- [ ] `discount_cents` is `Math.round(subtotal_cents * coupon.percent / 100)` when a coupon is present and the subtotal meets its `min_subtotal_cents`; otherwise `0`.
- [ ] Tax is computed on taxable line totals before any order-level discount. A product is taxable when its `tax_code` maps to `true` in `pricing.taxable_codes`. Tax rate is `pricing.tax_rates[state]`. Use `Math.round(taxable_subtotal_cents * rate)`.
- [ ] `shipping_cents` is `0` when `subtotal_cents - discount_cents >= pricing.free_shipping_min_cents`; otherwise use `pricing.shipping_cents`.
- [ ] `total_cents = subtotal_cents - discount_cents + tax_cents + shipping_cents`.
- [ ] `tests/cli.test.js` is updated. Existing tests still pass AND at least two new tests cover `quote`: one successful quote and one validation failure.

## Constraints

- **No new npm dependencies.**
- **No floating-money output.** All public amounts are integer cents.
- **No silent catches.** If parsing or file reading fails, emit a visible JSON error to stderr and exit `2`.
- **No extra stdout/stderr text** on the success path; downstream tooling parses stdout as JSON.
- **Lifecycle note.** The harness's DOCS phase flips this spec's frontmatter `status` after implementation completes — that is benchmark lifecycle bookkeeping, not a scope violation.

## Out of Scope

- Changing server routes or web UI.
- Inventory mutation or order persistence.
- Adding currencies, locales, or tax jurisdictions beyond `pricing.tax_rates`.
- Touching `server/`, `web/`, or `tests/server.test.js`.

## Verification

- `node --test tests/cli.test.js` exits 0.
- A quote with duplicate SKUs combines quantities before stock validation and emits exact integer-cent totals.
- A quote over combined stock exits `2`, prints one JSON error to stderr, and prints no stdout.
- The stock error object includes `sku`, `available`, and `requested`.
- `git diff --stat` shows only `bin/cli.js` and `tests/cli.test.js` touched (the pricing seed comes from setup, not the arm).
