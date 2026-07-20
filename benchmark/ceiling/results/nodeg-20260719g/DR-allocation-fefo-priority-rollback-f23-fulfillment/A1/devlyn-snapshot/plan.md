# Plan — `fulfill-wave` command

<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` — **edit**. Add a `fulfill-wave` case to the `switch (command)` dispatch in `main()` (`bin/cli.js:46-60`), plus supporting functions for input validation, order/warehouse/lot sorting, all-or-nothing FEFO allocation with rollback, and JSON stdout/stderr output. Satisfies Requirements 1–4 (validate-then-allocate, exit-2 error contract, priority/time/id processing order with single-warehouse/split rules, and the exact-shape success JSON).
- `tests/cli.test.js` — **edit**. Add at least two `fulfill-wave` tests (accepted allocation; rejected all-or-nothing order with stock restored for a later order) alongside the existing `hello`/`version` tests (`tests/cli.test.js:12-25`), reusing the existing `run()` / `execFileSync` harness (`tests/cli.test.js:8-10`). Satisfies Requirement 4's test-coverage clause.

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

**Out-of-scope expansions to refuse:**
- Carrier selection, package dimensions, backorders/partial order acceptance, persistence beyond stdout (spec's own Out-of-Scope list) — no code for any of these.
- New npm dependencies or a new argument-parsing library/style — reuse the existing manual `argv.indexOf(...)` pattern already used by `parseNameFlag` (`bin/cli.js:27-36`), only `fs`/`path` built-ins.
- Touching `USAGE` text (`bin/cli.js:8-19`) or any file outside the authorized surface — not required by any Requirement or existing test; leaving it out keeps the diff minimal (subtractive-first/goal-locked).
- Adding validation the spec doesn't ask for (e.g., warehouse-id uniqueness, non-negative distance) — spec only requires unique *order* ids and numeric distance/priority; extra checks would be speculative robustness.

**Ambiguous spec points, locked to one interpretation:**
- `submitted_at` "must parse as ISO dates or timestamps" — accept either a string or a number, valid if `new Date(value).getTime()` is not `NaN`; used only for comparison, not re-emitted.
- Missing/invalid `--input <path>` flag for `fulfill-wave` (flag absent, or path unreadable) is treated as part of this command's own "invalid input or file-read failure" exit-2 + stderr-JSON contract (Requirement 2) — **not** `hello`'s unrelated exit-1 + plain-text `--name requires a value` pattern (`bin/cli.js:31-34`), since the spec defines only one error contract for `fulfill-wave` and it explicitly names exit `2`.
- `remaining` sort (warehouse id, then sku, then expiry, then lot id) is produced by flattening all lots across all warehouses into one list and sorting once with a single 4-key comparator — more literal and less bug-prone than relying on nested iteration order to happen to line up.
- Rollback restores every deduction made across **all lines already processed for that order**, not just the failing line — an order's allocation attempt tracks a flat list of `{warehouse, lot, qty}` deductions and, on any line failure, adds each `qty` back to its exact lot before moving to the next order.
- "Allocation rows must remain in the exact sequence stock was chosen" — the per-order `allocations` array is built by pushing a row at the moment each lot is consumed, in line-array order then warehouse-then-lot iteration order; never sorted or regrouped afterward.
- Working warehouse/lot/order data used for mutation (stock deduction, sorting) is deep-cloned from the parsed input before any mutation, so the parsed-from-file object tree is never mutated even in memory, keeping "do not mutate the input file" unambiguous.

**Known failure modes for this language/framework:**
- `JSON.parse` throws `SyntaxError` on malformed input; `fs.readFileSync` throws on missing/unreadable paths — both must be caught explicitly (named `catch (err)` using `err.message`) and turned into the exit-2 stderr JSON object, never an empty/silent catch or a fallback value.
- `new Date('2024-02-30')` silently rolls over to a different date in JS — validate `YYYY-MM-DD` via regex capture of year/month/day plus a round-trip check against `Date.UTC(...)` components, not a bare `new Date(...)` truthiness check.
- Quantities must stay integers through allocation (`Math.min(needed, lot.qty)` on integer operands only) — no float arithmetic introduced.
- `Array.prototype.sort` is not stable-guaranteed pre-ES2019 engines, but Node 18+ (per `package.json:19-21` `engines.node >=18.0.0`) guarantees stable sort — safe to rely on for tie-breaking only when explicit comparator keys already cover every required tie-break level (priority, submitted_at, id / distance, warehouse id / expiry, lot id), so stability is not actually load-bearing here.

## Acceptance restatement

(verbatim from `.devlyn/criteria.generated.md`'s `## Verification` section)

- `npm test` passes: existing `hello`/`version` tests plus at least two new `fulfill-wave` tests (one accepted allocation, one rejected all-or-nothing order).
- An invalid `fulfill-wave --input` (e.g. malformed JSON) exits `2`, writes nothing to stdout, and writes exactly one parseable JSON object to stderr.
- A `single_warehouse: true` line rejects when only combined (not single) warehouse stock would suffice; a later all-or-nothing rejection restores stock so a subsequent order can still consume it.
- `remaining` lot rows include only positive quantities, sorted by warehouse id, then sku, then expiry, then lot id.
