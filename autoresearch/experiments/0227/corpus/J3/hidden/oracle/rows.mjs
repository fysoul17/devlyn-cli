import assert from 'node:assert/strict'
import { pathToFileURL } from 'node:url'

const { LRUCache } = await import(pathToFileURL(process.argv[2]).href)
const rows = {}
const check = (id, action) => {
  try {
    action()
    rows[id] = true
  } catch {
    rows[id] = false
  }
}
const noReadStatus = status => {
  assert.equal('get' in status, false)
  assert.equal('peek' in status, false)
  assert.equal('set' in status, false)
}
const fixture = (memoMethod, other = {}) => {
  let now = 100
  const hooks = []
  const cache = new LRUCache({
    max: 3,
    ttlResolution: 0,
    ttlAutopurge: false,
    perf: { now: () => now },
    dispose: (...args) => hooks.push(['dispose', ...args]),
    disposeAfter: (...args) => hooks.push(['disposeAfter', ...args]),
    onInsert: (...args) => hooks.push(['onInsert', ...args]),
    memoMethod,
    ...other,
  })
  return { cache, hooks, advance: value => { now = value } }
}
const item = (cache, key) => {
  const internals = LRUCache.unsafeExposeInternals(cache)
  const index = internals.keyMap.get(key)
  return index === undefined ? undefined : [
    internals.starts?.[index],
    internals.ttls?.[index],
    internals.sizes?.[index],
    cache.getRemainingTTL(key),
  ]
}
const thrown = action => {
  let caught
  try { action() } catch (error) { caught = error }
  return caught
}

check('J3-O1', () => {
  let calls = 0
  const { cache, advance } = fixture(() => { calls++; throw Error('unexpected') }, {
    ttl: 100, updateAgeOnGet: true,
  })
  cache.set('a', 'AA')
  cache.set('b', 'BBB')
  advance(125)
  const status = {}
  assert.equal(cache.memo('a', { status }), 'AA')
  assert.equal(calls, 0)
  assert.deepEqual([...cache.keys()], ['a', 'b'])
  assert.deepEqual([...cache.entries()], [['a', 'AA'], ['b', 'BBB']])
  assert.equal(cache.size, 2)
  assert.deepEqual(item(cache, 'a'), [125, 100, undefined, 100])
  assert.equal(cache.getRemainingTTL('b'), 75)
  assert.equal(status.op, 'memo')
  assert.equal(status.key, 'a')
  assert.equal(status.memo, 'hit')
  assert.equal(status.value, 'AA')
  assert.equal(status.cache, cache)
  noReadStatus(status)
})

check('J3-O2', () => {
  const calls = []
  const context = { id: 2 }
  const { cache, hooks, advance } = fixture((key, oldValue, { options, context: received }) => {
    calls.push([key, oldValue, received])
    options.updateAgeOnGet = false
    options.noUpdateTTL = true
    options.noDisposeOnSet = true
    options.ttl = 40
    return 'AAAA'
  }, { maxSize: 20, sizeCalculation: value => value.length,
    ttl: 100, updateAgeOnGet: true })
  cache.set('a', 'AA')
  cache.set('b', 'BBB')
  hooks.length = 0
  advance(125)
  const status = {}
  assert.equal(cache.memo('a', { forceRefresh: true, context, status }), 'AAAA')
  assert.equal(calls.length, 1)
  assert.deepEqual(calls[0].slice(0, 2), ['a', 'AA'])
  assert.equal(calls[0][2], context)
  assert.deepEqual([...cache.entries()], [['a', 'AAAA'], ['b', 'BBB']])
  assert.equal(cache.calculatedSize, 7)
  assert.deepEqual(item(cache, 'a'), [125, 100, 4, 100])
  assert.deepEqual(hooks, [['onInsert', 'AAAA', 'a', 'replace']])
  assert.equal(status.op, 'memo')
  assert.equal(status.memo, 'miss')
  assert.equal(status.forceRefresh, true)
  assert.equal(status.key, 'a')
  assert.equal(status.value, 'AAAA')
  assert.equal(status.context, context)
  assert.equal(status.cache, cache)
  noReadStatus(status)
})

check('J3-O3', () => {
  const oldValues = []
  const { cache, hooks, advance } = fixture((_key, oldValue, { options }) => {
    oldValues.push(oldValue)
    options.allowStale = true
    options.noDeleteOnStaleGet = true
    options.ttl = 40
    return 'CCC'
  }, { maxSize: 20, sizeCalculation: value => value.length, ttl: 10 })
  cache.set('a', 'AA')
  hooks.length = 0
  advance(111)
  assert.equal(cache.memo('a', { allowStale: false,
    noDeleteOnStaleGet: false, noUpdateTTL: true }), 'CCC')
  assert.deepEqual(oldValues, [undefined])
  assert.equal(cache.peek('a', { allowStale: true }), 'CCC')
  assert.equal(cache.size, 1)
  assert.equal(cache.calculatedSize, 3)
  assert.deepEqual(item(cache, 'a'), [111, 40, 3, 40])
  assert.deepEqual(hooks, [
    ['dispose', 'AA', 'a', 'expire'],
    ['disposeAfter', 'AA', 'a', 'expire'],
    ['onInsert', 'CCC', 'a', 'add'],
  ])
})

