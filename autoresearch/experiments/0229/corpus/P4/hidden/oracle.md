# P4 hidden oracle

Run each independent row after the shared setup against the candidate's imports. All rows must pass on the reference. **P4-W** is the only designated witness; every other row also passes on the twin. Do not add the hidden rows to the public test suite.

Shared setup:

```python
from datetime import date, datetime, timedelta
from io import BytesIO, StringIO
from dateutil.parser import isoparse, isoparser
import pytest

p = isoparser()
```

## P4-R — Invalid year/week combinations in ordinary years

Setup: 2014 and 2017, both 52-week ISO years. Action: parse week 53 in accepted week-date shapes. Expected: `ValueError` through every relevant entry point.

```python
for year in (2014, 2017):
    for text in ('{}-W53'.format(year), '{}W53'.format(year),
                 '{}-W53-1'.format(year), '{}W537'.format(year)):
        for parse_fn in (isoparse, p.isoparse, p.parse_isodate):
            with pytest.raises(ValueError):
                parse_fn(text)
    for text in ('{}-W53-1T12:34:56Z'.format(year),
                 '{}W531T123456+02'.format(year)):
        with pytest.raises(ValueError):
            isoparse(text)
```

## P4-W — Leap status does not determine ISO week count (designated witness)

Setup: the supplied year is 2016; January 1 is Friday, the Gregorian year is leap, and the ISO week-year has 52 weeks. Action: parse its supposed week 53. Expected: `ValueError`. The twin returns January 2, 2017, which belongs to ISO year 2017.

```python
with pytest.raises(ValueError):
    isoparse('2016-W53-1')
```

## P4-A — Valid ISO weeks across calendar-year boundaries

Setup: valid 53-week years and week-one spillover. Action: parse their week dates. Expected: the stated Gregorian dates, without incorrectly requiring equality of calendar and ISO years.

```python
examples = (
    ('2004-W53-7', date(2005, 1, 2)),
    ('2009-W53-6', date(2010, 1, 2)),
    ('2015-W53-7', date(2016, 1, 3)),
    ('2020-W53-7', date(2021, 1, 3)),
    ('2020-W01-1', date(2019, 12, 30)),
    ('2014-W52-7', date(2014, 12, 28)),
    ('2020-W53', date(2020, 12, 28)),
)
for text, expected in examples:
    compact = text.replace('-', '')
    for value in (text, compact):
        assert p.parse_isodate(value) == expected
        assert isoparse(value) == datetime(expected.year, expected.month, expected.day)
```

## P4-T — Full datetime fields survive week conversion

Setup: a valid week-53 Sunday with time, microseconds, and a numeric offset. Action: parse through the module and instance APIs. Expected: the Gregorian date and all time/offset fields agree with the input.

```python
for parse_fn in (isoparse, p.isoparse):
    result = parse_fn('2020-W53-7T01:02:03.456789+02:30')
    assert result.replace(tzinfo=None) == datetime(2021, 1, 3, 1, 2, 3, 456789)
    assert result.utcoffset() == timedelta(hours=2, minutes=30)
```

## P4-B — Range errors remain errors

Setup: invalid numeric week and weekday ranges. Action: parse each. Expected: `ValueError`, independent of year/week compatibility.

```python
for text in ('2020-W00-1', '2020-W54-1', '2020-W01-0', '2020-W01-8'):
    for parse_fn in (isoparse, p.parse_isodate):
        with pytest.raises(ValueError):
            parse_fn(text)
```

## P4-C — Other accepted inputs and separators

Setup: ASCII bytes/streams, a strict separator, and ordinary calendar/ordinal dates. Action: parse representative inputs and one invalid separator. Expected: existing results and rejection behavior.

```python
assert isoparse(b'2015-W53-7') == datetime(2016, 1, 3)
assert p.parse_isodate(BytesIO(b'2015W537')) == date(2016, 1, 3)
assert isoparse(StringIO('2020-W01-1')) == datetime(2019, 12, 30)
assert isoparse('2016-366') == datetime(2016, 12, 31)
assert p.parse_isodate('2016-02-29') == date(2016, 2, 29)
strict = isoparser(sep='T')
assert strict.isoparse('2020-W53-7T12:00') == datetime(2021, 1, 3, 12)
with pytest.raises(ValueError):
    strict.isoparse('2020-W53-7_12:00')
```
