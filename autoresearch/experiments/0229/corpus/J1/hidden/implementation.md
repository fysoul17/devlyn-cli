# J1 implementation brief

This request applies alone to the pinned tree. Do not ship hidden oracle cases as repository tests.

## Reference design

Change exactly these files:

- `src/rules_inline/state_inline.ts`
- `src/parser_inline.ts`
- `test/markdown-it/inline-cache.test.mjs` (new)

Keep `StateInline.cache` as `Record<number, number>`. Add an internal parallel numeric mapping, for example `cacheBounds`, that records the `posMax` used for each cached start. Initialize it per state, not on the prototype. Document its relationship to `cache`.

At entry to `skipToken`, capture the starting position and current upper bound. A hit requires both an existing numeric end and an equal recorded upper bound. On a miss, run the current algorithm unchanged and store both the ending position and the entry upper bound for that start. Store the captured entry bound, rather than relying on mutable state after rule execution. This keeps one answer per start, supports nested lookahead at other positions, and does not clear or repurpose the separate backtick-run cache. No cache clearing during ordinary tokenization is necessary.

Add public tests using the existing `node:test` and strict-assert style:

1. Create ``new md.inline.State('`a`', md, {}, [])``; call `skipToken` at zero with the full bound and expect position 3. Reset the position, narrow the bound to 2, call again, and expect position 1. Check that tokens and pending text are unchanged and the starting level is restored.
2. Put a counter rule before `text`, returning false. Revisit the same code span twice at zero with the same full bound; the counter runs once and both calls end at 3. Confirm the numeric end remains available as `state.cache[0]`.
3. Cache the span in ``'`a` xx'``, then narrow to bound 3, where it still ends at 3. The counter must run again despite the old end being inside the new range.
4. Check ordinary rendered code spans inside a link and an unmatched backtick, without reusing a state across increasing bounds.

These tests cover full and decreasing bounds only. Do not add a public test that revisits a position after increasing its bound. Existing repository tests, lint, build and type checks remain enabled and unchanged. `npm test` has no coverage threshold in this tree; do not introduce or weaken one.

## Twin construction

Use precisely the reference file set, including byte-identical public tests. Change only the bound comparison in the cache-hit predicate: accept a cached bound **less than or equal to** the current `posMax` instead of requiring equality. Continue to require an existing cached end, and keep recording the bound on misses.

This is the plausible mistaken assumption that expanding a lookahead window cannot invalidate a token already skipped inside the smaller window. Shrinking still recomputes, and unchanged bounds still hit. A backtick that was unmatched within the smaller range can gain its closer after expansion, so its previously short end is no longer valid. Do not add special cases, suggestive identifiers, or explanatory comments about this deviation.

The twin must pass the complete public command, including the new tests, and fail only J1-O3 among the hidden rows. Each arm must be tested independently against the pinned base in a writable copy.
