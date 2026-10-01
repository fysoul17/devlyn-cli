# P1 mechanism record

- **Family:** boundary semantics.
- **Mandatory clause:** “A forward slice with an omitted stop includes the remaining occurrences; an explicit stop of zero returns an empty list.”
- **Trigger:** a forward slice with `stop=0` on a nonempty recurrence whose cache is not complete.
- **Causal code path:** `rrulebase.__getitem__` chooses the iterator slice path and defaults the normalized stop by truthiness (`stop or None`). `itertools.islice` receives `None`, meaning no upper bound, instead of the valid exclusive boundary zero.
- **Incorrect behavior:** a request for an empty prefix returns occurrences. A completed cache continues to behave correctly through list subscription, making results depend on cache state.
- **Executable witness:** `P1-W` in `hidden/oracle.md`; the reference returns `[]`, the twin returns the five dates from January 1 through January 5, 2024.
- **Near-miss exclusions:** incorrect negative-index normalization; rejecting zero steps incorrectly; eager materialization of positive prefixes; recurrence generation errors; generic cache invalidation defects. They are separate mechanisms. This defect is specifically collapsing an explicit zero stop into an omitted stop.
