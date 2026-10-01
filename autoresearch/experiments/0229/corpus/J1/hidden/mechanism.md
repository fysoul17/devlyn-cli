# J1 mechanism record

- **Family:** boundary semantics.
- **Mandatory clause:** "A cached answer may be reused only when it was computed with the current `state.posMax`; changing the upper bound in either direction must cause that position to be examined again, even when its cached ending position lies within the new range."
- **Trigger:** Look ahead from position 0 in ``'`a`'`` at bound 2, reset position 0, then look ahead at bound 3 on the same state.
- **Causal code path:** `ParserInline.skipToken` stores an end and bound for position 0. The twin's hit predicate accepts the smaller recorded bound when the active bound increases, returning before `backticks` can examine the newly included closer.
- **Incorrect behavior:** The second call ends at 1, retaining the unmatched-opener result, rather than at 3 after the code span.
- **Executable witness:** J1-O3 in `oracle.md`.
- **Near-miss exclusions:** Reusing the same-bound cache is required, not defective. Shrinking a bound is handled correctly by this twin. Altering the backtick-run cache, changing nesting context, mutating source or environment, or observing the recursion-limit fallback would be different mechanisms. Cache-array identity and supporting multiple remembered bounds per start are not requirements.
