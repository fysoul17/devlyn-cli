---
id: "P3"
title: "Allow explicit refresh of resolved field types"
kind: feature
status: planned
complexity: high
depends_on: []
---

# Allow explicit refresh of resolved field types

## Context

`resolve_types` caches a successful resolution on the class, so later calls cannot pick up a changed namespace or a different `include_extras` choice. Tools that finish populating forward references after class creation need an explicit way to refresh field types while retaining a usable prior resolution if the new annotations cannot be evaluated.

## Requirements

- [ ] Add keyword-only `force=False` to `attr.resolve_types` and its public type stub, also available through the existing `attrs.resolve_types` export. Preserve all existing positional arguments and return the input class by identity.
- [ ] With `force=False`, preserve current behavior: a successful resolution is cached for that class, subsequent calls use the cache, and a subclass is not considered resolved merely because its base class has been resolved.
- [ ] With `force=True`, evaluate the class's current annotations using the supplied `globalns`, `localns`, and `include_extras` even after an earlier successful resolution. Replace types for matching fields and leave fields without matching annotations unchanged.
- [ ] A successful forced resolution establishes the usual cache state, so a following unforced call reuses it. Explicit `attribs` continues to select the fields to update and remains usable inside a field transformer before the class has become an attrs class.
- [ ] If annotation evaluation raises during a forced resolution, propagate that exception without changing field types or the class's resolution-cache state; a previously cached class must still be a cache hit on a subsequent unforced call.
- [ ] An initially unresolved class whose annotation evaluation fails remains unresolved and can be resolved by a later call after its namespace is repaired. Both forced and ordinary successful calls preserve the existing `include_extras` and inheritance semantics.

## Constraints

- **Add no dependencies.** Continue to use the standard-library annotation-resolution machinery.
- **Limit changes to `src/attr/_funcs.py`, `src/attr/__init__.pyi`, `tests/test_annotations.py`, and `typing_tests/baseline.py`.** The modern namespace already re-exports the same function and stub.
- **Keep existing test assertions and verification configuration intact.** Default callers must keep their current behavior.
- **Describe `force` and its failure behavior in the function docstring.** Callers need to know how refreshes interact with the cache.

## Out of Scope

- Automatic cache invalidation, caching separately for every namespace, or modifying `__annotations__` on behalf of callers.
- Transactional rollback of side effects performed by user annotation expressions or custom metaclasses.
- Accepting invalid objects in `attribs`, changing how inherited fields are copied, or thread-safety guarantees.
- Packaging, dependency, or release changes.

<!-- devlyn:verification -->
## Verification

The repository suite must include a compound test that resolves to one type, forces a successful refresh to a second type, and confirms an ordinary call reuses that second result. It must also cover initial resolution failure followed by repair and retry, and type-check a force call.

Run from the repository root:

- `PATH="/Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin:$PATH" PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 HYPOTHESIS_STORAGE_DIRECTORY="$TMPDIR/hypothesis" PYRIGHT_PYTHON_CACHE_DIR=/Users/Shared/devlyn-vr-0227/toolchains/attrs/pyright-cache /Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/python -m pytest -q -p no:cacheprovider` exits 0 and reports passing tests. This full run also includes the mypy plugin cases and the pyright diagnostic tests, so separate subset pytest invocations would duplicate those checks.
- `/Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/ruff check --no-cache .` exits 0 and reports `All checks passed!`, using the repository Ruff rules.
- `/Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/ruff format --check --no-cache .` exits 0 with all files formatted according to the repository configuration.
- `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 /Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/mypy --cache-dir=/private/tmp/attrs-author-mypy typing_tests` exits 0 and reports no issues in the configured typing examples.
- `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 /Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/mypy --cache-dir=/private/tmp/attrs-author-mypy src/attrs/__init__.pyi src/attr/__init__.pyi src/attr/_typing_compat.pyi src/attr/_version_info.pyi src/attr/converters.pyi src/attr/exceptions.pyi src/attr/filters.pyi src/attr/setters.pyi src/attr/validators.pyi` exits 0 and reports no issues in the public stubs listed by `tox.ini`.
- `PATH="/Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin:$PATH" PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 PYRIGHT_PYTHON_CACHE_DIR=/Users/Shared/devlyn-vr-0227/toolchains/attrs/pyright-cache /Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/pyright` exits 0 and reports zero errors and warnings for the configured typing baseline.

These use the repository's pytest, Ruff, mypy, and pyright configuration; the cache options keep generated caches outside the source tree. Requirements and constraints not exercised by these commands remain source-review obligations.
