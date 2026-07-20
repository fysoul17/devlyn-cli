# Plan — bench-cli cart command

<!-- devlyn:authorized-surface -->
## 1. Files to touch

- `bin/cli.js` — edit — add a `cart` command (dispatch, `--input` flag parsing, catalog load, validation, line-promotion math, tax/coupon/shipping math, JSON output) implementing Requirements 1–5 (`.devlyn/criteria.generated.md:7-11`).
- `tests/cli.test.js` — edit — add at least two new `node:test` cases for the cart command (one successful cart, one validation failure), writing any cart-input JSON to a runtime temp file (e.g. under `os.tmpdir()`) rather than a new checked-in fixture, per Requirement 6 (`.devlyn/criteria.generated.md:12`). Existing three tests (`hello default`, `hello with --name`, `version prints package version`) must keep passing unmodified.

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## 2. Risks

**Out-of-scope expansions to refuse**
- Do not touch `server/`, `web/`, `data/catalog.json`, `README.md`, or `package.json` (no new deps/devDeps/scripts) — explicit Constraint (`.devlyn/criteria.generated.md:16-17`).
- Do not add new checked-in fixture files (e.g. `tests/fixtures/*.json`). The constraint list is exactly `bin/cli.js` + `tests/cli.test.js`, so any cart-input JSON the new tests need must be materialized at test-run time (temp file), not committed as a new source file.
- Do not introduce a test framework dependency; keep `node:test` + `node:assert` + `execFileSync`, matching the existing pattern (`tests/cli.test.js:1-10`).

**Ambiguous spec sections — resolved by literal spec order, must be followed exactly**
- Requirement 5 lists error categories in this literal order: *invalid JSON, missing `items`, unknown SKU, non-positive/non-integer quantity, unknown coupon, unknown state, combined quantity over stock*. IMPLEMENT must validate in exactly this sequence and exit on the first failing category (single JSON object to stderr, exit 2, nothing on stdout):
  1. `invalid_json` — file read failure (e.g. ENOENT) or `JSON.parse` failure. Both fold into this one category since the requirement text only names "invalid JSON" plus a general "parsing/file-read failures must surface as JSON errors, not silent catches" — there is no separate file-not-found category in the spec.
  2. `missing_items` — `items` key absent or not an array.
  3. `unknown_sku` — checked across all combined-candidate items (any item whose `sku` is not a key in `catalog.products`).
  4. `invalid_quantity` — checked across **raw per-item** `qty` values (`Number.isInteger(qty) && qty > 0`), i.e. *before* combining duplicate SKUs. Requirement 3 scopes combining explicitly to "stock validation and promotion math," not to this earlier type check, so a raw negative/fractional qty on one duplicate row must fail even if the summed quantity would be positive.
  5. `unknown_coupon` — only checked when `coupon` is non-null; a `null`/absent coupon skips this check entirely and yields `coupon_discount_cents: 0`.
  6. `unknown_state` — `state` must be a key in `catalog.tax_rates`.
  7. `invalid_stock` — after combining, each SKU's summed qty must be `<= catalog.products[sku].stock`; first offending SKU (first-seen order) wins. This is the only error shape the spec fixes exactly: `{ "error": "invalid_stock", "sku": string, "available": number, "requested": number }`, `requested` = combined qty.
- Error object shape for the other six categories is not spec-mandated verbatim (only `invalid_stock` is). Use `{"error": "<code>"}` with codes `invalid_json`, `missing_items`, `unknown_sku`, `invalid_quantity`, `unknown_coupon`, `unknown_state` for internal consistency; Verification only requires exit 2 + empty stdout + one JSON error object on stderr for the general case.
- `--input` flag itself missing/valueless is a CLI-usage error, not part of the exit-2 JSON contract (that contract governs cart *input-file content* per Requirement 5). Mirror the existing `parseNameFlag` pattern (`bin/cli.js:27-36`): print a short message to stderr, `process.exit(1)`.

**Output-shape literals (restated verbatim from Requirement 2/3/4 — must match exactly)**
- Success stdout: exactly one JSON object, only top-level keys `subtotal_cents, line_discount_cents, coupon_discount_cents, tax_cents, shipping_cents, total_cents, items`, nothing on stderr. Build the object with keys in this literal order (JSON.stringify preserves insertion order).
- Each `items` row: exactly `sku, qty, line_subtotal_cents, line_discount_cents, line_total_cents`, one row per SKU in first-seen order (order of first occurrence in the input `items` array, not catalog order).
- `line_subtotal_cents` = combined qty × `catalog.products[sku].unit_cents`; `line_total_cents` = `line_subtotal_cents − line_discount_cents`; top-level `line_discount_cents` = sum of item line discounts.
- `buy_x_get_y_free` line discount = `Math.floor(qty / (buy_qty + free_qty)) * free_qty * unit_cents`.
- `per_unit_discount_cents` line discount = `per_unit_discount_cents * qty`, only when combined qty `>= min_qty`.
- Order of computation: (1) line promotions → (2) tax on `taxable_post_line_discount_cents` (sum of post-line-discount `line_total_cents` for items whose `tax_code` maps to `true` in `catalog.taxable_codes`), `tax_cents = Math.round(taxable_post_line_discount_cents * catalog.tax_rates[state])` — computed **before** the coupon is subtracted → (3) `coupon_discount_cents = Math.round((subtotal_cents - line_discount_cents) * coupon.percent / 100)` only when `subtotal_cents - line_discount_cents >= coupon.min_subtotal_cents`, else `0` → (4) `shipping_cents = 0` when `subtotal_cents - line_discount_cents - coupon_discount_cents >= catalog.free_shipping_min_cents`, else `catalog.shipping_cents`.
- `total_cents = subtotal_cents - line_discount_cents - coupon_discount_cents + tax_cents + shipping_cents`.
- Must not emit anything to stderr on the success path, and must not `console.log` anything until all validation has passed on the failure path (validate fully before the single write).

**Known failure modes for this language/framework**
- Forgetting first-seen item order when combining duplicate SKUs into a Map — must preserve insertion order (native `Map` iteration order matches insertion order, safe to use).
- Emitting more than one row per SKU, or a row for a SKU with 0 net qty — duplicates must collapse to exactly one row.
- Computing `taxable_post_line_discount_cents` from pre-discount `line_subtotal_cents` instead of post-discount `line_total_cents`.
- Computing the coupon threshold/amount against post-tax or post-shipping totals instead of `subtotal_cents - line_discount_cents`.
- Falling through to the existing `default:` switch branch (which prints `USAGE` and `process.exit(1)`) for cart-internal errors — cart must own its own exit path and never hit that branch for validation failures.

## 3. Acceptance restatement

(Verbatim from `.devlyn/criteria.generated.md`, `<!-- devlyn:verification -->` block)

- `node --test tests/` (full suite, including the two-or-more new cart tests, must pass)
- `node bin/cli.js cart --input <valid-cart.json>` prints exactly one JSON object on stdout with keys `subtotal_cents, line_discount_cents, coupon_discount_cents, tax_cents, shipping_cents, total_cents, items` and nothing on stderr, exit code `0`.
- `node bin/cli.js cart --input <invalid-cart.json>` (e.g. combined quantity over stock) exits `2`, prints exactly one JSON error object to stderr matching `{ "error": "invalid_stock", "sku": ..., "available": ..., "requested": ... }`, and prints nothing to stdout.
