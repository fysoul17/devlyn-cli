# C2 implementation plan

## Reference

Change exactly src/cachetools/__init__.py, tests/test_tlru.py, and docs/index.rst in both implementations. No stub change is needed because the public signatures are unchanged.

Give each TLRUCache instance a monotonically increasing assignment counter. Add an assignment-order field to _Item, initialized compatibly with its internal construction. Each successful storing assignment creates a new _Item with a fresh order, including replacement of an existing key. Allocate the order only after the current ttu validation and Cache.__setitem__ succeed. Leaving gaps would be harmless, but do not change admission or dead-on-arrival removal behavior.

Compare _Items by deadline first, then assignment order. Preserve support for deadline objects whose meaningful ordering is expressed by <; for example compare each deadline with the other in turn and use the assignment order if neither precedes the other. Do not use key or value as a tiebreaker. Retain heapq, the removed marker, the active-item OrderedDict, and the existing compaction path. Reads may reorder the LRU mapping but must not change the assignment field. Clear may reset the counter if it also resets all existing records, as it already does.

Document the deadline-first/current-assignment-second order in the existing TLRU expire documentation. Do not promise iteration order.

## Public repository tests

Add unittest tests to tests/test_tlru.py:

1. Three previously absent keys with the same deadline expire in insertion order. Read the first key before expiration and show that the order is unchanged.
2. Interleave two deadline groups; deadlines take precedence over insertion order and ties follow assignment order.
3. Delete one tied key and verify only the other tied keys are returned in order.
4. Replace a key with a different deadline that is distinct from every other current deadline; verify that only its newest value is returned at the new deadline.
5. Use nonorderable object keys and numeric values with equal deadlines. Verify no key comparison is attempted.
6. Verify ordinary LRU eviction after a read still selects the same victim. Retain the existing replacement, dead-on-arrival, datetime, and heap-compaction tests.

Public tests must not replace a key into a deadline shared by another current key. Existing tests compare expiration ties as sets or lengths, so the new order does not invalidate them. The pinned coverage configuration reports coverage but has no minimum threshold. Do not alter existing assertions or check configuration.

## Twin

In the replacement path, reuse the previous current _Item's assignment-order value instead of giving the replacement the fresh order. Fresh keys still get fresh orders; the per-cache counter can still advance on every successful assignment. All other code, comparison logic, tests, and documentation are identical.

Concretely, capture the previous current item at the same place the reference already looks it up to mark it removed; if present, assign its order to the new item. Keep the reference's fresh order when the key has no surviving current item after admission. This is a plausible confusion between the key's original insertion order and the assignment order of its current value.

This single mechanism changes only tied replacements. Different-deadline replacements and initial tied insertions behave identically. Do not add explanatory comments or names that signal the defect. Both patches must change exactly the three listed files.

