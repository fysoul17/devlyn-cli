# C1 hidden oracle

Each row starts with fresh state and is an independent test. Use the shared setup below. Run against an implementation from its repository root with PYTHONPATH=src. Exactly C1-O4 is the designated witness; every other row must pass on both implementations.

```python
from cachetools import Cache, TLRUCache

class Clock:
    def __init__(self):
        self.now = 0
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.now

def make_cache():
    clock = Clock()
    cache = TLRUCache(20, lambda key, value, now: value, timer=clock)
    return cache, clock

def resident_size(cache):
    # Avoid _TimedCache.currsize, which performs unlimited expiration.
    return Cache.currsize.fget(cache)
```

## C1-O1 — bounded drain

- Setup: make_cache(); store a=2, b=4, c=8.
- Action: execute the following with the fake clock still at zero.
- Expected: the first call removes two eligible values, physical accounting reflects one retained value, and a later call removes that value.

```python
cache, clock = make_cache()
cache.update(a=2, b=4, c=8)
assert cache.expire(10, limit=2) == [("a", 2), ("b", 4)]
assert resident_size(cache) == 1
assert Cache.__len__(cache) == 1
assert cache.expire(10) == [("c", 8)]
assert resident_size(cache) == 0
```

## C1-O2 — zero, validation, and exact cutoff

- Setup: one value expiring at 2.
- Action: call zero and invalid limits, then expire at precisely 2.
- Expected: zero and rejected limits leave the value resident; rejected limits do not sample time; equality expires the value.

```python
cache, clock = make_cache()
cache["a"] = 2
assert cache.expire(2, limit=0) == []
before_calls = clock.calls
for limit, error in [(-1, ValueError), (1.5, TypeError), ("1", TypeError)]:
    try:
        cache.expire(limit=limit)
    except error:
        pass
    else:
        raise AssertionError("invalid limit accepted")
assert clock.calls == before_calls
assert Cache.__len__(cache) == 1
assert cache.expire(2, limit=True) == [("a", 2)]
assert cache.expire(2, limit=False) == []
```

## C1-O3 — logical expiry and timer selection

- Setup: two values with distinct deadlines; advance the clock beyond both.
- Action: expire one value with omitted time, inspect logical lookup, then drain.
- Expected: the timer is sampled once for the bounded call, the remaining expired value is inaccessible but resident, and the later drain reports it.

```python
cache, clock = make_cache()
cache.update(a=2, b=3)
clock.now = 4
before_calls = clock.calls
assert cache.expire(limit=1) == [("a", 2)]
assert clock.calls == before_calls + 1
assert cache.get("b", "absent") == "absent"
assert resident_size(cache) == 1
assert cache.expire() == [("b", 3)]
cache["c"] = 10
assert cache["c"] == 10
```

## C1-O4 — obsolete record before an eligible value — designated witness

- Setup: three entries with distinct deadlines, followed by deletion of the earliest. The heap has three records and two active entries, below the existing compaction trigger of heap length > 2 * active length.
- Action: expire one resident value at time 3.
- Expected: the obsolete a record consumes no value budget; b is returned and removed. The twin returns [] and leaves b resident.

```python
cache, clock = make_cache()
cache.update(a=2, b=3, c=10)
del cache["a"]
assert cache.expire(3, limit=1) == [("b", 3)]
assert resident_size(cache) == 1
assert cache.expire(3) == []
assert cache["c"] == 10
```

## C1-O5 — unlimited replacement cleanup

- Setup: replace a deadline while keeping another current value.
- Action: expire without a limit before and after the replacement deadline.
- Expected: stale a is never reported or allowed to delete current a.

```python
cache, clock = make_cache()
cache.update(a=2, b=5)
cache["a"] = 9
assert cache.expire(5) == [("b", 5)]
assert cache["a"] == 9
assert cache.expire(9) == [("a", 9)]
```

