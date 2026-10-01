# P3 implementation instructions

Family: failure-state preservation. Apply this request alone to the pinned tree.

## Reference design

Change exactly `src/dateutil/tz/tz.py` and `tests/test_tz.py`. Keep this changed-file set and the test contents identical in both patches.

`GettzFunc`, created inside `__get_gettz`, owns a weak instance dictionary, an ordered strong cache, its configured size, and a lock. Its current `set_cache_size` stores the requested value before discovering invalid inputs through comparison or eviction. Correct this method locally:

1. Normalize `size` with `operator.index`. This accepts normal integers, booleans, and the integer-index protocol while rejecting floats and strings without coercion. Add the standard-library import.
2. Reject a negative normalized size with `ValueError` before committing any cache state. Let index-conversion exceptions propagate unchanged.
3. With the existing lock held, store the validated capacity and run the existing least-recently-used eviction loop. Leave weak references and recency of surviving entries intact. Keep the implicit `None` return.
4. Add a method docstring describing valid sizes, zero capacity, and rejection behavior. Do not alter `__call__`, `cache_clear`, or the other timezone factories.

Validation may occur before acquiring the lock because it does not read or mutate cache state. All committed updates must remain under the lock.

## Public tests added to the repository

Avoid dependence on the host timezone database or other factory caches. Make an isolated getter with `type(tz.gettz)()` and replace only that instance's `nocache` callable with a factory returning a fresh instance of a small `datetime.tzinfo` subclass. Such objects support weak references and have no other owner. The hidden oracle supplies a reusable example. Keep tests compatible with the repository's supported syntax.

- Valid capacities include zero, one, a larger integer, booleans, and an object whose `__index__` returns two. Assert the `None` return and resulting strong retention/eviction.
- Starting from a fresh empty getter, assert `ValueError` for `-1` and for an index object returning `-1`. Dispose of or explicitly reset this getter before any subsequent lookup or state assertion. This checks exception type without exercising the target history.
- Check `TypeError` for `None`, `'3'`, `1.5`, and a non-index object. Check propagation of a deliberate exception from `__index__`.
- A compound non-index failure test fills a size-three cache with A, B, C, touches A, rejects `'2'`, and inserts D. After garbage collection, B alone must have expired; A, C, D must remain. Then shrink to two and check that C expires. This exercises rejection, continued lookup, recency, and successful mutation while missing only the target negative-input commit.
- A valid shrink evicts oldest entries immediately. A valid grow preserves current entries and their ordering. Zero capacity drops strong retention but still reuses an object when the test holds a live reference to it.
- All fixture/global state must be restored; prefer isolated instances to global monkeypatching. Do not rely on object destruction timing without `gc.collect()`.

Do not add a negative-size rejection followed by lookup or retained-state assertions to the public tests. Keep generated input/state combinations from introducing that sequence. Existing tests use only nonnegative integer capacities.

## Twin construction

Leave `operator.index` validation before the lock as in the reference. Move only the negative-range check to immediately after assigning the normalized value to `self.__strong_cache_size` inside the lock, before the eviction loop:

```python
size = operator.index(size)
with self._cache_lock:
    self.__strong_cache_size = size
    if size < 0:
        raise ValueError('Cache size must be nonnegative')
    while len(self.__strong_cache) > size:
        self.__strong_cache.popitem(last=False)
```

The reference checks the range before the assignment. Use the same error text in both patches. This single validation/commit ordering mistake raises the right exception while retaining an invalid negative capacity. It does not evict immediately, but later cache hits evict objects because `len(strong_cache) > negative_capacity` is always true.

All other methods, documentation, and tests remain the reference versions. Use ordinary production comments and naming. The public negative-size cases inspect only the exception and discard/reset the instance; the compound failure case uses an invalid type that still fails before assignment. Thus both patches pass the public suite and the whole-project coverage target.
