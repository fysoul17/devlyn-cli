# J3 mechanism record

**Family:** failure-state preservation.

**Mandatory clause (verbatim from `spec.md`):**

> If `memoMethod` throws, `memo()` rethrows that same thrown value without changing cache membership, cached values, recency order, TTL durations or start times, entry sizes, or `calculatedSize`.

**Trigger:** An existing fresh entry is not MRU, `updateAgeOnGet` is enabled, and `memo(key, { forceRefresh: true })` invokes a callback that throws. The clock has advanced since insertion, so a premature successful-read effect both moves the key and refreshes its age. The callback does not mutate the cache or advance the clock.

**Causal code path:** The initial private `#peek` correctly selects the old value and the forced refresh. In the reference, `memoMethod` must return before the refreshing-path `#get` is reached. The twin moves just that `#get(k, lookupOptions)` above the callback. `#get` reaches its fresh-value branch and calls `#moveToTail` and `#updateItemAge`; the subsequent callback throws, so `#set` is never reached and those earlier read effects remain. The original source's `#memo` near lines 2978–2999 and `#get` near lines 3023–3080 identify the relevant helpers; the mechanism is the premature read mutation, not those line numbers.

**Incorrect behavior:** Failed recomputation changes eviction priority and restarts an existing TTL despite returning no value. The original value, size, and thrown identity can all remain correct, so those observations alone do not establish preservation. No extra catch, alternate exception, or second defect is needed.

**Twin edit:** Starting from the reference, relocate only the refreshing-path `#get(k, lookupOptions)` statement from immediately after the successful `memoMethod` call to immediately before it. Keep the snapshot, initial peek, non-refresh hit branch, set behavior, comments, tests, and changed-file set identical. The changed-file set is exactly `src/index.ts` and `test/memo-failure.ts` in both variants.

**Designated executable witness:** `J3-O7` in `oracle.md`. After the public pretest build, this standalone check runs from the repository root using the same command-prefix toolchain. It uses nonmutating observations and throws only from the memo callback:

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

The reference exits 0. The twin fails the final state assertion: entries are `[['a','AA'],['b','BBB']]` and the `a` time tuple is `['a',125,100,2,100]`. These are two observable effects of the one moved read, evaluated within one designated row.

**Near-miss exclusions:**

- A non-forced fresh hit skips the callback and must still update normal get recency and age; J3-O1 passes both variants.
- A successful forced refresh reaches the read and set in both variants; fixed-time success rows J3-O2–J3-O4 pass both, including saved lookup options and callback-modified set options.
- A stale hit with `allowStale: true` and no force skips the callback, and its ordinary deletion remains required; J3-O5 passes both.
- A throw for an absent key has no cached entry on which get effects can act; J3-O6 passes both.
- A throw for an already-MRU fresh key with age refresh disabled leaves all tracked state unchanged; this is the public compound test's failure phase and passes both.
- A stale-entry throw with default deletion could expose the same premature-read defect through membership/disposal changes, but it is not an additional oracle witness. Do not add it to public checks or hidden rows.
- Cache mutation by the callback itself, exceptions raised by another hook, and external side effects are explicitly outside this failure guarantee. They neither establish nor excuse this mechanism.

The relevant evidence is the preserved-state requirement, the fresh forced-refresh trigger, and the read-before-throw path. A nearby status-label mistake, a set-option snapshot mistake, or incorrect thrown identity is not this target mechanism.
