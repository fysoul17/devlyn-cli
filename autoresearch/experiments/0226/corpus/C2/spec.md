---
id: "C2"
title: "Stabilize TLRU expiration order for equal deadlines"
kind: feature
status: planned
complexity: high
depends_on: []
---

# Stabilize TLRU expiration order for equal deadlines

## Context

TLRUCache.expire returns removed pairs, which subclasses can use for expiration reporting. Several values often share a deadline, but the heap currently gives callers no stable order among them. Make this order deterministic without changing least-recently-used capacity eviction.

## Requirements

- [ ] TLRUCache.expire returns expired pairs in ascending deadline order.
- [ ] Among equal deadlines, return entries in the order of the successful assignments that established their current values; replacing an existing value gives that entry a new position after entries already assigned the same deadline.
- [ ] Reads and membership checks do not change equal-deadline expiration order. Capacity eviction continues to use the existing LRU policy.
- [ ] Deleted entries and obsolete versions of replaced entries are never returned. Removing obsolete heap records, including compaction, preserves the expiration order of current entries.
- [ ] Keys and values need not be orderable. Deadline types supported by the current time/ttu contract remain supported; ordering must not require new arithmetic on deadlines.
- [ ] Assignment that rejects a value or produces an already-expired deadline retains its existing cache behavior and does not give an unchanged surviving value a new expiration position.

## Constraints

- **Keep the public API unchanged.** This is an ordering guarantee for the existing expire result, so no new parameters or return types are needed.
- **Preserve heap-based expiration and lazy obsolete-record cleanup.** Avoid sorting all resident entries on every expiration or insertion, which would change the existing performance model.
- **Update only src/cachetools/__init__.py, tests/test_tlru.py, and docs/index.rst.** The comparison logic, its regression tests, and the TLRU expiration documentation are the complete scope.
- **Add no dependencies and preserve existing checks.** Standard-library ordering and per-cache bookkeeping are sufficient.

## Out of Scope

- Changing TLRUCache iteration order or promising stable tie order for other cache classes.
- A new ordering policy for capacity eviction.
- Changing exception recovery, cache serialization formats, or thread-safety guarantees.

<!-- devlyn:verification -->
## Verification

Run from the repository root, offline, with PYTHONPATH=src in the supplied Python 3.13 environment.

- `python -m pytest -q` exits 0. Add a compound test that inserts equal-deadline entries, reads one, expires the group, and checks assignment order; also cover mixed deadlines, deletion, replacement with a different deadline, nonorderable keys, and unchanged LRU eviction.
- `ruff check .` exits 0.
- `ruff format --check .` exits 0.
- `pyright` exits 0.

Semantics not exercised by these public tests remain source-review obligations under Requirements and Constraints, including interactions between replacement and equal deadlines, compaction, rejected assignments, and supported deadline types.

