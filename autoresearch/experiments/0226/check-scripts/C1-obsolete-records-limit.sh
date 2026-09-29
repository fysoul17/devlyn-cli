#!/bin/sh
# 0226 check (C1): obsolete TLRU heap records from overwritten or deleted keys
# must not count toward expire(limit=...). Exit 0 = clause holds.
set -eu
cd "$1"
exec python3 - <<'PY'
import cachetools


def cache():
    return cachetools.TLRUCache(10, ttu=lambda key, value, now: value, timer=lambda: 0)


# Overwrite: obsolete a@2 sits ahead of resident b@3 and a@4 (no compaction: 3 records, 2 items).
c = cache()
c["a"] = 2
c["b"] = 3
c["a"] = 4
assert c.expire(4, limit=1) == [("b", 3)]

# Single overwritten key: the obsolete record must not consume the only slot.
c = cache()
c["a"] = 2
c["a"] = 4
assert c.expire(4, limit=1) == [("a", 4)]

# Deletion: obsolete a@1 ahead of resident b@2 and c@3.
c = cache()
c["a"] = 1
c["b"] = 2
c["c"] = 3
del c["a"]
assert c.expire(3, limit=1) == [("b", 2)]
PY
