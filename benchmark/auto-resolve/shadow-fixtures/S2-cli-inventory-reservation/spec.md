---
id: "S2-cli-inventory-reservation"
title: "Add inventory reservation command"
status: planned
complexity: high
depends-on: []
---

# S2 Add Inventory Reservation Command

## Context

Warehouse operators need a deterministic CLI path to reserve stock for a batch
of orders. Add an inventory reservation CLI command that processes orders by
priority, preserves per-order rollback on insufficient stock, rejects duplicate
order ids, and emits an exact JSON output shape.

## Requirements

- [ ] Add `reserve-stock` to `bin/cli.js`.
- [ ] Accept `--stock <json>` as a JSON object mapping SKU strings to non-negative integer quantities.
- [ ] Accept `--orders <json>` as a JSON array of order objects. Each order has keys `id`, `sku`, `qty`, and `priority`.
- [ ] Process orders globally by `priority` descending, then original input order ascending.
- [ ] A reservation is all-or-nothing per order. It accepts only when the SKU exists and remaining stock has at least `qty`.
- [ ] A rejected reservation must not change stock. Use reason `unknown_sku` when the SKU is absent, or `insufficient_stock` when the SKU exists but lacks enough remaining stock.
- [ ] `reserved` is ordered by processing order. Each row has keys `id`, `sku`, `qty`.
- [ ] `rejected` is ordered in the original input order. Each row has keys `id`, `reason`.
- [ ] `stock` is an object whose keys are sorted alphabetically and whose values are remaining quantities.
- [ ] On success, write exactly one JSON object to stdout and no stderr. Keys: `reserved`, `rejected`, `stock`.
- [ ] Before processing any order, duplicate order ids are invalid input: exit `2`, write exactly one JSON error object `{ "error": "duplicate_order_id", "id": string }` to stderr, and write no stdout.

## Constraints

- Use only Node.js built-ins; add no npm dependencies.
- Touch only `bin/cli.js` and `tests/cli.test.js`.
- Do not silently catch JSON parse or validation errors. Surface invalid input as a user-visible error with nonzero exit.

## Out of Scope

- Reading input from files.
- Supporting fractional quantities.
- Supporting reservations across multiple warehouses.
- Changing `hello`, `version`, server routes, or package metadata.

## Verification

- `node --test tests/cli.test.js` passes.
- `node "$BENCH_FIXTURE_DIR/verifiers/priority-stock-reservation.js"` prints `{"ok":true}`.
- `node "$BENCH_FIXTURE_DIR/verifiers/duplicate-order-error.js"` prints `{"ok":true}`.
- Solo-headroom hypothesis: solo_claude is expected to miss all-or-nothing stock rollback or original-order rejected rows under priority processing; observable command `node "$BENCH_FIXTURE_DIR/verifiers/priority-stock-reservation.js"` exposes the miss.
