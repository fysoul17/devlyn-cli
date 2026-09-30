---
id: "J1"
title: "Allow has to require a minimum remaining TTL"
kind: feature
status: planned
complexity: high
depends_on: []
---

# Allow has to require a minimum remaining TTL

## Context

Some callers need to know whether a cached value will remain usable for an upcoming operation, rather than merely whether it is fresh now. `has()` already checks freshness without changing recency and can optionally refresh an entry's age. Add a per-call minimum remaining TTL so callers can make this decision without retrieving the value.

## Requirements

- [ ] Extend `LRUCache.HasOptions` with optional `minTTL`, measured in milliseconds. Omission and `undefined` mean zero; finite nonnegative numbers, including fractions, are accepted. Negative or nonfinite values throw `RangeError`, including when the key is absent.
- [ ] For a present, non-stale entry with an available value, `has(key, { minTTL })` returns true when its remaining TTL is greater than or equal to `minTTL`, and false when it is less. Entries without an expiration satisfy every accepted minimum.
- [ ] A zero minimum preserves existing `has()` behavior, including the library's existing expiration boundary. Absent entries, stale entries, and pending fetches without a previous value continue to return false.
- [ ] Evaluate the minimum against the remaining TTL before any age refresh. A false result does not refresh the entry's age or delete it; a true result honors the existing per-call and cache-level `updateAgeOnHas` settings.
- [ ] Checking a minimum does not change recency, stored values, entry count, or calculated size, and does not call insertion or disposal callbacks. For a pending refresh with an available previous value, apply the same freshness and minimum checks to that cached entry without disturbing the fetch.
- [ ] Add `"ttl"` to `Status.has` for a non-stale entry rejected by the minimum. Retain `"hit"`, `"stale"`, and `"miss"` for their existing cases; on a `"ttl"` result populate the existing TTL status fields from the unrefreshed entry.
- [ ] Document the option, its units, and the additional status outcome in the exported TypeScript API documentation, and add focused tests to the repository's test suite.

## Constraints

- **Zero new dependencies.** The existing TTL and status machinery is sufficient for this option.
- **Limit changes to `src/index.ts` and `test/has-min-ttl.ts`.** This keeps the change within the existing cache implementation and one focused regression test file.
- **Use the cache's existing TTL clock and resolution semantics.** Minimum checks must agree with the freshness decisions made by other cache operations.
- **Preserve the existing test, lint, build, and coverage configuration.** The normal repository checks must continue to evaluate the change.

## Out of Scope

- A cache-wide minimum TTL setting or equivalent options on `get`, `peek`, or `fetch`.
- Changing the library's definition of staleness, TTL resolution, or automatic purging.
- Fetch cancellation, proactive refresh, or new diagnostic events.

<!-- devlyn:verification -->
## Verification

- `PATH=/Users/Shared/devlyn-vr-0227/toolchains/node-lru-cache/node-bin:$PATH npm test -- -c -t0` exits 0. This runs the repository's CI test command and its `pretest` build; `tshy` provides the configured TypeScript compilation and declaration checks, so no separate type-check command is duplicated here. The added tests cover accepted and rejected minima, validation, unbounded lifetimes, existing miss/stale behavior, and a compound sequence in which rejection preserves age and order while a later accepted check refreshes age.
- Requirements and constraints not exercised by this command remain source-review obligations.
