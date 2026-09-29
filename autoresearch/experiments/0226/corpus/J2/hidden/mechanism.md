# J2 mechanism record

## Mandatory clause

The following is the requirement text reserved for `spec.md`:

> For custom mappings, a match against the original input must take precedence over a match found only after trimming; truthy must take precedence over falsy for the same candidate.

## Trigger

A string's original spelling matches one custom set, and its trimmed spelling matches the opposite set, after applying the configured case sensitivity. Neither spelling is a canonical boolean recognized by the earlier built-in conversion.

## Causal code path

lib/types/boolean.js → coerce → unchanged canonical true/false handling → custom candidate array → truthy/falsy loop. The first candidate that matches ends lookup.

## Incorrect behavior

The twin searches [value.trim(), value] instead of [value, value.trim()]. With truthy(' yes ').falsy('yes'), validating ' yes ' therefore selects falsy and returns false, although the original-input registration requires true.

## Executable witness

**J2-W**, defined with executable setup, action, and assertions in `hidden/oracle.md`. All other rows must pass on both variants.

## Near-miss exclusions

- Canonical 'true' and 'false' keeping their built-in precedence is required behavior, not this defect.
- Truthy winning over falsy for the same candidate is also required; the defect is precedence across the original and trimmed candidates.
- Rejecting padded custom strings altogether would be a different missing-feature defect.
- Trimming registrations rather than just the fallback input candidate would be a different defect.
- Case-insensitive matching in the default mode is expected, and strict validation still disables all coercion.

## Public-check separation

The public tests and reference implementation sketch in `hidden/implementation.md` run the affected code while leaving this particular data interaction unasserted. Keep the public tests identical in the reference and twin, retain the 100% coverage threshold, and change only the specified mechanism. Do not add any hidden-oracle command to `spec.expected.json`.
