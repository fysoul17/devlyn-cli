# Plan — bench-cli cart command

<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` (edit) — add a `cart` subcommand (parse `--input`, load `data/catalog.json`, validate the cart, price it, emit the JSON success/error contract) wired into the existing `switch (command)` block (`bin/cli.js:46-60`) alongside `hello`/`version`; add a one-line `cart --input <path>` entry to `USAGE` (`bin/cli.js:8-19`) for discoverability parity with the existing commands. Satisfies every pricing/validation Requirement in the criteria.
- `tests/cli.test.js` (edit) — add at least one successful-pricing test and at least one validation-failure test for `cart`, reusing the existing `run()`/`execFileSync` harness (`tests/cli.test.js:8-10`); existing `hello`/`version` tests (`tests/cli.test.js:12-25`) stay untouched and passing. Satisfies the Requirement "Update `tests/cli.test.js`... add at least two new tests for `cart`".

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

**Out-of-scope expansions to refuse** (per criteria's Out of Scope section):
- No changes to `server/` or `web/`.
- No changes to `data/catalog.json` schema or values — the cart command must read whatever is already on disk (`bin/cli.js` must not hardcode any product/promo/coupon/tax/shipping value from `data/catalog.json:1-27`).
- No `package.json` changes — `dependencies`/`devDependencies` stay exactly as read (`express` only, no devDependencies); no new npm packages.
- No README/docs updates.
- No new CLI flags beyond `--input`; no multi-cart, interactive, or streaming input modes.
- state.complexity says "large" but the actual surface is 2 files with a single responsibility each — no "Execution phases" section, no speculative abstractions (no promo-strategy plugin system, no generic validation framework). Implement as one straight-line function per Assumption-driven order below.

**Ambiguous spec sections — interpreted strictly per the criteria's own Assumptions (not re-litigated):**
1. Missing/malformed `--input` (flag absent, or given with no value / a value starting with `-`, mirroring the existing `parseNameFlag` pattern at `bin/cli.js:27-36`) → exit `2`, one JSON error object on stderr, nothing on stdout.
2. Non-`invalid_stock` error codes are descriptive snake_case (`invalid_json`, `missing_items`, `unknown_sku`, `invalid_quantity`, `unknown_coupon`, `unknown_state`, plus one for a missing `--input` flag and one for a catalog/input read failure) — exact key/value shape beyond `error` is not verified for these, only exit code 2 + single JSON object on stderr + empty stdout.
3. Validation order: parse input JSON → require `items` array → per item: unknown-SKU then invalid-qty → combine duplicate SKUs (sum qty, first-seen order) → unknown-coupon (only if `coupon` is non-null) → unknown-state → combined-qty-vs-stock.
4. Tax is `Math.round` once over the aggregate `taxable_post_line_discount_cents`, not rounded per line then summed.
5. `qty` validity = `Number.isInteger(qty) && qty > 0` (JSON.parse already gives native types, so this also rejects strings/non-numbers).
6. `--input` flag parsing follows the existing `--name` pattern (`bin/cli.js:27-36`): missing value or a value starting with `-` = invalid flag.

**Known failure modes for this shape of code:**
- Order of operations is the highest-risk part of the math — line promotions computed first per-item; `subtotal_cents`/`line_discount_cents` are sums of the (already-computed) per-item values; tax is computed on `(line_subtotal - line_discount)` for taxable items only, using the pre-coupon amount; coupon discount is computed on `(subtotal - line_discount)` and gates on that same value vs. `min_subtotal_cents`; shipping's free-threshold check uses `(subtotal - line_discount - coupon_discount)`, i.e. after the coupon; `total_cents` adds `tax_cents` un-reduced by the coupon. Get each formula's *input* right, not just its arithmetic.
- Duplicate-SKU combining must preserve first-seen order for the output `items` array — use an insertion-ordered `Map` keyed by `sku`, not a plain object relied on for numeric-like key ordering.
- Both `fs.readFileSync`/`JSON.parse` of the `--input` file and of `data/catalog.json` must be wrapped so a read/parse failure produces the JSON-error-on-stderr/exit-2 contract, never an uncaught exception or a swallow-and-continue.
- On any failure path, nothing may reach stdout — do not `console.log` partial state (e.g. echoing parsed input) before validation completes; write only to stderr on the failure path.
- On the success path, stdout must be *exactly* one JSON object with only the six specified top-level keys and each `items` row only the five specified keys — build plain object literals with those exact keys rather than spreading a richer internal object, so no internal bookkeeping field (e.g. a promotion match object) leaks into the output.
- `console.error`/`process.stderr.write` + `process.exit(2)` are synchronous here (single small JSON payload), so no async ordering hazard — but keep the error print and the exit call adjacent so a future edit can't separate them.
- A single thrown/caught error value (e.g. `{ code, ...details }`) at the top of the `cart` case, translated once into the stderr-JSON-and-exit(2) contract, is the natural way to avoid repeating that three-line pattern at every validation branch — this is the explicit, visible error handler the "no silent fallback" rule asks for, not a hidden fallback.

## Acceptance restatement

Verbatim copy of the criteria's `## Verification` block:

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
