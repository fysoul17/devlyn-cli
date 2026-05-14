# S2-cli-inventory-reservation NOTES

## What failure mode does this fixture detect?

Priority-sensitive inventory mutation with exact output-shape obligations.
Bare implementations commonly process input order instead of priority order,
partially decrement stock for rejected orders, or emit a plausible but wrong
JSON shape.

## What pipeline phase(s) is this testing?

- **PLAN / RISK_PROBES**: must notice priority ordering, rollback, duplicate id,
  and response-shape contracts as executable risks.
- **IMPLEMENT**: must add a CLI command without broadening scope or adding deps.
- **VERIFY**: hidden oracles exercise compound behavior that simple unit tests
  often miss.

## Why can't another fixture cover this?

S1 checks enum parsing and UTF-8 output. F31/F32 cover similar high-risk
rollback ideas in golden/control space, but S2 keeps the experiment in shadow
so new inventory allocation variants can be tested before promotion.

## When should this fixture be retired?

Retire or replace it if two consecutive measured runs show both bare and
solo_claude consistently satisfy priority ordering, rollback, duplicate id
handling, and exact output shape without pair assistance.

## Calibration status

- `20260513-s2-inventory-headroom`: bare `33`, solo_claude `99`, headroom gate
  `FAIL` because solo exceeded the `80` ceiling and timed out. Treat S2 as a
  shadow control unless it is reworked to preserve solo_claude headroom.
