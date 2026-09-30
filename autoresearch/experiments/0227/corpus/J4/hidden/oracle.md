# J4 hidden oracle

Run each row with a fresh cache against the built implementation. The code blocks are independent ESM bodies using this preamble:

```js
import assert from 'node:assert/strict'
import { LRUCache } from './dist/esm/node/index.js'
```

Use strict identity assertions for values. `keys()` is MRU-first; `dump()` is LRU-first. Exactly `J4-H6` is the designated witness; all other rows must pass both reference and twin.

## J4-H1 — constructor remeasurement and shrinking

Setup: `maxSize: 100`, constructor calculator reading `bytes`, two distinct objects initially sized 3 and 4. Action: mutate the first object to size 9 and set the same object, then shrink it to 2 and set again. Expected: size reports and status agree, the first object is MRU, identity is retained, and deletion subtracts the new size.

```js
const a = { bytes: 3 }
const b = { bytes: 4 }
const c = new LRUCache({ maxSize: 100, sizeCalculation: v => v.bytes })
c.set('a', a)
c.set('b', b)
a.bytes = 9
const grown = {}
assert.equal(c.set('a', a, { status: grown }), c)
assert.equal(c.peek('a'), a)
assert.equal(c.info('a').size, 9)
assert.deepEqual(c.dump().map(([k, e]) => [k, e.size]), [['b', 4], ['a', 9]])
assert.deepEqual([...c.keys()], ['a', 'b'])
assert.equal(c.calculatedSize, 13)
assert.equal(grown.set, 'update')
assert.equal(grown.entrySize, 9)
assert.equal(grown.totalCalculatedSize, 13)
a.bytes = 2
const shrunk = {}
c.set('a', a, { status: shrunk })
assert.equal(c.info('a').size, 2)
assert.equal(c.calculatedSize, 6)
assert.equal(shrunk.entrySize, 2)
assert.equal(shrunk.totalCalculatedSize, 6)
assert.equal(c.dump().reduce((sum, [, e]) => sum + e.size, 0), 6)
c.delete('a')
assert.equal(c.calculatedSize, 4)
```

## J4-H2 — size source precedence and equal primitive values

Setup: a size-limited cache with counted constructor and per-call calculators. Action: remeasure the same primitive first using a per-call calculator, then a valid explicit size. Expected: precedence is unchanged, calculators are not called for the explicit size, and all size reports track the accepted sizes.

```js
let defaults = 0
let overrides = 0
const c = new LRUCache({ maxSize: 50, sizeCalculation: () => { defaults++; return 3 } })
c.set('a', 'same')
assert.equal(defaults, 1)
c.set('a', 'same', { sizeCalculation: () => { overrides++; return 7 } })
assert.equal(defaults, 1)
assert.equal(overrides, 1)
assert.equal(c.info('a').size, 7)
const status = {}
c.set('a', 'same', {
  size: 5,
  sizeCalculation: () => { overrides++; return 9 },
  status,
})
assert.equal(defaults, 1)
assert.equal(overrides, 1)
assert.equal(c.calculatedSize, 5)
assert.equal(c.dump()[0][1].size, 5)
assert.equal(status.entrySize, 5)
assert.equal(status.totalCalculatedSize, 5)
assert.equal(status.set, 'update')
```

## J4-H3 — TTL and update callbacks remain consistent

Setup: controlled clock at 100, `ttlResolution: 0`, two entries, and all three callbacks recorded. Action: grow the first identical value while refreshing its TTL, then shrink it with `noUpdateTTL: true`. Expected: both operations are updates with no replacement disposal; TTL normally refreshes but the second call preserves the prior TTL/start.

```js
let now = 100
const inserted = []
const disposed = []
const after = []
const a = {}
const b = {}
const c = new LRUCache({
  maxSize: 100, ttl: 20, ttlResolution: 0, perf: { now: () => now },
  onInsert: (v, k, r) => inserted.push([v, k, r]),
  dispose: (v, k, r) => disposed.push([v, k, r]),
  disposeAfter: (v, k, r) => after.push([v, k, r]),
})
c.set('a', a, { size: 3 })
c.set('b', b, { size: 4 })
inserted.length = 0
now = 105
const grown = {}
c.set('a', a, { size: 8, ttl: 30, status: grown })
assert.equal(c.getRemainingTTL('a'), 30)
assert.equal(grown.ttl, 30)
assert.equal(grown.start, 105)
assert.equal(grown.entrySize, 8)
assert.equal(grown.totalCalculatedSize, 12)
now = 110
const shrunk = {}
c.set('a', a, { size: 2, ttl: 99, noUpdateTTL: true, status: shrunk })
assert.equal(c.getRemainingTTL('a'), 25)
assert.equal(shrunk.ttl, 30)
assert.equal(shrunk.start, 105)
assert.equal(shrunk.entrySize, 2)
assert.equal(shrunk.totalCalculatedSize, 6)
assert.deepEqual([...c.keys()], ['a', 'b'])
assert.equal(c.peek('a'), a)
assert.deepEqual(inserted, [[a, 'a', 'update'], [a, 'a', 'update']])
assert.equal(inserted[0][0], a)
assert.equal(inserted[1][0], a)
assert.deepEqual(disposed, [])
assert.deepEqual(after, [])
```

