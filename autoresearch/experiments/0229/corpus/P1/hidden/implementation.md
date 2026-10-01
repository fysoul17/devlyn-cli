# P1 implementation instructions

Family: boundary semantics. Apply this request alone to the pinned tree.

## Reference design

Change exactly `src/dateutil/rrule.py` and `tests/test_rrule.py`. Both patches must have this exact changed-file set; the tests must be identical between patches.

The relevant implementation is `rrulebase.__getitem__`. Completed caches already delegate to list subscription. In the slice path for an incomplete or absent cache:

1. Normalize each supplied slice component with the standard-library `operator.index` before numerical comparisons, preserving existing integer-index objects as well as ordinary integers. Keep omitted start/stop components as `None` while deciding the traversal path, and default a missing step to one.
2. Reject step zero with `ValueError` before taking any iterator path.
3. Materialize the finite recurrence for a negative step or a negative start/stop, then apply the normalized slice to that list. Preserve an omitted start in a reverse slice. This is also the existing strategy for reverse traversal.
4. Use `itertools.islice` for the remaining forward cases, defaulting a missing start to zero and passing an omitted stop through as `None`. An explicit zero stop must stay zero. Do not exhaust the recurrence to normalize an ordinary positive slice.
5. Leave integer subscription and the completed-cache fast path intact. No new argument types are needed. An empty forward range may return early.

Keep changes local; do not alter recurrence generation or cache invalidation. A short method comment/docstring may describe the two traversal strategies without explaining evaluation machinery.

## Public tests added to the repository

Use existing pytest/unittest conventions in `tests/test_rrule.py`. Use fresh finite objects for each assertion unless a cache transition is the point of the test. Cover both `rrule` and `rruleset`, where the latter contains a daily rule plus an exclusion. Compare the selected results with independently constructed lists.

- Negative bounds: `[-3:]`, `[:-1]`, `[1:-1:2]`, `[-20:3]`, and `[-3:-1]` on a six-occurrence finite rule. Cover disabled, incomplete, and complete caches. For an incomplete cache use a rule long enough that the ten-item cache prefetch does not complete it.
- Reverse slices: `[::-1]` and `[4:1:-2]` in the same cache modes.
- Omitted components and ordinary forward slices: `[:]`, `[1:4:2]`, and `[4:2]`.
- Zero step: `[::0]` raises in all three cache modes, including when the recurrence is empty.
- Bounded traversal: use a test subclass of `rrule` whose `_iter` yields three fixed occurrences and then raises `AssertionError`; `[1:3]` must return the second and third dates without reaching the failure. This avoids timing-based assertions or very long materializations.
- Preserve representative positive and negative integer subscription behavior and a forward slice whose bounds implement `__index__`.

Do not add explicit-zero-stop slice assertions to the public suite, including generated/property-test matrices. They would exercise the target mechanism. The other boundary and cache interactions above are public and must pass on both patches. Existing repository tests contain ordinary and reverse slice cases, but no explicit-zero-stop regression.

## Twin construction

Make exactly one semantic deviation in the new non-completed-cache forward slice path: replace the normalized stop with `stop or None` instead of preserving the distinction between zero and `None`. Leave component normalization, negative-bound materialization, step-zero validation, and every other reference change intact. If the reference has an early empty-range return, ensure this same stop value feeds it, so that it does not mask the deviation.

This treats the legitimate boundary `0` as an omitted endpoint. For example, a fresh five-occurrence rule's `[:0]` returns all five occurrences; a completed cache still returns `[]` through list slicing. Reusing the old truthiness-based default while adding the new slice handling is a plausible oversight.

No comments, symbols, or test names may advertise the deviation. Do not change tests or verification configuration between patches. The public suite does not invoke this path with a zero stop, and coverage is a whole-project 80% target, not full branch coverage.
