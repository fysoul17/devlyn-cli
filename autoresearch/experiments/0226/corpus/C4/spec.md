---
id: "C4"
title: "Resize cache capacity in place"
kind: feature
status: planned
complexity: high
depends_on: []
---

# Resize cache capacity in place

## Context

Applications may need to adjust a cache's memory budget without replacing the cache object shared by memoizing wrappers. Cache.maxsize is currently read-only, and constructing a replacement discards both retained entries and eviction history. Add an explicit resize operation that reuses the cache's existing size accounting and eviction policy.

## Requirements

- [ ] Add Cache.resize(maxsize), inherited by the built-in cache classes, returning None. It accepts the same non-negative capacities as the constructor, including zero, fractional capacities, and math.inf.
- [ ] Negative capacity raises ValueError before changing capacity, entries, size accounting, or eviction metadata.
- [ ] After a successful resize, cache.maxsize equals the requested capacity and cache.currsize is no greater than that capacity; enforce this using the stored getsizeof-based sizes rather than the number of entries.
- [ ] When removal is necessary, evict through the cache's existing popitem policy until the requested capacity can hold the retained entries. Preserve retained values and their relative eviction priority.
- [ ] Resizing does not recompute the sizes of retained values or invoke getsizeof on them. Growing or keeping sufficient capacity causes no capacity eviction; zero-sized values need not be evicted to reach capacity zero.
- [ ] Subsequent insertion and replacement enforce the new capacity using existing admission and size-accounting behavior. The same cache object remains usable by existing decorators.
- [ ] Timed caches perform their normal expired-entry cleanup before deciding whether capacity eviction is necessary, so expired entries cannot force eviction of live values.

## Constraints

- **Keep maxsize read-only.** The explicit operation makes any required eviction visible while preserving existing property assignment behavior.
- **Use existing eviction and accounting hooks.** Subclasses and decorators already depend on popitem and currsize, so resizing must preserve those interfaces and their meaning.
- **Update only src/cachetools/__init__.py, src/cachetools/__init__.pyi, tests/test_cache.py, and docs/index.rst.** These files cover the inherited operation, its type signature, focused tests, and base-cache documentation.
- **Add no dependencies and preserve existing checks.** The existing cache machinery is sufficient.

## Out of Scope

- Returning evicted pairs or adding eviction callbacks.
- Transactional rollback when a user-supplied size, timer, or eviction hook raises.
- Exact arithmetic of the existing size accounting, including floating-point rounding or overflow in currsize sums inherited from Cache. Capacity requirements use the library's existing accounting; resize must still stop evicting when the cache is empty, even if that accounting leaves a residual size above the requested capacity.
- Adding thread synchronization, remeasuring mutated values, or defining new validation for NaN or nonnumeric capacities.

<!-- devlyn:verification -->
## Verification

Run from the repository root, offline, with PYTHONPATH=src in the supplied Python 3.13 environment.

- `python -m pytest -q` exits 0. Add a compound test that changes LRU access order, shrinks a unit-sized cache, verifies the victim and new capacity, and inserts again under that capacity; also cover growth, zero, invalid capacity, inherited policies, timed cleanup, decorator reuse, and retention without remeasurement.
- `ruff check .` exits 0.
- `ruff format --check .` exits 0.
- `pyright` exits 0, including resize calls on typed cache instances.

Semantics not exercised by these public tests remain source-review obligations under Requirements and Constraints, including weighted capacity eviction, fractional stored sizes, zero-sized entries at zero capacity, and preservation of subclass accounting.
