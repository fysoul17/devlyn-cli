# P2 hidden oracle

Each row runs independently after the shared setup against the candidate. All rows must pass on the reference. **P2-W** is the sole designated witness; every other row must also pass on the twin. Do not copy the hidden blocks into the public suite.

Shared setup:

```python
from datetime import datetime, timedelta
import time
from dateutil import tz
from dateutil.parser import parse, parser, UnknownTimezoneWarning
import pytest

TEXT = '2012-01-19 17:21:00 -0300 (BRST)'
NAME_TEXT = '2012-01-19 17:21:00 BRST'
NUM_TEXT = '2012-01-19 17:21:00 -0300'
WALL = datetime(2012, 1, 19, 17, 21)
PAIR_ZONE = tz.tzoffset('PAIR', -7200)
NAME_ZONE = tz.tzoffset('NAME', -14400)
```

## P2-P — Tuple priority, name fallback, and ignoretz

Setup: conflicting, non-`None` pair and name values. Action: reuse the mapping for three parses with different resolution paths, through both public APIs. Expected: pair identity, name identity, then a naive datetime.

```python
mapping = {('BRST', -10800): PAIR_ZONE, 'BRST': NAME_ZONE}
for parse_fn in (parse, parser().parse):
    exact = parse_fn(TEXT, tzinfos=mapping)
    fallback = parse_fn(NAME_TEXT, tzinfos=mapping)
    ignored = parse_fn(TEXT, tzinfos=mapping, ignoretz=True)
    assert exact.tzinfo is PAIR_ZONE
    assert fallback.tzinfo is NAME_ZONE
    assert exact.replace(tzinfo=None) == WALL
    assert fallback.replace(tzinfo=None) == WALL
    assert ignored == WALL and ignored.tzinfo is None
```

## P2-W — Present None entry outranks the name (designated witness)

Setup: an exact pair explicitly maps to `None`; the name maps to an aware zone. Action: parse the matching named offset. Expected: a naive datetime. The twin uses the name's zone.

```python
mapping = {('BRST', -10800): None, 'BRST': NAME_ZONE}
result = parse(TEXT, tzinfos=mapping)
assert result.tzinfo is None
assert result == WALL
```

## P2-V — Conversion rules and absent components

Setup: tuple entries with supported values and pairs missing one component. Action: parse matching strings. Expected: conversions follow the existing name-key behavior, including zero, and a lone explicit `None` remains naive.

```python
for value, seconds in ((3600, 3600), (0, 0), ('UTC+0', 0)):
    result = parse(TEXT, tzinfos={('BRST', -10800): value, 'BRST': NAME_ZONE})
    assert result.utcoffset() == timedelta(seconds=seconds)
    assert result.replace(tzinfo=None) == WALL
assert parse(NAME_TEXT, tzinfos={('BRST', None): PAIR_ZONE}).tzinfo is PAIR_ZONE
assert parse(NUM_TEXT, tzinfos={(None, -10800): PAIR_ZONE}).tzinfo is PAIR_ZONE
assert parse(TEXT, tzinfos={('BRST', -10800): None}).tzinfo is None
with pytest.raises(TypeError):
    parse(TEXT, tzinfos={('BRST', -10800): object(), 'BRST': NAME_ZONE})
```

## P2-B — Built-in and legacy behavior

Setup: unmatched pairs, a legacy name-key `None`, and an unknown name. Action: parse without a matching tuple. Expected: name fallback, numeric-offset fallback, explicit naivety, and the existing unknown-timezone warning.

```python
assert parse(TEXT, tzinfos={('BRST', 3600): PAIR_ZONE, 'BRST': NAME_ZONE}).tzinfo is NAME_ZONE
assert parse(NUM_TEXT, tzinfos={('BRST', 3600): PAIR_ZONE}).utcoffset() == timedelta(hours=-3)
assert parse(NAME_TEXT, tzinfos={'BRST': None}).tzinfo is None
unknown = next(name for name in ('XYZ', 'QXZ', 'QZT') if name not in time.tzname)
with pytest.warns(UnknownTimezoneWarning):
    result = parse('2012-01-19 17:21:00 ' + unknown,
                   tzinfos={('BRST', 3600): PAIR_ZONE})
assert result == WALL and result.tzinfo is None
```

## P2-C — Callbacks and bypass

Setup: a recording callback and a mapping whose lookup operations fail if used. Action: parse normally with the callback and with `ignoretz` for both resolver forms. Expected: one callback call for ordinary parsing and no resolver access for `ignoretz`.

```python
calls = []
def resolve(name, offset):
    calls.append((name, offset))
    return PAIR_ZONE

assert parse(TEXT, tzinfos=resolve).tzinfo is PAIR_ZONE
assert calls == [('BRST', -10800)]
assert parse(TEXT, tzinfos=resolve, ignoretz=True) == WALL
assert calls == [('BRST', -10800)]

class UnreadableMapping(dict):
    def __contains__(self, key):
        raise AssertionError('unexpected lookup')
    def get(self, key, default=None):
        raise AssertionError('unexpected lookup')
    def __getitem__(self, key):
        raise AssertionError('unexpected lookup')

mapping = UnreadableMapping({('BRST', -10800): PAIR_ZONE})
assert parse(TEXT, tzinfos=mapping, ignoretz=True) == WALL
```
