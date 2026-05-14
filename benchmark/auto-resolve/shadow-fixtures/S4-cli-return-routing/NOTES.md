# S4-cli-return-routing NOTES

## What failure mode does this fixture detect?

Priority-sensitive return routing where policy decisions and mutable destination
capacity interact. Bare implementations commonly route in input order, decrement
capacity for rejected rows, apply the dispose/window rule after condition
branches, or emit rejected rows in processing order.

## What pipeline phase(s) is this testing?

- **PLAN / RISK_PROBES**: must notice priority ordering, condition/window rule
  order, capacity mutation, duplicate id handling, and output-shape contracts.
- **IMPLEMENT**: must add a CLI command without broadening scope or adding deps.
- **VERIFY**: hidden oracles exercise compound behavior that simple unit tests
  often miss.

## Why can't another fixture cover this?

S2 uses single-SKU inventory and S3 uses skill/capacity assignment. S4 adds a
policy-derived destination before capacity mutation, so it catches rule-order
and output-order failures that those fixtures do not.

## When should this fixture be retired?

Retire or replace it if two consecutive measured runs show both bare and
solo_claude consistently satisfy priority ordering, policy rule order, capacity
mutation, duplicate id handling, and exact output shape without pair assistance.

## Calibration status

- `20260513-s4-return-headroom`: bare `33`, solo_claude `98`, headroom gate
  `FAIL` because solo exceeded the `80` ceiling and timed out. Treat S4 as a
  shadow control unless it is reworked to preserve solo_claude headroom.
