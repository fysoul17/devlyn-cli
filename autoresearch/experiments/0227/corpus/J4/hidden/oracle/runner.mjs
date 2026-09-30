import assert from 'node:assert/strict'

import { LRUCache } from './dist/esm/node/index.js'



const rows = {}

try {
  await (async () => {
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
  })()
  rows['J4-H1'] = true
} catch (error) {
  rows['J4-H1'] = false
  console.error('J4-H1:', error)
}

try {
  await (async () => {
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
  })()
  rows['J4-H2'] = true
} catch (error) {
  rows['J4-H2'] = false
  console.error('J4-H2:', error)
}

try {
  await (async () => {
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
  })()
  rows['J4-H3'] = true
} catch (error) {
  rows['J4-H3'] = false
  console.error('J4-H3:', error)
}

try {
  await (async () => {
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
  })()
  rows['J4-H4'] = true
} catch (error) {
  rows['J4-H4'] = false
  console.error('J4-H4:', error)
}

try {
  await (async () => {
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
  })()
  rows['J4-H5'] = true
} catch (error) {
  rows['J4-H5'] = false
  console.error('J4-H5:', error)
}

try {
  await (async () => {
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
  })()
  rows['J4-H6'] = true
} catch (error) {
  rows['J4-H6'] = false
  console.error('J4-H6:', error)
}

process.stdout.write(JSON.stringify({ rows }) + '\n')
