# F27 CLI subscription proration

## Failure mode

This fixture detects billing implementations that look correct on one happy
path but mishandle date boundaries, per-segment rounding, duplicate credits, or
hardcode plan and tax rules instead of reading the seeded data file.

## Pipeline phase target

PLAN must separate input validation, period segmentation, per-segment proration,
credit de-duplication, tax calculation, and output formatting. VERIFY should
probe date boundary and data-source variants because a small example can pass
while production invoices are off by one day or one cent.

## Why existing fixtures do not cover it

F25 covers cart promotions and F26 covers payout ledger events. This fixture
adds subscription billing proration: effective-date segmentation, period-day
denominators, credit idempotency, and tax after credits. It was intended to
cover a pair-risk-probe gap, but the first real headroom smoke showed the
visible contract was explicit enough for `solo_claude` to solve cleanly.

## Retirement

Retire or replace if both bare and solo consistently exceed the headroom
thresholds, or if a later billing fixture provides the same proration and
idempotent-credit signal with lower wall time.

## Measurement notes

- `20260511-f27-headroom-smoke-061401`: headroom FAIL. Judge scores were
  bare 33 / solo_claude 94 (`solo_over_bare` +61). Bare passed 1 of 3
  verification commands; solo passed 3 of 3 with terminal `PASS`.
- Do not spend a pair arm on this fixture in its current shape. It needs either
  a harder visible contract that solo misses without pair probes, or rotation
  out of the pair-candidate set.
