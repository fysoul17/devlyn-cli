# P1 implementation instructions

Family: boundary semantics. This request applies by itself to the pinned tree.

## Reference

Change exactly these files: `src/attr/validators.py`, `src/attr/validators.pyi`, `tests/test_validators.py`, and `typing_tests/baseline.py`.

Add `between` to `validators.__all__`; the existing star re-export supplies the `attrs` namespace. Follow `_NumberValidator` with a frozen, slotted attrs validator carrying the bounds and the two inclusive flags. Check the bounds in the factory, before constructing the validator, with `if not lower <= upper`. Do not reject equal bounds merely because an endpoint is open.

In `__call__`, decide interval membership positively: the lower comparison and the upper comparison must both be true. Either comparison can raise its native exception. Produce the specified interval formatting for `repr` and the validation message. Do not coerce inputs or special-case floating-point values. Use the existing validator class conventions for equality and hashing. The stub should follow the generic single-bound validators, returning `_ValidatorType[_T]` for bounds of type `_T`.

Add public tests to `tests/test_validators.py` for exports, all four endpoint combinations with ordinary finite numbers, interior/exterior values, equal bounds, reversed bounds, infinite bounds, incompatible comparison types, representation, error-message contents, equality/hash, and successful `None` returns. Exercise a field with this validator through construction, assignment rejection without changing its old value, `optional`, and the global disabled context. Use finite ordinary values for the field integration tests. Add an ordinary integer-field example in the existing typing baseline. These tests should exercise the success and failure arms and both settings of each flag.

The added public tests must not supply an unordered value to the returned validator. Existing tests cover only existing APIs. Leave all existing assertions intact. Source docstrings and the stub remain identical in both implementations; do not add coverage exclusions or change checking configuration.

## Twin

Start from the reference and change only the membership predicate in the new validator's `__call__`. Reject on an out-of-range comparison: `value < lower` for an inclusive lower bound, `value <= lower` for an exclusive lower bound, `value > upper` for an inclusive upper bound, or `value >= upper` for an exclusive upper bound. Accept if neither bound rejects. Keep the factory's positive `lower <= upper` check intact.

This is the plausible assumption that inverting each comparison is equivalent to negating interval membership. It is equivalent for all ordered numbers in the public tests, including equal and infinite endpoints. It is false for an unordered value. No names, comments, messages, tests, or stubs should reveal the deviation. The twin changes exactly the same four files as the reference and retains identical public tests.
