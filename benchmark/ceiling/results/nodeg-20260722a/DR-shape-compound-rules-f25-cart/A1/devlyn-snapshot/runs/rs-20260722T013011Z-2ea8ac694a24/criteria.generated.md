# Criteria — bench-cli cart command

recommend: /devlyn:ideate first (this is a large, best-effort synthesized spec — see Assumptions)

## Requirements

- Add a `cart` subcommand: `bench-cli cart --input <path>`, wired into `bin/cli.js` alongside the existing `hello`/`version` commands.
- Input file at `<path>` is JSON: `{ "state": string, "coupon": string | null, "items": [{ "sku": string, "qty": number }] }`.
- All catalog data (products/unit prices/stock, tax codes, `taxable_codes`, `line_promotions`, `coupons`, `tax_rates`, `shipping_cents`, `free_shipping_min_cents`) is read from `data/catalog.json` at run time — no catalog value may be hardcoded in `bin/cli.js`; changing `data/catalog.json` must change the CLI's output without a code change.
- Duplicate SKUs in `items` are combined (quantities summed) before stock validation and promotion math. Output `items` rows are one per distinct SKU, in first-seen order.
- Every public amount is integer cents.
- **Line promotions** (applied before the coupon), from `catalog.line_promotions` matched by `sku`:
  - `buy_x_get_y_free`: line discount = `Math.floor(qty / (buy_qty + free_qty)) * free_qty * unit_cents`.
  - `per_unit_discount_cents`: applies only when combined `qty >= min_qty`; line discount = `per_unit_discount_cents * qty`.
  - A SKU with no matching promotion has line discount `0`.
- Per item row: `line_subtotal_cents = qty * unit_cents`, `line_total_cents = line_subtotal_cents - line_discount_cents`.
- Top-level `subtotal_cents` = sum of item `line_subtotal_cents`; top-level `line_discount_cents` = sum of item `line_discount_cents`.
- **Coupon** (applied after line promotions): when `coupon` is non-null, known in `catalog.coupons`, and `(subtotal_cents - line_discount_cents) >= coupon.min_subtotal_cents`, then `coupon_discount_cents = Math.round((subtotal_cents - line_discount_cents) * coupon.percent / 100)`; otherwise (coupon absent, or present but below its threshold) `coupon_discount_cents = 0`.
- **Tax** (computed after line promotions, before the coupon): for each item whose `tax_code` maps to `true` in `catalog.taxable_codes`, sum `(line_subtotal_cents - line_discount_cents)` across those taxable items into `taxable_post_line_discount_cents`; `tax_cents = Math.round(taxable_post_line_discount_cents * catalog.tax_rates[state])`. Non-taxable items contribute `0` to this sum.
- **Shipping**: `shipping_cents = 0` when `subtotal_cents - line_discount_cents - coupon_discount_cents >= catalog.free_shipping_min_cents`; otherwise `shipping_cents = catalog.shipping_cents`.
- **Total**: `total_cents = subtotal_cents - line_discount_cents - coupon_discount_cents + tax_cents + shipping_cents`.
- **Success output**: on success, stdout is exactly one JSON object with only the keys `subtotal_cents`, `line_discount_cents`, `coupon_discount_cents`, `tax_cents`, `shipping_cents`, `total_cents`, `items` — nothing else on stdout, nothing on stderr, exit `0`. Each `items` row has exactly the keys `sku`, `qty`, `line_subtotal_cents`, `line_discount_cents`, `line_total_cents` — no more, no less.
- **Validation failures** — each of the following must exit `2`, print exactly one JSON error object to stderr, and print nothing to stdout: invalid/unparseable input JSON, missing `items`, an unknown SKU, a non-positive or non-integer `qty`, an unknown coupon code, an unknown `state`, or a combined-quantity-over-stock condition.
  - The stock-failure error has the exact shape `{ "error": "invalid_stock", "sku": string, "available": number, "requested": number }`, where `requested` is the post-combine quantity for that SKU.
  - Parsing and file-read failures (both the `--input` file and `data/catalog.json`) must be caught and surfaced as a JSON error object on stderr with exit `2` — not an uncaught exception, not a silent catch that produces empty/placeholder output.
- Update `tests/cli.test.js`: existing `hello`/`version` tests keep passing; add at least two new tests for `cart` — at least one successful cart pricing case and at least one validation-failure case.
- Do not add any new npm dependency (`package.json` `dependencies`/`devDependencies` unchanged).
- Touch only `bin/cli.js` and `tests/cli.test.js`.

