# J3 hidden oracle

The designated witness is **J3-O7**, and no other row may fail for the prescribed twin. Each row runs in a new cache. Use strict identity for thrown sentinels and context objects. The reference passes all rows; the twin passes J3-O1 through J3-O6 and J3-O8, and fails J3-O7. Keep this oracle external to the reference/twin patches.

For timed rows, use a mutable `now` initialized to 100, `perf: { now: () => now }`, `ttlResolution: 0`, and `ttlAutopurge: false`, except that J3-O8 uses the advancing clock specified in that row. Do not advance time inside a memo callback. Use string values and `sizeCalculation: value => value.length` when size tracking is specified. Clear hook logs after seeding. Store each hook event as `[hookName, value, key, reason]`. Read state without mutating it: `entries()`/`keys()` for fresh order, `peek(key, { allowStale: true })` and `info(key)` for stale membership/value, `getRemainingTTL()` for remaining time, and read-only `LRUCache.unsafeExposeInternals()` access to map each key to its start, duration, and entry size. Do not write internals or compare `info().start`/`dump().start`, whose timestamps are converted to wall time. J3-O8 instead uses only the clock-free observations specified there.

The rows below have exactly the fields `id`, `setup`, `action`, and `expected`. Implement each as an independent assertion group, reporting all groups so a failure does not hide later results.

```yaml
- id: J3-O1
  setup: >-
    At now 100, construct a cache with max 3, ttl 100, updateAgeOnGet true,
    deterministic time, and a memoMethod that throws if called. Seed a='AA'
    then b='BBB'. Advance now to 125 and create an empty outer status object.
  action: >-
    Call memo('a', { status }) with no forced refresh, then inspect state.
  expected: >-
    Return 'AA'; memoMethod is never called. MRU-to-LRU keys are ['a','b'];
    both values remain stored; size is 2. Remaining TTL is 100 for a and 75
    for b; a's start is 125 and duration 100. Status has op='memo', key='a',
    memo='hit', value='AA', and cache equal to this cache; it has no new
    get, peek, or set property.
- id: J3-O2
  setup: >-
    At now 100, construct a cache with max 3, maxSize 20, string-length
    sizeCalculation, ttl 100, updateAgeOnGet true, deterministic time,
    and all three hook logs. Seed a='AA' then b='BBB', clear logs, and move
    now to 125. The memoMethod records arguments, sets options.updateAgeOnGet
    false, options.noUpdateTTL true, options.noDisposeOnSet true, and
    options.ttl 40, then returns 'AAAA'. Prepare a context object and empty
    outer status object.
  action: >-
    Call memo('a', { forceRefresh: true, context, status }) and inspect state.
  expected: >-
    Return and store 'AAAA'. One callback receives key a, prior value 'AA',
    and the exact context. Keys are ['a','b']; calculatedSize is 7 and a's
    entry size is 4. Resolved updateAgeOnGet true restarts a at 125, while
    callback noUpdateTTL preserves duration 100, so remaining TTL is 100.
    Hooks contain only ['onInsert','AAAA','a','replace']. Outer status has
    op memo, memo miss, forceRefresh true, key a, value 'AAAA', exact context,
    and cache identity, without new get, peek, or set fields.
- id: J3-O3
  setup: >-
    At now 100, construct a cache with max 3, maxSize 20, string-length
    sizeCalculation, ttl 10, deterministic time, and all three hook logs.
    Seed a='AA', clear logs, and advance now to 111. The callback records
    its old value, changes options.allowStale true and
    options.noDeleteOnStaleGet true, sets options.ttl 40, and returns 'CCC'.
  action: >-
    Call memo('a', { allowStale: false, noDeleteOnStaleGet: false,
    noUpdateTTL: true }) and inspect state.
  expected: >-
    Callback runs once with undefined old value. Return/store 'CCC'; size is
    1 and calculatedSize is 3. Entry start is 111, duration is 40, remaining
    TTL is 40. Logs, in order, are ['dispose','AA','a','expire'],
    ['disposeAfter','AA','a','expire'], ['onInsert','CCC','a','add'].
    Changing callback get options did not prevent the resolved stale deletion.
- id: J3-O4
  setup: >-
    At now 100, construct a cache with max 3, ttl 10, deterministic time,
    all three hook logs, and a callback that records its old value and
    returns 'NEW'. Seed a='OLD', clear logs, and advance now to 111.
  action: >-
    Call memo('a', { forceRefresh: true, allowStale: true,
    noDeleteOnStaleGet: true, noUpdateTTL: true }) and inspect through peek,
    info, getRemainingTTL, and read-only internals.
  expected: >-
    One callback receives 'OLD'; return/store 'NEW'; size is 1. The entry
    remains stale with start 100, duration 10, and remaining TTL -1.
    Hook order is ['dispose','OLD','a','set'],
    ['onInsert','NEW','a','replace'], ['disposeAfter','OLD','a','set'].
- id: J3-O5
  setup: >-
    At now 100, construct a cache with max 3, ttl 10, deterministic time,
    all three hook logs, and a callback that must not run. Seed a='OLD',
    clear logs, advance now to 111, and prepare an empty outer status.
  action: >-
    Call memo('a', { allowStale: true, status }) without forceRefresh.
  expected: >-
    Return 'OLD' without a callback. The default stale lookup deletes the
    entry: size 0, peek with allowStale true is undefined, and remaining
    TTL 0. Logs are ['dispose','OLD','a','expire'] followed by
    ['disposeAfter','OLD','a','expire']. Outer status reports memo hit and
    value 'OLD', with no new get or peek field.
- id: J3-O6
  setup: >-
    At now 100, construct a cache with max 3, maxSize 20, string-length
    sizeCalculation, ttl 100, deterministic time, and all three hook logs.
    Seed a='AA' then b='BBB', clear logs, and advance now to 125. The callback
    records arguments and throws a unique non-Error object without modifying
    options or the cache. Capture all stored state and prepare context/status.
  action: >-
    Call memo('missing', { context, status }); catch the thrown value and
    compare stored state and logs.
  expected: >-
    Catch the exact sentinel object. One callback receives 'missing',
    undefined prior value, and exact context. Entries remain b='BBB',a='AA'
    in that order; size 2, calculatedSize 5, durations 100, starts 100,
    entry sizes 3 and 2, remaining TTLs 75, and no hooks. The missing key
    stays absent. Outer status has memo miss and no result value.
- id: J3-O7
  setup: >-
    At now 100, construct a cache with max 3, maxSize 20, string-length
    sizeCalculation, ttl 100, updateAgeOnGet true, deterministic time,
    and all three hook logs. Seed a='AA' then b='BBB', clear logs, and
    advance now to 125. The memoMethod records key and old value then
    throws a unique sentinel without modifying the cache or options.
  action: >-
    Call memo('a', { forceRefresh: true }); catch the thrown value and
    inspect recency, membership, values, entry sizes, duration/start times,
    remaining TTLs, calculatedSize, and hook logs without get().
  expected: >-
    Catch the identical sentinel after one callback with ['a','AA'].
    Keys remain ['b','a'], values are b='BBB' and a='AA', size is 2,
    calculatedSize is 5, entry sizes are 3 and 2, each duration is 100,
    each start is 100, and each remaining TTL is 75. Hook logs are empty.
    The twin instead leaves keys ['a','b'], a's start 125 and remaining
    TTL 100; this single row fails. All other assertions in this row
    still pass on the twin.
- id: J3-O8
  setup: >-
    Use let now=100 and perf={now:()=>now++}, max 3, ttl 10,
    ttlResolution 0, ttlAutopurge false, allowStale false,
    updateAgeOnGet false, and all three hook logs. The memoMethod records
    any invocation and throws if called. Seed a='AA' without a status,
    confirm its stored start is 100 using read-only internals, clear logs,
    set now=110, and prepare an empty outer status object.
  action: >-
    Call memo('a', { status }) without forceRefresh. Inspect size, keyMap,
    valList, starts, ttls, hooks, and status without calling get, has,
    entries, keys, info, or getRemainingTTL, which could sample time again.
  expected: >-
    Return 'AA' without calling memoMethod. The lookup's time sample 110
    accepts the boundary value and leaves now=111. Size remains 1 and
    keyMap still maps a to an index whose value is 'AA', start is 100, and
    duration is 10. Hooks are empty: the accepted hit is neither deleted
    nor disposed. Status has op='memo', key='a', memo='hit', value='AA',
    and cache identity, with no forceRefresh, get, peek, or set fields.
    This row passes both the repaired reference and the prescribed twin.
```

