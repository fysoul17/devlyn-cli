# Plan — `fulfill-wave` command

## Evidence read at planning time

- `.devlyn/criteria.generated.md` (Requirements/Constraints/Out-of-Scope/Verification, lines 1-42).
- `bin/cli.js:1-64` — existing CLI: `switch (command)` dispatch (line 46), `USAGE` const listing every command (line 8), flag parsing via `argv.indexOf` returning a default or `process.exit(1)` on bad flag (`parseNameFlag`, lines 27-36), direct `fs`/`path` usage, `console.log`/`console.error`/`process.stdout.write`/`process.stderr.write` for output, explicit `process.exit` codes.
- `tests/cli.test.js:1-26` — `execFileSync('node', [CLI, ...args], { encoding: 'utf8' })` helper (no stdin plumbing), three existing `test()` blocks using `node:test`/`node:assert`, no `fs`/`os` imports yet.
- `package.json:19-21` — `engines.node >= 18.0.0` (stable `Array.prototype.sort`, no extra runtime constraints).

<!-- devlyn:authorized-surface -->
## 1. Files to touch

- `bin/cli.js` — **edit**. Add the `fulfill-wave` case to the command `switch`, an `--input` flag parser, JSON read/parse, full input validation, the allocation/rollback algorithm, and success/error output — this is the entire feature (Requirements 1-9). Also add a `fulfill-wave` line to the `USAGE` string, matching how `hello`/`version` are already documented (Constraint: "match the existing CLI's style").
- `tests/cli.test.js` — **edit**. Add `node:fs` and `node:os` requires (needed to write a temp input JSON file, since the existing `run()` helper only passes argv, no stdin), plus at least two new `test()` blocks: one accepted-allocation case, one rejected-all-or-nothing case (Requirement 10 / bullet "Update `tests/cli.test.js`").

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## 2. Risks

**Out-of-scope expansions to refuse:**
- No carrier selection, package dimensions, backorders, partial order acceptance, or persistence beyond stdout (explicit Out-of-Scope list).
- No new npm dependencies — use only `fs`, `path`, and other Node builtins already in scope for the file.
- Do not touch any file besides `bin/cli.js` and `tests/cli.test.js` (explicit Constraint, reinforced by the goal note restricting this run to exactly those two paths).
- Do not weaken or remove the three existing tests (`hello default`, `hello with --name`, `version prints package version`) — they stay green.
- Do not add a USAGE/help rewrite, refactor of `hello`/`version`, or any other "while I'm here" cleanup to `bin/cli.js` beyond what `fulfill-wave` requires.

**Known failure modes for this algorithm (the core allocation/rollback logic):**

1. **`single_warehouse: true` vs. the warehouse search order.** The same "distance ascending, then warehouse id ascending" consideration order governs both line kinds. For a `single_warehouse: true` line, IMPLEMENT must pick the *first* warehouse in that order whose *own* matching-lot stock (summed across its lots for that sku) is `>=` the line's remaining qty, then FEFO-draw entirely within that one warehouse. It must **not** fall back to combining stock across warehouses even when the combined total would suffice — that case is a rejection, not a partial multi-warehouse draw. Do not reorder warehouses by "most stock" or "best fit"; the order is purely distance/id, and the first sufficient warehouse wins even if a later, less-preferred warehouse also qualifies.

2. **Per-order (not per-line) atomic rollback.** "All-or-nothing" is scoped to the whole order, not to each line: if line 3 of an order fails after lines 1-2 already committed real stock deductions, all of lines 1-2's deductions must be undone before moving to the next order, and the order (not just line 3) is rejected. Plan of record to avoid needing partial-draw-then-undo within a single line: **pre-check total available matching qty before drawing** for every line (per-warehouse sum for `single_warehouse: true`; sum across all warehouses in consideration order for `single_warehouse: false`). A line only performs real stock deductions once it is known to be fully satisfiable, so a failing line itself never leaves partial deductions to unwind — only an order-level log of already-committed *earlier lines in the same order* needs to be reverted when a *later* line in that order fails. That log must be replayed (restore each `qty` decrement) before the order is recorded as rejected, so the next order in processing order sees pre-order stock levels.

3. **`remaining` is sorted independently, not by allocation/processing order.** After all orders are processed, filter every lot to `qty > 0` (a lot that hits exactly 0 must be dropped, not emitted as a zero row) and then sort strictly by `warehouse id asc, sku asc, expires asc, lot id asc` — this sort key is unrelated to the distance/FEFO consideration order used during allocation, so it must be computed as an explicit final sort over the flattened lot set, not inferred from insertion order.

4. **Two different output orderings for the same order set.** `accepted` must be emitted in *processing* order (priority desc, submitted_at asc, id asc) but `rejected` must be emitted in *original input array* order — these are different orderings over overlapping/complementary order-id sets. Build `accepted` by appending as each order is processed; build `rejected` by iterating the original `orders` array from the input and filtering to ids marked rejected during processing (a Set/Map of rejected ids keyed during the processing pass), not by appending rejections in processing order.

**Ambiguous spec sections resolved by strict, literal reading (do not silently pick a looser interpretation):**

