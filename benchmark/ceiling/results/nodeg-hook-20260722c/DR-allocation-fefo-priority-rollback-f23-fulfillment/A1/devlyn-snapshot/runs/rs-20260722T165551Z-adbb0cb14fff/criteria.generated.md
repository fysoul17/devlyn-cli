# Generated criteria — fulfill-wave CLI command

## Requirements

- Add a `fulfill-wave` subcommand to `bin/cli.js`, invoked as `bench-cli fulfill-wave --input <path>`, reading one JSON object from `<path>` with required arrays `warehouses` (each `{ id, distance, lots: [{ sku, lot, qty, expires }] }`) and `orders` (each `{ id, priority, submitted_at, lines: [{ sku, qty, single_warehouse }] }`).
- Validate the full input before allocating anything: ids/SKU/lot identifiers are non-empty strings; quantities are positive integers; `expires` is a valid `YYYY-MM-DD` calendar date; `submitted_at` parses as an ISO date/timestamp; `distance`/`priority` are numbers; `warehouses`/`orders`/`lots`/`lines` are arrays; order ids are unique. The input file must never be mutated.
- Process orders in global order: `priority` descending, then `submitted_at` ascending, then `id` ascending. Each order is all-or-nothing — if any line cannot be fully allocated, reject the whole order and roll back every tentative stock deduction it made; rejected orders must not affect stock available to later orders.
- `single_warehouse: false` lines may split across warehouses/lots; `single_warehouse: true` lines must be fully satisfied from one warehouse (which may combine multiple lots in that warehouse) and reject if no single warehouse alone has enough stock, even if combined stock across warehouses would suffice.
- Warehouse selection order: `distance` ascending, then warehouse `id` ascending. Lot consumption within a warehouse: FEFO — `expires` ascending, then `lot` id ascending. Allocation rows preserve the exact sequence stock was drawn in.
- On success, write exactly one parseable JSON object to stdout (nothing to stderr, no extra text) with only keys `accepted` (processing order; each `{ id, allocations: [{ sku, warehouse, lot, qty }] }`), `rejected` (original input order; each `{ id, reason: "insufficient_stock" }`), and `remaining` (positive leftover lots sorted by warehouse id, then sku, then expires, then lot id; each `{ warehouse, sku, lot, qty, expires }`).
- On invalid input or file-read failure, exit code `2`, write nothing to stdout, and write exactly one parseable JSON object (non-null, non-array) to stderr describing the failure.
- Update `tests/cli.test.js`: keep all existing tests passing, and add at least two `fulfill-wave` tests — one accepted allocation, one rejected all-or-nothing order.

## Constraints

- Only touch `bin/cli.js` and `tests/cli.test.js` (matches existing CLI structure: a `USAGE` string, a `switch (command)` dispatcher in `main()`, tests invoking `node bin/cli.js <args>` via `execFileSync`).
- No new npm dependencies (`package.json` currently declares only `express` as a runtime dependency for the server, unrelated to the CLI).
- No catch block that silently returns `null`/`undefined`/empty string/empty object, and no empty catch block.
- Out of scope: carrier selection, package dimensions, backorders/partial order acceptance, and persistence beyond stdout.

## Out of Scope

- Anything not in `bin/cli.js` or `tests/cli.test.js`.
- The existing `hello`/`version`/`--help` commands, beyond leaving them working.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "node --test tests/",
      "stdout_contains": ["# pass 11", "# fail 0"]
    },
    {
      "cmd": "TMP=$(mktemp) && printf '%s' '{\"warehouses\":[{\"id\":\"W1\",\"distance\":1,\"lots\":[{\"sku\":\"SKU1\",\"lot\":\"L1\",\"qty\":10,\"expires\":\"2026-01-01\"}]}],\"orders\":[{\"id\":\"O1\",\"priority\":1,\"submitted_at\":\"2026-01-01T00:00:00Z\",\"lines\":[{\"sku\":\"SKU1\",\"qty\":5,\"single_warehouse\":false}]}]}' > \"$TMP\" && node bin/cli.js fulfill-wave --input \"$TMP\"; CODE=$?; rm -f \"$TMP\"; exit $CODE",
      "stdout_contains": ["\"accepted\"", "\"O1\"", "\"SKU1\"", "\"W1\"", "\"L1\""]
    },
    {
      "cmd": "TMP=$(mktemp) && printf '%s' '{\"warehouses\":[{\"id\":\"W1\",\"distance\":1,\"lots\":[{\"sku\":\"SKU1\",\"lot\":\"L1\",\"qty\":3,\"expires\":\"2026-01-01\"}]}],\"orders\":[{\"id\":\"O1\",\"priority\":1,\"submitted_at\":\"2026-01-01T00:00:00Z\",\"lines\":[{\"sku\":\"SKU1\",\"qty\":5,\"single_warehouse\":false}]}]}' > \"$TMP\" && node bin/cli.js fulfill-wave --input \"$TMP\"; CODE=$?; rm -f \"$TMP\"; exit $CODE",
      "stdout_contains": ["\"rejected\"", "\"insufficient_stock\"", "\"remaining\"", "\"qty\":3"]
    },
    {
      "cmd": "TMP=$(mktemp) && printf '%s' '{\"warehouses\":[],\"orders\":[{\"id\":\"\",\"priority\":1,\"submitted_at\":\"bad\",\"lines\":[]}]}' > \"$TMP\" && node bin/cli.js fulfill-wave --input \"$TMP\" >/tmp/fw-stdout.$$ 2>/tmp/fw-stderr.$$; CODE=$?; OUT=$(cat /tmp/fw-stdout.$$); ERR=$(cat /tmp/fw-stderr.$$); rm -f \"$TMP\" /tmp/fw-stdout.$$ /tmp/fw-stderr.$$; if [ \"$CODE\" -eq 2 ] && [ -z \"$OUT\" ] && [ -n \"$ERR\" ]; then echo INVALID_INPUT_OK; exit 0; else echo INVALID_INPUT_FAIL; exit 1; fi",
      "stdout_contains": ["INVALID_INPUT_OK"]
    }
  ]
}
```