The required public compound test supplies the fresh-MRU failure near miss as well as a successful miss with capacity eviction. Do not add another hidden failure row involving changed recency, reset age, or default deletion of stale state: the calibration contract requires exactly one failed row for the twin. The same single ordering defect may affect those inputs, but they are not separate target mechanisms or separate designated witnesses.

## Executable designated-witness skeleton

After the public build, run this from the repository root. Incorporate this assertion group as J3-O7 into the external oracle runner; the other rows remain independent groups in that runner. This program is the same designated witness, not an additional oracle row.

```sh
PATH=/Users/Shared/devlyn-vr-0227/toolchains/node-lru-cache/node-bin:$PATH node --input-type=module <<'JS'
import assert from 'node:assert/strict'
import { LRUCache } from './dist/esm/index.js'

let now = 100
const sentinel = { error: 'memo calculation failed' }
const calls = []
const hooks = []
const cache = new LRUCache({
  max: 3,
  maxSize: 20,
  sizeCalculation: value => value.length,
  ttl: 100,
  ttlResolution: 0,
  updateAgeOnGet: true,
  perf: { now: () => now },
  dispose: (...args) => hooks.push(['dispose', ...args]),
  disposeAfter: (...args) => hooks.push(['disposeAfter', ...args]),
  onInsert: (...args) => hooks.push(['onInsert', ...args]),
  memoMethod: (key, oldValue) => {
    calls.push([key, oldValue])
    throw sentinel
  },
})
cache.set('a', 'AA')
cache.set('b', 'BBB')
hooks.length = 0
now = 125
let caught
try {
  cache.memo('a', { forceRefresh: true })
} catch (error) {
  caught = error
}
const internal = LRUCache.unsafeExposeInternals(cache)
const state = {
  entries: [...cache.entries()],
  size: cache.size,
  calculatedSize: cache.calculatedSize,
  times: ['a', 'b'].map(key => {
    const index = internal.keyMap.get(key)
    return [key, internal.starts[index], internal.ttls[index],
      internal.sizes[index], cache.getRemainingTTL(key)]
  }),
}
assert.equal(caught, sentinel)
assert.deepEqual(calls, [['a', 'AA']])
assert.deepEqual(hooks, [])
assert.deepEqual(state, {
  entries: [['b', 'BBB'], ['a', 'AA']],
  size: 2,
  calculatedSize: 5,
  times: [['a', 100, 100, 2, 75], ['b', 100, 100, 3, 75]],
})
JS
```
