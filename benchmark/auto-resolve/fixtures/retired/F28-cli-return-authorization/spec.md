---
id: "F28-cli-return-authorization"
title: "Return authorization policy"
status: planned
complexity: high
depends-on: []
---

# F28 Return authorization policy

## Context

`bench-cli` currently has greeting and version commands only. The task:
add an `authorize-return` command that reads an order and return request JSON
file, applies return windows, nonreturnable items, defective-item fee waivers,
exchange credits, and emits one exact cents-based authorization JSON without
mutating the input.

Return approvals feed finance and warehouse workflows, so policy precedence and
integer-cent totals must be deterministic.

## Requirements

- [ ] `bench-cli authorize-return --input <path>` reads JSON shaped as `{ "today": "YYYY-MM-DD", "order": Order, "request": ReturnRequest }`.
- [ ] `order` has `{ "id": string, "purchased_at": "YYYY-MM-DD", "items": Array<OrderItem> }`.
- [ ] Each order item has `{ "sku": string, "qty": number, "unit_cents": number, "return_window_days": number, "restocking_fee_percent": number, "nonreturnable"?: boolean }`.
- [ ] `request` has `{ "id": string, "lines": Array<ReturnLine> }`.
- [ ] Each return line has `{ "sku": string, "qty": number, "reason": string, "condition": "sealed" | "opened", "resolution": "refund" | "exchange" }`.
- [ ] Validate before authorization: dates must parse as ISO dates, ids and SKUs must be non-empty strings, quantities and cents must be positive integers, percents must be non-negative numbers, order SKUs must be unique, requested SKUs must exist, and total requested quantity per SKU must not exceed ordered quantity.
- [ ] Invalid input exits `2`, writes exactly one JSON error object to stderr, and writes nothing to stdout.
- [ ] Business rejections do not exit non-zero. A line is rejected with reason `"nonreturnable"` when the order item has `nonreturnable: true`.
- [ ] A line is rejected with reason `"expired"` when `today` is more than `return_window_days` after `purchased_at`. The purchase day counts as day 0.
- [ ] Nonreturnable rejection takes precedence over expiration.
- [ ] A defective return (`reason === "defective"`) waives any restocking fee.
- [ ] Otherwise, restocking fee is `0` for `condition: "sealed"` and `Math.round(unit_cents * qty * restocking_fee_percent / 100)` for `condition: "opened"`.
- [ ] Approved `refund` lines contribute `gross_cents - restocking_fee_cents` to `refund_cents`.
- [ ] Approved `exchange` lines contribute `gross_cents - restocking_fee_cents` to `exchange_credit_cents` and `0` to `refund_cents`.
- [ ] On success, write exactly one JSON object to stdout and no stderr. Keys: `request_id`, `order_id`, `approved`, `rejected`, `refund_cents`, `exchange_credit_cents`, `restocking_fee_cents`.
- [ ] `approved` rows are ordered by request line order and have keys `sku`, `qty`, `resolution`, `gross_cents`, `restocking_fee_cents`, `refund_cents`, `exchange_credit_cents`.
- [ ] `rejected` rows are ordered by request line order and have keys `sku`, `qty`, `reason`.
- [ ] The command must not modify the input file.
- [ ] `tests/cli.test.js` is updated. Existing tests still pass AND at least two new tests cover one mixed approval/rejection authorization and one validation failure.

## Constraints

- **No new npm dependencies.**
- **No floating-money output.** All public amounts are integer cents.
- **No silent catches.** Invalid input and file-read failures must surface as JSON errors with exit `2`.
- **No extra stdout/stderr text** on the success path; downstream tooling parses stdout as JSON.
- **Touch only `bin/cli.js` and `tests/cli.test.js`.**

## Out of Scope

- Inventory mutation or restocking side effects.
- Payment processor calls.
- Partial-line approvals.
- Currencies, locales, or tax calculation.
- Touching `server/`, `web/`, or `tests/server.test.js`.

## Verification

- `node --test tests/cli.test.js` exits 0.
- A mixed request applies nonreturnable before expiration, waives defective-item fees, and separates refund cents from exchange credit cents.
- An opened non-defective refund charges `Math.round(gross * restocking_fee_percent / 100)`.
- Invalid over-requested quantity exits `2`, prints one JSON error object to stderr, and prints no stdout.
- The input file contents are unchanged after authorization.
- `git diff --stat` shows only `bin/cli.js` and `tests/cli.test.js` touched.
