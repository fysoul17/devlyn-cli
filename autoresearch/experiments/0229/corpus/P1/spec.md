---
id: "P1"
title: "Make recurrence slices consistent across cache states"
kind: feature
status: planned
complexity: medium
depends_on: []
---

# Make recurrence slices consistent across cache states

## Context

Recurrence objects support subscription, but a slice can behave differently before and after their cache has been filled. Applications selecting a window or the last few occurrences should not need to materialize a recurrence first. Make these slices consistent while retaining incremental traversal for ordinary forward windows.

## Requirements

- [ ] For a finite `rrule` or `rruleset`, slices with negative start or stop indices, or a negative step, return the same list of occurrences as the corresponding slice of `list(recurrence)`.
- [ ] A forward slice with an omitted stop includes the remaining occurrences; an explicit stop of zero returns an empty list.
- [ ] A slice with step zero raises `ValueError`.
- [ ] Slice results and step-zero errors are the same with caching disabled, with an incomplete cache, and with a completed cache.
- [ ] Forward slices with nonnegative bounds and a positive step retain incremental traversal: a bounded prefix does not require exhausting the recurrence.
- [ ] Integer subscriptions, occurrence ordering, and recurrence generation retain their existing behavior.
- [ ] Slice bounds implementing the integer `__index__` protocol remain supported without coercing strings or floating-point values into integers.

## Constraints

- Change only `src/dateutil/rrule.py` and `tests/test_rrule.py`, because slicing belongs to the shared recurrence base and its existing tests.
- Add no dependencies, because Python's existing sequence and iterator facilities suffice.
- Keep the existing test, coverage, and tooling configuration unchanged, so the regression checks retain their meaning.
- Preserve the project's existing Python compatibility conventions, because the shared recurrence implementation serves all supported interpreters.

## Out of Scope

- New recurrence frequencies, filtering rules, or range-query methods.
- Optimizing negative-bound or reverse slices to avoid materialization.
- Changes to `before`, `after`, `xafter`, or `between`.
- Coercing strings or floating-point values into subscription arguments.

<!-- devlyn:verification -->
## Verification

- `PYTHONPATH=src COVERAGE_FILE=.tox/.coverage /Users/Shared/devlyn-vr-0228-dev/screen-0229/toolchains/dateutil/venv/bin/python -m pytest tests docs --cov-config=tox.ini --cov=dateutil --cov-fail-under=80` exits 0. This runs the repository's test command, including added regression cases for negative bounds, reverse slices, step-zero rejection, cache states, and bounded traversal; it enforces the project coverage target from `codecov.yml` locally.

- `XDG_CACHE_HOME=.cache BLACK_CACHE_DIR=.cache/black /Users/Shared/devlyn-vr-0228-dev/screen-0229/toolchains/dateutil/venv/bin/python -m darker --check --diff --color --isort --revision "$(git rev-list --max-parents=0 HEAD)" .` exits 0. This is the read-only Darker/isort check from the validation workflow, comparing changes with the pinned base at the root commit; formatter caches are directed to ignored output paths.
- `/Users/Shared/devlyn-vr-0228-dev/screen-0229/toolchains/dateutil/venv/bin/python -m pre_commit_hooks.debug_statement_hook src/dateutil/rrule.py tests/test_rrule.py` exits 0. This runs the configured debug-statement hook on the two authorized Python files.
- `git diff --check "$(git rev-list --max-parents=0 HEAD)" -- src/dateutil/rrule.py tests/test_rrule.py` exits 0. This checks changed-line whitespace against the pinned base at the root commit without invoking the configured whitespace fixer.

The automated checks provide baseline and selected regression coverage. Requirements and constraints not exercised by them remain source-review obligations. No type-check command is configured in this repository.
