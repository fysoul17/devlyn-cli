import assert from 'node:assert/strict'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

const moduleURL = pathToFileURL(
  resolve(process.argv[2], 'dist/esm/node/index.js'),
).href
const { LRUCache } = await import(moduleURL)

const makeCache = (allowStale = false, extra = {}) => {
  let now = 100
  const c = new LRUCache({
    max: 5,
    allowStale,
    ttlResolution: 0,
    ttlAutopurge: false,
    perf: { now: () => now },
    ...extra,
  })
  return { c, advance: () => (now = 120) }
}

const order = c => {
  const e = LRUCache.unsafeExposeInternals(c)
  return [...e.indexes({ allowStale: true })].map(i => e.keyList[i])
}

const record = (c, calls, accept) => (value, key, self) => {
  assert.equal(self, c)
  calls.push([key, value])
  return accept(key)
}

const rows = {
  'J2-W1': () => {
    const { c, advance } = makeCache(true)
    c.set('fresh', 'F', { ttl: 100 })
    c.set('stale', 'S', { ttl: 10 })
    advance()
    const calls = []
    const result = c.find(record(c, calls, () => true), {
      allowStale: false,
    })
    const e = LRUCache.unsafeExposeInternals(c)
    assert.deepEqual(
      {
        result,
        calls,
        size: c.size,
        order: order(c),
        freshStored: e.keyMap.has('fresh'),
        staleStored: e.keyMap.has('stale'),
        stale: c.peek('stale', { allowStale: true }),
        freshTTL: c.getRemainingTTL('fresh'),
        staleTTL: c.getRemainingTTL('stale'),
      },
      {
        result: 'F',
        calls: [['fresh', 'F']],
        size: 2,
        order: ['fresh', 'stale'],
        freshStored: true,
        staleStored: true,
        stale: 'S',
        freshTTL: 80,
        staleTTL: -10,
      },
    )
  },

  'J2-H2': () => {
    const { c, advance } = makeCache()
    c.set('fresh', 'F', { ttl: 100 })
    c.set('stale', 'S', { ttl: 10 })
    advance()
    const calls = []
    const result = c.find(record(c, calls, () => true), {
      allowStale: true,
    })
    const e = LRUCache.unsafeExposeInternals(c)
    assert.deepEqual(
      {
        result,
        calls,
        size: c.size,
        order: order(c),
        staleStored: e.keyMap.has('stale'),
        freshTTL: c.getRemainingTTL('fresh'),
      },
      {
        result: 'S',
        calls: [['stale', 'S']],
        size: 1,
        order: ['fresh'],
        staleStored: false,
        freshTTL: 80,
      },
    )
  },

  'J2-H3': () => {
    for (const allowStale of [false, true]) {
      for (const explicitUndefined of [false, true]) {
        const { c, advance } = makeCache(allowStale, {
          noDeleteOnStaleGet: true,
        })
        c.set('fresh', 'F', { ttl: 100 })
        c.set('stale', 'S', { ttl: 10 })
        advance()
        const calls = []
        const fn = record(c, calls, () => true)
        const result = explicitUndefined ?
          c.find(fn, { allowStale: undefined })
        : c.find(fn)
        const e = LRUCache.unsafeExposeInternals(c)
        assert.deepEqual(
          {
            result,
            calls,
            order: order(c),
            size: c.size,
            freshStored: e.keyMap.has('fresh'),
            staleStored: e.keyMap.has('stale'),
            freshTTL: c.getRemainingTTL('fresh'),
            staleTTL: c.getRemainingTTL('stale'),
          },
          {
            result: allowStale ? 'S' : 'F',
            calls: allowStale ? [['stale', 'S']] : [['fresh', 'F']],
            order: allowStale ? ['stale', 'fresh'] : ['fresh', 'stale'],
            size: 2,
            freshStored: true,
            staleStored: true,
            freshTTL: 80,
            staleTTL: -10,
          },
        )
      }
    }
  },

  'J2-H4': () => {
    const { c, advance } = makeCache()
    c.set('old-stale', 'O', { ttl: 10 })
    c.set('fresh', 'F', { ttl: 100 })
    c.set('new-stale', 'N', { ttl: 10 })
    advance()

    const firstCalls = []
    const first = c.find(
      record(c, firstCalls, key => key === 'old-stale'),
      { allowStale: true, noDeleteOnStaleGet: true },
    )
    const e = LRUCache.unsafeExposeInternals(c)
    assert.deepEqual(
      {
        first,
        calls: firstCalls,
        size: c.size,
        order: order(c),
        stored: ['old-stale', 'fresh', 'new-stale'].map(k => e.keyMap.has(k)),
        ttls: ['old-stale', 'fresh', 'new-stale'].map(k => c.getRemainingTTL(k)),
      },
      {
        first: 'O',
        calls: [['new-stale', 'N'], ['fresh', 'F'], ['old-stale', 'O']],
        size: 3,
        order: ['new-stale', 'fresh', 'old-stale'],
        stored: [true, true, true],
        ttls: [-10, 80, -10],
      },
    )

    const secondCalls = []
    const second = c.find(
      record(c, secondCalls, key => key === 'fresh'),
      { allowStale: true, updateAgeOnGet: true },
    )
    assert.deepEqual(
      {
        second,
        calls: secondCalls,
        size: c.size,
        order: order(c),
        stored: ['old-stale', 'fresh', 'new-stale'].map(k => e.keyMap.has(k)),
        ttls: ['old-stale', 'fresh', 'new-stale'].map(k => c.getRemainingTTL(k)),
      },
      {
        second: 'F',
        calls: [['new-stale', 'N'], ['fresh', 'F']],
        size: 3,
        order: ['fresh', 'new-stale', 'old-stale'],
        stored: [true, true, true],
        ttls: [-10, 100, -10],
      },
    )
  },

  'J2-H5': () => {
    const { c, advance } = makeCache()
    c.set('older', 'A', { ttl: 100 })
    c.set('stale', 'S', { ttl: 10 })
    c.set('newer', 'B', { ttl: 100 })
    advance()
    const keys = ['older', 'stale', 'newer']
    const e = LRUCache.unsafeExposeInternals(c)
    const before = {
      size: c.size,
      order: order(c),
      stored: keys.map(k => e.keyMap.has(k)),
      ttls: keys.map(k => c.getRemainingTTL(k)),
    }
    const calls = []
    const result = c.find(record(c, calls, () => false), {
      allowStale: false,
      updateAgeOnGet: true,
    })
    assert.equal(result, undefined)
    assert.deepEqual(calls, [['newer', 'B'], ['older', 'A']])
    assert.deepEqual(before, {
      size: 3,
      order: ['newer', 'stale', 'older'],
      stored: [true, true, true],
      ttls: [80, -10, 80],
    })
    assert.deepEqual(
      {
        size: c.size,
        order: order(c),
        stored: keys.map(k => e.keyMap.has(k)),
        ttls: keys.map(k => c.getRemainingTTL(k)),
      },
      before,
    )
  },

  'J2-H6': () => {
    const { c, advance } = makeCache(true)
    c.set('older', 'A', { ttl: 100 })
    c.set('newer', 'B', { ttl: 100 })
    advance()
    const calls = []
    const result = c.find(
      record(c, calls, key => key === 'older'),
      { allowStale: false, updateAgeOnGet: false },
    )
    assert.deepEqual(
      {
        result,
        calls,
        order: order(c),
        size: c.size,
        olderTTL: c.getRemainingTTL('older'),
        newerTTL: c.getRemainingTTL('newer'),
      },
      {
        result: 'A',
        calls: [['newer', 'B'], ['older', 'A']],
        order: ['older', 'newer'],
        size: 2,
        olderTTL: 80,
        newerTTL: 80,
      },
    )
  },

  'J2-H7': async () => {
    let resolveFetch
    const { c } = makeCache(false, {
      fetchMethod: () =>
        new Promise(resolve => {
          resolveFetch = resolve
        }),
    })
    c.set('ready', 'R', { ttl: 100 })
    const pending = c.fetch('pending')
    const calls = []
    const result = c.find(record(c, calls, () => true), {
      allowStale: true,
    })
    assert.equal(result, 'R')
    assert.deepEqual(calls, [['ready', 'R']])
    assert.equal(typeof resolveFetch, 'function')
    resolveFetch('P')
    assert.equal(await pending, 'P')
    assert.equal(result, 'R')
    assert.deepEqual(calls, [['ready', 'R']])
  },
}

const results = {}
for (const [id, run] of Object.entries(rows)) {
  try {
    await run()
    results[id] = true
  } catch {
    results[id] = false
  }
}
process.stdout.write(`${JSON.stringify({ rows: results })}\n`)
