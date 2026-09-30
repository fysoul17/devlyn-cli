# P1 hidden oracle

Run each row in a fresh namespace with `import attr`, `import attrs`, and `import pytest`. Common setup: define `@attrs.define class Sample: value: object`, then set `field = attrs.fields(Sample).value`. Call validators directly as `validator(None, field, value)` unless a row says otherwise. Exactly P1-O4 is the designated witness; all other rows must pass on both implementations.

## P1-O1 — closed interval

Setup: `v = attrs.validators.between(2, 7)`.

Action: validate `2`, `4`, and `7`, then separately validate `1` and `8`.

Expected: the first three calls return `None`; the last two raise `ValueError`. Each error mentions `value`, `[2, 7]`, and the rejected number. `repr(v)` is `<between validator for [2, 7]>`.

## P1-O2 — independent endpoints and degenerate intervals

Setup: construct validators for all four combinations of the two inclusive flags with bounds `2, 7`, then repeat with bounds `5, 5`.

Action: validate each endpoint and an interior value for the first set; validate `4`, `5`, and `6` for the second set.

Expected: interior `4` passes for every `2, 7` interval; an endpoint passes exactly when its own flag is true. For equal bounds, only `5` with both flags true passes. All other calls raise `ValueError`. Construction itself succeeds for every equal-bound combination. Check corresponding brackets in each representation.

## P1-O3 — construction and native comparisons

Setup: use factories with bounds `(7, 2)`, `(float("nan"), 7)`, and `(2, float("nan"))`; also create a valid `(2, 7)` validator.

Action: construct the three invalid configurations. Pass `1j` to the valid validator.

Expected: each invalid factory raises `ValueError`; the complex value raises `TypeError`. The invalid-bound check is unchanged in the twin.

## P1-O4 — unordered value (designated witness)

Setup and action, executable:

```python
v = attrs.validators.between(0.0, 1.0)
with pytest.raises(ValueError) as exc:
    v(None, field, float("nan"))
assert "value" in str(exc.value)
assert "[0.0, 1.0]" in str(exc.value)
assert "nan" in str(exc.value)
```

Expected: the value is rejected. The twin returns `None` because both out-of-range comparisons return false.

## P1-O5 — infinite endpoints and value objects

Setup: make closed and fully open validators with `-float("inf")` and `float("inf")` as bounds. Make two separate `between(2, 7)` validators.

Action: validate both infinities and zero with each interval; compare and hash the two finite validators.

Expected: closed accepts all three values; open accepts zero and rejects both infinities. The finite validators compare equal and have equal hashes. The two namespace exports refer to the same factory.

## P1-O6 — generated validation and composition

Setup: define a mutable `attrs.define` class with an integer field using `between(2, 7)` and another class with an optional field using `optional(between(2, 7))`.

Action: construct at `4`; assign `8` and then `7`. Construct the optional class with `None`. Under `attrs.validators.disabled()`, construct the first class with `8`; after leaving it, call `attrs.validate` on that object.

Expected: assignment of `8` raises `ValueError` and leaves `4` stored; assignment of `7` succeeds. Optional `None` succeeds. Disabled construction succeeds, and explicit validation after the context raises `ValueError`. Restore the validation switch in cleanup even if a row assertion fails.
