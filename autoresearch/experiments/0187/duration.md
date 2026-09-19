# Exact duration parsing

Implement `parse_duration(text)` in `duration.py`, returning integer milliseconds.
The existing `format_duration(milliseconds)` behavior must remain byte-for-byte
unchanged. Only duration.py and optional tests/test_regression.py may change.

Accept a string with optional surrounding ASCII space (0x20), tab (0x09), or LF (0x0a) and exactly
one unsigned decimal quantity followed immediately by a case-sensitive unit:
`ms`, `s`, `m`, or `h`. Quantities have one or more ASCII digits, optionally a dot
and one or more ASCII digits. Leading zeroes are valid. Reject signs, exponents,
internal whitespace, Unicode digits, missing units and trailing data. A non-string
raises TypeError; malformed text raises ValueError. Do not silently coerce input.

The result must be exact, nonnegative and at most 2**63-1 milliseconds. Fractional
quantities are accepted only when their conversion is an exact integer number of
milliseconds (for example 0.001s = 1, 0.0001s is rejected). All out-of-range and
nonintegral results raise ValueError, including values close to the upper bound.
No float rounding, new dependencies, CLI or additional public API.

Run `python3 -B -m unittest discover -s tests -v`, preserving the supplied tests,
spec.md, spec.expected.json and .gitignore. Add focused regressions as needed,
review every requirement and the final diff, and remove only task-created debris.
Local experiment commits only; the outer owner handles delivery. Report the actual
outcome and any unverified requirement; a passing check is not proof of untested
requirements.
