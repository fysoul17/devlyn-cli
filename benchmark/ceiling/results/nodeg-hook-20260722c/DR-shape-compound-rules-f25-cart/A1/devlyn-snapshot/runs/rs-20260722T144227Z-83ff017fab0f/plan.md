# Plan — bench-cli `cart` command

<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` — **edit**. Add a `cart` command branch to the `switch` in `main()` (bin/cli.js:46-60), a `--input` flag parser modeled on the existing `parseNameFlag` (bin/cli.js:27-36), a `data/catalog.json` loader modeled on `readPackageVersion` (bin/cli.js:21-25), and the pricing/validation pipeline (combine duplicate SKUs → validate → apply line promotions → coupon → tax → shipping → totals) plus a JSON-error-and-`exit(2)` path. Also extend `USAGE` (bin/cli.js:8-19) with the new command so `--help` stays accurate. Required because the goal is "Add a bench-cli cart command".
- `tests/cli.test.js` — **edit**. Keep the three existing tests (cli.test.js:12-25) passing unmodified, add a fixture helper that writes a temp cart JSON file (built-in `node:fs`/`node:os`, no new dependency) and reads it via `--input`, and add at least two new tests: one successful cart whose exact JSON stdout is asserted against hand-computed totals from the real `data/catalog.json` values, and one validation failure (e.g. unknown SKU or insufficient stock) asserting exit code `2`, empty stdout, and the exact JSON error shape on stderr. Required by "Update `tests/cli.test.js` so existing tests still pass and at least two new tests cover the cart command".

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

- **Scope fence.** `data/catalog.json`, `package.json`, `server/`, `web/`, `scripts/lint-json.js` are read-only/out-of-bounds. No new npm dependency (e.g. no arg-parsing or schema library) — hand-roll flag parsing and validation using only `fs`/`path`, consistent with the file's existing style.
- **Validation order is unspecified by the goal** across distinct error categories (invalid JSON, missing `items`, unknown SKU, bad qty, unknown coupon, unknown state, insufficient stock). IMPLEMENT must pick one fixed, deterministic order and apply it consistently rather than letting it fall out of incidental code structure. Planned order: (1) file read / JSON.parse, (2) `items` array present, (3) per-item validation in first-seen input order — SKU known in `catalog.products`, qty is a positive integer, (4) `state` known in `catalog.tax_rates`, (5) `coupon` is `null` or known in `catalog.coupons`, (6) combine duplicate SKUs preserving first-seen order, (7) per combined-SKU stock check (`qty <= catalog.products[sku].stock`), (8) pricing computation. This order satisfies the goal's one hard ordering constraint — "combined before stock validation and promotion math" — stock/promotion checks only run after combining.
- **Non-stock error JSON shape is not spec-dictated** (only `invalid_stock`'s shape is exact: `{ "error": "invalid_stock", "sku", "available", "requested" }`). Keep other error objects minimal and consistent (`{"error": "<code>", ...discriminating fields}`), and every failure path — including a missing/invalid `--input` value — must emit one structured JSON object to stderr and `exit(2)`; never an uncaught exception, a stack trace, or the existing default-branch pattern of `exit(1)` + `USAGE` text (bin/cli.js:56-59), which is unrelated to the cart contract.
- **No silent catches.** `JSON.parse` and `fs.readFileSync` failures (bad JSON, missing file, bad `--input`) must be caught and re-emitted as a structured JSON error — never swallowed into a default/fallback cart or catalog value (violates "No workaround" / "no silent catch").
- **Coupon `null` is not "unknown coupon."** Only a non-null coupon string absent from `catalog.coupons` triggers the unknown-coupon error; `coupon: null` means no coupon and contributes `coupon_discount_cents: 0`.
- **Taxability defaults to false.** A `tax_code` absent from `catalog.taxable_codes` (not just mapped to `false`) must be treated as non-taxable — the spec says taxable "exactly when" the code maps to `true`.
- **`Math.round` is banker's-rounding-free in JS** (rounds `.5` toward `+Infinity`); use it literally as the spec formulas specify — do not hand-roll alternate rounding.
- **SKU order preservation.** Use an insertion-ordered `Map` (not a plain object) to combine duplicate SKUs and to build the `items` output, so first-seen order is guaranteed even for numeric-looking SKU strings.
- **Promotion lookup stays minimal.** Only the two documented promotion types (`buy_x_get_y_free`, `per_unit_discount_cents`) get discount logic; a SKU with no matching promotion entry gets zero line discount — no new validation for hypothetical unknown promotion types, since the goal does not request it (goal-locked, no speculative robustness).
- **Out-of-scope expansions to refuse:** no new CLI flags beyond `--input`, no schema-validation library, no changes to `hello`/`version` behavior, no server/web wiring, no README/doc files beyond the in-CLI `USAGE` string update needed for `--help` accuracy.

## Acceptance restatement

Key testable Requirements (verbatim from `.devlyn/criteria.generated.md`):

- `bench-cli cart --input <path>` reads the cart JSON file, prices every item from `data/catalog.json`, combines duplicate SKU quantities before stock validation and promotion math, applies line promotions before the order coupon, and on success prints exactly one JSON object to stdout (no stderr) whose only keys are `subtotal_cents`, `line_discount_cents`, `coupon_discount_cents`, `tax_cents`, `shipping_cents`, `total_cents`, and `items` (one row per SKU in first-seen order, each with exactly `sku`, `qty`, `line_subtotal_cents`, `line_discount_cents`, `line_total_cents`).
- Line promotions apply before the coupon: a `buy_x_get_y_free` promotion's line discount is `Math.floor(qty / (buy_qty + free_qty)) * free_qty * unit_cents`; a `per_unit_discount_cents` promotion applies only when combined qty >= its `min_qty`, with line discount `per_unit_discount_cents * qty`.
- Coupon discount is `Math.round((subtotal_cents - line_discount_cents) * coupon.percent / 100)` when the post-line-discount subtotal meets `coupon.min_subtotal_cents`, else `0`. Tax is computed after line promotions and before the coupon: taxable exactly when `tax_code` maps to `true` in `catalog.taxable_codes`, rate from `catalog.tax_rates[state]`, `tax_cents = Math.round(taxable_post_line_discount_cents * rate)`. Shipping is free when `subtotal_cents - line_discount_cents - coupon_discount_cents >= catalog.free_shipping_min_cents`, else `catalog.shipping_cents`. `total_cents = subtotal_cents - line_discount_cents - coupon_discount_cents + tax_cents + shipping_cents`.
- Invalid JSON, missing `items`, an unknown SKU, a non-positive or non-integer quantity, an unknown coupon, an unknown state, or a combined quantity over stock exits `2`, prints exactly one JSON error object to stderr, and prints nothing to stdout; a stock failure has the exact shape `{ "error": "invalid_stock", "sku": string, "available": number, "requested": number }` with `requested` as the combined quantity. Parsing/file-read failures surface as JSON errors, never silent catches.
- `tests/cli.test.js` still passes its existing tests and gains at least two new tests covering the cart command (one successful cart, one validation failure); no new dependencies are added; only `bin/cli.js` and `tests/cli.test.js` are touched.

Constraints (verbatim):

- Every public amount is integer cents.
- All catalog-derived values (products, stock, tax codes, promotions, coupons, tax rates, shipping, free-shipping threshold) are read from `data/catalog.json` at runtime — changing those values must change the result without a code change.
- Duplicate SKUs are combined before stock validation and promotion math.

## Verification

```json
{
  "verification_commands": [
    { "cmd": "npm test", "exit_code": 0 }
  ]
}
```
