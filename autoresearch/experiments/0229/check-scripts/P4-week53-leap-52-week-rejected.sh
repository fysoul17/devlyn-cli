#!/bin/sh
# 0229 check (P4): Requirement 1 - isoparse, isoparser.isoparse and isoparser.parse_isodate reject week 53 with ValueError for Gregorian leap years whose ISO week-year has 52 weeks (2000, 2012, 2016, 2024, 2028, 2052), dashed and compact, with and without a weekday. Exit 0 = clause holds.
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
accepted = []
for year in (2000, 2012, 2016, 2024, 2028, 2052):
    assert calendar.isleap(year) and date(year, 12, 28).isocalendar()[1] == 52, year
    for text in ("{}-W53".format(year), "{}W53".format(year), "{}-W53-1".format(year)):
        for name, parse_fn in (("isoparse", isoparse), ("isoparser().isoparse", parser.isoparse),
                               ("isoparser().parse_isodate", parser.parse_isodate)):
            try:
                got = parse_fn(text)
            except ValueError:
                continue
            accepted.append("{}({!r}) -> {!r}".format(name, text, got))
if accepted:
    sys.exit("violated: " + "; ".join(accepted))
print("holds")
PY
