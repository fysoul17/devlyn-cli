# C4 hidden oracle

Each row starts with fresh state. Exactly C4-O4 is the designated witness; every other row passes on both implementations. Imports used below:

```python
import math
from cachetools import Cache, FIFOCache, LRUCache, TLRUCache, TTLCache, cached
```

## C4-O1 — policy preservation and future admission

- Setup: three unit-sized LRU entries a,b,c, then read a.
- Action: shrink to two and insert d.
- Expected: resize evicts b, reports new capacity, and later admission evicts c.

```python
cache = LRUCache(3)
cache.update(a="A", b="B", c="C")
assert cache["a"] == "A"
assert cache.resize(2) is None
assert cache.maxsize == cache.currsize == 2
assert set(cache) == {"a", "c"}
cache["d"] = "D"
assert set(cache) == {"a", "d"}
assert cache.currsize == 2
```

## C4-O2 — invalid capacity and capacity boundaries

- Setup: a two-entry FIFO cache.
- Action: reject a negative capacity; grow to infinity, shrink to a fractional capacity, then to zero.
- Expected: rejection changes no eviction order; valid capacities take effect and unit-sized victims follow FIFO.

```python
cache = FIFOCache(2)
cache.update(a="A", b="B")
try:
    cache.resize(-1)
except ValueError:
    pass
else:
    raise AssertionError("negative capacity accepted")
assert cache.maxsize == 2
assert cache.currsize == 2
assert cache.resize(math.inf) is None
assert cache.maxsize == math.inf
cache.resize(1.5)
assert cache.maxsize == 1.5
assert set(cache) == {"b"}
cache.resize(0)
assert cache.maxsize == 0
assert cache.currsize == 0
assert len(cache) == 0
```

## C4-O3 — retained weighted values are not remeasured

- Setup: two values of stored weight three in a cache with sufficient capacity; count size callback calls.
- Action: resize twice while both capacities can hold the total stored weight.
- Expected: capacity changes without eviction or another callback invocation.

```python
calls = []
def size(value):
    calls.append(value)
    return len(value)

cache = Cache(20, getsizeof=size)
a, b = [1, 2, 3], [4, 5, 6]
cache["a"], cache["b"] = a, b
a.append(7)
cache.resize(10)
cache.resize(8)
assert cache.maxsize == 8
assert cache.currsize == 6
assert cache["a"] is a and cache["b"] is b
assert len(calls) == 2
```

## C4-O4 — stored weight controls capacity eviction — designated witness

- Setup: three LRU values of weight two have total size six but entry count three; read a to make it recent.
- Action: resize to four.
- Expected: b is evicted, leaving size four and keys a,c. The twin retains all three values and exposes currsize=6 with maxsize=4.

```python
cache = LRUCache(10, getsizeof=len)
cache.update(a="AA", b="BB", c="CC")
assert cache["a"] == "AA"
assert cache.resize(4) is None
assert cache.maxsize == 4
assert cache.currsize == 4
assert set(cache) == {"a", "c"}
assert cache["a"] == "AA" and cache["c"] == "CC"
```

## C4-O5 — timed cleanup precedes capacity eviction

- Setup: for each timed cache, a expires at 5, while b and c expire at 8.
- Action: at time 5 resize to two.
- Expected: expired a is reclaimed and both live entries survive.

```python
for kind in ("ttl", "tlru"):
    now = [0]
    if kind == "ttl":
        cache = TTLCache(3, 5, timer=lambda: now[0])
    else:
        cache = TLRUCache(3, lambda key, value, time: time + 5,
                          timer=lambda: now[0])
    cache["a"] = "A"
    now[0] = 3
    cache.update(b="B", c="C")
    now[0] = 5
    cache.resize(2)
    assert set(cache) == {"b", "c"}
    assert cache.maxsize == cache.currsize == 2
```

## C4-O6 — existing decorator sees new capacity

- Setup: a memoizing wrapper using an LRU cache; fill it with two results.
- Action: resize the same cache to one and request a new result.
- Expected: wrapper identity remains bound to the cache and cache_info agrees with the resized cache.

```python
cache = LRUCache(3)

@cached(cache, info=True)
def f(value):
    return value * 2

assert f(1) == 2 and f(2) == 4
cache.resize(1)
assert f.cache is cache
assert f.cache_info().maxsize == 1
assert f.cache_info().currsize == 1
assert f(3) == 6
assert f.cache_info().currsize == 1
```

