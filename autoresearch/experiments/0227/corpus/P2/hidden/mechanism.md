# P2 mechanism record

- Family: ordering/precedence.
- Mandatory clause: “Use the serializer's returned value, including its type, to decide whether and how to recurse. Replacing a nested attrs instance or collection with a scalar must stop traversal of the original object.”
- Trigger: an attrs instance reached as a collection element is replaced by a scalar by the serializer.
- Causal code path: `_asdict_anything` captures the original type, invokes the serializer, then dispatches using that stale type. The attrs-instance branch calls `asdict` on the scalar replacement.
- Incorrect behavior: serialization raises `NotAnAttrsClassError` instead of emitting the scalar replacement without traversing the original attrs object.
- Executable witness: P2-O3 in `oracle.md`.
- Near-miss exclusions: failure to call the hook at all, duplicate callbacks, field filtering after serialization, dict entry reordering, output collection retention, and revisiting a replacement root are different mechanisms. Type-changing field-level callbacks are already handled by `asdict`; this defect is stale classification in the helper for nested occurrences.
