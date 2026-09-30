---
id: "J3"
title: "Preserve cache state when synchronous memoization fails"
kind: feature
status: planned
complexity: high
depends_on: []
---

# Preserve cache state when synchronous memoization fails

## Context

Applications use `memo()` to synchronously recalculate cached data and may retry when their calculation fails. A failed calculation should leave the cache available for that retry without consuming an entry, changing eviction priority, or extending its lifetime. Successful calculations should continue to honor the cache's existing lookup and insertion options.

## Requirements

- [ ] If `memoMethod` throws, `memo()` rethrows that same thrown value without changing cache membership, cached values, recency order, TTL durations or start times, entry sizes, or `calculatedSize`.
- [ ] A `memoMethod` failure causes no `dispose`, `disposeAfter`, or `onInsert` calls attributable to the failed `memo()` operation.
- [ ] When the lookup accepts a cached value and `forceRefresh` is false, return that selected value, apply the normal lookup effects, and do not invoke `memoMethod`; misses and forced refreshes invoke `memoMethod` once with the key, the lookup's prior value, and the supplied context.
- [ ] Resolve `allowStale`, `updateAgeOnGet`, and `noDeleteOnStaleGet` from the call's options and cache defaults at entry. Changes to those fields on the callback's options object do not change the current operation's lookup behavior or prior-value argument.
- [ ] After successful recomputation, perform the normal lookup effects using those resolved lookup options and store the returned value using the callback's resulting set options. This includes stale deletion, recency, age refresh, `noUpdateTTL`, size accounting, disposal and insertion behavior, and changes the callback makes to `ttl`, `size`, `sizeCalculation`, or `noDisposeOnSet`.
- [ ] Preserve the existing outer `status` and `context` behavior of `memo()`, including hit/miss classification, forced-refresh reporting, and the successful result value.
- [ ] Add regression coverage in `test/memo-failure.ts` for successful hits, misses, fresh and stale recomputation, callback-updated options, and thrown calculations, including a compound failure-and-retry scenario.
- [ ] **Design-only:** Update the `memo()` and `MemoizerMemoOptions` API comments to describe failure preservation and the entry-time lookup options without claiming that the state-changing lookup has already run before the callback.

## Constraints

- **Touch only `src/index.ts` and the new `test/memo-failure.ts`.** Keeping the change local protects unrelated cache operations and existing diagnostics snapshots.
- **Do not modify `test/memo.ts`.** The tracing suite imports it and records its events, so new scenarios belong in the separate test file.
- **Add no dependencies.** Existing TypeScript, Tap, and cache APIs are sufficient for this change.
- **Keep the existing public method signatures and option types.** Consumers should receive the stronger failure guarantee without migrating their code.
- **Use deterministic time in the regression tests.** The cache's `perf` option and `ttlResolution: 0` allow precise lifetime assertions without waiting on wall time.
- **Keep failure handling local to synchronous memoization.** The guarantee concerns cache effects of `memo()` itself; rolling back callback-owned work or redesigning the cache's other hooks would require a separate contract.

## Out of Scope

- Rolling back cache mutations, object mutations, or external side effects performed by `memoMethod` itself.
- New failure guarantees for exceptions from disposal, insertion, size calculation, diagnostics subscribers, or other hooks outside `memoMethod`.
- Changes to asynchronous `fetch()`, public `get()` or `set()` behavior, or automatic expiration scheduling.
- New options, public APIs, dependencies, or broad cache refactoring.

<!-- devlyn:verification -->
## Verification

- `PATH=/Users/Shared/devlyn-vr-0227/toolchains/node-lru-cache/node-bin:$PATH npm test -- -c -t0` exits 0. The new regression file covers a compound scenario that preloads two size-tracked entries, fails a forced recalculation of the most recent entry, compares cache state and callback logs, retries successfully with callback-updated set options, and inserts a third entry to verify eviction and accounting. It also covers hits, misses, fresh and stale successful recomputation, and a failed calculation for a missing key. The configured pretest build runs `tshy`, providing the repository's TypeScript checks as part of this command.

The command verifies the regression scenarios and existing suite. Review the implementation for the remaining semantic obligations across the supported options, error propagation, public API compatibility, and documentation accuracy; textual pattern checks do not establish those properties.
