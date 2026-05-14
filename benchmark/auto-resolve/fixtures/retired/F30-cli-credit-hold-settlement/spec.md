---
id: "F30-cli-credit-hold-settlement"
title: "Credit hold settlement"
status: planned
complexity: high
depends-on: []
---

# F30 Credit hold settlement

## Context

`bench-cli` currently has greeting and version commands only. The task:
add a `settle-holds` command that reads account credit holds and operations,
applies authorization/capture/release with idempotency and rollback, and emits
exact cents-based settlement state without mutating input.

Credit holds feed payment and ledger workflows, so duplicate operations,
failed operations, and available-credit calculations must be deterministic.

## Requirements

- [ ] `bench-cli settle-holds --input <path>` reads JSON shaped as `{ "accounts": Array<Account>, "operations": Array<Operation> }`.
- [ ] Each account has `{ "id": string, "balance_cents": number, "credit_limit_cents": number }`.
- [ ] Each operation has `{ "id": string, "account_id": string, "type": "authorize" | "capture" | "release", "hold_id": string, "amount_cents": number }`.
- [ ] Validate before settlement: ids and hold ids must be non-empty strings, account ids must be unique, balances and credit limits must be non-negative integers, amount cents must be positive integers, operation types must be one of the allowed strings, and every operation account must exist.
- [ ] Invalid input exits `2`, writes exactly one JSON error object to stderr, and writes nothing to stdout.
- [ ] Business rejections do not exit non-zero and do not mutate settlement state.
- [ ] Process operations in input order.
- [ ] An `authorize` operation creates one active hold when `credit_limit_cents - balance_cents - active_hold_cents >= amount_cents`; otherwise it is rejected with reason `"insufficient_credit"`.
- [ ] An `authorize` operation for a `hold_id` that is already active is rejected with reason `"duplicate_hold"`.
- [ ] A `capture` operation requires an active hold for the same account and exactly the requested amount available on that hold; otherwise it is rejected with reason `"unknown_hold"` or `"amount_mismatch"`.
- [ ] An approved `capture` increases `balance_cents` by `amount_cents` and removes the active hold.
- [ ] A `release` operation requires an active hold for the same account and exactly the requested amount available on that hold; otherwise it is rejected with reason `"unknown_hold"` or `"amount_mismatch"`.
- [ ] An approved `release` removes the active hold without changing `balance_cents`.
- [ ] Duplicate operation ids are idempotent: the first occurrence is processed normally; each later operation with the same `id` must not mutate state and emits `{ "id": string, "status": "duplicate", "original_status": "approved" | "rejected" }`.
- [ ] Approved rows have keys `id`, `status`, `type`, `account_id`, `hold_id`, `amount_cents`.
- [ ] Rejected rows have keys `id`, `status`, `reason`.
- [ ] Duplicate rows have keys `id`, `status`, `original_status`.
- [ ] On success, write exactly one JSON object to stdout and no stderr. Keys: `results`, `accounts`.
- [ ] `results` is ordered by input operation order.
- [ ] `accounts` is sorted by account id. Each account row has keys `id`, `balance_cents`, `active_hold_cents`, `available_cents`.
- [ ] The command must not modify the input file.
- [ ] `tests/cli.test.js` is updated. Existing tests still pass AND at least two new tests cover one mixed approved/rejected/duplicate settlement and one validation failure.

## Constraints

- **No new npm dependencies.**
- **No floating-money output.** All public amounts are integer cents.
- **No silent catches.** Invalid input and file-read failures must surface as JSON errors with exit `2`.
- **No extra stdout/stderr text** on the success path; downstream tooling parses stdout as JSON.
- **Touch only `bin/cli.js` and `tests/cli.test.js`.**

## Out of Scope

- Payment processor calls.
- Persistence beyond stdout.
- Partial captures or partial releases.
- Currencies, interest, fees, or statement generation.
- Touching `server/`, `web/`, or `tests/server.test.js`.

## Verification

- `node --test tests/cli.test.js` exits 0.
- A failed authorization does not reserve credit and does not block a later valid authorization.
- Capture removes the active hold and increases `balance_cents`.
- Release removes the active hold without changing `balance_cents`.
- Duplicate operation ids do not mutate state and report the original status.
- Reusing an active `hold_id` is rejected as `"duplicate_hold"`.
- Capture or release with a wrong amount is rejected as `"amount_mismatch"` and does not mutate state.
- Invalid unknown-account input exits `2`, prints one JSON error object to stderr, and prints no stdout.
- The input file contents are unchanged after settlement.
- `git diff --stat` shows only `bin/cli.js` and `tests/cli.test.js` touched.
