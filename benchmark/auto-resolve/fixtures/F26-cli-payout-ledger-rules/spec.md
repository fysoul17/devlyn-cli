---
id: "F26-cli-payout-ledger-rules"
title: "Payout command with ledger rules"
status: planned
complexity: high
depends-on: []
---

# F26 Payout command with ledger rules

## Context

`bench-cli` currently has greeting and version commands only. The task:
add a `payout` command that reads ledger events from a JSON file, applies
idempotent event handling and payout rules from `data/payout-rules.json`, and
prints exact merchant payout totals with processing fees, dispute fees,
reserves, and payouts in integer cents.

This is settlement math, so duplicate events must not corrupt totals and every
public amount must be integer cents.

## Requirements

- [ ] `bench-cli payout --input <path>` reads JSON shaped as `{ "events": [{ "id": string, "merchant_id": string, "type": "charge" | "refund" | "dispute", "amount_cents": number }] }`.
- [ ] Processing fee percent, fixed fee, dispute fee, reserve percent, and minimum payout threshold come from `data/payout-rules.json`. Do not hardcode these values in the command implementation.
- [ ] Events with the same `id` and identical JSON content are idempotent duplicates and are applied only once.
- [ ] Events with the same `id` but different JSON content are conflicting duplicates. Validation happens before payout totals are printed, exits `2`, writes exactly one JSON error object to stderr, and writes no stdout.
- [ ] Conflicting duplicate events use exact error shape `{ "error": "conflicting_duplicate", "id": string }`.
- [ ] Unknown event type, missing `merchant_id`, missing `id`, non-positive or non-integer `amount_cents`, missing `events`, invalid JSON, or unreadable input exits `2` and writes exactly one JSON error object to stderr.
- [ ] Merchant rows are emitted in first-seen merchant order after idempotent duplicate removal.
- [ ] A `charge` increases `gross_charge_cents` and adds a processing fee of `Math.round(amount_cents * processing_fee_percent / 100) + fixed_fee_cents`.
- [ ] A `refund` increases `refund_cents`. Refunds do not reverse processing fees.
- [ ] A `dispute` increases `dispute_cents` and adds `dispute_fee_cents` from the rules for each dispute event.
- [ ] For each merchant, compute `net_before_reserve = gross_charge_cents - refund_cents - dispute_cents - processing_fee_cents - dispute_fee_cents`.
- [ ] `reserve_cents` is `Math.round(net_before_reserve * reserve_percent / 100)` when `net_before_reserve > 0`; otherwise `0`.
- [ ] `payout_cents = net_before_reserve - reserve_cents`.
- [ ] If `0 < payout_cents < minimum_payout_cents`, keep the merchant row but set `payout_cents` to `0` and add the original positive amount into `reserve_cents`.
- [ ] On success, write exactly one JSON object to stdout and no stderr. Keys: `total_payout_cents`, `total_processing_fee_cents`, `total_dispute_fee_cents`, `total_reserve_cents`, `merchants`.
- [ ] Each merchant row has keys `merchant_id`, `gross_charge_cents`, `refund_cents`, `dispute_cents`, `processing_fee_cents`, `dispute_fee_cents`, `reserve_cents`, `payout_cents`.
- [ ] `tests/cli.test.js` is updated. Existing tests still pass AND at least two new tests cover `payout`: one successful payout and one validation failure.

## Constraints

- **No new npm dependencies.**
- **No floating-money output.** All public amounts are integer cents.
- **No silent catches.** If parsing or file reading fails, emit a visible JSON error to stderr and exit `2`.
- **No extra stdout/stderr text** on the success path; downstream tooling parses stdout as JSON.

## Out of Scope

- Persisting payouts or mutating a ledger.
- Currency conversion.
- Time zones, reporting periods, or settlement dates.
- Adding web UI or server routes.
- Touching `server/`, `web/`, or `tests/server.test.js`.

## Verification

- `node --test tests/cli.test.js` exits 0.
- Identical duplicate event IDs are applied only once before merchant totals are computed.
- A payout with charges, a refund, and a dispute computes processing fees, dispute fees, reserves, merchant payouts, and top-level totals exactly.
- Processing fees apply to charges only; refunds do not reverse processing fees.
- Dispute events subtract the dispute amount and add one dispute fee per dispute event.
- Merchant rows preserve first-seen merchant order after idempotent duplicate removal.
- A conflicting duplicate exits `2`, prints one JSON error to stderr, and prints no stdout.
- The conflicting duplicate error object includes `error` and `id`.
- Changing `data/payout-rules.json` fee or reserve settings changes command output without code changes.
- `git diff --stat` shows only `bin/cli.js` and `tests/cli.test.js` touched (the payout rules seed comes from setup, not the arm).
