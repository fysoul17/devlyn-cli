# Generated criteria — bench-cli cart command

## Requirements

- Add a `cart --input <path>` subcommand to `bin/cli.js` that reads a cart JSON file (`{ "state": string, "coupon": string | null, "items": [{ "sku": string, "qty": number }] }`) and prices it entirely from `data/catalog.json` (products/stock/tax_code, line_promotions, coupons, tax_rates, taxable_codes, shipping_cents, free_shipping_min_cents) — no hardcoded catalog values in code.
- Combine duplicate SKU quantities before stock validation and promotion math; preserve first-seen order for output rows.
- Apply line promotions before the order coupon: `buy_x_get_y_free` → `Math.floor(qty / (buy_qty + free_qty)) * free_qty * unit_cents`; `per_unit_discount_cents` (only when combined qty ≥ `min_qty`) → `per_unit_discount_cents * qty`.
- Coupon discount applies only when post-line-discount subtotal meets `coupon.min_subtotal_cents`: `Math.round((subtotal_cents - line_discount_cents) * coupon.percent / 100)`; else `0`.
- Tax computed after line promotions, before coupon: taxable when `catalog.taxable_codes[tax_code] === true`, rate from `catalog.tax_rates[state]`, `tax_cents = Math.round(taxable_post_line_discount_cents * rate)`.
- Shipping is `0` when `subtotal_cents - line_discount_cents - coupon_discount_cents >= catalog.free_shipping_min_cents`, else `catalog.shipping_cents`.
- `total_cents = subtotal_cents - line_discount_cents - coupon_discount_cents + tax_cents + shipping_cents`.
- On success: stdout is exactly one JSON object with only keys `subtotal_cents`, `line_discount_cents`, `coupon_discount_cents`, `tax_cents`, `shipping_cents`, `total_cents`, `items` (each item row: exactly `sku`, `qty`, `line_subtotal_cents`, `line_discount_cents`, `line_total_cents`); no stderr output.
- On any validation failure (invalid JSON, missing `items`, unknown SKU, non-positive/non-integer qty, unknown coupon, unknown state, combined qty over stock) exit `2`, print exactly one JSON error object to stderr, print nothing to stdout. Combined stock failure shape: `{ "error": "invalid_stock", "sku": string, "available": number, "requested": number }` where `requested` is the combined quantity.
- Parsing and file-read failures must surface as JSON errors, not silent catches.
- Update `tests/cli.test.js` so existing tests (`hello`, `version`) still pass and add at least two new tests covering the cart command: one successful cart, one validation failure.

## Constraints

- Existing file conventions: `bin/cli.js` uses `fs`/`path` core modules only, a `USAGE` help string, a `switch` on `command` in `main()`, and `process.exit(<code>)` + `console.error`/`process.stderr.write` for error paths (see current `hello`/`version`/default-case handling). Follow the same structural style for the new `cart` case.
- `tests/cli.test.js` uses `node:test` + `node:assert` + `execFileSync('node', [CLI, ...args], { encoding: 'utf8' })`; for the failure-path test, invoke the CLI in a way that captures both exit code and stderr (e.g. `spawnSync`) without breaking the existing `execFileSync` helper/tests.
- No new dependencies (package.json has only `express` for the server; do not add packages).
- Only touch `bin/cli.js` and `tests/cli.test.js`. Do not touch `server/`, `web/`, or `data/catalog.json` (catalog is a read-only data source; the goal's example values already support constructing both a success and a stock-failure test case).
- Use integer cents for every public amount; all rounding via `Math.floor` / `Math.round` exactly as specified per field.

## Out of Scope

- Any change to `server/index.js`, `web/index.html`, `data/catalog.json`, `package.json`, or other CLI commands (`hello`, `version`, `--help`).
- Anything not required to implement the `cart` command and its two required test additions.

<!-- devlyn:verification -->
## Verification

- `node --test tests/` — full existing + new test suite passes.
- `node bin/cli.js cart --input <fixture-with-ORDER10-coupon-and-duplicate-TEE-lines>.json` — prints exactly one JSON object with the required top-level keys and item-row shape.
- `node bin/cli.js cart --input <fixture-requesting-more-BAG-than-stock-4>.json` — exits 2, stdout empty, stderr is exactly `{"error":"invalid_stock","sku":"BAG","available":4,"requested":<N>}`.
