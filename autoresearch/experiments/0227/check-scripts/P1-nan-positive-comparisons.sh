#!/bin/sh
# Clause (spec.md Requirements): accept only when the >=/> lower and <=/< upper comparisons succeed; float("nan") must raise ValueError.
set -eu
cd "$1"
export PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1
exec python3 - <<'EOF'
import attrs
import pytest


@attrs.define
class Sample:
    value: object


field = attrs.fields(Sample).value
nan = float("nan")
flags = [(lo, up) for lo in (True, False) for up in (True, False)]

# NaN under every endpoint configuration, including equal (empty open) bounds.
for lower, upper in ((2, 7), (0.0, 1.0), (5, 5)):
    for lo, up in flags:
        v = attrs.validators.between(
            lower, upper, lower_inclusive=lo, upper_inclusive=up
        )
        with pytest.raises(ValueError):
            v(None, field, nan)


# NaN through generated validation: construction and assignment.
@attrs.define
class Validated:
    value: float = attrs.field(validator=attrs.validators.between(0.0, 1.0))


with pytest.raises(ValueError):
    Validated(nan)
item = Validated(0.5)
with pytest.raises(ValueError):
    item.value = nan
assert item.value == 0.5

# A partially ordered value outside the interval (not a subset of upper).
v = attrs.validators.between(frozenset(), frozenset({1, 2, 3}))
with pytest.raises(ValueError):
    v(None, field, frozenset({4}))


# The required operators are the ones used, and failing them rejects.
class Probe:
    def __init__(self):
        self.calls = []

    def _op(name):
        def op(self, other):
            self.calls.append(name)
            return False

        return op

    __ge__ = _op("ge")
    __gt__ = _op("gt")
    __le__ = _op("le")
    __lt__ = _op("lt")


for lo, up in flags:
    v = attrs.validators.between(2, 7, lower_inclusive=lo, upper_inclusive=up)
    allowed = {"ge" if lo else "gt", "le" if up else "lt"}
    probe = Probe()
    with pytest.raises(ValueError):
        v(None, field, probe)
    assert probe.calls, probe.calls
    assert set(probe.calls) <= allowed, (lo, up, probe.calls)
EOF
