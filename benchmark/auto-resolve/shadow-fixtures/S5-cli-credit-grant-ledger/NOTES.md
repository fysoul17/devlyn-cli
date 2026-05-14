# S5-cli-credit-grant-ledger NOTES

## What failure mode does this fixture detect?

Billing credit settlement where date ordering, same-day priority, grant
expiration, account isolation, and mutable grant balances interact. Bare or
single-pass implementations commonly process input order, use expired grants,
let one account consume another account's grant, or compute balances without
respecting earlier charge consumption.

## What pipeline phase(s) is this testing?

- **PLAN / RISK_PROBES**: must notice charge ordering, expiration boundaries,
  grant consumption order, account scoping, mutation, duplicate id handling, and
  exact output-shape contracts.
- **IMPLEMENT**: must add a CLI command without broadening scope or adding deps.
- **VERIFY**: hidden oracles exercise compound ledger behavior that simple unit
  tests often miss.

## Why can't another fixture cover this?

S2 covers inventory reservation, S3 covers agent assignment, and S4 covers return
routing. S5 adds money-like credit balances with date-bounded grant eligibility,
which catches a different class of ledger mutation and ordering failures.

## When should this fixture be retired?

Retire or replace it if two consecutive measured runs show both bare and
solo_claude consistently satisfy charge ordering, account scoping, expiration
boundaries, mutable grant balances, duplicate id handling, and exact output
shape without pair assistance.

## Calibration status

- `20260513-s5-credit-headroom`: bare `33`, solo_claude `98`, headroom gate
  `FAIL` because solo exceeded the `80` ceiling and timed out. Treat S5 as a
  shadow control unless it is reworked to preserve solo_claude headroom.