check('J3-O4', () => {
  const oldValues = []
  const { cache, hooks, advance } = fixture((_key, oldValue) => {
    oldValues.push(oldValue)
    return 'NEW'
  }, { ttl: 10 })
  cache.set('a', 'OLD')
  hooks.length = 0
  advance(111)
  assert.equal(cache.memo('a', { forceRefresh: true, allowStale: true,
    noDeleteOnStaleGet: true, noUpdateTTL: true }), 'NEW')
  assert.deepEqual(oldValues, ['OLD'])
  assert.equal(cache.peek('a', { allowStale: true }), 'NEW')
  assert.equal(cache.info('a').value, 'NEW')
  assert.equal(cache.size, 1)
  assert.deepEqual(item(cache, 'a'), [100, 10, undefined, -1])
  assert.deepEqual(hooks, [
    ['dispose', 'OLD', 'a', 'set'],
    ['onInsert', 'NEW', 'a', 'replace'],
    ['disposeAfter', 'OLD', 'a', 'set'],
  ])
})

check('J3-O5', () => {
  let calls = 0
  const { cache, hooks, advance } = fixture(() => { calls++; throw Error('unexpected') }, { ttl: 10 })
  cache.set('a', 'OLD')
  hooks.length = 0
  advance(111)
  const status = {}
  assert.equal(cache.memo('a', { allowStale: true, status }), 'OLD')
  assert.equal(calls, 0)
  assert.equal(cache.size, 0)
  assert.equal(cache.peek('a', { allowStale: true }), undefined)
  assert.equal(cache.getRemainingTTL('a'), 0)
  assert.deepEqual(hooks, [
    ['dispose', 'OLD', 'a', 'expire'],
    ['disposeAfter', 'OLD', 'a', 'expire'],
  ])
  assert.equal(status.memo, 'hit')
  assert.equal(status.value, 'OLD')
  noReadStatus(status)
})

check('J3-O6', () => {
  const sentinel = { failure: 6 }
  const context = { id: 6 }
  const calls = []
  const { cache, hooks, advance } = fixture((key, oldValue, { context: received }) => {
    calls.push([key, oldValue, received])
    throw sentinel
  }, { maxSize: 20, sizeCalculation: value => value.length, ttl: 100 })
  cache.set('a', 'AA')
  cache.set('b', 'BBB')
  hooks.length = 0
  advance(125)
  const status = {}
  assert.equal(thrown(() => cache.memo('missing', { context, status })), sentinel)
  assert.equal(calls.length, 1)
  assert.deepEqual(calls[0].slice(0, 2), ['missing', undefined])
  assert.equal(calls[0][2], context)
  assert.deepEqual([...cache.entries()], [['b', 'BBB'], ['a', 'AA']])
  assert.equal(cache.size, 2)
  assert.equal(cache.calculatedSize, 5)
  assert.deepEqual(item(cache, 'a'), [100, 100, 2, 75])
  assert.deepEqual(item(cache, 'b'), [100, 100, 3, 75])
  assert.equal(cache.peek('missing', { allowStale: true }), undefined)
  assert.deepEqual(hooks, [])
  assert.equal(status.memo, 'miss')
  assert.equal('value' in status, false)
})

check('J3-O7', () => {
  const sentinel = { failure: 7 }
  const calls = []
  const { cache, hooks, advance } = fixture((key, oldValue) => {
    calls.push([key, oldValue])
    throw sentinel
  }, { maxSize: 20, sizeCalculation: value => value.length,
    ttl: 100, updateAgeOnGet: true })
  cache.set('a', 'AA')
  cache.set('b', 'BBB')
  hooks.length = 0
  advance(125)
  assert.equal(thrown(() => cache.memo('a', { forceRefresh: true })), sentinel)
  assert.deepEqual(calls, [['a', 'AA']])
  assert.deepEqual([...cache.entries()], [['b', 'BBB'], ['a', 'AA']])
  assert.equal(cache.size, 2)
  assert.equal(cache.calculatedSize, 5)
  assert.deepEqual(item(cache, 'a'), [100, 100, 2, 75])
  assert.deepEqual(item(cache, 'b'), [100, 100, 3, 75])
  assert.deepEqual(hooks, [])
})

check('J3-O8', () => {
  let now = 100
  const hooks = []
  const calls = []
  const cache = new LRUCache({
    max: 3,
    ttl: 10,
    ttlResolution: 0,
    ttlAutopurge: false,
    allowStale: false,
    updateAgeOnGet: false,
    perf: { now: () => now++ },
    dispose: (...args) => hooks.push(['dispose', ...args]),
    disposeAfter: (...args) => hooks.push(['disposeAfter', ...args]),
    onInsert: (...args) => hooks.push(['onInsert', ...args]),
    memoMethod: (...args) => {
      calls.push(args)
      throw Error('unexpected memo callback')
    },
  })
  cache.set('a', 'AA')
  const internals = LRUCache.unsafeExposeInternals(cache)
  const seededIndex = internals.keyMap.get('a')
  assert.notEqual(seededIndex, undefined)
  assert.equal(internals.starts[seededIndex], 100)
  hooks.length = 0
  now = 110
  const status = {}
  assert.equal(cache.memo('a', { status }), 'AA')
  assert.equal(now, 111)
  assert.equal(calls.length, 0)
  assert.equal(cache.size, 1)
  const index = internals.keyMap.get('a')
  assert.equal(index, seededIndex)
  assert.equal(internals.valList[index], 'AA')
  assert.equal(internals.starts[index], 100)
  assert.equal(internals.ttls[index], 10)
  assert.deepEqual(hooks, [])
  assert.equal(status.op, 'memo')
  assert.equal(status.key, 'a')
  assert.equal(status.memo, 'hit')
  assert.equal(status.value, 'AA')
  assert.equal(status.cache, cache)
  assert.equal('forceRefresh' in status, false)
  noReadStatus(status)
})

process.stdout.write(JSON.stringify({ rows }) + '\n')
