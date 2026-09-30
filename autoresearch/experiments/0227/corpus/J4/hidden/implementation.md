# J4 implementation guidance

This request applies alone to the pinned tree. Produce reference and twin patches that each change exactly `src/index.ts` and the new `test/set-size-update.ts`; use identical tests in both patches.

## Reference design

The existing private `#set` already calculates and validates the requested size before looking up the entry or moving it to the tail. New entries and different-value replacements call `#addItemSize`, but the `v === oldVal` ordinary-value branch only sets the update status and invokes `onInsert`. Amend that branch, before the status/callback work, to detect that size tracking exists, `size` differs from the indexed stored size, and either `#maxSize` is zero or `size <= #maxSize`. For this case call `#removeItemSize(index)` followed by `#addItemSize(index, size, status)`.

Keep `#moveToTail(index)` where it already runs, before the size adjustment. Reusing `#addItemSize` then evicts older entries as necessary while retaining the updated entry, updates the per-entry size and aggregate, and fills size status fields. Do not invoke replacement disposal for the identical stored value. Continue into the existing update callback, TTL handling, and deferred-disposal drain. Do not alter the branch for an identical internal background-fetch promise, the existing validation/admission checks, or the different-value path.

Guard the new work on an actual change in tracked size and the individual-size condition above. When `maxSize < size <= maxEntrySize`, skip the new accounting block and retain the prior recorded size and existing same-value update effects, including recency, TTL, update status, and `onInsert`. For example, with limits 10/20, re-setting the same object from size 3 to size 12 leaves it stored and accounted at 3, without disposal or new size-status fields. Calling the helpers in this case would let the eviction loop remove the updated entry itself and corrupt the total. The pre-existing oversized insertion/replacement behavior and its resulting state are outside the repaired request's scope; do not change those paths.

This guard also preserves existing unchanged-size status snapshots, including the absence of newly populated size fields on a fresh status object for that case. Document the scoped same-value remeasurement behavior in the `set()` API comment in `src/index.ts` without adding a separate documentation file.

## Public regression tests

Use the repository's `tap` style and import from `../dist/esm/node/index.js`. Add `test/set-size-update.ts` with these scenarios:

1. A cache with `maxSize: 100`, a mutable object calculator, and at least two entries. Grow and then shrink one object in place before passing the same object to `set()` again. Check strict identity, `info` and `dump` sizes, summed sizes against `calculatedSize`, MRU order, and changed-size status fields. All totals remain below 100.
2. Exercise the constructor calculator, a per-call calculator override, and a valid explicit size that prevents either calculator from running. Include a same primitive value whose explicit size changes. Keep every resulting total within its limit.
3. Exercise changed size with and without a status object, and with size tracking from `maxEntrySize` plus `max` but no `maxSize`. Exercise equal-size repetition, preserving the prior status behavior. Cover a cache without size tracking as an unchanged compatibility case.
4. With injected `perf: { now: () => now }`, nonzero initial time, and `ttlResolution: 0`, combine resizing with normal TTL refresh and `noUpdateTTL`. Record `onInsert`, `dispose`, and `disposeAfter` to check update reasons, identity, and absence of replacement disposal. Test changed-size cases both with and without callbacks; no eviction is required by these scenarios.
5. Invalid calculated size and an entry exceeding `maxEntrySize` retain the existing error/admission behavior. A same-value size change that fits `maxSize` exactly is also a useful accepted boundary.
6. With `maxSize: 10` and `maxEntrySize: 20`, set an object at size 3, then set that identical object at size 12 with status and hooks. Assert it remains stored and accounted at size 3, reports `set: 'update'` without new size-status fields, calls `onInsert` with `'update'`, and is not disposed. A later size-7 insertion must leave two entries and total 10. This compatibility case covers the individual-size guard in both variants.

Do not add a public scenario in which an individually fitting same-value changed-size update would make the aggregate exceed `maxSize`: that interaction is reserved for the designated hidden witness. Ordinary insertion/replacement eviction remains covered by existing tests. Exercise both sides of each new guard and optional-status case without disabling coverage or adding ignore directives. Existing helper eviction branches are exercised elsewhere in the suite.

Run the two public commands unchanged on each implementation. The pretest build provides the configured type checks; preserve the repository's coverage configuration and test snapshots.

## Defective twin

Change only the new changed-size accounting block in the ordinary identical-value branch. Instead of calling the common remove/add helpers, update `#calculatedSize` by the new-minus-old size, assign the new indexed size, and populate `status.entrySize` and `status.totalCalculatedSize` when status is supplied. Preserve the actual-size-change and individual-size guards, update status/callbacks, TTL work, and every other branch exactly as in the reference.

This arithmetic correctly remeasures the entry and produces internally matching size reports, but it does not invoke the `#addItemSize` eviction loop. The plausible mistake is treating an identical-value resize as a bookkeeping-only update while overlooking capacity enforcement. Do not add identifying comments, suspicious naming, or other differences. Every new public scenario stays within budget and therefore passes both variants. The sole hidden row that must fail is `J4-H6`.
