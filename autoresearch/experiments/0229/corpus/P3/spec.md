---
id: "P3"
title: "Validate timezone cache sizes without disturbing cache state"
kind: feature
status: planned
complexity: high
depends_on: []
---

# Validate timezone cache sizes without disturbing cache state

## Context

`tz.gettz.set_cache_size` lets applications control how many timezone objects remain strongly cached. Invalid sizes currently can fail after altering the cache, leaving later lookups affected by a rejected configuration change. Give this method a defined input contract and preserve its existing cache behavior on successful changes.

## Requirements

- [ ] `tz.gettz.set_cache_size(size)` accepts nonnegative integers and values implementing the integer `__index__` protocol, using the resulting integer as the capacity. Booleans follow their normal integer values.
- [ ] A negative integer capacity raises `ValueError`; a value without an integer index raises `TypeError`. Exceptions raised by an object's `__index__` implementation propagate to the caller.
- [ ] Any rejected size leaves the configured capacity, retained timezone objects, and recency order unchanged; subsequent lookups behave as if that resize call had not occurred.
- [ ] A successful resize returns `None`; shrinking immediately evicts the least recently used strong-cache entries until the new capacity is met, and growing preserves current entries and their recency order.
- [ ] A capacity of zero disables strong retention while preserving the existing weak-cache identity behavior for timezone objects still held by callers.
- [ ] Document accepted sizes and failure behavior on `set_cache_size`, and keep successful lookups and `cache_clear` behavior compatible with the existing API.

## Constraints

- Change only `src/dateutil/tz/tz.py` and `tests/test_tz.py`, because this concerns the existing `gettz` cache implementation and tests.
- Add no dependencies, because integer-index validation and cache operations are available in the standard library.
- Keep cache updates synchronized with the existing cache lock, because resize and lookup share the strong cache.
- Keep the existing test, coverage, and tooling configuration unchanged, so the compatibility checks are not weakened.
- Preserve the project's existing Python compatibility conventions, because the cache API is shared by supported interpreters.

## Out of Scope

- New public cache-inspection APIs, cache implementations, or eviction policies.
- Changes to timezone resolution, timezone files, or the `tzoffset`/`tzstr` factory caches.
- New guarantees about timezone objects that have no remaining strong references.
- Changing how `cache_clear` handles the configured capacity.

<!-- devlyn:verification -->
## Verification

- `PYTHONPATH=src COVERAGE_FILE=.tox/.coverage /Users/Shared/devlyn-vr-0228-dev/screen-0229/toolchains/dateutil/venv/bin/python -m pytest tests docs --cov-config=tox.ini --cov=dateutil --cov-fail-under=80` exits 0. This runs the repository's test command, including an added populated-cache sequence that rejects an invalid size, performs further lookups, and checks eviction, plus input-validation and successful-resize regressions; it enforces the project coverage target from `codecov.yml` locally.

- `XDG_CACHE_HOME=.cache BLACK_CACHE_DIR=.cache/black /Users/Shared/devlyn-vr-0228-dev/screen-0229/toolchains/dateutil/venv/bin/python -m darker --check --diff --color --isort --revision "$(git rev-list --max-parents=0 HEAD)" .` exits 0. This is the read-only Darker/isort check from the validation workflow, comparing changes with the pinned base at the root commit; formatter caches are directed to ignored output paths.
- `/Users/Shared/devlyn-vr-0228-dev/screen-0229/toolchains/dateutil/venv/bin/python -m pre_commit_hooks.debug_statement_hook src/dateutil/tz/tz.py tests/test_tz.py` exits 0. This runs the configured debug-statement hook on the two authorized Python files.
- `git diff --check "$(git rev-list --max-parents=0 HEAD)" -- src/dateutil/tz/tz.py tests/test_tz.py` exits 0. This checks changed-line whitespace against the pinned base at the root commit without invoking the configured whitespace fixer.

The automated checks provide baseline and selected regression coverage. Requirements and constraints not exercised by them remain source-review obligations. No type-check command is configured in this repository.
