# P4 mechanism record

- **Family:** cross-field consistency.
- **Mandatory clause:** “`isoparse`, `isoparser.isoparse`, and `isoparser.parse_isodate` reject a week number that does not exist in the supplied ISO week-year with `ValueError`, including week 53 in a 52-week ISO year.”
- **Trigger:** week 53 is supplied with a Gregorian leap-year number whose January 1 is neither Wednesday nor Thursday, such as 2016, so its ISO week-year has only 52 weeks.
- **Causal code path:** `_calculate_weekdate` applies its new week-53 predicate, but the twin uses `jan1_weekday == 3 or calendar.isleap(year)`. The leap-year arm omits the Wednesday condition and incorrectly allows the input through to the existing week-one-plus-offset calculation.
- **Incorrect behavior:** the parser fabricates a Gregorian date in the following ISO year instead of rejecting the inconsistent year/week fields. Numeric ranges alone are satisfied, but the fields do not describe an existing ISO week date.
- **Executable witness:** `P4-W` in `hidden/oracle.md`; the reference raises `ValueError` for `2016-W53-1`, while the twin returns `datetime(2017, 1, 2)`.
- **Near-miss exclusions:** rejecting legitimate Gregorian-year spillover; wrong default weekday; off-by-one week arithmetic; timezone or midnight normalization; week numbers outside 1–53. The twin preserves those behaviors. The missing weekday condition on leap years is the defect.
