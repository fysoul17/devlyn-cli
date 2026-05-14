---
id: "F31-cli-seat-rebalance"
title: "Seat rebalance command"
status: planned
complexity: high
depends-on: []
---

# F31 Seat rebalance command

## Context

`bench-cli` currently has greeting and version commands only. The task:
add a `rebalance-seats` command that reads account capacity and seat events from
a JSON file, processes events by priority with all-or-nothing transfers, rejects
invalid per-event operations without corrupting state, and prints exact applied,
rejected, and final account rows.

This is account entitlement reconciliation. Downstream billing tools parse the
output, so success and error output must be exact machine-readable JSON.

## Requirements

- [ ] `bench-cli rebalance-seats --input <path>` reads JSON shaped as `{ "accounts": [{ "id": string, "region": string, "seats": number, "used": number }], "events": [event] }`.
- [ ] Valid event types are `reserve`, `release`, and `transfer`.
- [ ] `reserve` events have keys `id`, `type`, `account`, `qty`, `priority`, and `effective_at`.
- [ ] `release` events have keys `id`, `type`, `account`, `qty`, `priority`, and `effective_at`.
- [ ] `transfer` events have keys `id`, `type`, `from`, `to`, `qty`, `priority`, `effective_at`, and optional `allow_cross_region`.
- [ ] Before processing any event, duplicate event ids are invalid input: exit `2`, write exactly one JSON error object `{ "error": "duplicate_event_id", "id": string }` to stderr, and write no stdout.
- [ ] Before processing any event, account rows must have unique ids, non-empty string `id` and `region`, integer `seats >= 0`, and integer `used` with `0 <= used <= seats`. Invalid account input exits `2` with one JSON error object and no stdout.
- [ ] Before processing any event, every event `qty` must be a positive integer, every `priority` must be an integer, and every `effective_at` must be a non-empty string. Invalid event input exits `2` with one JSON error object and no stdout.
- [ ] Process events globally by `priority` descending, then `effective_at` ascending, then `id` ascending.
- [ ] `reserve` accepts only when the account exists and has at least `qty` free seats. On accept, increase that account's `used` by `qty`. Otherwise reject the event with reason `unknown_account` or `no_capacity`.
- [ ] `release` accepts only when the account exists and `used >= qty`. On accept, decrease that account's `used` by `qty`. Otherwise reject the event with reason `unknown_account` or `insufficient_used`.
- [ ] `transfer` is all-or-nothing. It accepts only when both accounts exist, the source has `used >= qty`, the destination has at least `qty` free seats, and both accounts have the same `region` unless `allow_cross_region` is `true`.
- [ ] A rejected `transfer` must not change either account. Use reason `unknown_account`, `region_mismatch`, `insufficient_used`, or `no_capacity` for the first failing transfer rule in the order listed above.
- [ ] On success, write exactly one JSON object to stdout and no stderr. Keys: `applied`, `rejected`, `accounts`.
- [ ] `applied` is ordered in processing order. Each row has keys `id`, `type`.
- [ ] `rejected` is ordered in the original input event order. Each row has keys `id`, `reason`.
- [ ] `accounts` is sorted by account id ascending. Each row has keys `id`, `region`, `seats`, `used`, `free`, where `free = seats - used`.
- [ ] `tests/cli.test.js` is updated. Existing tests still pass and at least two new tests cover `rebalance-seats`: one successful priority/transfer scenario and one validation failure.

## Constraints

- **No new npm dependencies.**
- **No hidden mutable global state.** The command must derive output only from the input JSON for that invocation.
- **No silent catches.** Parse and file-read failures must emit a visible JSON error to stderr and exit `2`.
- **No extra stdout/stderr text** on the success path; downstream tooling parses stdout as JSON.

## Out of Scope

- Persisting account state between command invocations.
- Adding billing invoices, plan catalogs, or currency calculations.
- Adding web UI or server routes.
- Touching `server/`, `web/`, or `tests/server.test.js`.

## Verification

- `node --test tests/cli.test.js` exits 0.
- A later high-priority transfer is processed before an earlier low-priority reserve, and the low-priority reserve can lose capacity because of that ordering.
- A rejected transfer leaves both source and destination account usage unchanged.
- Region mismatch rejects a transfer unless `allow_cross_region` is `true`.
- `rejected` rows are reported in the original input event order, even though processing order is priority based.
- Duplicate event ids exit `2`, print exactly `{ "error": "duplicate_event_id", "id": string }` to stderr, and print no stdout.
- Final `accounts` rows are sorted by id and include exact `free` values.
- `git diff --stat` shows only `bin/cli.js` and `tests/cli.test.js` touched.
- Solo-headroom hypothesis: solo_claude is expected to miss transfer rollback or rejected-row ordering under priority processing; observable command `node "$BENCH_FIXTURE_DIR/verifiers/priority-transfer-rollback.js"` exposes the miss.
