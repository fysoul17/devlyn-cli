# P1 mechanism record

- Family: boundary semantics.
- Mandatory clause: “Accept a value only when its comparison against each endpoint succeeds: use `>=` or `>` for the lower bound and `<=` or `<` for the upper bound according to the flags. An unordered value such as `float("nan")` must raise `ValueError`.”
- Trigger: a valid finite interval receives a floating-point NaN as the value to validate.
- Causal code path: `between` constructs the new validator; its `__call__` uses inverted out-of-range comparisons instead of requiring the two membership comparisons to succeed. NaN makes all of these ordered comparisons false.
- Incorrect behavior: the twin accepts NaN and returns `None`, allowing a field to contain a value outside the required comparison-defined interval.
- Executable witness: P1-O4 in `oracle.md`.
- Near-miss exclusions: incorrect brackets or error text; rejecting equal open bounds during construction; invalid-bound checking; coercing values; optional `None`; and failure to export the factory are different defects. Ordered-number endpoint mistakes are also different mechanisms. The target is the false equivalence between comparison negation and comparison inversion on an unordered value.
