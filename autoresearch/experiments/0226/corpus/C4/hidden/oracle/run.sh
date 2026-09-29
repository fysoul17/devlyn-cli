#!/bin/sh
set -eu

if [ "$#" -ne 1 ] || [ ! -f "$1/src/cachetools/__init__.py" ]; then
    echo "usage: oracle/run.sh <tree>" >&2
    exit 2
fi

if [ -x /Users/Shared/devlyn-0226/repos/cachetools/.venv-0226/bin/python ]; then
    oracle_python=/Users/Shared/devlyn-0226/repos/cachetools/.venv-0226/bin/python
elif command -v python >/dev/null 2>&1; then
    oracle_python=python
elif command -v python3 >/dev/null 2>&1; then
    oracle_python=python3
else
    echo "Python is unavailable" >&2
    exit 2
fi

PYTHONPATH="$1/src" PYTHONDONTWRITEBYTECODE=1 "$oracle_python" -B - <<'PY'
import json
import math

from cachetools import Cache, FIFOCache, LRUCache, TLRUCache, TTLCache, cached


def c4_o1():
    cache = LRUCache(3)
    cache.update(a="A", b="B", c="C")
    assert cache["a"] == "A"
    assert cache.resize(2) is None
    assert cache.maxsize == cache.currsize == 2
    assert set(cache) == {"a", "c"}
    cache["d"] = "D"
    assert set(cache) == {"a", "d"}
    assert cache.currsize == 2


def c4_o2():
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


def c4_o3():
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


def c4_o4():
    cache = LRUCache(10, getsizeof=len)
    cache.update(a="AA", b="BB", c="CC")
    assert cache["a"] == "AA"
    assert cache.resize(4) is None
    assert cache.maxsize == 4
    assert cache.currsize == 4
    assert set(cache) == {"a", "c"}
    assert cache["a"] == "AA" and cache["c"] == "CC"


def c4_o5():
    for kind in ("ttl", "tlru"):
        now = [0]
        if kind == "ttl":
            cache = TTLCache(3, 5, timer=lambda: now[0])
        else:
            cache = TLRUCache(
                3, lambda key, value, time: time + 5, timer=lambda: now[0]
            )
        cache["a"] = "A"
        now[0] = 3
        cache.update(b="B", c="C")
        now[0] = 5
        cache.resize(2)
        assert set(cache) == {"b", "c"}
        assert cache.maxsize == cache.currsize == 2


def c4_o6():
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


def c4_o7():
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
                cache = TLRUCache(
                    3, lambda key, value, time: time + 5, timer=timer
                )
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


def c4_o8():
    def make_cache(kind, calls):
        def size(value):
            calls.append(value)
            return value

        if kind == "lru":
            return LRUCache(math.inf, getsizeof=size)
        if kind == "ttl":
            return TTLCache(math.inf, 5, timer=lambda: 0, getsizeof=size)
        return TLRUCache(
            math.inf,
            lambda key, value, time: time + 5,
            timer=lambda: 0,
            getsizeof=size,
        )

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
            assert cache.currsize == math.inf
            calls_before = list(calls)
            assert cache.resize(capacity) is None
            assert cache.maxsize == capacity
            expected = {"a": 10**308, "b": 10**308, "z": 0.0}
            assert dict(cache) == (expected if capacity == math.inf else {})
            assert calls == calls_before


rows = {
    "C4-O1": c4_o1,
    "C4-O2": c4_o2,
    "C4-O3": c4_o3,
    "C4-O4": c4_o4,
    "C4-O5": c4_o5,
    "C4-O6": c4_o6,
    "C4-O7": c4_o7,
    "C4-O8": c4_o8,
}
results = {}
for row_id, check in rows.items():
    try:
        check()
    except Exception:
        results[row_id] = False
    else:
        results[row_id] = True
print(json.dumps({"rows": results}))
PY
