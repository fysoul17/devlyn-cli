---
id: "S5-cli-credit-grant-ledger"
title: "Add credit grant ledger command"
status: planned
complexity: high
depends-on: []
---

# S5 Add Credit Grant Ledger Command

## Context

Billing operations needs a deterministic CLI command that settles account
charges against expiring promotional credit grants. The command must combine
account isolation, date ordering, same-day priority, grant expiration, mutable
balances, duplicate id rejection, and exact machine-readable output.

## Requirements

- [ ] Add `settle-credits` to `bin/cli.js`.
- [ ] Accept `--grants <json>` as a JSON array of grant objects. Each grant has
  keys `id`, `account`, `cents`, and `expires_on`.
- [ ] Accept `--charges <json>` as a JSON array of charge objects. Each charge
  has keys `id`, `account`, `cents`, `occurred_on`, and `priority`.
- [ ] Accept `--as-of <YYYY-MM-DD>` as the ledger close date.
- [ ] Before settling any charge, duplicate charge ids are invalid input: exit `2`, write exactly one JSON error object `{ "error": "duplicate_charge_id", "id": string }` to stderr, and write no stdout.
- [ ] Process charges globally by `occurred_on` ascending, then `priority` descending, then original input order ascending.
- [ ] A grant is usable for a charge only when it belongs to the same `account`, has positive remaining `cents`, and `expires_on` is greater than or equal to the charge's `occurred_on`.
- [ ] For each charge, consume usable grants by `expires_on` ascending, then grant `id` ascending, until the charge is fully covered or no usable grant remains.
- [ ] Consuming a grant decrements that grant's remaining `cents` immediately; later charges see the reduced balance.
- [ ] Each `settled` row is ordered by processing order and has keys `id`, `covered_cents`, `uncovered_cents`, and `grants`.
- [ ] Each row's `grants` array is ordered by actual consumption order. Each
  item has keys `id` and `cents`.
- [ ] `balances` is ordered by grant `id` ascending. Each row has keys `id` and `remaining_cents`.
- [ ] `expired` is ordered by grant `id` ascending and includes grants with positive remaining `cents` whose `expires_on` is less than `--as-of`. Each row has keys `id` and `remaining_cents`.
- [ ] On success, write exactly one JSON object to stdout and no stderr. Keys: `settled`, `balances`, `expired`.

## Constraints

- Use only Node.js built-ins; add no npm dependencies.
- Touch only `bin/cli.js` and `tests/cli.test.js`.
- Do not silently catch JSON parse or validation errors. Surface invalid input
  as a user-visible error with nonzero exit.
- Do not persist grant balances between command invocations.

## Out of Scope

- Reading input from files.
- Taxes, invoices, refunds, currency conversion, or account creation.
- Changing `hello`, `version`, server routes, or package metadata.

## Verification

- `node --test tests/cli.test.js` passes.
- `node "$BENCH_FIXTURE_DIR/verifiers/credit-ledger-priority.js"` prints
  `{"ok":true}`.
- `node "$BENCH_FIXTURE_DIR/verifiers/duplicate-charge-error.js"` prints
  `{"ok":true}`.
- Solo-headroom hypothesis: solo_claude is expected to miss mutable grant balances across priority/date-ordered charges; observable command `node "$BENCH_FIXTURE_DIR/verifiers/credit-ledger-priority.js"` exposes the miss.
