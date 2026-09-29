#!/bin/sh
# 0226 check (C4): after Cache.resize(maxsize), currsize (getsizeof-based) is no
# greater than the requested capacity. Exit 0 = clause holds.
set -eu
cd "$1"
exec python3 - <<'PY'
import cachetools

cache = cachetools.Cache(10, getsizeof=len)
cache["a"] = "xxx"
cache["b"] = "yyy"  # currsize 6 with two entries
cache.resize(4)
assert cache.maxsize == 4
assert cache.currsize <= 4, cache.currsize
PY