## Out of Scope

- `server/` and `web/` — explicitly excluded by the goal; no changes there.
- Any change to `data/catalog.json`'s schema or values (the command must read whatever is already there).
- `package.json` dependency changes, README/docs updates, or new CLI flags beyond `--input`.
- Multi-cart-file, interactive, or streaming input modes.

## Assumptions

The goal is precise on the pricing/validation math itself; the following fill gaps the goal leaves open. Each is scope-narrowing and reversible.

1. **Missing/malformed `--input` flag** (flag absent, or given with no value) is treated the same as other CLI input errors: exit `2`, one JSON error object to stderr, nothing on stdout — even though it isn't literally one of the goal's enumerated validation-failure cases, since the goal's blanket "no silent catches, surface as JSON errors" rule implies the same contract for a missing flag.
2. **Non-`invalid_stock` error `error` codes** are an implementation choice: the goal pins the exact shape only for the stock case. This spec uses descriptive snake_case codes (e.g. `invalid_json`, `missing_items`, `unknown_sku`, `invalid_quantity`, `unknown_coupon`, `unknown_state`) for the other cases. Verification checks the general contract (exit `2`, one JSON object on stderr, empty stdout) for these, not an exact key/value shape.
3. **Validation order**: parse JSON → require `items` array → per item, unknown-SKU then invalid-qty → combine duplicate SKUs → unknown-coupon (if `coupon` non-null) → unknown-state → combined-qty-vs-stock. This mirrors the goal's prose enumeration order; the goal only hard-requires that combining happens before stock validation and promotion math.
4. **Tax rounding** happens once over the aggregate `taxable_post_line_discount_cents` (sum across taxable lines, each already net of its own line discount), matching the goal's singular `tax_cents = Math.round(taxable_post_line_discount_cents * rate)` formula — not rounded per line and then summed.
5. **`qty` validity**: must be a JS integer `> 0` (rejects `0`, negatives, non-integers, and non-numeric values) per "non-positive or non-integer quantity."
6. **`--input` flag parsing** follows the existing `--name` pattern already in `bin/cli.js` (missing value, or a value starting with `-`, is treated as a missing/invalid flag).

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "node --test tests/",
      "exit_code": 0
    },
    {
      "cmd": "node -e 'const os=require(\"os\"),fs=require(\"fs\"),path=require(\"path\"),{execFileSync}=require(\"child_process\"),assert=require(\"assert\");const f=path.join(os.tmpdir(),\"devlyn-cart-ok.json\");fs.writeFileSync(f,JSON.stringify({state:\"CA\",coupon:null,items:[{sku:\"MUG\",qty:2}]}));const out=execFileSync(\"node\",[\"bin/cli.js\",\"cart\",\"--input\",f],{encoding:\"utf8\"});const obj=JSON.parse(out);assert.deepStrictEqual(obj,{subtotal_cents:2400,line_discount_cents:0,coupon_discount_cents:0,tax_cents:0,shipping_cents:699,total_cents:3099,items:[{sku:\"MUG\",qty:2,line_subtotal_cents:2400,line_discount_cents:0,line_total_cents:2400}]});fs.unlinkSync(f);console.log(\"CART_OK\");'",
      "exit_code": 0,
      "stdout_contains": ["CART_OK"]
    },
    {
      "cmd": "node -e 'const os=require(\"os\"),fs=require(\"fs\"),path=require(\"path\"),{execFileSync}=require(\"child_process\"),assert=require(\"assert\");const f=path.join(os.tmpdir(),\"devlyn-cart-stock.json\");fs.writeFileSync(f,JSON.stringify({state:\"CA\",coupon:null,items:[{sku:\"BAG\",qty:5}]}));let code=0,stderrOut=\"\";try{execFileSync(\"node\",[\"bin/cli.js\",\"cart\",\"--input\",f],{encoding:\"utf8\"});}catch(e){code=e.status;stderrOut=e.stderr;}assert.strictEqual(code,2);const obj=JSON.parse(stderrOut);assert.deepStrictEqual(obj,{error:\"invalid_stock\",sku:\"BAG\",available:4,requested:5});fs.unlinkSync(f);console.log(\"STOCK_FAIL_OK\");'",
      "exit_code": 0,
      "stdout_contains": ["STOCK_FAIL_OK"]
    }
  ]
}
```
