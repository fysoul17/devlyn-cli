# P1 hidden oracle

Each row is an independent test. Execute its Python block after the shared setup, with the candidate's package importable. Every row must pass on the reference. Only **P1-W** is the designated witness; all other rows must pass on the twin as well. These blocks belong to the hidden harness, not the repository's public test suite.

Shared setup:

```python
from datetime import datetime, timedelta
from dateutil.rrule import DAILY, rrule, rruleset
import pytest

START = datetime(2024, 1, 1)

def dates(n):
    return [START + timedelta(days=i) for i in range(n)]

def make_rule(cache=False, n=25):
    return rrule(DAILY, dtstart=START, count=n, cache=cache)

def prepare(kind, mode):
    if kind == 'rule':
        obj = make_rule(cache=(mode != 'off'))
        expected = dates(25)
    else:
        obj = rruleset(cache=(mode != 'off'))
        obj.rrule(make_rule())
        obj.exdate(START + timedelta(days=3))
        expected = [d for d in dates(25) if d != START + timedelta(days=3)]
    if mode == 'partial':
        assert obj[0] == expected[0]
        assert not obj._cache_complete
    elif mode == 'complete':
        assert list(obj) == expected
        assert obj._cache_complete
    return obj, expected
```

## P1-N — Negative bounds and reverse traversal

Setup: fresh rule and set in each cache mode. Action: take negative-bound and reverse slices. Expected: equality with the corresponding finite-list slice.

```python
for kind in ('rule', 'set'):
    for mode in ('off', 'partial', 'complete'):
        for sl in (slice(-3, None), slice(None, -1), slice(1, -1, 2),
                   slice(-100, 3), slice(-3, -1), slice(None, None, -1),
                   slice(4, 1, -2)):
            obj, expected = prepare(kind, mode)
            assert obj[sl] == expected[sl]
```

## P1-W — Explicit zero endpoint (designated witness)

Setup: a fresh, uncached five-occurrence rule. Action: request `[:0]`. Expected: an empty list. The twin returns all five dates.

```python
obj = make_rule(n=5)
assert obj[:0] == []
```

## P1-F — Forward and omitted bounds

Setup: rule and set in each cache mode. Action: take full and bounded forward slices, and integer subscriptions. Expected: the normal ordered results.

```python
for kind in ('rule', 'set'):
    for mode in ('off', 'partial', 'complete'):
        obj, expected = prepare(kind, mode)
        assert obj[:] == expected
        assert obj[1:4:2] == expected[1:4:2]
        assert obj[4:2] == []
        assert obj[0] == expected[0]
        assert obj[-1] == expected[-1]

class IndexBound(object):
    def __init__(self, value):
        self.value = value
    def __index__(self):
        return self.value

obj = make_rule(n=5)
assert obj[IndexBound(1):IndexBound(4)] == dates(5)[1:4]
```

## P1-Z — Step-zero errors

Setup: each cache mode on a nonempty rule and an empty rule. Action: subscribe with step zero. Expected: `ValueError`.

```python
for mode in ('off', 'partial', 'complete'):
    obj, _ = prepare('rule', mode)
    with pytest.raises(ValueError):
        obj[::0]
for cache in (False, True):
    obj = make_rule(cache=cache, n=0)
    with pytest.raises(ValueError):
        obj[::0]
```

## P1-L — A prefix remains incremental

Setup: a recurrence iterator with a failure after its third yield. Action: select `[1:3]`. Expected: the second and third occurrences, without reaching the failure.

```python
class GuardedRule(rrule):
    def _iter(self):
        for d in dates(3):
            yield d
        raise AssertionError('prefix exhausted the recurrence')

obj = GuardedRule(DAILY, dtstart=START)
assert obj[1:3] == dates(3)[1:3]
```
