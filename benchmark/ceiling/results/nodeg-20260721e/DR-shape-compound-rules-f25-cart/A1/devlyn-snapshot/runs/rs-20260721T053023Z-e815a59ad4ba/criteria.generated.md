# Generated criteria — bench-cli cart command

## Requirements

- Add a `bench-cli cart --input <path>` command to `bin/cli.js` that reads a cart JSON file (`{ "state": string, "coupon": string|null, "items": [{"sku": string, "qty": number}] }`), prices it from `data/catalog.json`, and on success prints exactly one JSON object to stdout with no stderr output, containing only the keys `subtotal_cents`, `line_discount_cents`, `coupon_discount_cents`, `tax_cents`, `shipping_cents`, `total_cents`, `items` (one row per SKU in first-seen order, each row having exactly `sku`, `qty`, `line_subtotal_cents`, `line_discount_cents`, `line_total_cents`).
- Combine duplicate SKU quantities before stock validation and promotion math. All catalog data (products, stock, tax codes, promotions, coupons, tax rates, shipping, free-shipping threshold) must be read from `data/catalog.json` at runtime so changing catalog values changes results without a code change.
- Line promotions apply before the coupon: `buy_x_get_y_free` discount is `Math.floor(qty / (buy_qty + free_qty)) * free_qty * unit_cents`; `per_unit_discount_cents` applies only when combined qty >= `min_qty`, discount is `per_unit_discount_cents * qty`. Coupon discount is `Math.round((subtotal_cents - line_discount_cents) * coupon.percent / 100)` when the post-line-discount subtotal meets `coupon.min_subtotal_cents`, else `0`.
- Tax is computed after line promotions and before the coupon: a product is taxable when its `tax_code` maps to `true` in `catalog.taxable_codes`; `tax_cents = Math.round(taxable_post_line_discount_cents * catalog.tax_rates[state])`. Shipping is free (`0`) when `subtotal_cents - line_discount_cents - coupon_discount_cents >= catalog.free_shipping_min_cents`, else `catalog.shipping_cents`. `total_cents = subtotal_cents - line_discount_cents - coupon_discount_cents + tax_cents + shipping_cents`.
- Invalid JSON, missing `items`, an unknown SKU, a non-positive or non-integer quantity, an unknown coupon, an unknown state, or a combined quantity over stock must exit `2`, print exactly one JSON error object to stderr, and print nothing to stdout; the stock failure shape is exactly `{ "error": "invalid_stock", "sku": string, "available": number, "requested": number }` with `requested` the combined quantity. Parsing/file-read failures must surface as JSON errors, not silent catches.
- Update `tests/cli.test.js` so existing tests still pass, adding at least two new tests: one successful cart and one validation failure.

## Constraints

- Do not add dependencies (`package.json` `dependencies`/`devDependencies` stay unchanged).
- Only touch `bin/cli.js` and `tests/cli.test.js`; do not touch `server/` or `web/` files.
- Use integer cents for every public amount — no floating point in output.

## Out of Scope

- Any change to `server/` or `web/` directories.
- Any change to the contents of `data/catalog.json` (read-only input).
- New CLI commands beyond `cart`.
- Persisting cart state across runs.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "npm test",
      "exit_code": 0,
      "stdout_contains": [],
      "stdout_not_contains": []
    },
    {
      "cmd": "tmp=$(mktemp)\ncat > \"$tmp\" <<'EOF'\n{\"state\":\"OR\",\"coupon\":null,\"items\":[{\"sku\":\"MUG\",\"qty\":1}]}\nEOF\nout=$(node bin/cli.js cart --input \"$tmp\")\nrm -f \"$tmp\"\nprintf '%s' \"$out\" | node -e 'const fs=require(\"fs\");const obj=JSON.parse(fs.readFileSync(0,\"utf8\"));const keys=Object.keys(obj).sort().join(\",\");const expected=\"coupon_discount_cents,items,line_discount_cents,shipping_cents,subtotal_cents,tax_cents,total_cents\";if(keys!==expected){console.error(\"KEYS:\"+keys);process.exit(1);}if(obj.subtotal_cents!==1200||obj.line_discount_cents!==0||obj.coupon_discount_cents!==0||obj.tax_cents!==0||obj.shipping_cents!==699||obj.total_cents!==1899){console.error(\"VALUES:\"+JSON.stringify(obj));process.exit(1);}const it=obj.items;if(it.length!==1||it[0].sku!==\"MUG\"||it[0].qty!==1||it[0].line_subtotal_cents!==1200||it[0].line_discount_cents!==0||it[0].line_total_cents!==1200){console.error(\"ITEMS:\"+JSON.stringify(it));process.exit(1);}console.log(\"CART_SMOKE_OK\");'\n",
      "exit_code": 0,
      "stdout_contains": [
        "CART_SMOKE_OK"
      ],
      "stdout_not_contains": []
    },
    {
      "cmd": "tmp=$(mktemp)\nerrf=$(mktemp)\ncat > \"$tmp\" <<'EOF'\n{\"state\":\"CA\",\"coupon\":null,\"items\":[{\"sku\":\"TEE\",\"qty\":7},{\"sku\":\"TEE\",\"qty\":5}]}\nEOF\nout=$(node bin/cli.js cart --input \"$tmp\" 2>\"$errf\")\ncode=$?\nerr=$(cat \"$errf\")\nrm -f \"$tmp\" \"$errf\"\nif [ -n \"$out\" ]; then echo \"STDOUT_NOT_EMPTY:$out\"; exit 1; fi\nif [ \"$code\" -ne 2 ]; then echo \"BAD_EXIT:$code\"; exit 1; fi\nprintf '%s' \"$err\" | node -e 'const fs=require(\"fs\");const obj=JSON.parse(fs.readFileSync(0,\"utf8\"));const keys=Object.keys(obj).sort().join(\",\");if(keys!==\"available,error,requested,sku\"){console.error(\"KEYS:\"+keys);process.exit(1);}if(obj.error!==\"invalid_stock\"||obj.sku!==\"TEE\"||obj.available!==10||obj.requested!==12){console.error(\"VALUES:\"+JSON.stringify(obj));process.exit(1);}console.log(\"CART_STOCK_ERR_OK\");'\n",
      "exit_code": 0,
      "stdout_contains": [
        "CART_STOCK_ERR_OK"
      ],
      "stdout_not_contains": []
    }
  ]
}
```
