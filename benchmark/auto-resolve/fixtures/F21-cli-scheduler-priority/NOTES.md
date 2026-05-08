# F21 CLI scheduler priority

## Failure mode

This fixture detects implementations that pass simple scheduling tests while
missing interaction rules: global priority ordering, earliest-fit placement,
blocked-interval exclusion, half-open time boundaries, and deterministic output
ordering.

## Pipeline phase target

PLAN must preserve the ordering and interval invariants. IMPLEMENT must build a
small scheduling engine without adding dependencies. VERIFY should catch
counterexamples where local request order or naive overlap checks produce a
plausible but wrong schedule.

## Why existing fixtures do not cover it

F16 covers checkout arithmetic. F10/F11/F12/F15 cover server behavior. None
exercise a CLI algorithm where the correct result depends on sorting,
interval arithmetic, and output ordering at once.

## Retirement

Retire or replace when both bare and solo consistently exceed the headroom
thresholds, or if future fixtures cover the same interval-scheduling failure
mode with better discrimination.
