# P3 implementation instructions

Family: failure-state preservation. Apply independently to the pinned tree.

## Reference

Change exactly `src/attr/_funcs.py`, `src/attr/__init__.pyi`, `tests/test_annotations.py`, and `typing_tests/baseline.py`.

Extend the runtime and stub signatures with `*, force=False` / `*, force: bool = ...` after `include_extras`, preserving the existing five positional parameters. The existing cache guard becomes a condition that also enters for `force`. Preserve the current sequence inside it: obtain all hints with `typing.get_type_hints`, update matching Attribute objects, and only then assign `cls.__attrs_types_resolved__ = cls`. A force request bypasses reading the cache as a decision; it does not need to clear or temporarily mark the cache. This naturally leaves both the marker and field metadata untouched when evaluating hints raises.

Keep the inherited-marker comparison with `cls` and the `attribs is None` distinction. The source docstring should explain force, successful caching, and failure preservation. Add a typed `attrs.resolve_types(..., force=True)` call to the existing baseline's type-resolution example, using a valid class type.

Public runtime tests should cover: ordinary cache hits ignoring a changed namespace; forced refresh to a different binding followed by an unforced hit; repeated forced calls; changing `include_extras` on a successful refresh; fields without annotations remaining unchanged; subclass resolution after a base has been resolved; and a successful forced call with explicit Attribute objects in a field transformer. Add an initially unresolved forward reference that fails on an ordinary call, preserves its original field types, and succeeds after namespace repair. In a compound test, resolve a string annotation to `int`, refresh it to `str`, then pass a third namespace to an unforced call and assert it still retains `str`.

Public tests must not force annotation evaluation to fail. The ordinary initial-failure test is still appropriate and must not set `force=True`. All new force calls in public runtime tests must succeed. Existing default-path tests remain intact. Keep tests and the stub identical between reference and twin and do not relax coverage, lint, or typing configuration.

## Twin

Start from the reference. Inside the branch that performs resolution, before calling `typing.get_type_hints`, add eager invalidation for a forced request: `if force: cls.__attrs_types_resolved__ = None`. Make no other behavioral change. The existing successful end-of-function marker assignment remains present.

This resembles a conventional cache-refresh implementation that clears old data before recomputation. Successful refreshes overwrite the temporary marker, so every public force test passes. A failed forced refresh leaves the temporary value behind; subsequent default calls retry evaluation instead of using the still-valid prior field types. The twin changes the same four files as the reference, and the added invalidation receives no comment or name hinting at its defect.
