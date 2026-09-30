# J2 hidden oracle specification

Designated witness: **J2-W1**. It is the only row that must fail on the defective twin. Run every row in a fresh cache and report each row independently. Multiple assertions in J2-W1 are observations of one precedence defect, not separate oracle rows.

Use the built `LRUCache` export from `dist/esm/node/index.js`. All time values below use the existing constructor option `perf: { now: () => now }`, initially `now = 100`, with `ttlResolution: 0`, `ttlAutopurge: false`, and max 5. Entries shown as `key/value/TTL` are inserted in the listed order at time 100 unless specified otherwise. Use ordinary string values and no fetch method except in the fetch row. Advance by assigning `now = 120`, not by sleeping. Expiry is unambiguous: TTL 10 is expired and TTL 100 is fresh.

Record all predicate key/value pairs and cache identity. Observe full stored MRU order by read-only `unsafeExposeInternals(c).indexes({ allowStale: true })` mapped to `keyList`; ordinary iterators may filter stale entries. Observe membership with the exposed key map or `peek(key, { allowStale: true })` plus size. Do not use `get()` for postconditions, since it changes the state being measured.

| id | setup | action | expected |
| --- | --- | --- | --- |
| J2-W1 | Cache default `allowStale: true`, default `noDeleteOnStaleGet: false`. Insert `fresh/F/100`, then `stale/S/10`; advance to 120. Both values would satisfy the predicate. | Call `find(recordAndReturnTrue, { allowStale: false })`, then inspect stored order, membership, size, and remaining TTL. | Return `F`; predicate calls exactly `[["fresh", "F"]]` with the correct cache; size 2; full stored order `fresh, stale`; stale value still `S`; remaining TTLs fresh 80 and stale -10. Reference passes. Twin returns undefined, calls only `stale`, deletes it, and leaves size 1, so this row fails. |
| J2-H2 | Cache default false, insert `fresh/F/100`, then `stale/S/10`; advance to 120. | Call `find(recordAndReturnTrue, { allowStale: true })`. | Return `S`; calls only `stale/S`; stale entry removed; size 1 and stored order `fresh`; fresh TTL stays 80. Both arms pass. |
| J2-H3 | Four independent caches for the Cartesian product of default false/true and options omitted/explicit `{ allowStale: undefined }`. Set cache `noDeleteOnStaleGet: true`. Each contains `fresh/F/100`, then `stale/S/10`, and advances to 120. | Call `find(recordAndReturnTrue)` or `find(recordAndReturnTrue, { allowStale: undefined })` as selected. | False default: return `F`, call only `fresh/F`, order `fresh, stale`. True default: return `S`, call only `stale/S`, order `stale, fresh`. Every cache retains both entries and TTLs 80/-10. Both arms pass all subcases. |
| J2-H4 | Cache default false. Insert `old-stale/O/10`, `fresh/F/100`, then `new-stale/N/10`; advance to 120. | First `find` with true and `noDeleteOnStaleGet: true`, matching only `old-stale`; then `find` with true and `updateAgeOnGet: true`, matching only `fresh`. | First result `O`, calls `new-stale, fresh, old-stale`, size 3, stored order unchanged, TTLs -10/80/-10 by insertion order. Second result `F`, calls `new-stale, fresh`, size 3, order `fresh, new-stale, old-stale`, fresh TTL 100, both stale TTLs -10. Both arms pass. |
| J2-H5 | Cache default false; insert `older/A/100`, `stale/S/10`, `newer/B/100`; advance to 120. Snapshot full order and TTLs. | Call `find(recordAndReturnFalse, { allowStale: false, updateAgeOnGet: true })`. | Return undefined; calls exactly `newer/B, older/A`; all three entries retained in order `newer, stale, older`; TTLs unchanged at 80/-10/80 by insertion order. No callback for stale. Both arms pass. |
| J2-H6 | Cache default true; insert only fresh `older/A/100`, then `newer/B/100`; advance to 120. | Call `find` matching `older` with `{ allowStale: false, updateAgeOnGet: false }`. | Return `A`; calls `newer/B, older/A`; stored order `older, newer`; size 2 and both TTLs 80. Both arms pass because both entries are fresh. |
| J2-H7 | Cache default false with an unresolved fetch method and a recorded resolver. Insert `ready/R/100`, start `fetch("pending")` without an existing value, and retain its promise. Keep time at 100. | Call `find(recordAndReturnTrue, { allowStale: true })`; then resolve the pending fetch to `P` and await the saved promise for cleanup. | Search returns `R`; predicate sees only `ready/R`, never a promise or undefined placeholder. Resolving cleanup succeeds and does not alter the recorded search result. Both arms pass. |

Each row also checks the cache identity in every predicate call. No row other than J2-W1 may introduce the conjunction of a true cache default, explicit false per-call policy, and stale candidate entries. J2-H6 deliberately has only fresh entries.

## Executable witness skeleton

The implementer may use Node's built-in strict assertions in an external oracle file. This skeleton is a specification of the single row, not a repository patch:

```js
import assert from 'node:assert/strict'
import { LRUCache } from './dist/esm/node/index.js'

let now = 100
const c = new LRUCache({
  max: 5,
  allowStale: true,
  ttlResolution: 0,
  ttlAutopurge: false,
  perf: { now: () => now },
})
c.set('fresh', 'F', { ttl: 100 })
c.set('stale', 'S', { ttl: 10 })
now = 120
const calls = []
const result = c.find((value, key, self) => {
  assert.equal(self, c)
  calls.push([key, value])
  return true
}, { allowStale: false })
const e = LRUCache.unsafeExposeInternals(c)
const actual = {
  result,
  calls,
  size: c.size,
  order: [...e.indexes({ allowStale: true })].map(i => e.keyList[i]),
  stale: c.peek('stale', { allowStale: true }),
  freshTTL: c.getRemainingTTL('fresh'),
  staleTTL: c.getRemainingTTL('stale'),
}
assert.deepEqual(actual, {
  result: 'F',
  calls: [['fresh', 'F']],
  size: 2,
  order: ['fresh', 'stale'],
  stale: 'S',
  freshTTL: 80,
  staleTTL: -10,
})
```

If the oracle lives outside the repository, resolve its import against the tested checkout rather than the oracle file's own directory. A suitable runner executes each row with the same Node PATH assignment declared by the public commands, after the arm's normal build. Hidden execution is calibration material and must not be added to `spec.expected.json`.
