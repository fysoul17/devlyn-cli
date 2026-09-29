# C4 mechanism

- **Family:** cross-field consistency.
- **Mandatory clause:** "After a successful resize, cache.maxsize equals the requested capacity and cache.currsize is no greater than that capacity; enforce this using the stored getsizeof-based sizes rather than the number of entries."
- **Trigger:** custom value weights make the stored total exceed the requested capacity even though the number of entries fits.
- **Causal code path:** the new inherited Cache.resize method decides whether to evict, then publishes the requested private maximum. The twin compares len(self) to that maximum instead of the getsizeof-based self.currsize.
- **Incorrect behavior:** no required eviction occurs, and the cache reports a maximum of four alongside a current recorded size of six.
- **Executable witness:** C4-O4 in oracle.md.
- **Near-miss exclusions:** recomputing mutable value weights, choosing the wrong LRU victim, failing to update maxsize, changing constructor validation, omitting timed cleanup, or returning an unintended value are separate defects. Unit-size caches and weighted caches with enough capacity do not distinguish the pair.

