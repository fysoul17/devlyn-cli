---
id: "F22-cli-ledger-close"
title: "Ledger close command"
status: planned
complexity: high
depends-on: []
---

# F22 Ledger close command

## Context

Add a `bench-cli ledger-close --input <path>` command that reads account
opening balances and transaction events, applies chronological idempotent
ledger rules, rejects conflicting duplicate transaction ids, and prints exact
closing balances and audit counts.

The command is used in finance-style reconciliation. Determinism matters more
than convenience: every amount is integer cents, every accepted event is applied
once, and duplicate ids must not silently corrupt balances.

## Requirements

- [ ] `bench-cli ledger-close --input <path>` reads JSON shaped as `{ "accounts": Array<Account>, "transactions": Array<Transaction> }`.
- [ ] Each account has `{ "id": string, "currency": string, "opening_cents": number }`.
- [ ] Each transaction has `{ "id": string, "account": string, "currency": string, "kind": "debit" | "credit", "amount_cents": number, "occurred_at": string }`.
- [ ] Validate before applying balances: account ids are unique, transaction ids are non-empty strings, account references exist, currencies match the referenced account, `amount_cents` is a positive integer, and `kind` is either `debit` or `credit`.
- [ ] Conflicting duplicate transaction ids are invalid input. A duplicate id is conflicting when any field other than `id` differs from the first transaction with that id.
- [ ] Exact duplicate transactions are idempotent: apply the first copy once and count later exact copies in `duplicates_ignored`.
- [ ] Apply accepted unique transactions in chronological order by `occurred_at` ascending, then `id` ascending.
- [ ] A `debit` subtracts `amount_cents`; a `credit` adds `amount_cents`.
- [ ] Negative closing balances are allowed and must be reported, not rejected.
- [ ] Invalid input exits `2`, writes exactly one JSON error object to stderr, and writes nothing to stdout.
- [ ] Conflicting duplicate transaction ids use the exact stderr JSON shape `{ "error": "conflicting_duplicate", "id": string }`.
- [ ] On success, write exactly one JSON object to stdout and no stderr. Keys: `accounts`, `applied_count`, `duplicates_ignored`.
- [ ] Output `accounts` sorted by account id ascending. Each row has keys `id`, `currency`, `closing_cents`.
- [ ] `tests/cli.test.js` is updated. Existing tests still pass AND at least two ledger tests cover one success case and one invalid-input case.

## Constraints

- **No new npm dependencies.**
- **No floating-money output.** All amounts are integer cents.
- **No silent catches.** Invalid input and file-read failures must surface as JSON errors with exit `2`.
- **No mutation of the input file.**
- **No extra stdout/stderr text** on the success path; downstream tooling parses stdout as JSON.
- **Touch only `bin/cli.js` and `tests/cli.test.js`.**
- **Lifecycle note.** The harness's DOCS phase flips this spec's frontmatter `status` after implementation completes — that is benchmark lifecycle bookkeeping, not a scope violation.

## Out of Scope

- Exchange rates.
- Decimal currency parsing.
- Persistence or database writes.
- Account creation from transactions.
- Touching `server/`, `web/`, or `tests/server.test.js`.

## Verification

- `node --test tests/cli.test.js` exits 0.
- Exact duplicate transactions are counted in `duplicates_ignored` and applied once.
- Conflicting duplicate transaction ids exit `2`, write one JSON error to stderr, and write no stdout.
- Conflicting duplicate transaction ids use the exact stderr JSON shape `{ "error": "conflicting_duplicate", "id": string }`.
- Transactions are applied in chronological order by `occurred_at` ascending, then `id` ascending.
- Negative closing balances are allowed and appear in output.
- `git diff --stat` shows only `bin/cli.js` and `tests/cli.test.js` touched.
