---
id: "F27-cli-gift-card-redemption"
title: "Gift card command with redemption rules"
status: planned
complexity: high
depends-on: []
---

# F27 Gift card command with redemption rules

## Context

`bench-cli` currently has greeting and version commands only. The task:
add a `gift-card` command that reads cart lines and gift-card redemption
requests from a JSON file, prices products from `data/gift-cards.json`, and
prints exact gift-card application totals in integer cents.

Gift-card balances are money-like state, so duplicate line and redemption
requests must be combined before validation. The command only calculates the
result; it does not persist balance changes.

## Requirements

- [ ] `bench-cli gift-card --input <path>` reads JSON shaped as `{ "order_id": string, "lines": [{ "sku": string, "qty": number }], "redeems": [{ "card_id": string, "amount_cents": number }] }`.
- [ ] Product prices, gift-card balances, and gift-card active flags come from `data/gift-cards.json`. Do not hardcode product prices, card balances, or active flags in the command implementation.
- [ ] Combine duplicate SKUs before computing line totals. The output `items` array must contain one row per SKU in first-seen order.
- [ ] Combine duplicate `card_id` redemption requests before validating balances and before computing remaining balances. The output `redemptions` array must contain one row per card in first-seen order.
- [ ] Validation happens before any result is printed. Invalid JSON, missing `lines`, missing `redeems`, unknown SKU, unknown card, inactive card, non-positive or non-integer `qty`, non-positive or non-integer `amount_cents`, missing `order_id`, combined card redemption over balance, or total redemption over subtotal exits `2` and writes exactly one JSON error object to stderr.
- [ ] Combined card redemption over balance uses exact error shape `{ "error": "insufficient_balance", "card_id": string, "available_cents": number, "requested_cents": number }`.
- [ ] Total redemption over subtotal uses exact error shape `{ "error": "redemption_exceeds_subtotal", "subtotal_cents": number, "requested_cents": number }`.
- [ ] On success, write exactly one JSON object to stdout and no stderr. Keys: `order_id`, `subtotal_cents`, `gift_card_applied_cents`, `amount_due_cents`, `items`, `redemptions`.
- [ ] Each output item row has keys `sku`, `qty`, `line_cents`. `line_cents` is `unit_cents * combined_qty`.
- [ ] Each redemption row has keys `card_id`, `applied_cents`, `remaining_balance_cents`. `remaining_balance_cents` is the starting balance from `data/gift-cards.json` minus the combined requested redemption for that card.
- [ ] `gift_card_applied_cents` is the sum of combined redemption amounts.
- [ ] `amount_due_cents = subtotal_cents - gift_card_applied_cents`.
- [ ] `tests/cli.test.js` is updated. Existing tests still pass AND at least two new tests cover `gift-card`: one successful redemption and one validation failure.

## Constraints

- **No new npm dependencies.**
- **No floating-money output.** All public amounts are integer cents.
- **No silent catches.** If parsing or file reading fails, emit a visible JSON error to stderr and exit `2`.
- **No extra stdout/stderr text** on the success path; downstream tooling parses stdout as JSON.
- **Lifecycle note.** The harness's DOCS phase flips this spec's frontmatter `status` after implementation completes — that is benchmark lifecycle bookkeeping, not a scope violation.

## Out of Scope

- Persisting changed gift-card balances.
- Taxes, shipping, coupons, or currencies beyond integer cents.
- Adding server routes or web UI.
- Touching `server/`, `web/`, or `tests/server.test.js`.

## Verification

- `node --test tests/cli.test.js` exits 0.
- Duplicate SKUs are combined before line totals are computed.
- Duplicate `card_id` redemption rows are combined before balance validation.
- A successful redemption emits exact item rows, redemption rows, applied total, and amount due.
- Changing `data/gift-cards.json` product prices or card balances changes command output without code changes.
- A combined card redemption over balance exits `2`, prints one JSON error to stderr, and prints no stdout.
- The insufficient balance error object includes `error`, `card_id`, `available_cents`, and `requested_cents`.
- `git diff --stat` shows only `bin/cli.js` and `tests/cli.test.js` touched (the gift-card seed comes from setup, not the arm).
