import json
import sys
import time
import warnings
from datetime import datetime, timedelta

from dateutil import tz
from dateutil.parser import UnknownTimezoneWarning, parse, parser


TEXT = '2012-01-19 17:21:00 -0300 (BRST)'
NAME_TEXT = '2012-01-19 17:21:00 BRST'
NUM_TEXT = '2012-01-19 17:21:00 -0300'
WALL = datetime(2012, 1, 19, 17, 21)
PAIR_ZONE = tz.tzoffset('PAIR', -7200)
NAME_ZONE = tz.tzoffset('NAME', -14400)


def priority_and_fallback():
    mapping = {('BRST', -10800): PAIR_ZONE, 'BRST': NAME_ZONE}
    for parse_fn in (parse, parser().parse):
        exact = parse_fn(TEXT, tzinfos=mapping)
        fallback = parse_fn(NAME_TEXT, tzinfos=mapping)
        ignored = parse_fn(TEXT, tzinfos=mapping, ignoretz=True)
        assert exact.tzinfo is PAIR_ZONE
        assert fallback.tzinfo is NAME_ZONE
        assert exact.replace(tzinfo=None) == WALL
        assert fallback.replace(tzinfo=None) == WALL
        assert ignored == WALL and ignored.tzinfo is None


def present_none():
    mapping = {('BRST', -10800): None, 'BRST': NAME_ZONE}
    result = parse(TEXT, tzinfos=mapping)
    assert result.tzinfo is None
    assert result == WALL


def conversions():
    for value, seconds in ((3600, 3600), (0, 0), ('UTC+0', 0)):
        result = parse(TEXT, tzinfos={('BRST', -10800): value,
                                      'BRST': NAME_ZONE})
        assert result.utcoffset() == timedelta(seconds=seconds)
        assert result.replace(tzinfo=None) == WALL
    assert parse(NAME_TEXT, tzinfos={('BRST', None): PAIR_ZONE}).tzinfo is PAIR_ZONE
    assert parse(NUM_TEXT, tzinfos={(None, -10800): PAIR_ZONE}).tzinfo is PAIR_ZONE
    assert parse(TEXT, tzinfos={('BRST', -10800): None}).tzinfo is None
    try:
        parse(TEXT, tzinfos={('BRST', -10800): object(), 'BRST': NAME_ZONE})
    except TypeError:
        pass
    else:
        raise AssertionError('invalid pair value was accepted')


def built_in_and_legacy():
    assert parse(TEXT, tzinfos={('BRST', 3600): PAIR_ZONE,
                                'BRST': NAME_ZONE}).tzinfo is NAME_ZONE
    assert parse(NUM_TEXT, tzinfos={('BRST', 3600): PAIR_ZONE}).utcoffset() == timedelta(hours=-3)
    assert parse(NAME_TEXT, tzinfos={'BRST': None}).tzinfo is None
    unknown = next(name for name in ('XYZ', 'QXZ', 'QZT')
                   if name not in time.tzname)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always', UnknownTimezoneWarning)
        result = parse('2012-01-19 17:21:00 ' + unknown,
                       tzinfos={('BRST', 3600): PAIR_ZONE})
    assert any(issubclass(item.category, UnknownTimezoneWarning)
               for item in caught)
    assert result == WALL and result.tzinfo is None


def callbacks_and_bypass():
    calls = []

    def resolve(name, offset):
        calls.append((name, offset))
        return PAIR_ZONE

    assert parse(TEXT, tzinfos=resolve).tzinfo is PAIR_ZONE
    assert calls == [('BRST', -10800)]
    assert parse(TEXT, tzinfos=resolve, ignoretz=True) == WALL
    assert calls == [('BRST', -10800)]

    class UnreadableMapping(dict):
        def __contains__(self, key):
            raise AssertionError('unexpected lookup')

        def get(self, key, default=None):
            raise AssertionError('unexpected lookup')

        def __getitem__(self, key):
            raise AssertionError('unexpected lookup')

    mapping = UnreadableMapping({('BRST', -10800): PAIR_ZONE})
    assert parse(TEXT, tzinfos=mapping, ignoretz=True) == WALL


ROWS = {
    'P2-P': priority_and_fallback,
    'P2-W': present_none,
    'P2-V': conversions,
    'P2-B': built_in_and_legacy,
    'P2-C': callbacks_and_bypass,
}


def main():
    results = {}
    for row_id, check in ROWS.items():
        try:
            check()
        except Exception:
            results[row_id] = False
        else:
            results[row_id] = True
    print(json.dumps({'rows': results}, separators=(',', ':')))


if __name__ == '__main__':
    main()
