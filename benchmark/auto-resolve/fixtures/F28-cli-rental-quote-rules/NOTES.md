# F28 CLI rental quote rules

## Why this fixture exists

F27 was rejected because the direct bare arm passed every verifier. F28 returns
to the F16 pattern that produced valid lift: exact success shape plus exact
validation shape, with enough arithmetic and date handling that a direct
implementation is likely to leak extra fields or miss one contract.

## Pair expectation

PLAN must preserve the date-counting and duplicate-combine invariants.
IMPLEMENT must keep all public amounts in integer cents and read rules from
`data/rental-rules.json`. VERIFY should probe both the Friday-to-Tuesday
weekend count and the combined-stock exact error shape.

## Isolation

F16 covers checkout tax rules. F28 covers rental-day UTC math, weekend
surcharges, deposits, protection fees, and non-persistent inventory validation.
