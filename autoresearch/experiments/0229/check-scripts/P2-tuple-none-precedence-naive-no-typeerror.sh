#!/bin/sh
# 0229 check (P2): when the exact (tzname, tzoffset) tuple key is present with value None and a name-only key also matches, the tuple entry is selected by key presence: the selected None gives a naive result, and an unsupported name-key value is never converted, so no TypeError (spec.md Requirements 2 and 4). Exit 0 = clause holds.
set -eu
cd "$1"
export PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1
exec python3 - "$PWD" <<'PY'
import os
import sys
from datetime import datetime

import dateutil
from dateutil.parser import parse
from dateutil.tz import tzoffset

tree = os.path.realpath(sys.argv[1])
assert os.path.realpath(dateutil.__file__).startswith(tree + "/src/"), dateutil.__file__

TEXT = "2012-01-19 17:21:00 -0300 (BRST)"
WALL = datetime(2012, 1, 19, 17, 21)

failures = []
# The name-key values the findings use as the competing entry, plus the
# unsupported name-key value of their TypeError claim.
for name_value in (3600, -14400, tzoffset("NAME", -14400), object()):
    tzinfos = {("BRST", -10800): None, "BRST": name_value}
    try:
        result = parse(TEXT, tzinfos=tzinfos)
    except Exception as exc:  # any exception departs from the required naive result
        failures.append("%r: raised %s: %s" % (name_value, type(exc).__name__, exc))
        continue
    if result.tzinfo is not None or result != WALL:
        failures.append("%r: got %r, expected naive %r" % (name_value, result, WALL))

if failures:
    sys.exit("violated:\n" + "\n".join(failures))
print("holds")
PY
