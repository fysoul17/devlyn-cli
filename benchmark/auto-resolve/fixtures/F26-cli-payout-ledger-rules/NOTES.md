# F26 CLI payout ledger rules

## Failure mode

This fixture detects settlement implementations that pass simple payout tests
while mishandling idempotent events, conflicting duplicates, fee ordering,
dispute fees, reserves, minimum payout holds, and top-level totals.

## Pipeline phase target

PLAN must preserve event deduplication and arithmetic order. IMPLEMENT must keep
fee/reserve math in integer cents and avoid hardcoded rules. VERIFY should build
adversarial ledger examples with repeated IDs, refunds, disputes, and reserves.

## Why existing fixtures do not cover it

F16 covers quote math and F25 covers cart promotions, but neither has ledger
idempotency or conflicting duplicate events. F21/F23 cover scheduling and
allocation ordering, not payout ledger arithmetic.

## Measurement status

Headroom run `20260508-f26-headroom` rejected F26 as full-pipeline pair-lift
evidence: bare scored 25, but `solo_claude` scored 98 and passed all 4
verification commands, so the fixture is at solo ceiling. Keep it as a ledger
math control unless the spec is revised to expose a lower solo ceiling.

## Retirement

Retire or replace this fixture if another fixture provides the same
idempotent-ledger signal with cleaner full-pipeline pair headroom.
