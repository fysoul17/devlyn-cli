# J4 mechanism record

## Mandatory clause

The following is the requirement text reserved for `spec.md`:

> For a resolved divisor, both the decimal-place rejection and the scaled remainder calculation must use the divisor's precision, even when the value being validated has fewer decimal places.

## Trigger

A referenced fractional divisor has more decimal places than the value being checked. For the designated witness, the divisor is 0.25 and the dividend is the whole number 1.

## Causal code path

lib/validator.js resolves and validates the rule's base reference → lib/types/number.js multiple.validate sees baseDecimalPlace === null → derives decimal-place metadata and pfactor → checks precision → computes the rounded scaled remainder. Metadata must come from the resolved base.

## Incorrect behavior

The twin derives baseDecimalPlace from value instead of base only in the new reference path. In J4-W this produces zero decimal places and scale 1; Math.round(1) % Math.round(0.25) is NaN because the denominator rounds to zero. The twin reports number.multiple for an exact multiple.

## Executable witness

**J4-W**, defined with executable setup, action, and assertions in `hidden/oracle.md`. All other rows must pass on both variants.

## Near-miss exclusions

- Preserving the original reference object in the error context is required and remains correct.
- Rejecting a nonnumeric or nonpositive resolved base with any.ref is expected behavior.
- Literal fractional divisors use the preexisting correct metadata; a defect there would be separate.
- General floating-point limitations at extreme magnitudes or very long decimal expansions are not the requested arithmetic redesign.
- Storing resolved metadata in mutable rule state would be a separate cross-validation caching defect; this twin changes only the source of precision within one invocation.
- Equal-precision sibling values exercising the new branch do not demonstrate consistency when the dividend is less precise.

## Public-check separation

The public tests and reference implementation sketch in `hidden/implementation.md` run the affected code while leaving this particular data interaction unasserted. Keep the public tests identical in the reference and twin, retain the 100% coverage threshold, and change only the specified mechanism. Do not add any hidden-oracle command to `spec.expected.json`.
