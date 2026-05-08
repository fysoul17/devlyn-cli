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
idempotency or conflicting duplicate events. F21/F23 became oracle-control
fixtures, so this adds a fresh visible-contract stateful arithmetic candidate.

## Retirement

Retire or replace this fixture if solo consistently reaches ceiling or if
another fixture provides the same idempotent-ledger signal with cleaner
full-pipeline pair lift.
