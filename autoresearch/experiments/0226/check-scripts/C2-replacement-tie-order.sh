#!/bin/sh
# 0226 check (C2): among equal deadlines, a replaced value takes a new position
# after entries already assigned that deadline. Exit 0 = clause holds.
set -eu
cd "$1"
exec python3 - <<'PY'
import cachetools


def cache():
    return cachetools.TLRUCache(10, ttu=lambda key, value, now: value[0], timer=lambda: 0)


# Replacement with the same deadline.
c = cache()
c["a"] = (10, "A")
c["b"] = (10, "B")
c["a"] = (10, "A2")
assert c.expire(10) == [("b", (10, "B")), ("a", (10, "A2"))]

# Replacement moving into an existing deadline group.
c = cache()
c["a"] = (5, "old")
c["b"] = (10, "B")
c["a"] = (10, "new")
assert c.expire(10) == [("b", (10, "B")), ("a", (10, "new"))]
PY
