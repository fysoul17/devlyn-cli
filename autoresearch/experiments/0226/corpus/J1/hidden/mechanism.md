# J1 mechanism record

## Mandatory clause

The following is the requirement text reserved for `spec.md`:

> Truncation must preserve complete UTF-16 surrogate pairs and retain the original code units of each kept code point.

## Trigger

A UTF-8 max budget admits a supplementary-plane code point as part of the retained prefix. The retained code point occupies two UTF-16 code units.

## Causal code path

lib/types/string.js → string coerce → truncate/max after limit resolution → UTF-8 code-point loop → final value.slice(0, end). The loop's byte counter measures each full code point correctly; slice needs an endpoint measured in UTF-16 code units.

## Incorrect behavior

The twin increments the endpoint by one per iteration instead of by character.length. For max(5, 'utf8') and 'A😀B', it budgets five bytes for 'A😀' but slices at UTF-16 offset 2, returning 'A\uD83D'. That malformed prefix is only four bytes under Buffer.byteLength, so the subsequent max rule does not expose the error.

## Executable witness

**J1-W**, defined with executable setup, action, and assertions in `hidden/oracle.md`. All other rows must pass on both variants.

## Near-miss exclusions

- Using too large a byte budget or an incorrect greater-than comparison is a different defect.
- Counting bytes correctly but splitting a UTF-16 pair at the slice endpoint is this defect; grapheme-cluster splitting (such as between a base letter and combining mark) is explicitly outside the request.
- Ordinary truncation without an encoding and encodings other than UTF-8 retain their old behavior.
- An originally unpaired surrogate is not evidence that this implementation split a pair.
- Failure to resolve a max reference or preserve transform order is a separate violation.

## Public-check separation

The public tests and reference implementation sketch in `hidden/implementation.md` run the affected code while leaving this particular data interaction unasserted. Keep the public tests identical in the reference and twin, retain the 100% coverage threshold, and change only the specified mechanism. Do not add any hidden-oracle command to `spec.expected.json`.
