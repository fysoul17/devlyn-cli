# C4 implementation plan

## Reference

Change exactly src/cachetools/__init__.py, src/cachetools/__init__.pyi, tests/test_cache.py, and docs/index.rst in both implementations.

Add Cache.resize(self, maxsize), near the existing capacity properties. First reject maxsize < 0 using ValueError, consistent with the constructor. Read self.currsize once to run normal cleanup. Repeatedly call self.popitem() with the guard `while self.currsize > maxsize and len(self):`. Finally assign the private maximum-size field and return None implicitly. Do not call getsizeof or rebuild/reinsert retained entries. Keep maxsize a read-only property.

The nonempty guard must be checked before every popitem call, so inherited floating-point residue cannot cause an extra popitem on an empty cache. Leave Cache's current-size counter and stored-size table to the existing deletion and expiration hooks. Do not reconcile or sum recorded sizes, coerce numeric types, clamp the counter, or introduce an epsilon. Rounding, overflow, and resulting infinities or NaNs in the inherited accounting are outside this change's arithmetic contract. In particular, successful resize of an emptied cache need not normalize a residual counter to zero. Both implementations share this termination guard and unchanged accounting.

Using the public self.currsize is material: it means stored weighted size on ordinary caches and triggers existing cleanup on timed caches. The reference loop guard reads self.currsize after each eviction, preserving subclass accounting, rather than comparing the private counter or a local sum. The len(self) conjunct tests only whether a victim remains; it does not compare cardinality with capacity. Capacity victims are selected by dynamic self.popitem(), preserving built-in policy implementations and subclass hooks. Errors from caller hooks do not require rollback. Keep this repair local to resize; existing insertion, replacement, and deletion behavior remains unchanged.

Add _TimedCache.resize(self, maxsize): reject negative capacity with the same ValueError before entering the timer context, then delegate to Cache.resize(self, maxsize) inside with self.__timer. Hold that context for the whole base operation, including all loop checks, evictions, and capacity assignment. The existing reentrant timer wrapper gives cleanup and popitem the same time observation throughout the resize, so advancing time cannot cause popitem to expire entries after the size check and then evict an unnecessary live entry or raise on an empty cache. Both TTLCache and TLRUCache inherit this override.

Add def resize(self, maxsize: float) -> None to the Cache stub. Describe the operation beside the base Cache documentation, expose it in the documented members, and explain weighted capacity, inherited eviction, and unchanged getsizeof accounting, including the arithmetic limitation and safe termination on an empty cache.

## Public repository tests

Add tests in tests/test_cache.py using explicit cache classes/factories as needed. Preserve all existing tests.

1. Unit-sized LRU cache: insert a,b,c, read a, shrink to two, check b was evicted, maxsize/currsize are two, and returned result is None; insert d and verify c is evicted under the new limit.
2. Unit-sized caches: growth without eviction, unchanged size, shrinking to zero, empty cache, math.inf, and a fractional capacity such as 1.5 (one unit-sized survivor). Negative capacity must leave data/capacity unchanged.
3. Inherited FIFO/LFU/RR policies: use unit values and deterministic RR choice; make an unambiguous LFU victim. Include base Cache itself. Do not rely on unspecified tied LFU order.
4. TTLCache and TLRUCache: make one entry expire while two remain live, then resize to a capacity that exactly holds the two live unit-sized values. Assert no live victim.
5. Keep a cached wrapper bound to a cache, resize the object, and verify cache identity, cache_info capacity, and later admission.
6. Custom getsizeof retention: use stored weights greater than one, but resize only to capacities that fit all existing total weight (for example total weight six, old capacity twenty, new capacities ten and eight). Assert no getsizeof calls, no value replacement, and correct properties. A mutable value can change after admission while its recorded size remains unchanged, provided both total stored weight and entry count remain within all capacities used.

No public weighted scenario may put stored weight and entry count on different sides of the requested bound; no public zero-weight scenario may retain more entries than the requested numerical bound. The twin must pass those tests and the untouched suite. The pinned check configuration has no coverage threshold; do not add exemptions or weaken tests/configuration.

## Twin

Make exactly one change in the new Cache.resize loop guard: use len(self) > maxsize instead of self.currsize > maxsize, yielding `while len(self) > maxsize and len(self):`. Keep negative validation, the initial public currsize read, the nonempty conjunct, unchanged accounting, self.popitem(), assignment to the private capacity, the return value, the _TimedCache.resize timer context and delegation, documentation, stub, and all tests identical.

This is a plausible reuse of mapping cardinality for an operation often tested on unit-sized caches. Timed len(self) still performs normal expiration, so the public timed-cache scenarios also pass. On a weighted cache whose entry count fits but recorded weight does not, the loop stops too early and publishes an inconsistent maxsize/currsize pair.

Do not add comments, names, or extra branches that announce the defect. Both patches against the pinned tree must change exactly the four listed files.
