#!/bin/sh
# J4 Requirement 3 ("Each evicted entry must receive the existing eviction disposal behavior"): under noDisposeOnSet, same-value growth gives the evicted entry the same dispose/disposeAfter delivery as the unchanged different-value eviction path.
set -eu
cd "$1"
npm run prepare >/dev/null 2>&1
node --input-type=module <<'JS'
import assert from 'node:assert/strict'
import { LRUCache } from './dist/esm/node/index.js'

const run = sameValue => {
  const a = {}
  const b = {}
  const disposed = []
  const after = []
  const c = new LRUCache({
    maxSize: 10,
    dispose: (v, k, r) => disposed.push([k, r, v === b]),
    disposeAfter: (v, k, r) => after.push([k, r, v === b]),
  })
  c.set('a', a, { size: 3 })
  c.set('b', b, { size: 4 })
  c.set('a', sameValue ? a : {}, { size: 7, noDisposeOnSet: true })
  const immediate = { disposed: [...disposed], after: [...after] }
  c.set('z', {}, { size: 1 })
  return { immediate, later: { disposed, after } }
}
const existing = run(false)
assert.deepEqual(existing.immediate.disposed, [['b', 'evict', true]])
assert.deepEqual(run(true), existing)
JS
