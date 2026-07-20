# Generated criteria — fulfill-wave command

## Requirements

- [ ] Add a `fulfill-wave` command to `bin/cli.js` invoked as `bench-cli fulfill-wave --input <path>`.
- [ ] Input file is one JSON object `{ "warehouses": Array<Warehouse>, "orders": Array<Order> }` with `Warehouse = { id: string, distance: number, lots: Array<Lot> }`, `Lot = { sku: string, lot: string, qty: number, expires: "YYYY-MM-DD" }`, `Order = { id: string, priority: number, submitted_at: string, lines: Array<Line> }`, `Line = { sku: string, qty: number, single_warehouse: boolean }`.
- [ ] Validate the complete input before allocating anything: ids/sku/lot identifiers are non-empty strings; quantities are positive integers; `expires` is a valid `YYYY-MM-DD` calendar date; `submitted_at` parses as an ISO date or timestamp; `distance`/`priority` are numbers; `warehouses`/`orders`/`lots`/`lines` are arrays; order ids are unique. Do not mutate the input file.
- [ ] Process orders globally ordered by `priority` descending, then `submitted_at` ascending, then `id` ascending.
- [ ] Each order is all-or-nothing: if any line cannot be fully allocated, reject the order and roll back every tentative stock deduction made for it. Accepted orders reduce stock visible to later orders; rejected orders leave stock untouched.
- [ ] A line with `single_warehouse: false` may split its quantity across multiple warehouses and lots. A line with `single_warehouse: true` must be fulfilled entirely from one warehouse (it may still draw from multiple lots within that warehouse); reject the line if no single warehouse holds enough stock even when the sum across warehouses would suffice.
- [ ] Warehouse consideration order: `distance` ascending, then warehouse `id` ascending. Within a chosen warehouse, consume matching lots FEFO: `expires` ascending, then lot `id` ascending. Allocation rows must appear in the exact order stock was drawn.
- [ ] On success: write exactly one parseable JSON object to stdout, nothing to stderr, no other text. Keys are exactly `accepted`, `rejected`, `remaining`.
  - `accepted`: processing order; each row exactly `{ id: string, allocations: Array<{ sku: string, warehouse: string, lot: string, qty: number }> }`.
  - `rejected`: original input order; each row exactly `{ id: string, reason: "insufficient_stock" }`.
  - `remaining`: positive leftover lot quantities only, sorted by warehouse id, then sku, then expiry, then lot id; each row exactly `{ warehouse: string, sku: string, lot: string, qty: number, expires: "YYYY-MM-DD" }`.
- [ ] On invalid input or file-read failure: exit code `2`, nothing on stdout, exactly one parseable JSON object (non-null, non-array) on stderr. No prescribed member names for that object.
- [ ] Update `tests/cli.test.js`: keep all existing tests passing; add at least two `fulfill-wave` tests — one covering an accepted allocation, one covering a rejected all-or-nothing order.

## Constraints

- No catch block that silently returns `null`, `undefined`, `''`, or `{}`, and no empty catch block — handle/report explicitly.
- No new npm dependencies.
- Only touch `bin/cli.js` and `tests/cli.test.js`.
- Match the existing CLI's style (command dispatch via `switch`, `USAGE` string, explicit `process.exit` codes, direct `fs`/`path` usage — see current `bin/cli.js`).

## Out of Scope

- Carrier selection, package dimensions.
- Backorders or partial order acceptance.
- Persistence beyond stdout.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "node --test tests/", "exit_code": 0 }
  ]
}
```
