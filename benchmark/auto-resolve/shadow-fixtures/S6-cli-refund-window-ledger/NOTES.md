# S6-cli-refund-window-ledger NOTES

## What failure mode does this fixture detect?

Refund settlement where category windows, priority ordering, mutable per-order
remaining refundable cents, fee calculation, and exact output-shape obligations
interact. Bare or single-pass implementations commonly process input order,
forget that an earlier high-priority refund consumes later refundable balance,
or report rejected rows in processing order.

## What pipeline phase(s) is this testing?

- **PLAN / RISK_PROBES**: must notice priority ordering, date-window policy,
  mutable per-order balances, duplicate id handling, and output-shape contracts.
- **IMPLEMENT**: must add a CLI command without broadening scope or adding deps.
- **VERIFY**: hidden oracles exercise compound refund ledger behavior that
  simple unit tests often miss.

## Why can't another fixture cover this?

S5 covers credit grant consumption by charge date. S6 flips the money-like
mutation to customer refunds, where priority ordering and refund-window policy
jointly decide whether a later input row consumes the balance first.

## When should this fixture be retired?

Retire or replace it if two consecutive measured runs show both bare and
solo_claude consistently satisfy priority ordering, refund-window policy,
cumulative refundable balances, duplicate id handling, and exact output shape
without pair assistance.

## Calibration status

- `20260514-s6-refund-headroom-v1`: bare `33`, solo_claude `98`, headroom
  gate `FAIL` because solo exceeded the `80` ceiling and timed out. Treat S6 as
  a shadow control unless it is reworked to preserve solo_claude headroom.
