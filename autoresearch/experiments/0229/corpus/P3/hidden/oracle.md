# P3 hidden oracle

Run each row independently after the shared setup. Every row must pass on the reference. **P3-W** is the only designated witness; all other rows must pass on both patches. These tests are hidden, not additions to `tests/test_tz.py`.

Shared setup uses fresh, weak-referenceable timezone objects and a fresh instance of the same getter class as `tz.gettz`; no system timezone files or independent factory caches participate:

```python
import gc
import weakref
from datetime import timedelta, tzinfo
from dateutil import tz
import pytest

class Zone(tzinfo):
    def __init__(self, name):
        self.name = name
    def utcoffset(self, dt):
        return timedelta(0)
    def dst(self, dt):
        return timedelta(0)
    def tzname(self, dt):
        return self.name

def getter(size):
    result = type(tz.gettz)()
    result.nocache = lambda name=None: Zone(name)
    assert result.set_cache_size(size) is None
    return result

def fill(g, names):
    return {name: weakref.ref(g(name)) for name in names}

class IndexSize(object):
    def __init__(self, value):
        self.value = value
    def __index__(self):
        return self.value
```

## P3-I — Input validation

Setup: fresh empty getters. Action: supply valid index sizes, invalid types, negative integers, and a raising index implementation. Expected: the specified return values or exception classes. No later lookup follows a negative failure in this row.

```python
for value in (0, 1, 5, False, True, IndexSize(2)):
    g = getter(3)
    assert g.set_cache_size(value) is None
for value in (None, '3', 1.5, object()):
    g = getter(3)
    with pytest.raises(TypeError):
        g.set_cache_size(value)
for value in (-1, IndexSize(-1)):
    g = getter(3)
    with pytest.raises(ValueError):
        g.set_cache_size(value)

failure = RuntimeError('conversion failed')
class BrokenIndex(object):
    def __index__(self):
        raise failure

g = getter(3)
with pytest.raises(RuntimeError) as raised:
    g.set_cache_size(BrokenIndex())
assert raised.value is failure
```

## P3-W — Negative rejection followed by a hit (designated witness)

Setup: a size-three cache retaining A, B, C with no caller-held strong references. Action: reject `-1`, then look up C again. Expected: all three objects remain retained and the C object is reused. The twin wrongly evicts A during the hit because the rejected capacity was committed.

```python
g = getter(3)
refs = fill(g, ('A', 'B', 'C'))
gc.collect()
assert all(ref() is not None for ref in refs.values())
with pytest.raises(ValueError):
    g.set_cache_size(-1)
assert g('C') is refs['C']()
gc.collect()
assert all(ref() is not None for ref in refs.values())
```

## P3-F — Conversion failure preserves capacity and recency

Setup: retain A, B, C and touch A. Action: reject a string, insert D, then shrink successfully. Expected: rejection changes nothing; D evicts B, and the later shrink evicts C.

```python
g = getter(3)
refs = fill(g, ('A', 'B', 'C'))
assert g('A') is refs['A']()
with pytest.raises(TypeError):
    g.set_cache_size('2')
refs['D'] = weakref.ref(g('D'))
gc.collect()
assert refs['B']() is None
assert all(refs[name]() is not None for name in ('A', 'C', 'D'))
assert g.set_cache_size(2) is None
gc.collect()
assert refs['C']() is None
assert refs['A']() is not None and refs['D']() is not None
```

## P3-S — Successful resizing and recency

Setup: a size-three cache, with A refreshed after B and C. Action: shrink through an index object, grow, then insert two more objects. Expected: B expires immediately at shrink; growth keeps A and C; insertion beyond capacity later evicts C.

```python
g = getter(3)
refs = fill(g, ('A', 'B', 'C'))
assert g('A') is refs['A']()
assert g.set_cache_size(IndexSize(2)) is None
gc.collect()
assert refs['B']() is None
assert refs['A']() is not None and refs['C']() is not None
assert g.set_cache_size(3) is None
refs['D'] = weakref.ref(g('D'))
gc.collect()
assert all(refs[name]() is not None for name in ('C', 'A', 'D'))
refs['E'] = weakref.ref(g('E'))
gc.collect()
assert refs['C']() is None
assert all(refs[name]() is not None for name in ('A', 'D', 'E'))
```

## P3-Z — Zero capacity and caller-held identities

Setup: a populated cache and a caller-held object. Action: set zero capacity, reuse the live object, then release it. Expected: unheld objects expire, the held object is reused while alive, and it expires after the caller releases it.

```python
g = getter(2)
held = g('A')
a_ref = weakref.ref(held)
b_ref = weakref.ref(g('B'))
assert g.set_cache_size(0) is None
gc.collect()
assert b_ref() is None
assert g('A') is held
del held
gc.collect()
assert a_ref() is None
```

## P3-C — Cache clear remains compatible

Setup: a size-one cache and a live caller reference. Action: clear, resolve the same name, then insert another name. Expected: clear removes lookup identity and retains capacity one.

```python
g = getter(1)
held = g('A')
g.cache_clear()
fresh = g('A')
assert fresh is not held
fresh_ref = weakref.ref(fresh)
del fresh
g('B')
gc.collect()
assert fresh_ref() is None
```
