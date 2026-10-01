from datetime import date, datetime, timedelta
from io import BytesIO, StringIO
import json
import sys

from dateutil.parser import isoparse, isoparser


def raises_value_error(parse_fn, value):
    try:
        parse_fn(value)
    except ValueError:
        return
    raise AssertionError('Expected ValueError for {!r}'.format(value))


def row_r():
    parser = isoparser()
    for year in (2014, 2017):
        for value in ('{}-W53'.format(year), '{}W53'.format(year),
                      '{}-W53-1'.format(year), '{}W537'.format(year)):
            for parse_fn in (isoparse, parser.isoparse, parser.parse_isodate):
                raises_value_error(parse_fn, value)
        for value in ('{}-W53-1T12:34:56Z'.format(year),
                      '{}W531T123456+02'.format(year)):
            raises_value_error(isoparse, value)


def row_w():
    raises_value_error(isoparse, '2016-W53-1')


def row_a():
    parser = isoparser()
    examples = (
        ('2004-W53-7', date(2005, 1, 2)),
        ('2009-W53-6', date(2010, 1, 2)),
        ('2015-W53-7', date(2016, 1, 3)),
        ('2020-W53-7', date(2021, 1, 3)),
        ('2020-W01-1', date(2019, 12, 30)),
        ('2014-W52-7', date(2014, 12, 28)),
        ('2020-W53', date(2020, 12, 28)),
    )
    for value, expected in examples:
        for form in (value, value.replace('-', '')):
            assert parser.parse_isodate(form) == expected
            assert isoparse(form) == datetime(expected.year, expected.month,
                                              expected.day)


def row_t():
    parser = isoparser()
    for parse_fn in (isoparse, parser.isoparse):
        result = parse_fn('2020-W53-7T01:02:03.456789+02:30')
        assert result.replace(tzinfo=None) == datetime(2021, 1, 3, 1, 2, 3,
                                                       456789)
        assert result.utcoffset() == timedelta(hours=2, minutes=30)


def row_b():
    parser = isoparser()
    for value in ('2020-W00-1', '2020-W54-1', '2020-W01-0', '2020-W01-8'):
        for parse_fn in (isoparse, parser.parse_isodate):
            raises_value_error(parse_fn, value)


def row_c():
    parser = isoparser()
    assert isoparse(b'2015-W53-7') == datetime(2016, 1, 3)
    assert parser.parse_isodate(BytesIO(b'2015W537')) == date(2016, 1, 3)
    assert isoparse(StringIO('2020-W01-1')) == datetime(2019, 12, 30)
    assert isoparse('2016-366') == datetime(2016, 12, 31)
    assert parser.parse_isodate('2016-02-29') == date(2016, 2, 29)
    strict = isoparser(sep='T')
    assert strict.isoparse('2020-W53-7T12:00') == datetime(2021, 1, 3, 12)
    raises_value_error(strict.isoparse, '2020-W53-7_12:00')


def main():
    rows = {}
    for name, check in (('P4-R', row_r), ('P4-W', row_w), ('P4-A', row_a),
                        ('P4-T', row_t), ('P4-B', row_b), ('P4-C', row_c)):
        try:
            check()
        except Exception:
            rows[name] = False
        else:
            rows[name] = True
    json.dump({'rows': rows}, sys.stdout)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
