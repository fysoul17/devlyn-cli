---
id: "J2"
title: "Honor find options when selecting cache candidates"
kind: feature
status: planned
complexity: high
depends_on: []
---

# Honor find options when selecting cache candidates

## Context

Callers use `find()` to locate the newest cached value satisfying a predicate, sometimes accepting expired values for a particular lookup. Its options already control retrieval of the matching value, but candidate selection currently follows only the cache's default stale policy. A lookup should apply one consistent stale policy while searching and retrieving its result.

## Requirements

- [ ] `find(fn, getOptions)` uses an explicitly supplied `getOptions.allowStale` value, whether `true` or `false`, in preference to `cache.allowStale` when selecting candidates. An omitted or `undefined` value inherits the cache's current setting.
- [ ] When the effective stale policy is false, expired entries do not reach the predicate; searching continues toward older eligible entries without deleting or refreshing the excluded entries.
- [ ] When the effective stale policy is true, expired entries are eligible alongside fresh entries. Eligible values reach the predicate in most-recently-used to least-recently-used order, and the first truthy predicate result selects the value to retrieve.
- [ ] Predicate calls retain the `(value, key, cache)` arguments. A search without a match returns `undefined` and leaves entry membership, recency, and TTL ages unchanged.
- [ ] Retrieving a match preserves the existing get-option behavior: a fresh match becomes most recently used and honors `updateAgeOnGet`; a stale match honors `noDeleteOnStaleGet`, including the default removal of an ordinary expired entry. Entries merely visited by the predicate are not refreshed or promoted.
- [ ] Existing behavior for values involved in a background fetch remains intact, including skipping a pending fetch that has no previous value.
- [ ] Add focused regressions in `test/find-options.ts` for option inheritance, stale inclusion, predicate order and arguments, and the retrieval effects described above.

## Constraints

- **Change only `src/index.ts` and `test/find-options.ts`.** The behavior belongs to `find()` and its focused regressions, so existing iterator APIs and unrelated tests should not need edits.
- **Add no dependencies.** The repository already provides the test runner and a configurable time source needed for deterministic TTL checks.
- **Preserve the existing public method signature and option types.** Callers should receive the corrected behavior without changing their code or type annotations.
- **Keep time-based regression checks deterministic.** Use the existing configurable clock facilities so expiry assertions do not depend on scheduler delays.

## Out of Scope

- Changing the behavior or defaults of standalone `get()`, `peek()`, `fetch()`, or cache iterators.
- Adding new lookup options, predicate mutation guarantees, expiry boundaries, or background-fetch policies.
- Changing dependencies, generated distribution files, or snapshots.

<!-- devlyn:verification -->
## Verification

- `PATH=/Users/Shared/devlyn-vr-0227/toolchains/node-lru-cache/node-bin:$PATH npm test -- -c -t0` exits 0. This includes the configured `pretest` build and its TypeScript checks, the existing suite, and `test/find-options.ts`. The focused tests cover option inheritance, per-call stale inclusion and exclusion, and predicate order and arguments. A compound scenario searches through stale and fresh candidates, records predicate arguments and order, retains a matched stale value on request, then retrieves and promotes a fresh value with an age refresh; it checks membership, recency, and remaining TTL after both searches. Separate cases check stale removal and a search with no match.

Requirements and constraints not exercised by this command remain source-review obligations.
