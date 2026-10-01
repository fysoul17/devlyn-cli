---
id: "P4"
title: "Validate ISO week numbers against their week-year"
kind: feature
status: planned
complexity: medium
depends_on: []
---

# Validate ISO week numbers against their week-year

## Context

The ISO parser accepts week dates, but checking only that a week number lies between 1 and 53 can turn a nonexistent week into a date in a different ISO year. Applications importing schedules need an invalid year/week combination to be rejected, while valid dates spanning a calendar-year boundary must continue to work. Validate the week and its ISO year together.

## Requirements

- [ ] `isoparse`, `isoparser.isoparse`, and `isoparser.parse_isodate` reject a week number that does not exist in the supplied ISO week-year with `ValueError`, including week 53 in a 52-week ISO year.
- [ ] Valid week dates continue to return the corresponding Gregorian date even when its calendar year differs from the supplied ISO week-year.
- [ ] Apply the year/week validation to both compact and dashed week-date forms, including date-only week forms whose omitted weekday defaults to Monday.
- [ ] Preserve the existing weekday range of 1 through 7 and reject week numbers outside 1 through 53 with `ValueError`.
- [ ] For supported full datetime inputs, changing week validation preserves the parsed time, fractional seconds, and timezone offset.
- [ ] Preserve calendar-date and ordinal-date parsing, ASCII string/bytes/stream handling, and the configured date/time separator behavior. Document the ISO week-year validity rule in the parser source.

## Constraints

- Change only `src/dateutil/parser/isoparser.py` and `tests/test_isoparser.py`, because the common ISO week-date conversion helper and its tests own this validation.
- Add no dependencies, because `calendar` and `datetime` already provide the needed calendar calculations.
- Keep the existing test, coverage, and tooling configuration unchanged, so accepted-format regressions remain visible.
- Preserve the project's existing Python compatibility conventions, because the ISO parser supports the same interpreters as the library.

## Out of Scope

- New ISO input formats or expanded years.
- Changes to the general-purpose `parse` API or recurrence rules.
- Changes to fractional-time parsing, offset parsing, or midnight rollover.
- Representing dates outside the range supported by `datetime.date`.

<!-- devlyn:verification -->
## Verification

- `PYTHONPATH=src COVERAGE_FILE=.tox/.coverage /Users/Shared/devlyn-vr-0228-dev/screen-0229/toolchains/dateutil/venv/bin/python -m pytest tests docs --cov-config=tox.ini --cov=dateutil --cov-fail-under=80` exits 0. This runs the repository's test command, including added invalid year/week combinations, valid calendar-year spillovers, and datetime-field preservation across both ISO parsing entry points; it enforces the project coverage target from `codecov.yml` locally.

- `XDG_CACHE_HOME=.cache BLACK_CACHE_DIR=.cache/black /Users/Shared/devlyn-vr-0228-dev/screen-0229/toolchains/dateutil/venv/bin/python -m darker --check --diff --color --isort --revision "$(git rev-list --max-parents=0 HEAD)" .` exits 0. This is the read-only Darker/isort check from the validation workflow, comparing changes with the pinned base at the root commit; formatter caches are directed to ignored output paths.
- `/Users/Shared/devlyn-vr-0228-dev/screen-0229/toolchains/dateutil/venv/bin/python -m pre_commit_hooks.debug_statement_hook src/dateutil/parser/isoparser.py tests/test_isoparser.py` exits 0. This runs the configured debug-statement hook on the two authorized Python files.
- `git diff --check "$(git rev-list --max-parents=0 HEAD)" -- src/dateutil/parser/isoparser.py tests/test_isoparser.py` exits 0. This checks changed-line whitespace against the pinned base at the root commit without invoking the configured whitespace fixer.

The automated checks provide baseline and selected regression coverage. Requirements and constraints not exercised by them remain source-review obligations. No type-check command is configured in this repository.
