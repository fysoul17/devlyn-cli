# C3 hidden oracle

Each row is independent. Exactly C3-O4 is the designated witness; every other row passes on both implementations. Shared setup:

```python
from cachetools import Cache, TTLCache

class DeadlineError(Exception):
    pass

class Clock:
    def __init__(self):
        self.now = 0
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.now

class Offset:
    def __init__(self):
        self.fail = False
        self.calls = 0
        self.error = DeadlineError("deadline unavailable")

    def __radd__(self, now):
        self.calls += 1
        if self.fail:
            raise self.error
        return now + 5

def make_cache(maxsize=3):
    clock, offset = Clock(), Offset()
    cache = TTLCache(maxsize, offset, timer=clock, getsizeof=len)
    return cache, clock, offset

def fail_assignment(cache, offset, key, value):
    offset.fail = True
    try:
        cache[key] = value
    except DeadlineError as error:
        assert error is offset.error
    else:
        raise AssertionError("deadline failure swallowed")
    finally:
        offset.fail = False
```

## C3-O1 — successful replacement refreshes deadline

- Setup: a at time 0; replace it at time 3 with a larger value.
- Action: expire at the old deadline and then at the new deadline.
- Expected: the current value survives the old deadline, has its current recorded size, and is reported once.

```python
cache, clock, offset = make_cache()
cache["a"] = "A"
clock.now = 3
cache["a"] = "AA"
assert cache.expire(5) == []
assert cache["a"] == "AA"
assert cache.currsize == 2
assert cache.expire(8) == [("a", "AA")]
assert cache.currsize == 0
```

## C3-O2 — failed live replacement preserves eviction order

- Setup: a and b fill a cache, both live at time zero.
- Action: fail replacement of a, then insert c.
- Expected: a's old contents and weight survive the failure; the later insertion evicts a because the failed operation did not make it recent.

```python
cache, clock, offset = make_cache(2)
cache["a"] = "A"
cache["b"] = "B"
fail_assignment(cache, offset, "a", "X")
assert Cache.__getitem__(cache, "a") == "A"
assert Cache.currsize.fget(cache) == 2
cache["c"] = "C"
assert "a" not in cache
assert cache["b"] == "B"
assert cache["c"] == "C"
assert cache.currsize == 2
```

## C3-O3 — failed new-key admission preserves a full live cache

- Setup: a full two-entry cache with live values.
- Action: fail insertion of c, then expire normally.
- Expected: both original values and their original deadlines remain; c never appears.

```python
cache, clock, offset = make_cache(2)
cache["a"] = "A"
cache["b"] = "B"
fail_assignment(cache, offset, "c", "C")
assert "c" not in cache
assert Cache.currsize.fget(cache) == 2
assert cache.expire(5) == [("a", "A"), ("b", "B")]
```

## C3-O4 — failure preserves pending expiration — designated witness

- Setup: a expires at 5 and b at 8; advance to 5 without running cleanup.
- Action: fail insertion of c, then explicitly collect expired pairs.
- Expected: a is still available to expire's reporting path and b survives. The twin has already removed a, so its expire(5) returns [].

```python
cache, clock, offset = make_cache()
cache["a"] = "A"
clock.now = 3
cache["b"] = "B"
clock.now = 5
fail_assignment(cache, offset, "c", "C")
assert cache.expire(5) == [("a", "A")]
assert cache["b"] == "B"
assert cache.currsize == 1
assert "c" not in cache
```

Do not call len(cache), cache.currsize, repr(cache), or any other cleanup-triggering observer between advancing the clock and the explicit expire assertion.

## C3-O5 — one calculation and recovered timer context

- Setup: fail an assignment into an empty cache, then advance the clock.
- Action: successfully insert at time 20 and inspect call counts before any ordinary cache read.
- Expected: one new timer sample and one new addition; expiry is 25.

```python
cache, clock, offset = make_cache()
fail_assignment(cache, offset, "a", "A")
clock.now = 20
timer_calls, addition_calls = clock.calls, offset.calls
cache["b"] = "B"
assert clock.calls == timer_calls + 1
assert offset.calls == addition_calls + 1
assert cache.expire(24) == []
assert cache.expire(25) == [("b", "B")]
```