- `submitted_at` is typed as `string` (per the Order shape in Requirement 2), so "parses as ISO date or timestamp" means: the string is either an ISO-8601 date/datetime parseable by `Date.parse`/`new Date(...)`, or a numeric-epoch-milliseconds string (all digits) — validate/parse accordingly; do not accept non-string types for this field since the type is explicitly `string`.
- `expires` validation is calendar-strict: `YYYY-MM-DD` format *and* a real calendar date (e.g. reject `2024-02-30`, `2024-13-01`), not just a regex-shape check — verify by round-tripping the parsed year/month/day back against the input, not by trusting a lenient `new Date()` overflow-rollover.
- "quantities are positive integers" applies to input validation itself: a lot or line with `qty: 0` (or negative, or non-integer) is *invalid input* (exit 2), not a value to silently accept and later filter out of `remaining`.
- `distance`/`priority` "are numbers": since these values come from `JSON.parse`, a `typeof value === 'number'` check is sufficient (valid JSON cannot encode `NaN`/`Infinity`) — no extra finiteness check is needed or should be added.
- Requirement 3's enumerated validation list does **not** include a type check for `single_warehouse` (only ids/sku/lot strings, quantities, `expires`, `submitted_at`, `distance`/`priority` numbers, array-ness of the four named collections, and order-id uniqueness are listed) — do not add an unlisted boolean-type validation for `single_warehouse`; branch on it with a strict `=== true` check so any non-`true` value takes the multi-warehouse path, matching the type default without inventing new validation surface.
- "Do not mutate the input file" is satisfied by never writing to the `--input` path; the in-memory working copy used for tentative deductions is a derived structure, not the parsed input object graph, so there is no ambiguity about touching the original parsed data either.

**No-workaround discipline:**
- The single top-level `try/catch` around read+parse+validate+process must funnel every failure (missing/invalid `--input` flag, `ENOENT`/read error, JSON.parse error, thrown validation error) into the same explicit exit-2 + single-JSON-object-on-stderr path — this is not a silent catch because it always reports (JSON body + nonzero exit), and the spec defines exactly two outcomes (success, or invalid-input/file-read-failure) with no third code path, so collapsing all failure causes into one explicit, reported outcome is the literal contract, not a shortcut.
- Do not reuse the existing `--name`-style pattern (`console.error` + `process.exit(1)` + plain text) or the `default:` case's `USAGE`-dump pattern for any `fulfill-wave` failure — both would violate "nothing on stdout" / "exactly one JSON object on stderr, no other text."

## 3. Acceptance restatement

### Requirements (verbatim)

- Add a `fulfill-wave` command to `bin/cli.js` invoked as `bench-cli fulfill-wave --input <path>`.
- Input file is one JSON object `{ "warehouses": Array<Warehouse>, "orders": Array<Order> }` with `Warehouse = { id: string, distance: number, lots: Array<Lot> }`, `Lot = { sku: string, lot: string, qty: number, expires: "YYYY-MM-DD" }`, `Order = { id: string, priority: number, submitted_at: string, lines: Array<Line> }`, `Line = { sku: string, qty: number, single_warehouse: boolean }`.
- Validate the complete input before allocating anything: ids/sku/lot identifiers are non-empty strings; quantities are positive integers; `expires` is a valid `YYYY-MM-DD` calendar date; `submitted_at` parses as an ISO date or timestamp; `distance`/`priority` are numbers; `warehouses`/`orders`/`lots`/`lines` are arrays; order ids are unique. Do not mutate the input file.
- Process orders globally ordered by `priority` descending, then `submitted_at` ascending, then `id` ascending.
- Each order is all-or-nothing: if any line cannot be fully allocated, reject the order and roll back every tentative stock deduction made for it. Accepted orders reduce stock visible to later orders; rejected orders leave stock untouched.
- A line with `single_warehouse: false` may split its quantity across multiple warehouses and lots. A line with `single_warehouse: true` must be fulfilled entirely from one warehouse (it may still draw from multiple lots within that warehouse); reject the line if no single warehouse holds enough stock even when the sum across warehouses would suffice.
- Warehouse consideration order: `distance` ascending, then warehouse `id` ascending. Within a chosen warehouse, consume matching lots FEFO: `expires` ascending, then lot `id` ascending. Allocation rows must appear in the exact order stock was drawn.
- On success: write exactly one parseable JSON object to stdout, nothing to stderr, no other text. Keys are exactly `accepted`, `rejected`, `remaining`.
  - `accepted`: processing order; each row exactly `{ id: string, allocations: Array<{ sku: string, warehouse: string, lot: string, qty: number }> }`.
  - `rejected`: original input order; each row exactly `{ id: string, reason: "insufficient_stock" }`.
  - `remaining`: positive leftover lot quantities only, sorted by warehouse id, then sku, then expiry, then lot id; each row exactly `{ warehouse: string, sku: string, lot: string, qty: number, expires: "YYYY-MM-DD" }`.
- On invalid input or file-read failure: exit code `2`, nothing on stdout, exactly one parseable JSON object (non-null, non-array) on stderr. No prescribed member names for that object.
- Update `tests/cli.test.js`: keep all existing tests passing; add at least two `fulfill-wave` tests — one covering an accepted allocation, one covering a rejected all-or-nothing order.

### Verification (verbatim)

```json
{
  "verification_commands": [
    { "cmd": "node --test tests/", "exit_code": 0 }
  ]
}
```
