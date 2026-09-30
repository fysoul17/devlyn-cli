# J1 implementation instructions

This request applies independently to the pinned repository. Both implementations change exactly `src/index.ts` and the new `test/has-min-ttl.ts`. Do not change dependencies, configuration, snapshots, or coverage exclusions.

## Reference design

Extend `LRUCache.HasOptions` with `minTTL?: Milliseconds`, and extend `Status.has` with `'ttl'`. Update their JSDoc and the public `has()` documentation. Leave the public wrapper's existing metrics behavior intact.

In `#has`, resolve `minTTL = 0` along with the existing options. Reject a nonfinite or negative minimum with `RangeError` before looking up the key. `Number.isFinite(minTTL)` and a negative comparison suffice; do not require an integer.

Keep the existing missing-key, stale-entry, and background-fetch-without-a-value paths. Inside the non-stale path, before `#updateItemAge`, use a guard equivalent to:

```ts
if (minTTL > 0 && this.getRemainingTTL(k) < minTTL) {
  if (status) {
    status.has = 'ttl'
    this.#statusTTL(status, index)
  }
  return false
}
```

The positive-minimum guard preserves the current zero-minimum expiration boundary and avoids extra clock work for old calls. `getRemainingTTL` already handles immortal entries, the cache's clock, and resolution caching. Reuse it instead of subtracting `Date.now()` from internal starts. After the guard, follow the original successful `has()` path, including optional age refresh and status reporting. A background refresh with an old value follows the same path as an ordinary entry; do not abort or replace its promise.

## Tests added to the public suite

Use `tap` and import `LRUCache` from `../dist/esm/node/index.js`, matching other focused tests. Use the public `perf: { now: () => now }` option, initialize `now` to 100, and set `ttlResolution: 0` for exact assertions. No real-time sleeps are needed. Every scenario below must pass on both implementations.

1. Validate negative, `NaN`, and both infinite minima on present and missing keys; assert `RangeError`. Accept zero, `undefined`, and a fractional minimum. Exercise omitted options as well.
2. With TTL 100, insert at 100 and inspect at 175: minimum 20 is accepted and minimum 30 is rejected. With a fractional minimum use 20.5, never 25. Assert hit/`ttl` status, unrefreshed TTL fields on rejection, unchanged entry count and value, and no callback calls after resetting setup logs. Exercise the rejected branch both with and without a status object.
3. Compound scenario: insert `a`, then `b`, at 100 with TTL 100 and `updateAgeOnHas: true`. At 175 reject `a` with minimum 30, check order stays `[b, a]` and remaining TTL stays 25; then accept minimum 20 and check its TTL becomes 100 while order still stays `[b, a]`. Also cover a per-call false age-refresh override and a per-call true override on a false-default cache.
4. Cover no TTL tracking and an entry with `ttl: 0` in a TTL-tracked cache. Both satisfy a large finite minimum. Cover missing and expired entries, confirming stale entries remain resident, and zero minimum at the existing expiration boundary.
5. With deferred fetches, cover a pending miss without a previous value and a forced refresh with a previous value. Inspect the refresh at remaining TTL 25 using minima 20 and 30, then resolve and await all promises. Confirm checking does not abort the fetch. Cover sufficient lifetime with and without status.

Do not add a public test where a positive minimum exactly equals the entry's remaining TTL. Values on either side execute both outcomes of the new comparison, including its status/no-status paths, so the omitted equality input does not require a coverage exemption. Keep any additional coverage tests away from that equality input. The existing suite covers the original branches; run the full declared checks on both arms without lowering thresholds.

## Twin

Starting from the reference, change only the rejection comparison in the new positive-minimum guard from `getRemainingTTL(k) < minTTL` to `getRemainingTTL(k) <= minTTL`. Do not change the `minTTL > 0` guard, validation, statuses, age update order, tests, or documentation. This is the familiar strict-versus-inclusive mistake when expressing an acceptance boundary as a rejection condition; no comment or name should call attention to it.

The resulting twin rejects a fresh entry with exactly the requested positive lifetime. All other inputs in the public tests and the non-witness oracle rows have unchanged outcomes. Both patches retain exactly the same two changed files.
