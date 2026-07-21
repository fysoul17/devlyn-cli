---
complexity: medium
---

# Generated criteria — fulfill-wave command

## Requirements

- Add a `fulfill-wave` command to `bin/cli.js` reachable as `bench-cli fulfill-wave --input <path>`. Fully validate the input JSON object (`{ warehouses: Array<Warehouse>, orders: Array<Order> }`) before allocating anything: ids/SKU/lot identifiers are non-empty strings, quantities are positive integers, lot `expires` values are valid `YYYY-MM-DD` calendar dates, `submitted_at` parses as an ISO date or timestamp, `distance`/`priority` are numbers, `warehouses`/`orders`/`lots`/`lines` are arrays, and order ids are unique. Never mutate the input file on disk.
- Process orders in one global pass ordered by `priority` descending, then `submitted_at` ascending, then `id` ascending. Each order is all-or-nothing: if any line cannot be fully allocated, reject the order and restore every stock deduction tentatively made for it during that order's attempt. Accepted orders reduce stock visible to later orders; rejected orders leave stock untouched.
- Honor per-line warehouse/lot selection rules: a `single_warehouse: false` line may split across warehouses and lots; a `single_warehouse: true` line must be filled entirely from one warehouse (it may still consume multiple lots within that warehouse) and is rejected when no single warehouse holds enough stock even if combined stock across warehouses would suffice. Choose warehouses by `distance` ascending then warehouse `id` ascending; within a chosen warehouse consume matching lots FEFO (`expires` ascending, then lot `id` ascending). Allocation rows must stay in the exact sequence stock was chosen.
- On success, write exactly one parseable JSON object to stdout and nothing to stderr, with only the keys `accepted` (processing order; each row `{ id, allocations: [{ sku, warehouse, lot, qty }] }`), `rejected` (original input order; each row `{ id, reason: "insufficient_stock" }`), and `remaining` (positive leftover lot quantities sorted by warehouse id, then sku, then expiry, then lot id; each row `{ warehouse, sku, lot, qty, expires }`).
- On invalid input or a file-read failure, exit with code `2`, write nothing to stdout, and write exactly one parseable JSON object (non-null, non-array) to stderr; never use a catch block that silently returns `null`/`undefined`/`""`/`{}` or an empty catch block. Update `tests/cli.test.js` so every existing test still passes and add at least two new `fulfill-wave` tests: one accepted allocation and one rejected all-or-nothing order.

## Constraints

- Only touch `bin/cli.js` and `tests/cli.test.js` — no other files.
- No new npm dependencies; use Node builtins only (existing `fs`/`path` usage in `bin/cli.js` is the established pattern).
- Match the existing CLI's dispatch style: a `switch` on the command name inside `main()`, `--help` usage text listing the new command, `process.exit` for error codes, and explicit error output — no silent fallback swallowing errors (`bin/cli.js:38-60` is the existing pattern for flag parsing and error exit).

## Out of Scope

- Carrier selection, package dimensions, backorders, partial order acceptance, and persistence beyond stdout (explicitly excluded by the goal).
- Any change to `server/`, `package.json`, `scripts/`, or the existing `hello`/`version` commands beyond adding `fulfill-wave` to the usage text.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "npm test",
      "exit_code": 0
    },
    {
      "cmd": "node bin/cli.js --help",
      "exit_code": 0,
      "stdout_contains": ["fulfill-wave"]
    }
  ]
}
```
