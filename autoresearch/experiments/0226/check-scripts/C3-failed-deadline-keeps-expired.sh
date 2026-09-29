#!/bin/sh
# 0226 check (C3): if computing a TTLCache assignment's deadline raises, the same
# exception propagates and expired entries awaiting cleanup stay reportable by a
# later expire(). Exit 0 = clause holds.
set -eu
cd "$1"
exec python3 - <<'PY'
import cachetools


class Boom(Exception):
    pass


class Timer:
    now = 0

    def __call__(self):
        return self.now


class TTL:
    fail = False

    def __radd__(self, other):
        if self.fail:
            raise Boom()
        return other + 5


for key in ("c", "b"):  # a new key, then replacement of a live key
    timer, ttl = Timer(), TTL()
    cache = cachetools.TTLCache(10, ttl=ttl, timer=timer)
    cache["a"] = "A"  # expires at 5
    timer.now = 3
    cache["b"] = "B"  # expires at 8
    timer.now = 6  # "a" has expired but is still resident
    ttl.fail = True
    try:
        cache[key] = "X"
    except Boom:
        pass
    else:
        raise AssertionError("deadline failure did not propagate")
    ttl.fail = False
    assert cache.expire(6) == [("a", "A")]
    assert dict(cache.items()) == {"b": "B"}
PY
