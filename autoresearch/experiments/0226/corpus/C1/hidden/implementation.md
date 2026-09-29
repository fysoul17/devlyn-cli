# C1 implementation plan

## Reference

Change exactly these files in both implementations:

- src/cachetools/__init__.py
- src/cachetools/__init__.pyi
- tests/test_tlru.py
- docs/index.rst

Extend only TLRUCache.expire(time=None, *, limit=None). Validate the limit before selecting time or touching the heap: None or isinstance(limit, int) is accepted; a negative int raises ValueError and any other type raises TypeError. A zero limit may return immediately. Keep the existing timer selection, heap compaction, and deadline comparisons.

Track the number of active expired values removed during this call. Stop the loop when this number reaches a finite limit or when the heap has no eligible front record. Popping a removed _Item is bookkeeping and must not advance that count. Advance the count inside the existing not-item.removed branch, together with appending the pair and removing the base data and active item mapping. Keep all existing calls to expire unlimited. Retain the original strict time < expires comparison and do not compare keys.

Update the existing TLRUCache stub with limit: int | None = None and the keyword-only separator. Document the parameter, return semantics, retained expired values, and the distinction between a value limit and a work limit.

## Public repository tests

Add ordinary unittest methods to tests/test_tlru.py, using its Timer and explicitly parameterized cache types where needed for pyright.

1. Insert three values with distinct deadlines and no replacements/deletions. At a time after all three deadlines, expire with limit=2; assert the first two pairs and use Cache.__len__(cache) and Cache.currsize.fget(cache), or an equivalent non-expiring base accessor, to check one resident entry remains. Ordinary containment/get must report that entry expired. An unlimited expire returns only the final pair.
2. On separate caches without obsolete records, cover limit=0, limit=None, limit larger than the eligible count, no eligible entries, and expiry exactly at the cutoff. Check True/False limits.
3. Invalid negative, float, and string limits raise before the timer is called and before resident entries change. In tests for intentionally invalid types, use the repository's typing conventions or an Any-typed callable so pyright accepts the deliberate runtime checks.
4. A supplied time takes precedence over the fake clock. A counted timer is read once when time is omitted. Verify ordinary insertion after a partial drain and unlimited implicit cleanup.

Do not add a public finite-limit scenario containing obsolete heap records. Keep the existing tests unchanged. The pinned tox.ini requests coverage reporting but sets no fail-under threshold; none is configured in pyproject.toml. Do not add coverage exclusions, lower checks, or install dependencies.

## Twin

Use the reference files verbatim except for one change in TLRUCache.expire: move the removed-value counter increment out of the not-item.removed branch so every heap pop advances the limit counter. Keep the same limit guard, validation, heap compaction, and result append logic. This is a plausible implementation of a batch counter at the loop level.

There must be no comments, identifiers, extra branches, or test changes advertising this deviation. In particular, never return an obsolete record as an expired pair. Unlimited behavior is identical; finite calls without obsolete records are identical. The existing suite and all added public tests therefore pass. Both diffs against the pinned tree touch exactly the four files listed above.

