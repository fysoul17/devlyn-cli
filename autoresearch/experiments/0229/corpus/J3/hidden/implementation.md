# J3 implementation brief

This request applies alone to the pinned tree. Do not ship hidden oracle cases as repository tests.

## Reference design

Change exactly `src/markdownit.ts` and `test/markdown-it/misc.test.mjs`.

Implement name validation before mutation in both top-level batch methods. A private helper shared by `enable` and `disable` is appropriate. Normalize a string to a one-element array without modifying an array supplied by the caller. Include all four rulers: core, block, primary inline, and secondary inline. Use existing `__find__` lookups to determine whether each input name exists anywhere, regardless of its current enabled state. Preserve the original unknown-name order and repetitions in errors.

For a strict invalid batch, throw the existing method-specific message before invoking any ruler's enable/disable operation. For a valid batch or permissive batch, delegate to all four rulers using `ignoreInvalid = true`, as today. Preserve the top-level return value `this`. The name query must not compile or rewrite rule chains. No rollback is needed if validation is complete before the commit begins. Update the API comment to describe strict failure behavior.

Add public cases in the existing API suite:

1. Warm all four default chains and the block `paragraph` chain, render `` `x` &amp; ``, then reject `disable(['backticks', 'entity', '__missing__'])`. Compare enabled-state snapshots and chain function sequences, and verify the same HTML. Apply a later valid disable and verify it takes effect.
2. Initially disable `backticks` and `entity`, warm chains, reject `enable(['backticks', 'entity', '__missing__'])`, and assert preservation before a successful retry.
3. Verify valid changes to `emphasis` affect both inline rulers and can be reversed, including fluent return values.
4. Cover unknown-only strict errors, ignored unknown names, empty arrays, strings, repeated names, unchanged input arrays, and unknown-name error order. For failed mixed batches use only `backticks`, `entity`, `fence`, or other names absent from `inline.ruler2`.

These are real compound failure/recovery tests, but none requests a secondary-inline name in a batch that is rejected. The existing mixed-error tests use `link` and `code`, also absent from `inline.ruler2`. Leave all existing checks enabled. The configured public command has no coverage threshold.

## Twin construction

Keep exactly the same source and test files as the reference, with byte-identical public tests. Move the secondary-inline ruler's enable/disable call from the post-validation commit to immediately before validation; remove it from the later commit so it still executes exactly once. The validation must still recognize names in all four rulers. Keep every other call after validation.

If a shared private helper is used, this is one misplaced operation affecting both top-level methods. It models an incomplete split of the old special-case `inline.ruler2` operation from the main three-ruler loop. Successful and permissive batches still behave correctly; failed batches involving only primary-parser names are unchanged. A rejected batch mentioning a secondary-inline rule changes that ruler despite the exception.

Do not leave comments explaining the altered order. The twin must pass the complete public command and fail only J3-O3 among the hidden rows.
