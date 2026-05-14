# S3-cli-ticket-assignment NOTES

## What failure mode does this fixture detect?

Priority-sensitive support ticket allocation with deterministic tie-breakers and
exact output-shape obligations. Bare implementations commonly process input
order, pick the first matching agent instead of the specified capacity/id
tie-breaker, or report rejected tickets in processing order.

## What pipeline phase(s) is this testing?

- **PLAN / RISK_PROBES**: must notice priority ordering, allocation tie-breakers,
  capacity mutation, duplicate id handling, and output-shape contracts.
- **IMPLEMENT**: must add a CLI command without broadening scope or adding deps.
- **VERIFY**: hidden oracles exercise compound behavior that simple unit tests
  often miss.

## Why can't another fixture cover this?

S2 checks inventory reservation against SKU stock. S3 changes the resource
shape to agent skill matching and capacity tie-breakers, so it catches a
different allocation failure while staying in shadow.

## When should this fixture be retired?

Retire or replace it if two consecutive measured runs show both bare and
solo_claude consistently satisfy priority ordering, agent tie-breakers,
duplicate id handling, and exact output shape without pair assistance.

## Calibration status

- `20260513-s3-ticket-headroom`: bare `33`, solo_claude `99`, headroom gate
  `FAIL` because solo exceeded the `80` ceiling and timed out. Treat S3 as a
  shadow control unless it is reworked to preserve solo_claude headroom.
