---
id: "F27-cli-subscription-proration"
title: "Subscription invoice proration"
status: planned
complexity: high
depends-on: []
---

# F27 Subscription invoice proration

## Context

Add a subscription-invoice command that prorates plan changes across a billing
period, applies idempotent credits, reads plan and tax rules from
data/subscription-plans.json, and prints exact integer-cent invoice totals.

Subscription billing is money movement. Off-by-one date ranges, per-invoice
rounding instead of per-segment rounding, or duplicate credits can silently
undercharge or overcharge customers.

## Requirements

- [ ] `bench-cli subscription-invoice --input <path>` reads JSON shaped as `{ "customer_id": string, "state": string, "period": { "start": "YYYY-MM-DD", "end": "YYYY-MM-DD" }, "changes": Array<Change>, "credits": Array<Credit> }`.
- [ ] Plan monthly prices and state tax rates come from `data/subscription-plans.json`. Do not hardcode these values in the command implementation.
- [ ] Each change has `{ "date": "YYYY-MM-DD", "plan": string }`.
- [ ] Each credit has `{ "id": string, "amount_cents": number }`.
- [ ] Dates are interpreted as UTC calendar dates. The billing period start is inclusive and the end is exclusive.
- [ ] Validate before printing any invoice output: `customer_id` and `state` are non-empty strings, period dates are valid ISO dates, `period.start < period.end`, `changes` is a non-empty array, one change starts exactly on `period.start`, all change dates are within `[period.start, period.end)`, plans exist in the rules file, credit ids are non-empty strings, and credit amounts are positive integers.
- [ ] Unknown state exits `2`, writes exactly one JSON error object to stderr, and writes nothing to stdout.
- [ ] Identical duplicate credits, where both `id` and `amount_cents` match, are idempotent and apply only once.
- [ ] Credits with the same `id` but different `amount_cents` are conflicting duplicates. They exit `2` with exact error shape `{ "error": "conflicting_credit", "id": string }`, write it to stderr, and write nothing to stdout.
- [ ] Sort changes by `date` ascending. If two changes have the same `date`, the later entry in the input wins for that date.
- [ ] Build invoice segments from each effective change until the next change date or `period.end`. Omit zero-day superseded segments.
- [ ] `period_days` is the UTC calendar-day difference between `period.start` and `period.end`.
- [ ] Each segment amount is `Math.round(plan.monthly_cents * segment_days / period_days)`. Round each segment independently before summing.
- [ ] `subtotal_cents` is the sum of segment amounts.
- [ ] `credit_cents` is the sum of unique credit amounts, capped at `subtotal_cents`.
- [ ] Tax is computed after credits: `tax_cents = Math.round((subtotal_cents - credit_cents) * tax_rate)`.
- [ ] `total_cents = subtotal_cents - credit_cents + tax_cents`.
- [ ] On success, write exactly one JSON object to stdout and no stderr. Keys: `customer_id`, `period_days`, `subtotal_cents`, `credit_cents`, `tax_cents`, `total_cents`, `segments`.
- [ ] Each segment row has keys `plan`, `start`, `end`, `days`, and `amount_cents`, ordered by segment start date.
- [ ] `tests/cli.test.js` is updated. Existing tests still pass AND at least two new tests cover `subscription-invoice`: one successful prorated invoice and one validation failure.

## Constraints

- **No new npm dependencies.**
- **No floating-money output.** All public amounts are integer cents.
- **No silent catches.** Invalid input, unreadable files, and invalid rules must surface as JSON errors with exit `2`.
- **No extra stdout/stderr text** on the success path; downstream tooling parses stdout as JSON.
- **Touch only `bin/cli.js` and `tests/cli.test.js`.**

## Out of Scope

- Payment collection.
- Invoice persistence.
- Time zones beyond UTC calendar dates.
- Coupons, discounts, or taxes beyond the seeded rules file.
- Adding web UI or server routes.
- Touching `server/`, `web/`, or `tests/server.test.js`.

## Verification

- `node --test tests/cli.test.js` exits 0.
- A period with multiple plan changes computes UTC calendar-day segments using an inclusive start and exclusive end.
- Each segment is rounded independently before `subtotal_cents` is summed.
- Duplicate identical credits apply once, while conflicting duplicate credits fail with the exact JSON error.
- Tax is computed after credits and `total_cents` uses integer cents only.
- Changing `data/subscription-plans.json` prices or tax rates changes command output without code changes.
- `git diff --stat` shows only `bin/cli.js` and `tests/cli.test.js` touched (the rules seed comes from setup, not the arm).
