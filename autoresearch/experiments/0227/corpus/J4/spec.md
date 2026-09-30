---
id: "J4"
title: "Refresh size accounting when setting the same value"
kind: feature
status: planned
complexity: high
depends_on: []
---

# Refresh size accounting when setting the same value

## Context

Applications can mutate a cached object in place and call `set()` again to refresh its size. The cache currently calculates the new size but retains the previous accounting when the value is identical to the stored value. This leaves the reported entry size and total size inconsistent with the most recent `set()` call.

## Requirements

- [ ] For an existing ordinary cached value, when `maxSize` is zero or the computed entry size is at most `maxSize`, a successful `set(key, value, options)` with `value ===` the stored value must record a changed size using the existing size-selection rules: a valid explicit `size` takes precedence, otherwise the per-call `sizeCalculation` or constructor calculator supplies the size. When the computed size exceeds a nonzero `maxSize` but passes the existing `maxEntrySize` check, preserve the prior recorded size and existing same-value update behavior.
- [ ] After such a size change, `info(key).size`, the corresponding `dump()` entry's `size`, and `calculatedSize` must reflect the new size; `calculatedSize` must equal the sum of the stored entry sizes. A supplied status object must report the new `entrySize` and final `totalCalculatedSize`.
- [ ] When the remeasured entry individually fits the configured size limits but the resulting total would exceed a nonzero `maxSize`, the same-value update must evict least-recently-used entries until the total fits, retaining the updated entry as most recently used. Each evicted entry must receive the existing eviction disposal behavior.
- [ ] A successful same-value update must retain the value's identity and report `status.set === 'update'`; `onInsert`, when configured, must receive that value with reason `'update'`. Remeasurement must not dispose the updated value as a replacement.
- [ ] The existing TTL rules must apply to a resized same-value entry: normally the supplied or default TTL is refreshed, while `noUpdateTTL` preserves the previous TTL and start time.
- [ ] If the computed size is unchanged, preserve the existing same-value update behavior, including recency, callbacks, and status-field population. Caches without size tracking must retain their existing behavior.
- [ ] Preserve the existing validation and `maxEntrySize` handling: invalid size calculation must fail before changing the cached entry, and an entry exceeding `maxEntrySize` must follow the existing rejection/deletion behavior.

## Constraints

- **Zero new dependencies.** Existing helpers and test infrastructure provide the required size accounting and assertions.
- **Limit implementation changes to `src/index.ts` and `test/set-size-update.ts`.** The correction belongs in the existing set operation and a focused regression test file.
- **Preserve other set and fetch paths.** Insertion, replacement by a different value, and pending background-fetch bookkeeping already have their own accounting and must remain compatible.

## Out of Scope

- Automatically detecting mutations without another `set()` call.
- Adding a public resize API or changing size option precedence.
- Repairing insertion or different-value replacement for entry sizes above a nonzero `maxSize` when a larger `maxEntrySize` has been configured, including their admission, accounting, status, callback, and subsequent-state consequences. The guarantees above do not extend to cache state already corrupted by those operations.
- Changing callback reentrancy guarantees or TTL expiration boundaries.

<!-- devlyn:verification -->
## Verification

- `PATH=/Users/Shared/devlyn-vr-0227/toolchains/node-lru-cache/node-bin:$PATH npm test -- -c -t0` exits 0. Its configured pretest build performs the repository's TypeScript checks; the test suite includes compound cases that remeasure the same value and check entry/total accounting, status, recency, callbacks, and TTL behavior together, plus existing coverage checks.
- Requirements and constraints not exercised by this command remain source-review obligations.
