#!/bin/sh
# 0229 check (P1): "an explicit stop of zero returns an empty list" (spec.md Requirements), the same with caching disabled, an incomplete cache and a completed cache, and without exhausting the recurrence. Exit 0 = clause holds.
set -eu
cd "$1"
export PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1
exec python3 - "$PWD" <<'PY'
import os
import sys
from datetime import datetime, timedelta

import dateutil

assert os.path.realpath(dateutil.__file__).startswith(
    os.path.realpath(sys.argv[1]) + "/src/"
), dateutil.__file__

from dateutil.rrule import DAILY, rrule, rruleset

START = datetime(2024, 1, 1)
ZERO_STOPS = (slice(None, 0), slice(0, 0), slice(2, 0))


def dates(n):
    return [START + timedelta(days=i) for i in range(n)]


def prepare(kind, mode):
    cache = mode != "off"
    rule = rrule(DAILY, dtstart=START, count=25, cache=cache)
    if kind == "rule":
        obj, expected = rule, dates(25)
    else:
        obj = rruleset(cache=cache)
        obj.rrule(rrule(DAILY, dtstart=START, count=25))
        obj.exdate(START + timedelta(days=3))
        expected = [d for d in dates(25) if d != START + timedelta(days=3)]
    if mode == "partial":
        assert obj[0] == expected[0]
        assert not obj._cache_complete, "setup: cache unexpectedly complete"
    elif mode == "complete":
        assert list(obj) == expected
        assert obj._cache_complete, "setup: cache not complete"
    return obj


failures = []

# A nonempty finite rrule/rruleset in every cache state: [:0], [0:0], [2:0] must be [].
for kind in ("rule", "set"):
    for mode in ("off", "partial", "complete"):
        for sl in ZERO_STOPS:
            got = prepare(kind, mode)[sl]
            if got != []:
                failures.append(
                    "%s cache=%s [%s:%s] returned %d occurrence(s), not []"
                    % (kind, mode, sl.start, sl.stop, len(got))
                )


# An empty prefix must not exhaust the recurrence (an unbounded rrule whose
# iteration fails after three occurrences stands in for an infinite one).
class GuardedRule(rrule):
    def _iter(self):
        for d in dates(3):
            yield d
        raise AssertionError("explicit zero stop exhausted the recurrence")


for sl in ZERO_STOPS:
    try:
        got = GuardedRule(DAILY, dtstart=START)[sl]
    except AssertionError as exc:
        failures.append("guarded [%s:%s]: %s" % (sl.start, sl.stop, exc))
    else:
        if got != []:
            failures.append(
                "guarded [%s:%s] returned %d occurrence(s), not []"
                % (sl.start, sl.stop, len(got))
            )

if failures:
    sys.exit("violated:\n  " + "\n  ".join(failures))
print("holds")
PY
