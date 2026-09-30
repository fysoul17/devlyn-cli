---
id: "P1"
title: "Add an interval validator"
kind: feature
status: planned
complexity: high
depends_on: []
---

# Add an interval validator

## Context

Numeric fields commonly need both a lower and an upper bound. attrs currently supplies individual comparison validators; an interval validator would give this common combination a single representation and error message, including a choice of open or closed endpoints.

## Requirements

- [ ] Expose `between(lower, upper, *, lower_inclusive=True, upper_inclusive=True)` through both `attr.validators` and `attrs.validators`, with a matching public type stub.
- [ ] By default, accept both endpoints and all values between them. Setting either inclusive flag to `False` excludes that endpoint; the flags work independently.
- [ ] Validate bounds when constructing the validator: if `lower <= upper` returns false, raise `ValueError`. Equal bounds are valid, including with open endpoints; such an open interval accepts no values.
- [ ] Accept a value only when its comparison against each endpoint succeeds: use `>=` or `>` for the lower bound and `<=` or `<` for the upper bound according to the flags. An unordered value such as `float("nan")` must raise `ValueError`.
- [ ] Preserve comparison semantics without numeric coercion. Ordered infinite endpoints work normally, and exceptions raised by the comparisons propagate unchanged.
- [ ] For a rejected value, raise `ValueError` with a message containing the field name, the interval, and the rejected value. Represent intervals with `repr` of the bounds, a comma and space, and `[`/`]` for inclusive or `(`/`)` for exclusive endpoints; the validator's representation is `<between validator for INTERVAL>`.
- [ ] The validator returns `None` on success, works with normal construction, assignment validation, and `optional`, and obeys the existing global validation switch when invoked through attrs-generated validation. Equal configurations compare equal and are hashable when their bounds are hashable.

## Constraints

- **Add no dependencies.** Existing comparison operators and attrs validator machinery suffice.
- **Limit changes to `src/attr/validators.py`, `src/attr/validators.pyi`, `tests/test_validators.py`, and `typing_tests/baseline.py`.** The feature belongs beside the current comparison validators and their tests.
- **Keep existing validators and verification configuration unchanged.** Applications using the existing single-bound validators must retain their behavior.
- **Document the API in its source docstring.** The new callable needs the same discoverable argument and exception documentation as its neighbors.

## Out of Scope

- Unbounded endpoints expressed as `None`, automatic bound swapping, or numeric conversion.
- New interval container types or changes to `lt`, `le`, `ge`, `gt`, or `ne`.
- Packaging, dependency, or release changes.

<!-- devlyn:verification -->
## Verification

The repository suite must include the new endpoint matrix and field-validation tests, including assignment rejection followed by a valid assignment. The typing baseline must include an integer field using the new validator.

Run from the repository root:

- `PATH="/Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin:$PATH" PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 HYPOTHESIS_STORAGE_DIRECTORY="$TMPDIR/hypothesis" PYRIGHT_PYTHON_CACHE_DIR=/Users/Shared/devlyn-vr-0227/toolchains/attrs/pyright-cache /Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/python -m pytest -q -p no:cacheprovider` exits 0 and reports passing tests. This full run also includes the mypy plugin cases and the pyright diagnostic tests, so separate subset pytest invocations would duplicate those checks.
- `/Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/ruff check --no-cache .` exits 0 and reports `All checks passed!`, using the repository Ruff rules.
- `/Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/ruff format --check --no-cache .` exits 0 with all files formatted according to the repository configuration.
- `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 /Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/mypy --cache-dir=/private/tmp/attrs-author-mypy typing_tests` exits 0 and reports no issues in the configured typing examples.
- `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 /Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/mypy --cache-dir=/private/tmp/attrs-author-mypy src/attrs/__init__.pyi src/attr/__init__.pyi src/attr/_typing_compat.pyi src/attr/_version_info.pyi src/attr/converters.pyi src/attr/exceptions.pyi src/attr/filters.pyi src/attr/setters.pyi src/attr/validators.pyi` exits 0 and reports no issues in the public stubs listed by `tox.ini`.
- `PATH="/Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin:$PATH" PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 PYRIGHT_PYTHON_CACHE_DIR=/Users/Shared/devlyn-vr-0227/toolchains/attrs/pyright-cache /Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/pyright` exits 0 and reports zero errors and warnings for the configured typing baseline.

These use the repository's pytest, Ruff, mypy, and pyright configuration; the cache options keep generated caches outside the source tree. Requirements and constraints not exercised by these commands remain source-review obligations.
