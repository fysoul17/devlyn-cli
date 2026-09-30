#!/bin/sh
# J4 Requirement 3: a same-value growth whose total exceeds a nonzero maxSize evicts LRU entries (with eviction disposal), keeps the updated entry MRU, and reports the fitting total.
set -eu
cd "$1"
npm run prepare >/dev/null 2>&1
node --input-type=module <<'JS'
import assert from 'node:assert/strict'
import { LRUCache } from './dist/esm/node/index.js'

const a = {}
const b = {}
const disposed = []
const after = []
const c = new LRUCache({
  maxSize: 10,
  dispose: (v, k, r) => disposed.push([v, k, r]),
  disposeAfter: (v, k, r) => after.push([v, k, r]),
})
c.set('a', a, { size: 3 })
c.set('b', b, { size: 4 })
const status = {}
c.set('a', a, { size: 8, status })
assert.equal(c.peek('a'), a)
assert.deepEqual([...c.keys()], ['a'])
assert.equal(c.has('b'), false)
assert.equal(c.calculatedSize, 8)
assert.equal(status.totalCalculatedSize, 8)
assert.deepEqual(disposed, [[b, 'b', 'evict']])
assert.deepEqual(after, [[b, 'b', 'evict']])
JS
