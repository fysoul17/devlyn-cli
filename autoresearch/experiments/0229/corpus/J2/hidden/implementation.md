# J2 implementation brief

This request applies alone to the pinned tree. Do not ship hidden oracle cases as repository tests.

## Reference design

Change exactly `src/ruler.ts` and `test/markdown-it/ruler.test.mjs`.

Add documented `moveBefore(ruleName: string, beforeName: string): void` near the existing registration methods. Resolve both indices with `__find__`, checking the moved name first and throwing the existing `Parser rule not found: ...` style of error before touching the array. Return without changing anything for equal indices or when the moved rule is already immediately before the anchor.

Remove the existing registration object with `splice`. Insert that same object before the anchor. If the removed index was less than the original anchor index, the insertion index is the original anchor index minus one; otherwise it is the original anchor index. Invalidate `__cache__` after a real move. Keep function identity, `enabled`, and `alt` on the existing object. Do not mutate arrays previously returned by `getRules`.

Public tests in the existing Ruler suite should cover:

1. Register `a`, `b`, `c` with distinguishable functions and alternate chains, warm default and alternate chains, then move `c` before `a`. Assert execution/function order `[c, a, b]` and corresponding filtered alternate order.
2. Disable a later rule, move it before an earlier anchor, verify it is still excluded, then enable it and check its new location and alternate membership.
3. Self moves and already-adjacent moves leave order unchanged, including calls after the cache is warm.
4. Absent moved and anchor names throw the correct errors with no changes; when both are absent, the moved-name error has precedence.
5. An integration test may use the exported `MarkdownIt` class to install two core rules that append text, move the later one before the earlier one, and assert rendered text order.

Do not add a public move from an earlier position to a later nonadjacent anchor. Existing tests are unchanged except for the new cases. The pinned `npm test` runs no coverage threshold; do not add or weaken one.

## Twin construction

Keep the same files and byte-identical public tests. Change only the insertion-index calculation after removal: insert at the anchor's original index without subtracting one for a moved rule that originally preceded the anchor. Preserve both early no-op cases, validation, cache invalidation, and registration identity.

This is a common array-index mistake: the index found before a removal is reused after that removal has shifted the anchor. Later-to-earlier moves, self moves, and already-adjacent moves work. An earlier-to-later nonadjacent move lands immediately after the anchor. Do not add comments or names that reveal the mistake.

The twin must pass all public checks and fail only J2-O2 among the hidden rows. Both arms change exactly the two named files.
