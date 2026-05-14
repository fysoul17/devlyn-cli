# F22 CLI ledger close

## Failure mode

This fixture detects finance-style reconciliation mistakes: applying duplicate
transactions twice, silently accepting conflicting duplicate ids, validating
only while mutating balances, rejecting negative balances that are explicitly
allowed, or producing nondeterministic account ordering.

## Pipeline phase target

PLAN must separate validation, idempotency, chronological application, and
output formatting. IMPLEMENT must keep cents as integers and avoid fallback
error handling. VERIFY should catch duplicate-id counterexamples and negative
balance behavior.

## Why existing fixtures do not cover it

F16 covers order quote arithmetic, but not ledger idempotency or full-input
validation before mutation. F21 covers interval scheduling. Server fixtures
cover API behavior rather than CLI reconciliation.

## Measurement status

Headroom runs reject F22 as full-pipeline pair-lift evidence. In
`20260507-f21-f22-full-pipeline-pair`, F22 scored bare 91 / solo_claude 98 and
failed the headroom gate. In `20260508-f22-exact-error-headroom`, F22 scored
bare 94 / solo_claude 98 after the exact-error fixture revision. Keep it as a ledger
reconciliation control, not as counted `solo < pair` evidence.

## Retirement

Retire or replace if both bare and solo consistently score above the headroom
thresholds, or if a future ledger fixture captures the same duplicate-id and
validation-before-mutation risks with stronger discrimination.
