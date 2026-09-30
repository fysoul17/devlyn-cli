# J1 hidden oracle

Implement these rows as executable assertions against each implementation's built `dist/esm/node/index.js`. Each row uses a new cache and new callback logs. Unless a row overrides them, use `max: 4`, TTL 100, `ttlResolution: 0`, `ttlAutopurge: false`, and a public clock `perf: { now: () => now }`, with `now = 100` during insertion. Read order through `keys()` and use `peek` rather than `get` when inspecting values. All promises created by a row must be settled and awaited.

Exactly one row is designated as the witness. Every other row must pass on both arms.

## J1-O1 — designated witness

- **Setup:** Insert `a -> A`, then `b -> B`, at 100. Keep age refresh disabled. Set `now = 175` and prepare an empty status object.
- **Action:** Call `has('a', { minTTL: 25, status })`.
- **Expected on reference:** Return `true`; `status.has === 'hit'`; TTL fields are `ttl: 100`, `start: 100`, `now: 175`, `remainingTTL: 25`. Order remains `['b', 'a']`, size remains 2, and `getRemainingTTL('a') === 25`.
- **Twin difference:** Returns false with `status.has === 'ttl'` because it rejects equality. This is the only designated failing row.

Executable body for this row, run from the built repository root (or resolve
the import against that root in the external oracle runner):

```js
import assert from 'node:assert/strict'
import { LRUCache } from './dist/esm/node/index.js'

let now = 100
const c = new LRUCache({
  max: 4,
  ttl: 100,
  ttlResolution: 0,
  ttlAutopurge: false,
  perf: { now: () => now },
})
c.set('a', 'A')
c.set('b', 'B')
now = 175
const status = {}
assert.equal(c.has('a', { minTTL: 25, status }), true)
assert.equal(status.has, 'hit')
assert.equal(status.ttl, 100)
assert.equal(status.start, 100)
assert.equal(status.now, 175)
assert.equal(status.remainingTTL, 25)
assert.deepEqual([...c.keys()], ['b', 'a'])
assert.equal(c.size, 2)
assert.equal(c.getRemainingTTL('a'), 25)
```

## J1-O2 — rejection followed by accepted age refresh

- **Setup:** Insert `a -> A`, then `b -> B`, with `updateAgeOnHas: true`; set `now = 175`. Register disposal and insertion logs and clear them after setup.
- **Action:** Call `has('a', { minTTL: 30, status: rejected })`, inspect remaining TTL and order, then call `has('a', { minTTL: 20, status: accepted })`.
- **Expected on reference:** First call returns false, reports `'ttl'` and remaining TTL 25, and leaves order and TTL unchanged. Second returns true, reports `'hit'`, and refreshes `a` to start 175/remaining TTL 100. Both calls leave order `['b', 'a']`, size 2, and callback logs empty. Both arms pass.

## J1-O3 — zero minimum and existing expiration behavior

- **Setup:** Insert `a -> A` at 100; keep age refresh disabled.
- **Action:** At 200 call `has('a', { minTTL: 0 })`; at 201 call it again with a fresh status object. Also inspect the resident entry with `peek('a', { allowStale: true })`.
- **Expected on reference:** Return true at 200 and false at 201; the latter status is `'stale'`, not `'ttl'`. Value remains `A` and size remains 1. Both arms pass.

## J1-O4 — immortal entries and missing keys

- **Setup:** Create one cache with only `max: 4` and one with TTL tracking. Set `a -> A` in the first and `a -> A` with `ttl: 0` in the second.
- **Action:** On both, call `has('a', { minTTL: 1000000 })` and `has('missing', { minTTL: 1000000, status })` with separate status objects.
- **Expected on reference:** Existing entries return true and have remaining TTL `Infinity`; missing entries return false with status `'miss'`. No entries are inserted or removed. Both arms pass.

## J1-O5 — validation and fractional minima

- **Setup:** Insert `a -> A`; set `now = 175`.
- **Action:** For each of `-1`, `NaN`, `Infinity`, and `-Infinity`, call `has` on both `a` and a missing key. Then call `has('a', { minTTL: 20.5 })`, `has('a', { minTTL: 30.5 })`, and `has('a', { minTTL: undefined })`.
- **Expected on reference:** Each invalid minimum throws `RangeError`; valid calls return true, false, and true respectively. The entry retains remaining TTL 25 and no membership changes occur. Both arms pass.

## J1-O6 — pending miss and pending refresh

- **Setup:** Provide a deferred `fetchMethod` that records its abort signal. First start a fetch of missing `m`; separately insert `a -> A` at 100 and start a forced refresh of `a`. Keep age refresh disabled; set the clock to 175.
- **Action:** Check `m` with minimum 20, and check `a` with minima 20 and 30. Inspect signals, then resolve both fetches to ordinary values and await their returned promises.
- **Expected on reference:** The pending miss returns false. The refresh returns true for 20 and false for 30 while retaining `A` as its previous value. Neither check aborts a fetch. Both fetches settle normally and cache their results. Both arms pass.

## J1-O7 — age-refresh override and size preservation

- **Setup:** Use `maxSize: 20`, TTL 100, and `updateAgeOnHas: true`; insert `a -> A` with size 3 and `b -> B` with size 4. Advance to 175.
- **Action:** Call `has('a', { minTTL: 20, updateAgeOnHas: false })`; then on an otherwise identical false-default cache call it with `updateAgeOnHas: true`.
- **Expected on reference:** Both calls return true; the first keeps remaining TTL 25 and the second refreshes it to 100. Both retain size 2, calculated size 7, and order `['b', 'a']`. Both arms pass.
