# F23 CLI fulfillment wave

## Failure mode

This fixture detects plausible allocators that pass simple order tests while
missing production-critical interactions: priority before input order,
all-or-nothing rollback, FEFO lot ordering, distance tie-breaks, and
single-warehouse constraints.

## Pipeline phase target

PLAN must separate validation, order processing, tentative allocation, rollback,
and final output sorting. IMPLEMENT must avoid partial mutation leaks. VERIFY
should construct counterexamples where a partial allocation looks locally valid
but corrupts later orders.

## Why existing fixtures do not cover it

F21 covers interval scheduling. F16 covers quote arithmetic. F22 was too easy
for bare in the first calibration run. This fixture targets allocation rollback
and inventory consumption across multiple dimensions.

## Retirement

Retire or replace if both bare and solo consistently exceed the headroom
thresholds, or if a later logistics fixture provides the same rollback and
allocation-order signal with less wall time.
