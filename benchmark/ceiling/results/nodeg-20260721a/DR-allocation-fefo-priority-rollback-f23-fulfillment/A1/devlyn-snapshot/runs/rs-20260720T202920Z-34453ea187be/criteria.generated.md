# Generated criteria — fulfill-wave command

## Requirements

- Add a `fulfill-wave` command to `bin/cli.js` invoked as `bench-cli fulfill-wave --input <path>`. The input file is one JSON object `{ "warehouses": Array<Warehouse>, "orders": Array<Order> }` where `Warehouse = { id: string, distance: number, lots: Array<Lot> }`, `Lot = { sku: string, lot: string, qty: number, expires: "YYYY-MM-DD" }`, `Order = { id: string, priority: number, submitted_at: string, lines: Array<Line> }`, `Line = { sku: string, qty: number, single_warehouse: boolean }`.
- Validate the complete input before allocating anything: ids/SKU/lot identifiers are non-empty strings; quantities are positive integers; lot `expires` values are valid `YYYY-MM-DD` calendar dates; `submitted_at` parses as an ISO date or timestamp; `distance`/`priority` are numbers; `warehouses`/`orders`/`lots`/`lines` are arrays; order ids are unique. Do not mutate the input file on disk.
- Process orders globally ordered by `priority` descending, then `submitted_at` ascending, then `id` ascending. Each order is all-or-nothing: if any line cannot be fully allocated, reject the order and roll back every tentative stock deduction made for that order. Accepted orders reduce stock visible to later orders; rejected orders leave stock untouched.
- A `single_warehouse: false` line may split across warehouses and lots. A `single_warehouse: true` line must be filled entirely from one warehouse (it may still span multiple lots within that warehouse) and must be rejected when no single warehouse holds enough stock, even if combined stock across warehouses would suffice.
- Warehouse selection order: `distance` ascending, then warehouse `id` ascending. Lot selection within a chosen warehouse: FEFO — `expires` ascending, then `lot` id ascending. Allocation rows must appear in the exact sequence stock was consumed.
- On success: write exactly one parseable JSON object to stdout, write nothing to stderr, emit no extra text, and exit 0. The object's only keys are `accepted`, `rejected`, and `remaining`. `accepted` follows processing order; each row is exactly `{ "id": string, "allocations": Array<Allocation> }` with `Allocation = { "sku": string, "warehouse": string, "lot": string, "qty": number }`. `rejected` follows original input order; each row is exactly `{ "id": string, "reason": "insufficient_stock" }`. `remaining` contains only positive leftover lot quantities, sorted by warehouse id, then sku, then expiry, then lot id; each row is exactly `{ "warehouse": string, "sku": string, "lot": string, "qty": number, "expires": "YYYY-MM-DD" }`.
- On invalid input or a file-read failure: exit code 2, write nothing to stdout, and write exactly one parseable JSON value (a non-null, non-array object; member names not otherwise prescribed) to stderr. Do not use a catch block that silently returns `null`/`undefined`/`''`/`{}`, and do not use an empty catch block.
- Update `tests/cli.test.js` so every existing test still passes, and add at least two new `fulfill-wave` tests: one covering an accepted allocation and one covering a rejected all-or-nothing order.

## Constraints

- Only touch `bin/cli.js` and `tests/cli.test.js`.
- No new npm dependencies.
- Follow the existing CLI pattern already in `bin/cli.js` (command dispatch in `main()`'s `switch`, `USAGE` text update) and the existing test pattern in `tests/cli.test.js` (`run(args)` helper via `execFileSync`).

## Out of Scope

- Carrier selection, package dimensions, backorders or partial order acceptance, and persistence beyond stdout.
- Anything not in `bin/cli.js` or `tests/cli.test.js`.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "node --test tests/", "exit_code": 0 }
  ]
}
```
