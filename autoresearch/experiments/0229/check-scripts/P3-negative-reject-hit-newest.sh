#!/bin/sh
# 0229 check (P3): after set_cache_size(-1) is rejected on a size-3 gettz cache retaining A, B, C, a cache hit on C reuses C and evicts nothing (A, B, C stay retained). Exit 0 = clause holds.
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

hit = g("C")
if hit is not refs["C"]():
    sys.exit("violated: after rejected set_cache_size(-1) (%s), lookup of C did not reuse the cached C" % rejected)
del hit
gc.collect()
lost = [name for name in "ABC" if refs[name]() is None]
if lost:
    sys.exit("violated: after rejected set_cache_size(-1) (%s), the hit on C evicted %s" % (rejected, lost))
print("holds")
PY
