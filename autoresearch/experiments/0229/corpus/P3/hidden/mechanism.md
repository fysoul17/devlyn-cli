# P3 mechanism record

- **Family:** failure-state preservation.
- **Mandatory clause:** “Any rejected size leaves the configured capacity, retained timezone objects, and recency order unchanged; subsequent lookups behave as if that resize call had not occurred.”
- **Trigger:** a negative integer size is rejected on a populated `gettz` cache, followed by an ordinary cache hit.
- **Causal code path:** `GettzFunc.set_cache_size` converts the index, acquires the lock, and stores the negative size before raising `ValueError`. The lock is released correctly, but `__strong_cache_size` remains negative. `GettzFunc.__call__` then refreshes an entry and sees `len(__strong_cache) > __strong_cache_size`, evicting an entry even though the previously configured capacity was not exceeded.
- **Incorrect behavior:** callers receive the expected resize exception but lose cached timezone identities on later successful lookups. This is retained configuration corruption, not just an incorrect exception class.
- **Executable witness:** `P3-W` in `hidden/oracle.md`; the hit on C leaves A, B, C alive on the reference but drops the only strong reference to A on the twin.
- **Near-miss exclusions:** wrong eviction direction during successful shrink; zero-size weak-cache behavior; failed integer conversion; swallowed exceptions; unreleased locks; other timezone factory caches. The twin changes only the placement of the negative-range check relative to committing the capacity.
