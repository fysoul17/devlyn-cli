import assert from 'node:assert/strict'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

const modulePath = resolve(process.env.ORACLE_TREE, 'dist/esm/node/index.js')
const { LRUCache } = await import(pathToFileURL(modulePath).href)

const cacheWithClock = (clock, options = {}) =>
  new LRUCache({
    max: 4,
    ttl: 100,
    ttlResolution: 0,
    ttlAutopurge: false,
    perf: { now: () => clock.now },
    ...options,
  })

const cases = {
  'J1-O1': () => {
    const clock = { now: 100 }
    const c = cacheWithClock(clock)
    c.set('a', 'A')
    c.set('b', 'B')
    clock.now = 175
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
  },

  'J1-O2': () => {
    const clock = { now: 100 }
    const inserted = []
    const disposed = []
    const c = cacheWithClock(clock, {
      updateAgeOnHas: true,
      onInsert: (...args) => inserted.push(args),
      dispose: (...args) => disposed.push(args),
    })
    c.set('a', 'A')
    c.set('b', 'B')
    inserted.length = 0
    clock.now = 175
    const rejected = {}
    assert.equal(c.has('a', { minTTL: 30, status: rejected }), false)
    assert.equal(rejected.has, 'ttl')
    assert.equal(rejected.ttl, 100)
    assert.equal(rejected.start, 100)
    assert.equal(rejected.now, 175)
    assert.equal(rejected.remainingTTL, 25)
    assert.equal(c.getRemainingTTL('a'), 25)
    assert.deepEqual([...c.keys()], ['b', 'a'])
    const accepted = {}
    assert.equal(c.has('a', { minTTL: 20, status: accepted }), true)
    assert.equal(accepted.has, 'hit')
    assert.equal(accepted.ttl, 100)
    assert.equal(accepted.start, 175)
    assert.equal(accepted.now, 175)
    assert.equal(accepted.remainingTTL, 100)
    assert.equal(c.getRemainingTTL('a'), 100)
    assert.deepEqual([...c.keys()], ['b', 'a'])
    assert.equal(c.size, 2)
    assert.deepEqual(inserted, [])
    assert.deepEqual(disposed, [])
  },

  'J1-O3': () => {
    const clock = { now: 100 }
    const c = cacheWithClock(clock)
    c.set('a', 'A')
    clock.now = 200
    assert.equal(c.has('a', { minTTL: 0 }), true)
    clock.now = 201
    const status = {}
    assert.equal(c.has('a', { minTTL: 0, status }), false)
    assert.equal(status.has, 'stale')
    assert.equal(c.peek('a', { allowStale: true }), 'A')
    assert.equal(c.size, 1)
  },

  'J1-O4': () => {
    const clock = { now: 100 }
    const untracked = new LRUCache({ max: 4 })
    const tracked = cacheWithClock(clock)
    untracked.set('a', 'A')
    tracked.set('a', 'A', { ttl: 0 })
    for (const c of [untracked, tracked]) {
      assert.equal(c.has('a', { minTTL: 1000000 }), true)
      assert.equal(c.getRemainingTTL('a'), Infinity)
      const status = {}
      assert.equal(
        c.has('missing', { minTTL: 1000000, status }),
        false,
      )
      assert.equal(status.has, 'miss')
      assert.equal(c.size, 1)
      assert.equal(c.peek('a'), 'A')
    }
  },

  'J1-O5': () => {
    const clock = { now: 100 }
    const c = cacheWithClock(clock)
    c.set('a', 'A')
    clock.now = 175
    for (const minTTL of [-1, NaN, Infinity, -Infinity]) {
      for (const key of ['a', 'missing']) {
        assert.throws(() => c.has(key, { minTTL }), RangeError)
      }
    }
    assert.equal(c.has('a', { minTTL: 20.5 }), true)
    assert.equal(c.has('a', { minTTL: 30.5 }), false)
    assert.equal(c.has('a', { minTTL: undefined }), true)
    assert.equal(c.getRemainingTTL('a'), 25)
    assert.equal(c.size, 1)
    assert.equal(c.peek('a'), 'A')
  },

  'J1-O6': async () => {
    const clock = { now: 100 }
    const resolvers = new Map()
    const signals = new Map()
    const c = cacheWithClock(clock, {
      fetchMethod: (key, _oldValue, { signal }) => {
        signals.set(key, signal)
        return new Promise(resolve => resolvers.set(key, resolve))
      },
    })
    const missing = c.fetch('m')
    c.set('a', 'A')
    const refresh = c.fetch('a', { forceRefresh: true })
    clock.now = 175
    try {
      assert.equal(c.has('m', { minTTL: 20 }), false)
      assert.equal(c.has('a', { minTTL: 20 }), true)
      assert.equal(c.has('a', { minTTL: 30 }), false)
      assert.equal(c.peek('a'), 'A')
      assert.equal(c.getRemainingTTL('a'), 25)
      assert.equal(signals.get('m')?.aborted, false)
      assert.equal(signals.get('a')?.aborted, false)
    } finally {
      resolvers.get('m')?.('M')
      resolvers.get('a')?.('new A')
      const settled = await Promise.allSettled([missing, refresh])
      assert.deepEqual(settled, [
        { status: 'fulfilled', value: 'M' },
        { status: 'fulfilled', value: 'new A' },
      ])
      assert.equal(c.peek('m'), 'M')
      assert.equal(c.peek('a'), 'new A')
    }
  },

  'J1-O7': () => {
    const clock = { now: 100 }
    const make = updateAgeOnHas => {
      const c = cacheWithClock(clock, {
        maxSize: 20,
        updateAgeOnHas,
      })
      c.set('a', 'A', { size: 3 })
      c.set('b', 'B', { size: 4 })
      return c
    }
    const enabled = make(true)
    const disabled = make(false)
    clock.now = 175
    assert.equal(
      enabled.has('a', { minTTL: 20, updateAgeOnHas: false }),
      true,
    )
    assert.equal(enabled.getRemainingTTL('a'), 25)
    assert.equal(
      disabled.has('a', { minTTL: 20, updateAgeOnHas: true }),
      true,
    )
    assert.equal(disabled.getRemainingTTL('a'), 100)
    for (const c of [enabled, disabled]) {
      assert.equal(c.size, 2)
      assert.equal(c.calculatedSize, 7)
      assert.deepEqual([...c.keys()], ['b', 'a'])
    }
  },
}

const rows = {}
for (const [id, run] of Object.entries(cases)) {
  try {
    await run()
    rows[id] = true
  } catch (error) {
    rows[id] = false
  }
}
process.stdout.write(`${JSON.stringify({ rows })}\n`)
