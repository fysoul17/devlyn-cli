# Generated criteria — fulfill-wave command

## Context

Add a `fulfill-wave` command to `bin/cli.js` (bench-cli) that allocates order lines against warehouse lot stock: validate input, process orders by priority/time/id, allocate FEFO within a chosen warehouse, and roll back all-or-nothing on any unfulfillable line.

## Requirements

- [ ] `bench-cli fulfill-wave --input <path>` reads one JSON object `{ "warehouses": [...], "orders": [...] }`, validates it completely before allocating (non-empty string ids/sku/lot, positive-integer quantities, valid `YYYY-MM-DD` lot expiry, parseable `submitted_at`, numeric distance/priority, array-typed collections, unique order ids), and never mutates the input file.
- [ ] Invalid input or a file-read failure exits `2`, writes nothing to stdout, and writes exactly one parseable JSON object (not null, not an array) to stderr.
- [ ] Orders process in strict global order — priority descending, then `submitted_at` ascending, then id ascending. A `single_warehouse: true` line is rejected when no single warehouse holds enough stock even if combined stock across warehouses would suffice; a `single_warehouse: false` line may split across warehouses and lots.
- [ ] An order is all-or-nothing: if any line cannot be fully allocated, the whole order is rejected and every tentative stock deduction made for it is restored before the next order is considered. Warehouses are chosen by distance ascending then id ascending; lots within a chosen warehouse are consumed FEFO (expiry ascending, then lot id ascending); allocation rows stay in the exact sequence stock was chosen.
- [ ] On success, stdout is exactly one parseable JSON object with only `accepted` (processing order; rows `{ id, allocations: [{ sku, warehouse, lot, qty }] }`), `rejected` (original input order; rows `{ id, reason: "insufficient_stock" }`), and `remaining` (positive-qty lot rows only, sorted by warehouse id, then sku, then expiry, then lot id; rows `{ warehouse, sku, lot, qty, expires }`) — stderr stays empty. `tests/cli.test.js` keeps all existing tests passing and gains at least two new `fulfill-wave` tests covering an accepted allocation and a rejected all-or-nothing order.

## Constraints

- **Only touch `bin/cli.js` and `tests/cli.test.js`.** Everything else (carrier selection, package dimensions, backorders/partial acceptance, persistence beyond stdout) is out of scope.
- **No new npm dependencies.** The existing `hello`/`version` commands in `bin/cli.js` use only Node.js built-ins (`fs`, `path`); `fulfill-wave` follows the same zero-dependency style.
- **No silent catches.** Never swallow an error into `null`/`undefined`/`''`/`{}` and never leave an empty catch block — invalid/unreadable input surfaces through the exit-2 stderr contract, not a fallback value.
- **Follow the existing dispatch pattern.** Add `fulfill-wave` as a new `case` in `main()`'s `switch (command)`, matching the existing `process.stderr` + explicit `process.exit` error style rather than introducing a new argument-parsing approach.

## Out of Scope

- Carrier selection and package dimensions.
- Backorders or partial order acceptance.
- Persistence beyond stdout (no writing output or state to disk).

<!-- devlyn:verification -->
## Verification

- `npm test` passes: existing `hello`/`version` tests plus at least two new `fulfill-wave` tests (one accepted allocation, one rejected all-or-nothing order).
- An invalid `fulfill-wave --input` (e.g. malformed JSON) exits `2`, writes nothing to stdout, and writes exactly one parseable JSON object to stderr.
- A `single_warehouse: true` line rejects when only combined (not single) warehouse stock would suffice; a later all-or-nothing rejection restores stock so a subsequent order can still consume it.
- `remaining` lot rows include only positive quantities, sorted by warehouse id, then sku, then expiry, then lot id.

```json
{
  "verification_commands": [
    { "cmd": "npm test" },
    {
      "cmd": "node -e \"require('fs').writeFileSync('.tmp-fulfill-wave-invalid.json','not json')\" && node bin/cli.js fulfill-wave --input .tmp-fulfill-wave-invalid.json; code=$?; rm -f .tmp-fulfill-wave-invalid.json; test \"$code\" -eq 2"
    }
  ]
}
```
