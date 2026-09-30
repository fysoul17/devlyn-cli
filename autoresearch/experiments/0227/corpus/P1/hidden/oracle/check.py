"""Run the independent hidden interval checks."""

import json

import pytest


COMMON = """
import attr
import attrs
import pytest

@attrs.define
class Sample:
    value: object

field = attrs.fields(Sample).value
"""

ROWS = {
    "P1-O1": """
v = attrs.validators.between(2, 7)
for value in (2, 4, 7):
    assert v(None, field, value) is None
for value in (1, 8):
    with pytest.raises(ValueError) as exc:
        v(None, field, value)
    message = str(exc.value)
    assert "value" in message
    assert "[2, 7]" in message
    assert str(value) in message
assert repr(v) == "<between validator for [2, 7]>"
""",
    "P1-O2": """
for lower_inclusive in (True, False):
    for upper_inclusive in (True, False):
        left = "[" if lower_inclusive else "("
        right = "]" if upper_inclusive else ")"
        v = attrs.validators.between(
            2, 7,
            lower_inclusive=lower_inclusive,
            upper_inclusive=upper_inclusive,
        )
        assert repr(v) == f"<between validator for {left}2, 7{right}>"
        for value, accepted in (
            (2, lower_inclusive), (4, True), (7, upper_inclusive)
        ):
            if accepted:
                assert v(None, field, value) is None
            else:
                with pytest.raises(ValueError):
                    v(None, field, value)

        equal = attrs.validators.between(
            5, 5,
            lower_inclusive=lower_inclusive,
            upper_inclusive=upper_inclusive,
        )
        assert repr(equal) == f"<between validator for {left}5, 5{right}>"
        for value in (4, 5, 6):
            if value == 5 and lower_inclusive and upper_inclusive:
                assert equal(None, field, value) is None
            else:
                with pytest.raises(ValueError):
                    equal(None, field, value)
""",
    "P1-O3": """
for lower, upper in (
    (7, 2), (float("nan"), 7), (2, float("nan"))
):
    with pytest.raises(ValueError):
        attrs.validators.between(lower, upper)
v = attrs.validators.between(2, 7)
with pytest.raises(TypeError):
    v(None, field, 1j)
""",
    "P1-O4": """
v = attrs.validators.between(0.0, 1.0)
with pytest.raises(ValueError) as exc:
    v(None, field, float("nan"))
assert "value" in str(exc.value)
assert "[0.0, 1.0]" in str(exc.value)
assert "nan" in str(exc.value)
""",
    "P1-O5": """
lower = -float("inf")
upper = float("inf")
closed = attrs.validators.between(lower, upper)
opened = attrs.validators.between(
    lower, upper, lower_inclusive=False, upper_inclusive=False
)
for value in (lower, 0, upper):
    assert closed(None, field, value) is None
assert opened(None, field, 0) is None
for value in (lower, upper):
    with pytest.raises(ValueError):
        opened(None, field, value)
first = attrs.validators.between(2, 7)
second = attrs.validators.between(2, 7)
assert first == second
assert hash(first) == hash(second)
assert attr.validators.between is attrs.validators.between
""",
    "P1-O6": """
@attrs.define
class Validated:
    value: int = attrs.field(validator=attrs.validators.between(2, 7))

@attrs.define
class OptionalValidated:
    value: int | None = attrs.field(
        validator=attrs.validators.optional(attrs.validators.between(2, 7))
    )

item = Validated(4)
with pytest.raises(ValueError):
    item.value = 8
assert item.value == 4
item.value = 7
assert item.value == 7
assert OptionalValidated(None).value is None
prior = attrs.validators.get_disabled()
try:
    with attrs.validators.disabled():
        invalid = Validated(8)
    with pytest.raises(ValueError):
        attrs.validate(invalid)
finally:
    attrs.validators.set_disabled(prior)
""",
}


def main():
    results = {}
    for row_id, source in ROWS.items():
        namespace = {"__name__": f"oracle_{row_id.replace('-', '_')}"}
        try:
            exec(COMMON + source, namespace)
        except (Exception, pytest.fail.Exception):
            results[row_id] = False
        else:
            results[row_id] = True

    print(json.dumps({"rows": results}, separators=(",", ":")))


if __name__ == "__main__":
    main()
