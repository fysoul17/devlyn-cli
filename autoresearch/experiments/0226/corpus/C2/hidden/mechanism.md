# C2 mechanism

- **Family:** ordering/precedence.
- **Mandatory clause:** "Among equal deadlines, return entries in the order of the successful assignments that established their current values; replacing an existing value gives that entry a new position after entries already assigned the same deadline."
- **Trigger:** a successful replacement shares a deadline with entries assigned after the key's old version but before its new version.
- **Causal code path:** TLRUCache.__setitem__ replaces its active heap item while marking the old one obsolete. The twin copies the old assignment-order field to the new item; _Item.__lt__ then applies that stale field when deadlines tie.
- **Incorrect behavior:** the replacement expires in the old key position, ahead of entries whose current assignments preceded it.
- **Executable witness:** C2-O3 in oracle.md.
- **Near-miss exclusions:** a wrong deadline comparison, changing LRU eviction, comparing keys, returning obsolete versions, changing iteration order, or failing during assignment is not this defect. Initial tied insertions and replacements with unique deadlines do not distinguish the pair.

