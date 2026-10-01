# J2 mechanism record

- **Family:** ordering/precedence.
- **Mandatory clause:** "The resulting order must place the moved rule immediately before the anchor whether its original position was earlier or later than the anchor; all other rules must retain their relative order."
- **Trigger:** Move an existing rule toward a later, nonadjacent anchor in the same ruler.
- **Causal code path:** `Ruler.moveBefore` resolves indices, removes the moved registration, and inserts it using the anchor index. The twin retains the index from before removal, even when removal shifted the anchor left.
- **Incorrect behavior:** The moved rule is inserted immediately after the anchor and therefore executes with the opposite precedence. For `[a,b,c,d]`, moving `a` before `c` gives `[b,c,a,d]` instead of `[b,a,c,d]`.
- **Executable witness:** J2-O2 in `oracle.md`.
- **Near-miss exclusions:** Later-to-earlier moves, self moves, already-adjacent moves, absent-name handling, and cache invalidation all work in this twin. Array identity for previously returned chains is not promised. Duplicate names use the existing first match; changing that policy or losing enabled/alternate metadata would be a separate defect.
