#!/bin/sh
# 0229 check (P4): Requirement 1 (week 53 rejected with ValueError for the 52-week leap years 2000, 2012, 2016, 2024, 2028, 2052 through isoparse, isoparser.isoparse and parse_isodate) and, where the parser docstring states "Week 53 is valid only when January 1 is a Thursday, or a Wednesday in a leap year", the code accepts week 53 exactly in those years. Exit 0 = clause holds.
set -eu
cd "$1"
PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1 python3 - "$PWD" <<'PY'
import calendar
import os
import sys
from datetime import date

import dateutil
from dateutil.parser import isoparse, isoparser

assert os.path.realpath(dateutil.__file__).startswith(os.path.realpath(sys.argv[1]) + "/src/"), dateutil.__file__

parser = isoparser()
problems = []
for year in (2000, 2012, 2016, 2024, 2028, 2052):
    assert calendar.isleap(year) and date(year, 12, 28).isocalendar()[1] == 52, year
    for text in ("{}-W53".format(year), "{}W53".format(year), "{}-W53-1".format(year)):
        for name, parse_fn in (("isoparse", isoparse), ("isoparser().isoparse", parser.isoparse),
                               ("isoparser().parse_isodate", parser.parse_isodate)):
            try:
                got = parse_fn(text)
            except ValueError:
                continue
            problems.append("{}({!r}) -> {!r}".format(name, text, got))

doc = " ".join((isoparser.isoparse.__doc__ or "").split())
if "Week 53 is valid only when January 1 is a Thursday, or a Wednesday in a leap year" in doc:
    for year in range(1600, 2401):
        jan1 = date(year, 1, 1).weekday()
        documented = jan1 == 3 or (jan1 == 2 and calendar.isleap(year))
        try:
            parser.parse_isodate("{:04d}-W53".format(year))
        except ValueError:
            accepted = False
        else:
            accepted = True
        if accepted != documented:
            problems.append("docstring rule says week 53 of {} is {}, code {} it".format(
                year, "valid" if documented else "invalid", "accepts" if accepted else "rejects"))
if problems:
    sys.exit("violated: " + "; ".join(problems[:20]))
print("holds")
PY
