# C1 mechanism

- **Family:** boundary semantics.
- **Mandatory clause:** "Obsolete heap records from overwritten or deleted entries do not count toward limit, and their removal must not remove or report the current value of a key."
- **Trigger:** a finite positive expiration limit, an obsolete record at the heap front, and an active expired value behind it; the heap is below the compaction threshold.
- **Causal code path:** TLRUCache.expire removes front records from its heap. The reference increments its budget counter only when removing an active expired value. The twin increments once per heap pop, including records already marked removed.
- **Incorrect behavior:** the call stops before removing the required number of eligible resident entries and returns too few pairs. With limit=1 it returns an empty list even though b is eligible.
- **Executable witness:** C1-O4 in oracle.md.
- **Near-miss exclusions:** returning stale values, deleting a replacement value, accepting negative limits, treating equality as live, changing unlimited expiration, or changing the heap compaction threshold are separate defects. Neither a time/work bound nor deterministic ordering among equal deadlines is required.

