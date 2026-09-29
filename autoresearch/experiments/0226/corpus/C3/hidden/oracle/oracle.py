"""Independent behavioral checks for the C3 TTL assignment guarantee."""

import json
import sys

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


def c3_o1():
    cache, clock, offset = make_cache()
    cache["a"] = "A"
    clock.now = 3
    cache["a"] = "AA"
    assert cache.expire(5) == []
    assert cache["a"] == "AA"
    assert cache.currsize == 2
    assert cache.expire(8) == [("a", "AA")]
    assert cache.currsize == 0


def c3_o2():
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


def c3_o3():
    cache, clock, offset = make_cache(2)
    cache["a"] = "A"
    cache["b"] = "B"
    fail_assignment(cache, offset, "c", "C")
    assert "c" not in cache
    assert Cache.currsize.fget(cache) == 2
    assert cache.expire(5) == [("a", "A"), ("b", "B")]


def c3_o4():
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


def c3_o5():
    cache, clock, offset = make_cache()
    fail_assignment(cache, offset, "a", "A")
    clock.now = 20
    timer_calls, addition_calls = clock.calls, offset.calls
    cache["b"] = "B"
    assert clock.calls == timer_calls + 1
    assert offset.calls == addition_calls + 1
    assert cache.expire(24) == []
    assert cache.expire(25) == [("b", "B")]


def check(row):
    try:
        row()
    except Exception:
        return False
    return True


def main():
    rows = {
        "C3-O1": c3_o1,
        "C3-O2": c3_o2,
        "C3-O3": c3_o3,
        "C3-O4": c3_o4,
        "C3-O5": c3_o5,
    }
    json.dump({"rows": {name: check(row) for name, row in rows.items()}}, sys.stdout)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
