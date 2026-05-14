# F31 CLI seat rebalance

## Failure mode

This fixture detects implementations that pass simple entitlement updates while
missing the interaction between priority ordering, transfer rollback, rejected
row ordering, and exact machine-readable error handling.

## Pipeline phase target

PLAN must preserve the ordering distinction between processing order and
rejected-output order. IMPLEMENT must keep transfer mutations all-or-nothing.
VERIFY should build adversarial cases where a later high-priority transfer
changes the outcome of an earlier low-priority reserve, and where a failed
transfer would corrupt state if mutations are applied too early.

## Why existing fixtures do not cover it

F21 covers scheduling priority and blocked intervals. F23 covers inventory
allocation rollback. F25 covers checkout calculation order. This fixture covers
account entitlement reconciliation with a different state shape and a duplicate
event-id hard error.

## Retirement

Headroom run `20260512-f31-seat-rebalance-headroom` rejected this fixture as
pair-lift evidence: bare scored 33 but carried judge/result/verify
disqualifiers, and solo_claude scored 98 with all 3 verification commands
passing. It should remain a control fixture unless reworked to lower the solo
ceiling.

Retire or replace this fixture if either `bare` or `solo_claude` consistently
reaches ceiling, or if a later fixture covers priority event processing plus
all-or-nothing transfer rollback with cleaner full-pipeline lift.
