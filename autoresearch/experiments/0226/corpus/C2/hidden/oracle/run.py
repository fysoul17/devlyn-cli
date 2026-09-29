import json
import pathlib
import sys


tree = pathlib.Path(sys.argv[1]).resolve()
if not (tree / "src" / "cachetools" / "__init__.py").is_file():
    raise SystemExit("tree has no cachetools source")
sys.path.insert(0, str(tree / "src"))

from cachetools import TLRUCache  # noqa: E402


def make_cache(maxsize=20):
    return TLRUCache(maxsize, lambda key, value, now: value[0], timer=lambda: 0)


def o1():
    cache = make_cache()
    cache["a"] = (10, "A")
    cache["b"] = (5, "B")
    cache["c"] = (10, "C")
    cache["d"] = (5, "D")
    return (
        cache["a"] == (10, "A")
        and "b" in cache
        and [key for key, value in cache.expire(10)] == ["b", "d", "a", "c"]
        and cache.currsize == 0
    )


def o2():
    cache = make_cache()
    cache["a"] = (5, "old")
    cache["b"] = (8, "B")
    cache["a"] = (12, "new")
    return cache.expire(8) == [("b", (8, "B"))] and cache.expire(12) == [
        ("a", (12, "new"))
    ]


def o3():
    cache = make_cache()
    cache["a"] = (10, "old")
    cache["b"] = (10, "B")
    cache["c"] = (10, "C")
    cache["a"] = (10, "new")
    return cache.expire(10) == [
        ("b", (10, "B")),
        ("c", (10, "C")),
        ("a", (10, "new")),
    ] and len(cache) == 0


def o4():
    cache = make_cache()
    for key in range(6):
        cache[key] = (10, key)
    for key in range(4):
        del cache[key]
    return cache.expire(10) == [(4, (10, 4)), (5, (10, 5))]


def o5():
    cache = make_cache(2)
    a, b, c = object(), object(), object()
    cache[a] = (10, "A")
    cache[b] = (10, "B")
    if cache[a] != (10, "A"):
        return False
    cache[c] = (10, "C")
    return b not in cache and cache.expire(10) == [
        (a, (10, "A")),
        (c, (10, "C")),
    ]


def o6():
    cache = TLRUCache(2, lambda key, value, now: 10, timer=lambda: 0, getsizeof=len)
    cache["a"] = "A"
    cache["b"] = "B"
    try:
        cache["a"] = "too large"
    except ValueError:
        pass
    else:
        return False
    return cache.expire(10) == [("a", "A"), ("b", "B")]


def run(check):
    try:
        return bool(check())
    except Exception:
        return False


checks = {
    "C2-O1": o1,
    "C2-O2": o2,
    "C2-O3": o3,
    "C2-O4": o4,
    "C2-O5": o5,
    "C2-O6": o6,
}
print(json.dumps({"rows": {row: run(check) for row, check in checks.items()}}))
