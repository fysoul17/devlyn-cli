#!/bin/sh
# 0229 check (P3): a rejected set_cache_size(-1) leaves the size-3 capacity, retained zones and recency unchanged: later hits on C and A evict nothing, and a new zone D then evicts exactly the LRU entry B. Exit 0 = clause holds.
set -eu
cd "$1"
PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1 exec python - "$PWD" <<'PY'
import gc
import os
import sys
import weakref
from datetime import timedelta, tzinfo

from dateutil import tz

assert os.path.realpath(tz.__file__).startswith(os.path.realpath(sys.argv[1]) + "/src/"), tz.__file__


class Zone(tzinfo):
    def __init__(self, name):
        self.name = name

    def utcoffset(self, dt):
        return timedelta(0)

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return self.name


g = type(tz.gettz)()
g.nocache = lambda name=None: Zone(name)
g.set_cache_size(3)
refs = {name: weakref.ref(g(name)) for name in "ABC"}
gc.collect()
assert all(ref() is not None for ref in refs.values()), "setup: size-3 cache did not retain A, B, C"

try:
    g.set_cache_size(-1)
except Exception as exc:
    rejected = type(exc).__name__
else:
    sys.exit("violated: set_cache_size(-1) was accepted, committing a negative capacity")

for name in "CA":
    hit = g(name)
    if hit is not refs[name]():
        sys.exit("violated: after rejected set_cache_size(-1) (%s), lookup of %s did not reuse the cached object" % (rejected, name))
    del hit
    gc.collect()
    lost = [other for other in "ABC" if refs[other]() is None]
    if lost:
        sys.exit("violated: after rejected set_cache_size(-1) (%s), the hit on %s evicted %s" % (rejected, name, lost))

refs["D"] = weakref.ref(g("D"))
gc.collect()
alive = sorted(name for name, ref in refs.items() if ref() is not None)
if alive != ["A", "C", "D"]:
    sys.exit("violated: after rejected set_cache_size(-1) (%s), inserting D under capacity 3 left %s retained, expected ['A', 'C', 'D']" % (rejected, alive))
print("holds")
PY
