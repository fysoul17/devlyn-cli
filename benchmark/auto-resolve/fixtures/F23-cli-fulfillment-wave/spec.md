---
id: "F23-cli-fulfillment-wave"
title: "Fulfillment wave allocator"
status: planned
complexity: high
depends-on: []
---

# F23 Fulfillment wave allocator

## Context

Add a `bench-cli fulfill-wave --input <path>` command that allocates
prioritized orders across warehouses and inventory lots using all-or-nothing
order rollback, FEFO lot choice, distance tie-breaks, and single-warehouse line
constraints.

The allocator prepares a batch for warehouse pickers. A plausible partial plan
is worse than no plan: rejected orders must not consume stock, and accepted
orders must be deterministic.

## Requirements

- [ ] `bench-cli fulfill-wave --input <path>` reads JSON shaped as `{ "warehouses": Array<Warehouse>, "orders": Array<Order> }`.
- [ ] Each warehouse has `{ "id": string, "distance": number, "lots": Array<Lot> }`.
- [ ] Each lot has `{ "sku": string, "lot": string, "qty": number, "expires": "YYYY-MM-DD" }`.
- [ ] Each order has `{ "id": string, "priority": number, "submitted_at": string, "lines": Array<Line> }`.
- [ ] Each line has `{ "sku": string, "qty": number, "single_warehouse": boolean }`.
- [ ] Validate before allocation: ids are non-empty strings, quantities are positive integers, dates parse as ISO dates, priorities are numbers, and order ids are unique.
- [ ] Process orders by `priority` descending, then `submitted_at` ascending, then `id` ascending.
- [ ] An order is all-or-nothing. If any line cannot be fully allocated, reject the order and roll back all allocations tentatively made for that order.
- [ ] For a normal line where `single_warehouse` is `false`, allocation may split across warehouses and lots.
- [ ] For a line where `single_warehouse` is `true`, the entire line quantity must come from one warehouse. It may use multiple lots inside that warehouse, but it must not split across warehouses.
- [ ] Warehouse choice order is `distance` ascending, then warehouse id ascending.
- [ ] Lot choice inside a warehouse is FEFO: `expires` ascending, then lot id ascending.
- [ ] Accepted allocations reduce stock for later orders in the same wave. Rejected orders do not reduce stock.
- [ ] If an order cannot be fully allocated, reject with `{ "id": string, "reason": "insufficient_stock" }`.
- [ ] Invalid input exits `2`, writes exactly one JSON error object to stderr, and writes nothing to stdout.
- [ ] On success, write exactly one JSON object to stdout and no stderr. Keys: `accepted`, `rejected`, `remaining`.
- [ ] `accepted` is ordered by processing order. Each accepted row has keys `id`, `allocations`.
- [ ] Each allocation row has keys `sku`, `warehouse`, `lot`, `qty` and rows are ordered in the sequence stock was chosen.
- [ ] `rejected` is ordered by original input order. Each rejected row has keys `id`, `reason`.
- [ ] `remaining` is sorted by warehouse id, then sku, then expires, then lot. Each row has keys `warehouse`, `sku`, `lot`, `qty`, `expires`.
- [ ] `tests/cli.test.js` is updated. Existing tests still pass AND at least two fulfill-wave tests cover one accepted allocation and one rejected all-or-nothing order.

## Constraints

- **No new npm dependencies.**
- **No silent catches.** Invalid input and file-read failures must surface as JSON errors with exit `2`.
- **No mutation of the input file.**
- **No extra stdout/stderr text** on the success path; downstream tooling parses stdout as JSON.
- **Touch only `bin/cli.js` and `tests/cli.test.js`.**
- **Lifecycle note.** The harness's DOCS phase flips this spec's frontmatter `status` after implementation completes — that is benchmark lifecycle bookkeeping, not a scope violation.

## Out of Scope

- Carrier selection.
- Package dimensions.
- Backorders or partial order acceptance.
- Persistence beyond stdout.
- Touching `server/`, `web/`, or `tests/server.test.js`.

## Verification

- `node --test tests/cli.test.js` exits 0.
- A higher-priority order consumes stock before a lower-priority order even when the lower-priority order appears first in the input.
- A rejected order rolls back all tentative allocations and does not reduce stock available to later orders.
- `single_warehouse: true` does not split a line across warehouses even if total stock across warehouses is enough.
- Lot choice is FEFO by expiry date, then lot id.
- `remaining` is sorted by warehouse id, then sku, then expires, then lot.
- `git diff --stat` shows only `bin/cli.js` and `tests/cli.test.js` touched.
