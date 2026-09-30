---
id: "P4"
title: "Reset evolved field aliases to their generated defaults"
kind: feature
status: planned
complexity: high
depends_on: []
---

# Reset evolved field aliases to their generated defaults

## Context

Field transformers use `Attribute.evolve` to copy and adapt field metadata. They can set a custom initializer alias, but clearing that choice with `alias=None` currently leaves an incomplete Attribute until class construction later fills it in; a transformer should be able to obtain a complete, reusable field description immediately.

## Requirements

- [ ] Treat an explicit `Attribute.evolve(alias=None)` as resetting the alias to the generated default: strip leading underscores from the resulting field name and set `alias_is_default` to `True`. The returned Attribute must already contain this concrete alias.
- [ ] When the same evolve call changes `name` and resets `alias`, derive the alias from the new name. Its `name`, `alias`, and `alias_is_default` must describe the same resulting field.
- [ ] A reset Attribute can be renamed by a later evolve call that omits `alias`; its default alias must follow that subsequent rename as usual.
- [ ] Reject `alias=None` combined with `alias_is_default=False` in the same call with `ValueError`, because the request simultaneously asks for a generated alias and marks it explicit.
- [ ] Preserve other evolve behavior: non-`None` explicit aliases remain usable, explicit aliases survive name-only changes, existing `alias_is_default` overrides remain effective when no reset is requested, and unrelated metadata changes are preserved. The original Attribute remains unchanged.
- [ ] For field names already supported by class generation, a field transformer returning a reset Attribute must produce a working class whose initializer and `attrs.evolve` use that Attribute's alias, while instance storage and `attrs.fields` use its field name. This must work for both slotted and dictionary-backed classes.

## Constraints

- **Add no dependencies.** Reuse attrs' existing default-alias convention.
- **Limit changes to `src/attr/_make.py` and `tests/test_hooks.py`.** Alias normalization belongs in `Attribute.evolve`, which is shared by both public namespaces.
- **Keep existing assertions and verification configuration intact.** The extension must preserve established field-transformer behavior.
- **Document the reset behavior in `Attribute.evolve`'s docstring.** Transformers need a clear distinction between omitting `alias` and explicitly passing `None`.

## Out of Scope

- New alias spelling rules, validation of Python identifier syntax, or duplicate-alias detection.
- Expanding which transformer-created field names can be used by class generation.
- Changes to normal `field(alias=...)` declarations, pickle formats, or instance `attrs.evolve` itself.
- Packaging, dependency, or release changes.

<!-- devlyn:verification -->
## Verification

The repository suite must include a compound field-transformer test that resets an alias, renames in a subsequent evolve call, builds the class, and uses both its initializer and instance evolve. It must cover both slotted and dictionary-backed classes.

Run from the repository root:

- `PATH="/Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin:$PATH" PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 HYPOTHESIS_STORAGE_DIRECTORY="$TMPDIR/hypothesis" PYRIGHT_PYTHON_CACHE_DIR=/Users/Shared/devlyn-vr-0227/toolchains/attrs/pyright-cache /Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/python -m pytest -q -p no:cacheprovider` exits 0 and reports passing tests. This full run also includes the mypy plugin cases and the pyright diagnostic tests, so separate subset pytest invocations would duplicate those checks.
- `/Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/ruff check --no-cache .` exits 0 and reports `All checks passed!`, using the repository Ruff rules.
- `/Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/ruff format --check --no-cache .` exits 0 with all files formatted according to the repository configuration.
- `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 /Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/mypy --cache-dir=/private/tmp/attrs-author-mypy typing_tests` exits 0 and reports no issues in the configured typing examples.
- `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 /Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/mypy --cache-dir=/private/tmp/attrs-author-mypy src/attrs/__init__.pyi src/attr/__init__.pyi src/attr/_typing_compat.pyi src/attr/_version_info.pyi src/attr/converters.pyi src/attr/exceptions.pyi src/attr/filters.pyi src/attr/setters.pyi src/attr/validators.pyi` exits 0 and reports no issues in the public stubs listed by `tox.ini`.
- `PATH="/Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin:$PATH" PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 PYRIGHT_PYTHON_CACHE_DIR=/Users/Shared/devlyn-vr-0227/toolchains/attrs/pyright-cache /Users/Shared/devlyn-vr-0227/toolchains/attrs/venv/bin/pyright` exits 0 and reports zero errors and warnings for the configured typing baseline.

These use the repository's pytest, Ruff, mypy, and pyright configuration; the cache options keep generated caches outside the source tree. Requirements and constraints not exercised by these commands remain source-review obligations.
