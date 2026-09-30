#!/bin/sh
# 0227 check (J3): if memoMethod throws, memo() rethrows it without changing membership, recency, TTL starts/durations, sizes, calculatedSize, or firing dispose/disposeAfter/onInsert. Exit 0 = clause holds.
set -eu
cd "$1"
npm run prepare >/dev/null 2>&1
exec node --input-type=module <<'JS'
import assert from 'node:assert/strict'
import { LRUCache } from './dist/esm/node/index.js'

const sentinel = { failed: true }
const make = updateAgeOnGet => {
  const clock = { now: 100 }
  const hooks = []
  const calls = []
  const cache = new LRUCache({
    max: 2,
    maxSize: 20,
    sizeCalculation: value => value.length,
    ttl: 100,
    ttlResolution: 0,
    ttlAutopurge: false,
    updateAgeOnGet,
    perf: { now: () => clock.now },
    dispose: (v, k, r) => hooks.push(['dispose', v, k, r]),
    disposeAfter: (v, k, r) => hooks.push(['disposeAfter', v, k, r]),
    onInsert: (v, k, r) => hooks.push(['onInsert', v, k, r]),
    memoMethod: (key, oldValue) => {
      calls.push([key, oldValue])
      throw sentinel
    },
  })
  return { cache, hooks, calls, clock }
}
const snapshot = cache => {
  const internal = LRUCache.unsafeExposeInternals(cache)
  const order = [...internal.indexes({ allowStale: true })].map(i => [
    internal.keyList[i],
    internal.valList[i],
    internal.starts[i],
    internal.ttls[i],
    internal.sizes[i],
  ])
  return { order, size: cache.size, calculatedSize: cache.calculatedSize }
}
const failed = (cache, key, options) => {
  let caught
  try {
    cache.memo(key, options)
  } catch (error) {
    caught = error
  }
  return caught
}

// Fresh least-recent entry, forced refresh, age refresh on and off.
for (const updateAgeOnGet of [true, false]) {
  const { cache, hooks, calls, clock } = make(updateAgeOnGet)
  cache.set('a', 'AA')
  cache.set('b', 'BBB')
  hooks.length = 0
  clock.now = 125
  const before = snapshot(cache)
  assert.equal(failed(cache, 'a', { forceRefresh: true }), sentinel)
  assert.deepEqual(calls, [['a', 'AA']])
  assert.deepEqual(snapshot(cache), before, `fresh forced, updateAgeOnGet=${updateAgeOnGet}`)
  assert.deepEqual(hooks, [], `fresh forced hooks, updateAgeOnGet=${updateAgeOnGet}`)
  // A later insertion must still evict the least-recent entry 'a'.
  cache.set('c', 'C')
  assert.deepEqual([...cache.keys()], ['c', 'b'], `eviction, updateAgeOnGet=${updateAgeOnGet}`)
}

// Stale entry with default allowStale/noDeleteOnStaleGet: a miss whose calculation throws.
{
  const { cache, hooks, clock } = make(false)
  cache.set('a', 'AA')
  clock.now = 150
  cache.set('b', 'BBB')
  hooks.length = 0
  clock.now = 210
  const before = snapshot(cache)
  assert.equal(failed(cache, 'a', {}), sentinel)
  assert.deepEqual(snapshot(cache), before, 'stale miss state')
  assert.deepEqual(hooks, [], 'stale miss hooks')
}
JS
