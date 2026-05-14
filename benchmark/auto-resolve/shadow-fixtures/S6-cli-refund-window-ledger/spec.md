---
id: "S6-cli-refund-window-ledger"
title: "Add refund window ledger command"
status: planned
complexity: high
depends-on: []
---

# S6 Add Refund Window Ledger Command

## Context

Finance operations needs a deterministic CLI command that settles refund
requests against original orders. The command must combine category refund
windows, priority ordering, cumulative per-order refundable balances, duplicate
id rejection, and exact machine-readable output.

## Requirements

- [ ] Add `settle-refunds` to `bin/cli.js`.
- [ ] Accept `--policies <json>` as a JSON object whose keys are category names and whose values have keys `refund_window_days` and `restocking_fee_cents`.
- [ ] Accept `--orders <json>` as a JSON array of order objects. Each order has keys `id`, `category`, `paid_cents`, `purchased_on`, and `fulfilled`.
- [ ] Accept `--refunds <json>` as a JSON array of refund request objects. Each refund has keys `id`, `order`, `cents`, `priority`, and `requested_on`.
- [ ] Before settling any refund, duplicate refund ids are invalid input: exit `2`, write exactly one JSON error object `{ "error": "duplicate_refund_id", "id": string }` to stderr, and write no stdout.
- [ ] Process refund requests globally by `priority` descending, then `requested_on` ascending, then original input order ascending.
- [ ] A refund rejects with reason `unknown_order` when the order does not exist.
- [ ] A refund rejects with reason `unfulfilled_order` when the order exists but `fulfilled` is not `true`.
- [ ] A refund rejects with reason `unknown_policy` when the order category has no policy.
- [ ] A refund rejects with reason `window_expired` when `requested_on` is more than `refund_window_days` after `purchased_on`.
- [ ] A refund accepts only when the order's remaining refundable cents is at least the requested `cents`.
- [ ] A rejected refund with reason `over_refund` must not change that order's remaining refundable cents.
- [ ] For each accepted refund, decrement that order's remaining refundable cents by the requested `cents`.
- [ ] For each accepted refund, compute `fee_cents` as the category policy's `restocking_fee_cents` capped at the requested `cents`, and compute `net_cents = cents - fee_cents`.
- [ ] `approved` is ordered in processing order. Each row has keys `id`, `order`, `refund_cents`, `fee_cents`, and `net_cents`.
- [ ] `rejected` is ordered in the original input refund order. Each row has keys `id`, `reason`.
- [ ] `orders` is ordered by order id ascending. Each row has keys `id` and `remaining_refundable_cents`.
- [ ] On success, write exactly one JSON object to stdout and no stderr. Keys: `approved`, `rejected`, `orders`.

## Constraints

- Use only Node.js built-ins; add no npm dependencies.
- Touch only `bin/cli.js` and `tests/cli.test.js`.
- Do not silently catch JSON parse or validation errors. Surface invalid input as a user-visible error with nonzero exit.
- Do not persist refund balances between command invocations.
- All public money amounts are integer cents.

## Out of Scope

- Reading input from files.
- Taxes, payment gateway calls, currency conversion, or store-credit issuance.
- Partial approval of a single refund request.
- Changing `hello`, `version`, server routes, or package metadata.

## Verification

- `node --test tests/cli.test.js` passes.
- `node "$BENCH_FIXTURE_DIR/verifiers/priority-refund-ledger.js"` prints `{"ok":true}`.
- `node "$BENCH_FIXTURE_DIR/verifiers/duplicate-refund-error.js"` prints `{"ok":true}`.
- Solo-headroom hypothesis: solo_claude is expected to miss cumulative remaining refundable cents or original-order rejected rows under priority-ordered refund settlement; observable command `node "$BENCH_FIXTURE_DIR/verifiers/priority-refund-ledger.js"` exposes the miss.
