---
id: "P2"
title: "Apply asdict serializers before traversing nested values"
kind: feature
status: planned
complexity: high
depends_on: []
---

# Apply asdict serializers before traversing nested values

## Context

An `asdict` value serializer can replace a field's value before recursion, but nested collection elements currently receive different treatment: nested attrs instances and collections are traversed without first being offered to the serializer. A serializer should be able to prune or replace a nested object using the same traversal rules as a field value.

## Requirements

- [ ] With recursion enabled, offer every value reached through a collection element or dictionary key/value to `value_serializer(None, None, value)` before traversing it. This includes nested attrs instances, collections, dictionaries, and scalar values.
- [ ] For each attrs field, retain the existing order: read the field, apply its filter to the original value, and, only if included, call `value_serializer(instance, attribute, value)`. A rejected field receives no serializer call or recursive traversal.
- [ ] Use the serializer's returned value, including its type, to decide whether and how to recurse. Replacing a nested attrs instance or collection with a scalar must stop traversal of the original object.
- [ ] Call the serializer once per reached value occurrence, before that occurrence's children. Do not call it again on the immediate replacement; visit the replacement's children normally. Do not introduce a callback for the top-level attrs instance itself. Repeated references in separate positions remain separate occurrences.
- [ ] Preserve traversal order: fields in attrs field order, sequence elements in iteration order, and dictionary entries in iteration order with each key before its value. Use the same filter and serializer for recursively reached attrs fields.
- [ ] Preserve `recurse=False`, calls without a serializer, `dict_factory`, and collection-retention behavior. `attrs.asdict` must inherit the behavior while retaining its existing collection-type policy. Callback exceptions propagate unchanged.

## Constraints

- **Add no dependencies.** This extends the existing recursive conversion machinery.
- **Limit changes to `src/attr/_funcs.py` and `tests/test_hooks.py`.** Both public namespaces already delegate to this implementation.
- **Update the existing serializer-call expectations only for the newly specified callbacks.** Existing traversal and filtering assertions must continue to protect compatibility.
- **Keep verification configuration unchanged and document the callback contract in the source docstring.** Users and existing checks must see the same public API and checking rules.

## Out of Scope

- A serializer callback for dictionary keys that are attrs field names, or for the top-level instance.
- Cycle detection, reference deduplication, or repeated serialization of a replacement root.
- Expanding the supported collection types, making unhashable serialized keys valid, or changing `astuple`.
- Packaging, dependency, or release changes.

<!-- devlyn:verification -->
## Verification

The repository suite must include a compound serializer test that combines field filtering, a nested replacement of the same concrete collection type, callback-order assertions, and the final output. Existing serializer-call expectations must account for the newly specified callbacks.

Run from the repository root:

- `PATH="/Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin:$PATH" PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 HYPOTHESIS_STORAGE_DIRECTORY="$TMPDIR/hypothesis" PYRIGHT_PYTHON_CACHE_DIR=/Users/Shared/devlyn-vr-0227/toolchains/attrs/pyright-cache /Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/python -m pytest -q -p no:cacheprovider` exits 0 and reports passing tests. This full run also includes the mypy plugin cases and the pyright diagnostic tests, so separate subset pytest invocations would duplicate those checks.
- `/Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/ruff check --no-cache .` exits 0 and reports `All checks passed!`, using the repository Ruff rules.
- `/Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/ruff format --check --no-cache .` exits 0 with all files formatted according to the repository configuration.
- `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 /Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/mypy --cache-dir=/private/tmp/attrs-author-mypy typing_tests` exits 0 and reports no issues in the configured typing examples.
- `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 /Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/mypy --cache-dir=/private/tmp/attrs-author-mypy src/attrs/__init__.pyi src/attr/__init__.pyi src/attr/_typing_compat.pyi src/attr/_version_info.pyi src/attr/converters.pyi src/attr/exceptions.pyi src/attr/filters.pyi src/attr/setters.pyi src/attr/validators.pyi` exits 0 and reports no issues in the public stubs listed by `tox.ini`.
- `PATH="/Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin:$PATH" PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 PYRIGHT_PYTHON_CACHE_DIR=/Users/Shared/devlyn-vr-0227/toolchains/attrs/pyright-cache /Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/pyright` exits 0 and reports zero errors and warnings for the configured typing baseline.

These use the repository's pytest, Ruff, mypy, and pyright configuration; the cache options keep generated caches outside the source tree. Requirements and constraints not exercised by these commands remain source-review obligations.
