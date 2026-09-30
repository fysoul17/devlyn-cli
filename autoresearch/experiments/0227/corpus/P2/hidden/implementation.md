# P2 implementation instructions

Family: ordering/precedence. Apply independently to the pinned tree.

## Reference

Change exactly `src/attr/_funcs.py` and `tests/test_hooks.py`.

The field-level `asdict` loop already filters and serializes before classifying the value. Keep that order. In `_asdict_anything`, call the serializer at entry when present, assigning its return to `val`; only then compute `val_type = type(val)` and use that type for the existing atomic/attrs/collection/dictionary dispatch. Remove the two old leaf-only callback sites so scalar values are not serialized twice. Retain the existing recursive argument propagation, dictionary key handling, factories, and collection policy. A replacement attrs instance enters `asdict` directly, which serializes its fields but never re-offers that instance as a root. No callback is added for a field-name string used as an output key.

Update the serializer argument documentation in `asdict`. In `tests/test_hooks.py`, update the existing `test_asdict_calls` test to include the new `(None, None, child)` events for attrs instances reached through a list and a dictionary value, in their proper positions. Do not change its original field events. Existing datetime-to-string behavior must remain passing.

Add public tests for an identity serializer logging a nested list/dict/attrs traversal, including dictionary key-before-value order and field filtering. Add transformations that preserve each structural category: prune an element from a nested list by returning another list, remove an entry from a nested dict by returning another dict, and change scalar values. Assert callbacks visit the replacement children and never visit removed children. Check repeated references as separate occurrences, both namespace entry points, `recurse=False`, retained tuple versus default list output, a dictionary factory, and propagation of a specific callback exception object. One compound test should combine filtering, a nested same-type replacement, call-order logging, and the final output assertion.

Do not add public tests in which a serializer result crosses between the atomic, attrs-instance, collection, and dict dispatch categories for a nested value. Use identity serializers for attrs instances reached through collections. Existing datetime-to-string conversion is safe: the twin's fallback leaf branch also returns the converted string. Keep public tests and documentation identical in the two implementations. No coverage exemptions or configuration changes are needed: traversal arms remain covered by the suite.

## Twin

Starting with the reference, move just `val_type = type(val)` from after the new entry serializer call to before it in `_asdict_anything`. Continue assigning the callback result to `val`, but use the previously captured `val_type` for dispatch. Leave the field-level `asdict` implementation unchanged.

This is a plausible stale-local mistake while moving the existing hook: the result is stored correctly, yet classification still describes the original object. Identity callbacks, transformations within the same concrete collection type, and the existing datetime conversion continue to work. A nested attrs instance replaced with a string enters the attrs branch using its old type and calls `asdict` on the string. The changed-file set is the same two files, with no suggestive comments or names.