## J4-H4 — unchanged sizes and tracking without total limit

Setup: a `max`/`maxEntrySize` cache without a total size limit, plus a plain `max` cache. Action: set the same object at the same tracked size, then grow it; repeat a same-value set in the plain cache. Expected: unchanged-size status does not acquire size fields, changed-size accounting works without `maxSize`, and plain-cache behavior remains unchanged.

```js
const a = {}
const c = new LRUCache({ max: 3, maxEntrySize: 20 })
c.set('a', a, { size: 3 })
c.set('b', {}, { size: 4 })
const unchanged = {}
c.set('a', a, { size: 3, status: unchanged })
assert.equal(unchanged.set, 'update')
assert.equal(Object.hasOwn(unchanged, 'entrySize'), false)
assert.equal(Object.hasOwn(unchanged, 'totalCalculatedSize'), false)
assert.deepEqual([...c.keys()], ['a', 'b'])
c.set('a', a, { size: 10 })
assert.equal(c.info('a').size, 10)
assert.equal(c.calculatedSize, 14)
const plain = new LRUCache({ max: 2 })
plain.set('a', a)
plain.set('b', {})
const status = {}
plain.set('a', a, { status })
assert.equal(status.set, 'update')
assert.equal(plain.calculatedSize, 0)
assert.deepEqual([...plain.keys()], ['a', 'b'])
assert.deepEqual(plain.info('a'), { value: a })
```

## J4-H5 — validation, entry limit, and exact total limit

Setup: `maxSize: 10`, `maxEntrySize: 6`, entries of size 3 and 4. Action: attempt a same-value calculation returning -1; accept size 6, making the total exactly 10; then attempt size 7. Expected: invalid calculation throws before recency/accounting changes, exact total is accepted without eviction, and the oversized update follows existing deletion behavior.

```js
const a = {}
const b = {}
const c = new LRUCache({ maxSize: 10, maxEntrySize: 6 })
c.set('a', a, { size: 3 })
c.set('b', b, { size: 4 })
assert.throws(() => c.set('a', a, { sizeCalculation: () => -1 }), TypeError)
assert.equal(c.peek('a'), a)
assert.equal(c.info('a').size, 3)
assert.equal(c.calculatedSize, 7)
assert.deepEqual([...c.keys()], ['b', 'a'])
c.set('a', a, { size: 6 })
assert.equal(c.calculatedSize, 10)
assert.equal(c.size, 2)
assert.deepEqual([...c.keys()], ['a', 'b'])
const oversized = {}
c.set('a', a, { size: 7, status: oversized })
assert.equal(oversized.set, 'miss')
assert.equal(oversized.maxEntrySizeExceeded, true)
assert.equal(c.has('a'), false)
assert.equal(c.peek('b'), b)
assert.equal(c.calculatedSize, 4)
```

## J4-H6 — designated witness: same-value growth enforces total size

Setup: `maxSize: 10`, with `a`, `b`, and `c` inserted in that order at size 3 each; all values are distinct objects. Action: set the same object at `a` with size 8. Expected: `a` becomes MRU and stays stored; `b` then `c` are evicted; final count is 1 and total is 8. Size status and update callbacks must describe the surviving entry, and both disposal callbacks must receive eviction notifications for `b` and `c` only.

```js
const a = {}
const b = {}
const cValue = {}
const inserted = []
const disposed = []
const after = []
const c = new LRUCache({
  maxSize: 10,
  onInsert: (v, k, r) => inserted.push([v, k, r]),
  dispose: (v, k, r) => disposed.push([v, k, r]),
  disposeAfter: (v, k, r) => after.push([v, k, r]),
})
c.set('a', a, { size: 3 })
c.set('b', b, { size: 3 })
c.set('c', cValue, { size: 3 })
inserted.length = 0
const status = {}
c.set('a', a, { size: 8, status })
assert.deepEqual([...c.keys()], ['a'])
assert.equal(c.size, 1)
assert.equal(c.calculatedSize, 8)
assert.equal(c.peek('a'), a)
assert.deepEqual(c.dump(), [['a', { value: a, size: 8 }]])
assert.equal(c.info('a').size, 8)
assert.equal(status.set, 'update')
assert.equal(status.entrySize, 8)
assert.equal(status.totalCalculatedSize, 8)
assert.deepEqual(inserted, [[a, 'a', 'update']])
assert.deepEqual(disposed, [[b, 'b', 'evict'], [cValue, 'c', 'evict']])
assert.deepEqual(after, [[b, 'b', 'evict'], [cValue, 'c', 'evict']])
```

The twin retains all three entries, ordered `a`, `c`, `b`, with `calculatedSize` and `status.totalCalculatedSize` equal to 14 and no eviction notifications. That is one capacity-enforcement mechanism failure with several observable consequences, all confined to this designated row.
