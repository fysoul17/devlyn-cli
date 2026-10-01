#!/bin/sh
# 0229 check (P3): after set_cache_size(-1) is rejected on a size-3 gettz cache retaining only A, a lookup of new zone B evicts nothing (A and B both stay retained). Exit 0 = clause holds.
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
refs = {"A": weakref.ref(g("A"))}
gc.collect()
assert refs["A"]() is not None, "setup: size-3 cache did not retain A"

try:
    g.set_cache_size(-1)
except Exception as exc:
    rejected = type(exc).__name__
else:
    sys.exit("violated: set_cache_size(-1) was accepted, committing a negative capacity")

refs["B"] = weakref.ref(g("B"))
gc.collect()
lost = [name for name in "AB" if refs[name]() is None]
if lost:
    sys.exit("violated: after rejected set_cache_size(-1) (%s), the lookup of B left %s unretained" % (rejected, lost))
print("holds")
PY
