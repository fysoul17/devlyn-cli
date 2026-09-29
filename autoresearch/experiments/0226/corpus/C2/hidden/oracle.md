# C2 hidden oracle

Each row is independent. Exactly C2-O3 is the designated witness; all other rows pass on both implementations. Use this shared setup:

```python
from cachetools import TLRUCache

def make_cache(maxsize=20):
    # Values carry (deadline, payload); time remains zero during setup.
    return TLRUCache(maxsize, lambda key, value, now: value[0], timer=lambda: 0)
```

## C2-O1 — deadline precedence and read independence

- Setup: interleave assignments to deadlines 10 and 5.
- Action: read the first key, then expire all four entries.
- Expected: earlier deadlines first, assignment order within each group.

```python
cache = make_cache()
cache["a"] = (10, "A")
cache["b"] = (5, "B")
cache["c"] = (10, "C")
cache["d"] = (5, "D")
assert cache["a"] == (10, "A")
assert "b" in cache
assert [key for key, value in cache.expire(10)] == ["b", "d", "a", "c"]
assert cache.currsize == 0
```

## C2-O2 — replacement with a distinct deadline

- Setup: a expires at 5, b at 8; replace a with deadline 12.
- Action: expire at 8, then at 12.
- Expected: stale a is ignored and its current value is returned only at 12.

```python
cache = make_cache()
cache["a"] = (5, "old")
cache["b"] = (8, "B")
cache["a"] = (12, "new")
assert cache.expire(8) == [("b", (8, "B"))]
assert cache.expire(12) == [("a", (12, "new"))]
```

## C2-O3 — current assignment wins a tied replacement — designated witness

- Setup: a, b, c share deadline 10; replace a without changing that deadline.
- Action: expire the tied group.
- Expected: b, c, then the new a. The twin returns the new a before b and c.

```python
cache = make_cache()
cache["a"] = (10, "old")
cache["b"] = (10, "B")
cache["c"] = (10, "C")
cache["a"] = (10, "new")
assert cache.expire(10) == [
    ("b", (10, "B")),
    ("c", (10, "C")),
    ("a", (10, "new")),
]
assert len(cache) == 0
```

## C2-O4 — deletion and heap compaction

- Setup: six distinct keys have the same deadline; delete the first four, leaving enough obsolete records to trigger compaction.
- Action: expire the remaining two.
- Expected: only current entries appear, in assignment order after heap rebuilding.

```python
cache = make_cache()
for key in range(6):
    cache[key] = (10, key)
for key in range(4):
    del cache[key]
assert cache.expire(10) == [(4, (10, 4)), (5, (10, 5))]
```

## C2-O5 — nonorderable keys and independent LRU order

- Setup: three plain object keys and capacity two; a and b share a deadline.
- Action: read a, insert c, then expire.
- Expected: LRU evicts b; expiration reports a before c without ordering the keys.

```python
cache = make_cache(2)
a, b, c = object(), object(), object()
cache[a] = (10, "A")
cache[b] = (10, "B")
assert cache[a] == (10, "A")
cache[c] = (10, "C")
assert b not in cache
assert cache.expire(10) == [(a, (10, "A")), (c, (10, "C"))]
```

## C2-O6 — failed admission does not move an existing entry

- Setup: a weighted cache with two tied entries whose weights fit.
- Action: reject an oversized replacement of the first key, then expire.
- Expected: both old values survive in their original order.

```python
cache = TLRUCache(
    2, lambda key, value, now: 10, timer=lambda: 0, getsizeof=len
)
cache["a"] = "A"
cache["b"] = "B"
try:
    cache["a"] = "too large"
except ValueError:
    pass
else:
    raise AssertionError("oversized assignment accepted")
assert cache.expire(10) == [("a", "A"), ("b", "B")]
```

