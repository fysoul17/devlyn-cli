# PLAN — bench-cli `cart` command

<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` (edit) — add a `cart` command: parse `--input <path>`, read the cart JSON,
  read `data/catalog.json` at runtime, validate in the fixed order (json → items → sku →
  qty → coupon → state → stock), combine duplicate SKU quantities, run the line-promotion /
  coupon / tax / shipping / total math, and print exactly one JSON object to stdout on
  success or exactly one JSON error object to stderr + `process.exit(2)` on any validation
  failure. Satisfies Requirements 1–5 (`.devlyn/criteria.generated.md`).
- `tests/cli.test.js` (edit) — keep the 3 existing tests (`hello default`, `hello with
  --name`, `version prints package version`) passing unchanged; add at least 2 new tests:
  one successful `cart` run (assert on the returned JSON shape/values) and one validation
  failure (assert on exit code 2, empty stdout, and the JSON error on stderr). Satisfies
  Requirement 6.

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

- **Out-of-scope expansions to refuse**: any edit to `server/`, `web/`, `data/catalog.json`
  (read-only input per Out-of-Scope), or `package.json`/`package-lock.json` (Constraint: no
  new dependencies — implement with only the already-imported `fs`/`path` builtins). No CLI
  commands beyond `cart`. No persistence of cart state across runs.
- **Validation order is a category-wide two-pass, not a per-item single pass.**
  `pipeline.state.json.risk_profile.reasons` states the ordered stages literally as
  `json, items, sku, qty, coupon, state, stock`. Read this as 7 sequential *phases* over the
  whole request, not "per item: sku then qty": (1) file-read/`JSON.parse` failure, (2)
  `items` missing or not an array, (3) scan the *entire* items array in order and fail on
  the first unknown SKU (checked against `catalog.products`) before any qty check runs, (4)
  scan the *entire* items array again and fail on the first qty that is not
  `typeof qty === 'number' && Number.isInteger(qty) && qty > 0`, (5) if `cart.coupon` is not
  `null`, it must be a key in `catalog.coupons` else `unknown_coupon`, (6) `cart.state` must
  be a key in `catalog.tax_rates` else `unknown_state` (this also naturally catches a
  missing/undefined `state` — no separate "state missing" branch needed), (7) **only after**
  all of the above pass, combine duplicate SKU quantities (sum, preserve first-seen order)
  and compare each combined qty against `catalog.products[sku].stock`; the first SKU (in
  first-seen order) whose combined qty exceeds stock fails with the exact shape
  `{ "error": "invalid_stock", "sku": string, "available": number, "requested": number }`
  (`requested` is the *combined* qty; `available` is `catalog.products[sku].stock`; `qty >
  stock` fails, `qty === stock` passes). This two-pass reading is a judgment call the spec
  doesn't mechanically pin (only single-error-type cases are in the verification commands),
  but it is the more literal reading of the stage list and IMPLEMENT must follow it rather
  than re-deciding.
- **Error JSON shape for the six non-stock failures is unspecified beyond "one JSON error
  object"** — only `invalid_stock`'s shape is mandated verbatim. Use a minimal, consistent
  `{"error": "<code>", ...minimal context}` for the other five (e.g. `invalid_json`,
  `missing_items`, `unknown_sku`, `invalid_qty`, `unknown_coupon`, `unknown_state`) without
  inventing extra mandatory fields the verification doesn't check for — do not overfit to a
  guessed shape beyond what's needed to be a valid, informative JSON error object.
- **No silent catch.** File-read failure (e.g. `--input` path doesn't exist) and
  `JSON.parse` failure must both be caught and turned into the same explicit JSON error
  contract (exit 2, one stderr JSON object, empty stdout) — not an uncaught exception/stack
  trace, and not a bare `catch {}` that swallows the cause. This is the No-Workaround
  principle: the catch must produce the required explicit error, not hide one.
- **Missing `--input` flag entirely is not one of the 6 listed exit-2 failure modes.**
  Treat it as a plain usage error consistent with the existing `--name`-requires-a-value
  pattern already in `bin/cli.js` (`console.error` + `process.exit(1)`), not as a JSON-error
  exit-2 case — do not invent a new area of the exit-2 contract the spec never asked for.
- **Integer-cents discipline.** Every public amount (`subtotal_cents`, `line_discount_cents`,
  `coupon_discount_cents`, `tax_cents`, `shipping_cents`, `total_cents`, and each item's
  `line_subtotal_cents`/`line_discount_cents`/`line_total_cents`) must be produced by the
  literal formulas in Requirement 3–4 using `Math.floor`/`Math.round` exactly where the spec
  places them — no alternate rounding order, no float accumulation that could change a
  boundary result (e.g. computing coupon percent as a pre-divided fraction before
  multiplying, instead of `Math.round((subtotal_cents - line_discount_cents) *
  coupon.percent / 100)` as written).
- **Formula ledger, verbatim from Requirements 3–4** (restated here so IMPLEMENT does not
  re-derive or paraphrase):
  - `line_subtotal_cents(sku) = qty_combined(sku) * unit_cents(sku)`; `subtotal_cents = Σ line_subtotal_cents`.
  - `buy_x_get_y_free` line discount: `Math.floor(qty / (buy_qty + free_qty)) * free_qty * unit_cents`.
  - `per_unit_discount_cents` line discount: only when combined qty `>= min_qty`, discount is `per_unit_discount_cents * qty`; otherwise `0`. A SKU with no matching entry in `catalog.line_promotions` has line discount `0`.
  - `line_discount_cents = Σ` per-line discounts; `line_total_cents(sku) = line_subtotal_cents(sku) - line_discount_cents(sku)`.
  - `coupon_discount_cents = Math.round((subtotal_cents - line_discount_cents) * coupon.percent / 100)` when `(subtotal_cents - line_discount_cents) >= coupon.min_subtotal_cents`, else `0`.
  - `tax_cents = Math.round(taxable_post_line_discount_cents * catalog.tax_rates[state])`, where `taxable_post_line_discount_cents` sums `(line_subtotal_cents - line_discount_cents)` only over items whose `catalog.taxable_codes[product.tax_code] === true`. Tax is computed on the post-line-discount, pre-coupon base.
  - `shipping_cents = 0` when `subtotal_cents - line_discount_cents - coupon_discount_cents >= catalog.free_shipping_min_cents`, else `catalog.shipping_cents`.
  - `total_cents = subtotal_cents - line_discount_cents - coupon_discount_cents + tax_cents + shipping_cents`.
- **Catalog is the single source of truth at runtime** — read `data/catalog.json` fresh each
  invocation (e.g. via `path.join(__dirname, '..', 'data', 'catalog.json')`, matching the
  existing `readPackageVersion` pattern); do not inline/hardcode any product, promotion,
  coupon, tax, or shipping value from the catalog into `bin/cli.js` (Requirement 2). Build
  the SKU→promotion lookup once from `catalog.line_promotions` (an array; the current
  catalog has at most one promotion per SKU — do not assume this always holds beyond what's
  needed, just look up by `sku` and use whatever single match exists, if any).
- **Empty `items: []` is not a listed failure mode** — do not add a rejection for it; it
  should just price to an all-zero cart plus shipping. Do not add checks the spec doesn't
  request (Goal-locked: no speculative robustness).
- **Existing tests are a contract**: do not remove or weaken `hello default`, `hello with
  --name`, or `version prints package version`. `tests/server.test.js` is untouched/out of
  scope; `npm test` running it too is expected and not this change's concern.

## Acceptance restatement

Verbatim from `.devlyn/criteria.generated.md`'s `<!-- devlyn:verification -->` block:

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
