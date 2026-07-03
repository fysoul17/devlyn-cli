---
id: "F34-cli-settle-inflight"
title: "Settle command with in-flight authorizations"
status: planned
complexity: high
depends-on: []
---

# F34 Settle command with in-flight authorizations

## Context

`bench-cli` gets a `settle` command that previews a batch of credit
transfers between accounts. Every transfer must be authorized through the
seeded gateway module before settlement. The gateway is slow, so
authorizations for different transfers must be able to overlap — but the
ledger math must stay exact and order-stable.

## Requirements

- [ ] `bench-cli settle --input <path>` reads JSON shaped as `{ "transfers": [{ "id": string, "from": string, "to": string, "amount": number }] }`.
- [ ] Account starting balances come from `data/accounts.json`. The command must not modify `data/accounts.json`.
- [ ] Every transfer is authorized by calling `authorize(transfer)` from `lib/gateway.js` exactly once per transfer. Do not modify, reimplement, or bypass `lib/gateway.js`.
- [ ] Authorizations must be able to overlap: while one transfer's authorization is awaited, later transfers' authorizations must be able to start. The seeded gateway records the maximum number of authorizations in flight at once in `data/gateway-stats.json`; settling the six-transfer sample in `## Verification` must record `high_water` of at least `3`.
- [ ] Regardless of the order in which authorizations complete, transfers settle in file order, each exactly once. A transfer is accepted when the sender's balance — after all earlier-in-file accepted transfers — covers the amount; otherwise it is rejected.
- [ ] Each rejected transfer produces exact row shape `{ "id": string, "error": "insufficient_funds", "available": number, "requested": number }`, where `available` is the sender's balance at that transfer's turn in file order.
- [ ] Validation happens before any authorization starts. Invalid JSON, missing or non-string `id`/`from`/`to`, unknown account, or non-positive or non-integer `amount` exits `2` and writes exactly one JSON error object to stderr with shape `{ "error": "invalid_input", "reason": string }`, printing nothing to stdout.
- [ ] On success, write exactly one JSON object to stdout and no stderr. Keys: `accepted` (array of transfer ids in file order), `rejected` (array of rejected rows in file order), `balances` (object with the final balance of every account in `data/accounts.json`).
- [ ] `tests/cli.test.js` is updated. Existing tests still pass AND at least two new tests cover `settle`: one where a later-in-file transfer depends on an earlier-in-file transfer's settlement, and one rejection.

## Constraints

- **No new npm dependencies.**
- **No silent catches.** If parsing or file reading fails, emit a visible JSON error to stderr and exit `2`.
- **No extra stdout/stderr text** on the success path; downstream tooling parses stdout as JSON.
- Balances are integer credits; no floating-point money.

## Out of Scope

- Persisting settlement results (settle is a preview; `data/accounts.json` stays untouched).
- Changing server routes, web UI, or `lib/gateway.js`.
- Retry, timeout, or failure handling for the gateway beyond what it returns.
- Touching `server/`, `web/`, or `tests/server.test.js`.

## Verification

- `node --test tests/cli.test.js` exits 0.
- Settling a six-transfer file where authorizations complete in reverse file order still yields file-order settlement: exact `accepted`, `rejected`, and `balances` values.
- `data/gateway-stats.json` shows `calls` equal to the number of transfers and `high_water` of at least `3`.
- An unknown account exits `2`, prints one JSON error to stderr, and prints no stdout.
- `git diff --stat` shows only `bin/cli.js` and `tests/cli.test.js` touched (accounts and gateway are seeded by setup, not the arm).

## Solo-headroom hypothesis

A capable solo_claude baseline is expected to miss the decoupling of
authorization completion order from file-order settlement — applying
balance changes as authorizations resolve instead of at each transfer's
file-order turn; observable command
`node "$BENCH_FIXTURE_DIR/verifiers/ordered-settlement.js"` exposes the miss.
