---
id: "F32-cli-subscription-renewal"
title: "Subscription renewal command"
status: planned
complexity: high
depends-on: []
---

# F32 Subscription renewal command

## Context

`bench-cli` currently has greeting and version commands only. The task:
add a `renew-subscriptions` command that applies subscription renewal requests,
uses expiring customer credits in deterministic order, rolls back credits when a
renewal cannot be paid, and prints exact invoice, rejected, and remaining-credit
rows.

This is billing reconciliation. Downstream finance tools parse stdout as JSON,
so field names, error objects, and row shapes are part of the contract.

## Requirements

- [ ] `bench-cli renew-subscriptions --input <path>` reads JSON shaped as `{ "as_of": string, "plans": [plan], "customers": [customer], "credits": [credit], "renewals": [renewal] }`.
- [ ] Each plan has keys `id`, `monthly_cents`, `included_seats`, and `overage_cents`.
- [ ] Each customer has keys `id`, `plan`, and `active`.
- [ ] Each credit has keys `id`, `customer`, `cents`, and `expires_at`.
- [ ] Each renewal has keys `id`, `customer`, `seats`, `months`, `priority`, `requested_at`, and `max_due_cents`.
- [ ] Before processing any renewal, duplicate renewal ids are invalid input: exit `2`, write exactly one JSON error object `{ "error": "duplicate_renewal_id", "id": string }` to stderr, and write no stdout.
- [ ] Before processing any renewal, all cents, seat, month, and priority fields must be integers; `monthly_cents`, `overage_cents`, `included_seats`, `cents`, `seats`, and `months` must be non-negative except `seats` and `months` must be positive. Invalid input exits `2` with one JSON error object and no stdout.
- [ ] Process renewals globally by `priority` descending, then `requested_at` ascending, then `id` ascending.
- [ ] A renewal rejects with reason `unknown_customer` when the customer does not exist, `inactive_customer` when the customer is inactive, and `unknown_plan` when the customer's plan does not exist.
- [ ] Renewal subtotal is `(plan.monthly_cents + max(0, seats - plan.included_seats) * plan.overage_cents) * months`.
- [ ] Usable credits are credits for the same customer with `expires_at >= as_of` and `cents > 0`, consumed by `expires_at` ascending, then `id` ascending.
- [ ] A renewal accepts only when `subtotal_cents - credit_applied_cents <= max_due_cents`.
- [ ] A rejected renewal with reason `payment_required` must not consume any credits, even if it tentatively applied credits before discovering the remaining due exceeded `max_due_cents`.
- [ ] On success, write exactly one JSON object to stdout and no stderr. Keys: `invoices`, `rejected`, `remaining_credits`.
- [ ] `invoices` is ordered in processing order. Each row has keys `id`, `customer`, `subtotal_cents`, `credit_applied_cents`, `due_cents`, and `credits`.
- [ ] Each invoice `credits` row has keys `id` and `applied_cents`, ordered by the credit consumption order.
- [ ] `rejected` is ordered in the original input renewal order. Each row has keys `id` and `reason`.
- [ ] `remaining_credits` includes only non-expired credits with positive cents after accepted renewals, sorted by `customer`, then `expires_at`, then `id`. Each row has keys `id`, `customer`, `cents`, and `expires_at`.
- [ ] `tests/cli.test.js` is updated. Existing tests still pass and at least two new tests cover `renew-subscriptions`: one successful priority/rollback scenario and one validation failure.

## Constraints

- **No new npm dependencies.**
- **No floating money output.** All public amounts are integer cents.
- **No hidden mutable global state.** The command must derive output only from the input JSON for that invocation.
- **No silent catches.** Parse and file-read failures must emit a visible JSON error to stderr and exit `2`.
- **No extra stdout/stderr text** on the success path; downstream tooling parses stdout as JSON.

## Out of Scope

- Persisting renewal state between command invocations.
- Adding invoices to a database or writing files.
- Adding currencies, payment gateways, or tax rules.
- Adding web UI or server routes.
- Touching `server/`, `web/`, or `tests/server.test.js`.

## Verification

- `node --test tests/cli.test.js` exits 0.
- A later high-priority renewal is processed before an earlier low-priority renewal, and the low-priority renewal can lose usable credits because of that ordering.
- A rejected `payment_required` renewal leaves all tentatively applied credits available for later renewals.
- Credits are consumed by `expires_at` ascending, then `id` ascending, and expired or zero-cent credits are absent from `remaining_credits`.
- `rejected` rows are reported in the original input renewal order, even though processing order is priority based.
- Duplicate renewal ids exit `2`, print exactly `{ "error": "duplicate_renewal_id", "id": string }` to stderr, and print no stdout.
- Output row key names and nested `credits` key names match the visible spec exactly, with no aliased or extra keys.
- `git diff --stat` shows only `bin/cli.js` and `tests/cli.test.js` touched.
- Solo-headroom hypothesis: solo_claude is expected to miss payment-required credit rollback or expiring-credit consumption order; observable command `node "$BENCH_FIXTURE_DIR/verifiers/priority-credit-rollback.js"` exposes the miss.
