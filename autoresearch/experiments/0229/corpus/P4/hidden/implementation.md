# P4 implementation instructions

Family: cross-field consistency. Apply this request alone to the pinned tree.

## Reference design

Change exactly `src/dateutil/parser/isoparser.py` and `tests/test_isoparser.py`; preserve this changed-file set and the test contents in the twin.

The shared `_calculate_weekdate(year, week, day)` checks numeric week/day ranges, finds the Monday of ISO week one from January 4, then adds a day offset. It currently allows week 53 for every year. Add a year-dependent check before returning a constructed date, using existing `calendar`/`datetime` imports.

An ISO year has 53 weeks exactly when January 1 is Thursday, or January 1 is Wednesday and the Gregorian year is a leap year. With `weekday()` using Monday=0, a direct implementation is:

```python
jan1_weekday = date(year, 1, 1).weekday()
has_week_53 = (jan1_weekday == 3 or
               (jan1_weekday == 2 and calendar.isleap(year)))
if week == 53 and not has_week_53:
    raise ValueError('Invalid week: {} for year {}'.format(week, year))
```

Alternatively the reference may derive the last ISO week from December 28, but use the explicit predicate above if doing so makes the required single twin edit easiest to keep local. Maintain the existing week/day range checks and week-one arithmetic. Do not reject a valid date merely because the resulting Gregorian year differs from `year`: for example, `2015-W53-7` means January 3, 2016, and belongs to ISO year 2015. All entry points and accepted byte/stream forms share this helper.

Update the parser's week-date documentation and the helper's week-range description in this same source file. No new exported API or dependency is needed.

## Public tests added to the repository

Use the conventions and format parametrization already in `tests/test_isoparser.py`.

- Reject week 53 for Gregorian non-leap years 2014 and 2017, whose ISO week-years have 52 weeks, with `ValueError`. Cover compact/dashed forms, explicit weekdays, omitted weekday in date-only forms, and full datetimes with an explicit weekday. Exercise module-level `isoparse`, instance `isoparse`, and `parse_isodate` as applicable.
- Accept week 53 in 2015 and 2020, including Sunday spillovers to January 3 of the following calendar year; retain the existing 2004 and 2009 cases.
- Accept week one of 2020 beginning December 30, 2019, and week 52 of 2014. Cover date-only and explicit-time conversions.
- Check a full valid input such as `2020-W53-7T01:02:03.456789+02:30`: Gregorian date January 3, 2021, the stated wall time/microseconds, and a +02:30 offset all survive conversion.
- Existing range-error, stream/bytes, separator, calendar, and ordinal tests remain. A few representative regressions may be added if useful.

Do not add invalid-week-53 cases for Gregorian leap years to public tests or exhaustive/property-test year matrices. In particular, 2016 and 2024 have only 52 ISO weeks but are the cases the target predicate mishandles. The existing suite's accepted week-53 leap-year example (2004) is valid and passes both patches.

## Twin construction

Replace only the reference's `has_week_53` predicate with:

```python
has_week_53 = (jan1_weekday == 3 or calendar.isleap(year))
```

Keep all bounds checks, error text, conversion arithmetic, documentation, and public tests unchanged. This accidentally treats leap-year status as sufficient for week 53, instead of also requiring a Wednesday January 1 for that arm of the predicate. It is a plausible oversimplification of the two calendar conditions.

Do not use names or comments that disclose the defect. The twin still rejects ordinary 52-week non-leap years and accepts the public valid examples, but accepts week 53 for a Gregorian leap year whose ISO week-year has only 52 weeks. The public suite does not cover that combination and whole-project coverage remains above the declared target.
