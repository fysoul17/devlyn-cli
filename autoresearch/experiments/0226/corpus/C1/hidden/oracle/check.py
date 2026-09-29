import json

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
    return Cache.currsize.fget(cache)


def bounded_drain():
    cache, clock = make_cache()
    cache.update(a=2, b=4, c=8)
    assert cache.expire(10, limit=2) == [("a", 2), ("b", 4)]
    assert resident_size(cache) == 1
    assert Cache.__len__(cache) == 1
    assert cache.expire(10) == [("c", 8)]
    assert resident_size(cache) == 0


def zero_validation_exact_cutoff():
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


def logical_expiry_timer_selection():
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


def obsolete_record_before_eligible_value():
    cache, clock = make_cache()
    cache.update(a=2, b=3, c=10)
    del cache["a"]
    assert cache.expire(3, limit=1) == [("b", 3)]
    assert resident_size(cache) == 1
    assert cache.expire(3) == []
    assert cache["c"] == 10


def unlimited_replacement_cleanup():
    cache, clock = make_cache()
    cache.update(a=2, b=5)
    cache["a"] = 9
    assert cache.expire(5) == [("b", 5)]
    assert cache["a"] == 9
    assert cache.expire(9) == [("a", 9)]


rows = {
    "C1-O1": bounded_drain,
    "C1-O2": zero_validation_exact_cutoff,
    "C1-O3": logical_expiry_timer_selection,
    "C1-O4": obsolete_record_before_eligible_value,
    "C1-O5": unlimited_replacement_cleanup,
}

results = {}
for name, check in rows.items():
    try:
        check()
    except Exception:
        results[name] = False
    else:
        results[name] = True

print(json.dumps({"rows": results}))
