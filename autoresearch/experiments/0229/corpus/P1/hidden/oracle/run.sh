#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    echo 'usage: oracle/run.sh <tree>' >&2
    exit 2
fi

candidate_tree=$(cd "$1" && pwd -P)
oracle_tmp=$(mktemp -d /private/tmp/dateutil-oracle.XXXXXX)
trap 'rm -rf "$oracle_tmp"' EXIT HUP INT TERM
cd "$oracle_tmp"

PYTHONPATH="$candidate_tree/src" PYTHONDONTWRITEBYTECODE=1 \
XDG_CACHE_HOME="$oracle_tmp" HYPOTHESIS_STORAGE_DIRECTORY="$oracle_tmp/hypothesis" \
/Users/Shared/devlyn-vr-0228-dev/screen-0229/toolchains/dateutil/venv/bin/python - <<'PY'
import json
from datetime import datetime, timedelta

from dateutil.rrule import DAILY, rrule, rruleset
import pytest


START = datetime(2024, 1, 1)


def dates(n):
    return [START + timedelta(days=i) for i in range(n)]


def make_rule(cache=False, n=25):
    return rrule(DAILY, dtstart=START, count=n, cache=cache)


def prepare(kind, mode):
    if kind == 'rule':
        obj = make_rule(cache=(mode != 'off'))
        expected = dates(25)
    else:
        obj = rruleset(cache=(mode != 'off'))
        obj.rrule(make_rule())
        obj.exdate(START + timedelta(days=3))
        expected = [d for d in dates(25) if d != START + timedelta(days=3)]
    if mode == 'partial':
        assert obj[0] == expected[0]
        assert not obj._cache_complete
    elif mode == 'complete':
        assert list(obj) == expected
        assert obj._cache_complete
    return obj, expected


def negative_and_reverse():
    for kind in ('rule', 'set'):
        for mode in ('off', 'partial', 'complete'):
            for sl in (slice(-3, None), slice(None, -1), slice(1, -1, 2),
                       slice(-100, 3), slice(-3, -1), slice(None, None, -1),
                       slice(4, 1, -2)):
                obj, expected = prepare(kind, mode)
                assert obj[sl] == expected[sl]


def explicit_zero_endpoint():
    obj = make_rule(n=5)
    assert obj[:0] == []


def forward_and_omitted():
    for kind in ('rule', 'set'):
        for mode in ('off', 'partial', 'complete'):
            obj, expected = prepare(kind, mode)
            assert obj[:] == expected
            assert obj[1:4:2] == expected[1:4:2]
            assert obj[4:2] == []
            assert obj[0] == expected[0]
            assert obj[-1] == expected[-1]

    class IndexBound(object):
        def __init__(self, value):
            self.value = value

        def __index__(self):
            return self.value

    obj = make_rule(n=5)
    assert obj[IndexBound(1):IndexBound(4)] == dates(5)[1:4]

    for kind in ('rule', 'set'):
        for mode in ('off', 'partial', 'complete'):
            for bound in (1.0, '1'):
                for sl in (slice(bound, 3), slice(1, bound)):
                    obj, _ = prepare(kind, mode)
                    with pytest.raises(TypeError):
                        obj[sl]


def step_zero():
    for mode in ('off', 'partial', 'complete'):
        obj, _ = prepare('rule', mode)
        with pytest.raises(ValueError):
            obj[::0]
    for cache in (False, True):
        obj = make_rule(cache=cache, n=0)
        with pytest.raises(ValueError):
            obj[::0]


def incremental_prefix():
    class GuardedRule(rrule):
        def _iter(self):
            for d in dates(3):
                yield d
            raise AssertionError('prefix exhausted the recurrence')

    obj = GuardedRule(DAILY, dtstart=START)
    assert obj[1:3] == dates(3)[1:3]


rows = {}
for row_id, check in (
    ('P1-N', negative_and_reverse),
    ('P1-W', explicit_zero_endpoint),
    ('P1-F', forward_and_omitted),
    ('P1-Z', step_zero),
    ('P1-L', incremental_prefix),
):
    try:
        check()
    except (Exception, pytest.fail.Exception):
        rows[row_id] = False
    else:
        rows[row_id] = True

print(json.dumps({'rows': rows}, separators=(',', ':')))
PY
