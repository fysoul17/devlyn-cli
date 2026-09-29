# C3 mechanism

- **Family:** failure-state preservation.
- **Mandatory clause:** "If computing that deadline raises, propagate the same exception and leave resident values, recorded sizes, LRU order, and expiration bookkeeping unchanged, including expired entries awaiting cleanup."
- **Trigger:** TTLCache assignment when at least one expired value remains physically resident and addition of the sampled time and ttl raises.
- **Causal code path:** the twin's TTLCache.__setitem__ calls self.expire(time) before preparing expires. That call removes data, size records, and linked expiration/LRU records; subsequent arithmetic raises, and there is no rollback.
- **Incorrect behavior:** the failed assignment consumes expired entries and their later expire result, even though it never admits a new value. The reference computes the deadline first, so a later expire still reports those entries.
- **Executable witness:** C3-O4 in oracle.md.
- **Near-miss exclusions:** storing the new value before the calculation, refreshing the wrong successful deadline, reading the timer twice, swallowing or replacing the exception, or failing to restore timer nesting are different defects. Callback side effects and rollback from later getsizeof/hash/eviction errors are outside scope.

