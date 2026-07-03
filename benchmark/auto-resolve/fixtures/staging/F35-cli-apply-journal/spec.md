---
id: "F35-cli-apply-journal"
title: "Apply command with journal replay and all-or-nothing persistence"
status: planned
complexity: high
depends-on: []
---

# F35 Apply command with journal replay and all-or-nothing persistence

## Context

`bench-cli` gets an `apply` command that applies a file of inventory
adjustments to `data/inventory.json`. Runs are re-deliverable: a journal at
`data/journal.json` records which ops have already been applied, so a
delivered-again op must not change inventory twice. A batch either fully
persists or leaves both files untouched.

## Requirements

- [ ] `bench-cli apply --input <path>` reads JSON shaped as `{ "ops": [{ "op_id": string, "sku": string, "delta": number, "priority": number }] }`.
- [ ] Quantities come from `data/inventory.json`; the applied-op record comes from the journal's `applied` array in `data/journal.json`. Both are seeded by setup.
- [ ] Validation happens before any application. Invalid JSON, missing or non-string `op_id`/`sku`, unknown `sku`, non-integer `delta` or `priority`, or an `op_id` that appears more than once in the input file exits `2` and writes exactly one JSON error object to stderr with shape `{ "error": "invalid_input", "reason": string }`, printing nothing to stdout and changing neither file.
- [ ] An op whose `op_id` is already listed in the journal's `applied` array is recorded as skipped and changes nothing, regardless of its other fields.
- [ ] Non-skipped ops apply in descending `priority`; ties apply in file order.
- [ ] An op fails when applying its `delta` would take the sku's quantity below zero, evaluated at its turn in that order, with exact error shape `{ "error": "insufficient_stock", "op_id": string, "sku": string, "available": number, "requested": number }` where `available` is the quantity at that op's turn and `requested` is the absolute value of its `delta`.
- [ ] If any op fails, nothing persists: `data/inventory.json` and `data/journal.json` are byte-for-byte unchanged, the command exits `2`, and exactly one JSON error object is written to stderr with nothing on stdout.
- [ ] On success, persist the final quantities to `data/inventory.json`, append the applied `op_id`s to the journal's `applied` array in application order, and write exactly one JSON object to stdout with keys `applied` (op_ids in application order), `skipped` (op_ids in file order), and `inventory` (final quantities for every sku). Nothing is written to stderr on success.
- [ ] `tests/cli.test.js` is updated. Existing tests still pass AND at least two new tests cover `apply`: one success mixing a journaled op with different priorities, and one failing batch that leaves both files unchanged.

## Constraints

- **No new npm dependencies.**
- **No silent catches.** If parsing or file reading fails, emit a visible JSON error to stderr and exit `2`.
- **No extra stdout/stderr text** on the success path; downstream tooling parses stdout as JSON.
- Quantities are integers; no fractional inventory.

## Out of Scope

- Changing server routes, web UI, or journal schema.
- Concurrency across multiple `apply` processes.
- Pruning or rewriting existing journal entries.
- Touching `server/`, `web/`, or `tests/server.test.js`.

## Verification

- `node --test tests/cli.test.js` exits 0.
- A batch mixing a journaled op, unequal priorities, and a priority tie yields exact `applied` order, exact `skipped`, exact final `inventory`, and the journal grows by exactly the applied op_ids in that order.
- A batch whose failing op is only discoverable after higher-priority ops have consumed or added stock reports `available` at that op's turn and leaves both files byte-for-byte unchanged.
- A duplicated `op_id` in the input file exits `2` with one JSON error on stderr and no stdout.
- `git diff --stat` shows only `bin/cli.js` and `tests/cli.test.js` touched (inventory and journal are seeded by setup, not the arm).

## Solo-headroom hypothesis

A capable solo_claude baseline is expected to miss that each op's
`available` stock is evaluated at its turn in priority order rather than
against the pre-batch inventory or file order; observable command
`node "$BENCH_FIXTURE_DIR/verifiers/rollback.js"` exposes the miss.
