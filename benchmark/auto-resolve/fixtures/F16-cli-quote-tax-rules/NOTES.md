# F16 CLI quote tax rules

## Failure mode

This fixture detects checkout implementations that pass visible happy-path
tests while missing product-grade invariants: duplicate-SKU aggregation,
combined stock validation, externalized pricing rules, exact JSON output,
and integer-cent tax/discount/shipping order.

## Pipeline phase target

PLAN must preserve calculation order and validation invariants. BUILD must
implement constrained arithmetic without adding dependencies. VERIFY should
catch edge cases that a shallow implementation or shallow tests miss.

## Why existing fixtures do not cover it

F1/F2 test CLI shape, but not business-rule arithmetic. F10/F11/F12 test
server behavior and persistence. F15 tests review behavior. None combine
hidden product math, exact machine output, and source-of-truth pricing.

## Retirement

Retire or replace this fixture if both bare and solo consistently score
above the headroom thresholds, or if future fixtures cover the same
calculation-order and hidden-verifier failure modes with better signal.