## C4-O7 — timed resize with advancing time

- Setup: for each of TTLCache and TLRUCache, use unit-sized entries with a expiring at 5 and b,c at 8. Arm the timer to return 4 on its first read during resize and either 5 or 8 on every subsequent read.
- Action: resize to two without externally freezing the timer, then inspect the cache at the later time.
- Expected: resize returns None without raising and publishes capacity two in both cases. At time 5, b and c both survive: expiration of a must not cause an additional live victim. At time 8, all entries are expired and cleanup leaves size zero; expiration between reads must not make resize raise KeyError. This row passes on both implementations because all stored sizes are one.

With the repaired design's single observation at time 4, a is the ordinary capacity victim; inspection after resize observes the later time.

```python
class AdvancingTimer:
    def __init__(self):
        self.now = 0
        self.next_time = None

    def __call__(self):
        time = self.now
        if self.next_time is not None:
            self.now = self.next_time
        return time


for kind in ("ttl", "tlru"):
    for next_time in (5, 8):
        timer = AdvancingTimer()
        if kind == "ttl":
            cache = TTLCache(3, 5, timer=timer)
        else:
            cache = TLRUCache(3, lambda key, value, time: time + 5,
                              timer=timer)
        cache["a"] = "A"
        timer.now = 3
        cache.update(b="B", c="C")
        timer.now = 4
        timer.next_time = next_time
        assert cache.resize(2) is None
        assert cache.maxsize == 2
        expected = {"b", "c"} if next_time == 5 else set()
        assert set(cache) == expected
        assert cache.currsize == len(expected)
```

## C4-O8 — inherited arithmetic and safe termination

- Setup: fresh LRU, TTL, and TLRU caches with fractional weights or mixed large integer and floating-point weights. Timers stay fixed; count getsizeof calls. All assignments succeed using Cache's existing accounting.
- Action: resize fractional entries to zero or a tiny positive capacity, then resize the empty cache again. Resize the mixed-weight cache to infinity without eviction, or to zero with a leading zero-sized victim.
- Expected: resize returns None without raising, publishes the requested capacity, and does not remeasure values. Fractional cases and the mixed-weight zero-capacity case empty the cache; the infinity case retains every entry. Do not require an exact retained-weight sum, currsize == 0, or currsize <= capacity when inherited rounding or overflow prevents those results. Both guards empty the fractional cases at these bounds, retain all entries at infinity, and empty the mixed-weight zero-capacity case, so this row passes on both implementations.

The infinity case reproduces the reconciliation OverflowError: summing the two large integers before adding 0.0 overflows, although the inherited counter is already infinity. With a leading x=0.0, an initial sum would succeed, but repeating it after evicting x would overflow. Neither sum is part of resize under the narrowed contract.

```python
def make_cache(kind, calls):
    def size(value):
        calls.append(value)
        return value

    if kind == "lru":
        return LRUCache(math.inf, getsizeof=size)
    if kind == "ttl":
        return TTLCache(math.inf, 5, timer=lambda: 0, getsizeof=size)
    return TLRUCache(math.inf, lambda key, value, time: time + 5,
                     timer=lambda: 0, getsizeof=size)


for kind in ("lru", "ttl", "tlru"):
    for capacity in (0, 1e-18):
        calls = []
        cache = make_cache(kind, calls)
        cache.update(a=0.1, b=0.2)
        assert cache.resize(capacity) is None
        assert cache.maxsize == capacity
        assert len(cache) == 0
        assert cache.resize(0) is None
        assert cache.maxsize == 0
        assert len(cache) == 0
        assert calls == [0.1, 0.2]

    for capacity in (math.inf, 0):
        calls = []
        cache = make_cache(kind, calls)
        if capacity == 0:
            cache["x"] = 0.0
        cache.update(a=0, b=0, z=0.0)
        cache["a"] = 10**308
        cache["b"] = 10**308
        assert cache.currsize == math.inf  # inherited accounting
        calls_before = list(calls)
        assert cache.resize(capacity) is None
        assert cache.maxsize == capacity
        expected = {"a": 10**308, "b": 10**308, "z": 0.0}
        assert dict(cache) == (expected if capacity == math.inf else {})
        assert calls == calls_before
```
