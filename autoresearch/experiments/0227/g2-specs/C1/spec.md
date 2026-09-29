---
id: "C1"
title: "Bound explicit TLRU expiration batches"
kind: feature
status: planned
complexity: high
depends_on: []
---

# Bound explicit TLRU expiration batches

## Context

Applications sometimes reclaim expired cache values in batches between other work. TLRUCache currently removes every eligible value in one expire call, and its expiration heap can also contain obsolete records from replacements and deletions. Add a bound on the number of resident values reclaimed by an explicit call.

## Requirements

- [ ] Extend TLRUCache.expire to accept a keyword-only limit argument, defaulting to None; existing calls retain their behavior and return a list of expired (key, value) pairs.
- [ ] For a positive limit, remove and return exactly the smaller of limit and the number of resident entries expired at the selected time, processing earlier deadlines first; equal-deadline order remains unspecified.
- [ ] Obsolete heap records from overwritten or deleted entries do not count toward limit, and their removal must not remove or report the current value of a key.
- [ ] A zero limit returns an empty list without removing resident entries. None imposes no bound.
- [ ] Accept None and int limits, including bool with its ordinary integer meaning. Reject negative integers with ValueError and other types with TypeError before sampling the timer or changing cache state.
- [ ] An entry expiring exactly at the selected time is eligible. For calls with a positive or None limit, use an explicit time when supplied and otherwise sample the timer once.
- [ ] Values left behind by a bounded call remain physically resident until later cleanup but are inaccessible through ordinary expired-key lookup. Later unlimited expiration returns the remaining expired pairs, and size accounting and subsequent insertion remain correct.

## Constraints

- **Keep automatic expiration unlimited.** Existing insertion, size inspection, and eviction paths must continue to reclaim all eligible entries, so the new argument does not alter normal cache admission.
- **Preserve nonnumeric deadline support and heap maintenance.** Existing timer/ttu comparisons and obsolete-record compaction must continue to work for supported deadline types.
- **Update only src/cachetools/__init__.py, src/cachetools/__init__.pyi, tests/test_tlru.py, and docs/index.rst.** Runtime behavior, its public signature, tests, and the existing TLRU documentation belong together in this focused change.
- **Add no dependencies and preserve existing checks.** The feature requires only the existing implementation and standard library.

## Out of Scope

- Adding a limit argument to TTLCache or changing eviction policies.
- A bound on elapsed time, heap operations, or temporary bookkeeping memory.
- New expiration callbacks or asynchronous cleanup.

<!-- devlyn:verification -->
## Verification

Run from the repository root.

- `python --version` reports Python 3.13.
- `PYTHONPATH=src python -m pytest -q` exits 0. Add tests that expire a prefix of distinct deadlines with a positive limit, verify the retained resident size without triggering cleanup, and drain the remainder; also cover zero, None, invalid arguments, exact deadlines, and ordinary lookup of retained expired values.
- `ruff check .` exits 0.
- `ruff format --check .` exits 0.
- `pyright` exits 0, including calls using the new keyword argument.

Semantics not exercised by these public tests remain source-review obligations under Requirements and Constraints, including interactions with obsolete heap records, compaction, custom deadline types, and automatic expiration.
