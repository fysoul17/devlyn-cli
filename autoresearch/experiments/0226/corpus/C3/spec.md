---
id: "C3"
title: "Preserve TTL cache state when deadline calculation fails"
kind: feature
status: planned
complexity: high
depends_on: []
---

# Preserve TTL cache state when deadline calculation fails

## Context

TTLCache permits custom timer and ttl types, so computing an entry's expiration time can raise. Currently assignment can alter cached values before this computation finishes. Ensure a failed deadline calculation leaves the cache usable and preserves the state callers had before the assignment.

## Requirements

- [ ] Each TTLCache assignment computes its prospective expiration deadline once from the timer value sampled for that assignment and the configured ttl.
- [ ] If computing that deadline raises, propagate the same exception and leave resident values, recorded sizes, LRU order, and expiration bookkeeping unchanged, including expired entries awaiting cleanup.
- [ ] After such a failure, later reads, expiration, eviction, and successful assignments continue to behave as they would if the failed assignment had not occurred.
- [ ] Successful assignment retains existing behavior: reclaim expired entries, enforce capacity with the existing LRU policy, store the new value, and establish its deadline from the assignment's sampled time.
- [ ] Replacing an existing key successfully refreshes its deadline and LRU position without leaving an extra active expiration record or changing size accounting incorrectly.
- [ ] Preserve supported nonnumeric timer/ttl combinations, including datetime plus timedelta, and restore the timer context after either success or failure.

## Constraints

- **Prepare the deadline before mutating cache state.** Cache data and expiration metadata must never describe different versions merely because timer/ttl addition raised.
- **Reuse the assignment's timer snapshot.** Expiration cleanup and the new deadline must agree on the same time even when the underlying clock advances between calls.
- **Update only src/cachetools/__init__.py, tests/test_ttl.py, and docs/index.rst.** This is a TTL assignment guarantee with no public signature change.
- **Add no dependencies and preserve existing checks.** The existing timer context and standard Python exception behavior are sufficient.

## Out of Scope

- Transactional rollback for errors from key hashing, getsizeof, custom eviction, or overridden expiration methods.
- Undoing side effects performed by caller-supplied timer or ttl objects themselves.
- Changing TLRUCache, TTL eligibility boundaries, or thread-safety guarantees.

<!-- devlyn:verification -->
## Verification

Run from the repository root, offline, with PYTHONPATH=src in the supplied Python 3.13 environment.

- `python -m pytest -q` exits 0. Add a compound test that fails deadline calculation while replacing a live key in a full cache, then performs a successful insertion and checks the resulting LRU victim and sizes; also cover failure for a new key, one deadline calculation per successful assignment, refresh, and timer-context recovery.
- `ruff check .` exits 0.
- `ruff format --check .` exits 0.
- `pyright` exits 0.

Semantics not exercised by these public tests remain source-review obligations under Requirements and Constraints, including failure with pending expired entries, custom time arithmetic, and preservation of expiration bookkeeping.

