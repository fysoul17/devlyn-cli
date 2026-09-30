# J2 implementation design

This is implementer-only authoring material. Build the reference, defective twin, and executable oracle later in a writable copy; the author has not patched the pinned repository or run commands that modify it.

## Existing behavior and scope

The pinned `src/index.ts` defines `find()` at approximately lines 1961-1974. It calls `this.#indexes()` without options, so the generator at approximately lines 1815-1828 applies `this.allowStale`. Once a predicate succeeds, `find()` calls `this.#get(key, getOptions)`. The latter already independently defaults `allowStale`, `updateAgeOnGet`, and `noDeleteOnStaleGet` and implements the desired matched-entry effects. The candidate-selection default is the only production behavior needing correction.

Both arms must change exactly `src/index.ts` and the new `test/find-options.ts`. Do not edit `test/find.ts`, generated artifacts, dependency metadata, or snapshot files. Use the existing build imports and avoid importing new tests from snapshot-sensitive aggregate tests.

## Reference

Pass the resolved per-call stale policy into `#indexes` within `find()`:

```ts
for (const i of this.#indexes({
  allowStale: getOptions.allowStale ?? this.allowStale,
})) {
  // Existing find body remains unchanged.
}
```

An explicit boolean controls candidate filtering; an absent or undefined property inherits the cache's current public setting. Leave the background-fetch value extraction, undefined-value skip, predicate invocation, and `#get(key, getOptions)` call unchanged. A brief method comment may document that the get options govern candidate eligibility as well as retrieval. Do not change `#indexes` globally or temporarily mutate `cache.allowStale`.

## Public test design

Create `test/find-options.ts`, importing `t` from `tap` and `LRUCache` from `../dist/esm/node/index.js`, as the existing find test does. Use `let now = 100` and constructor options `perf: { now: () => now }, ttlResolution: 0, ttlAutopurge: false`. Advance `now` directly. A strictly positive start avoids the existing zero-start convention. Do not use real delays.

Use separately constructed caches so one assertion's retrieval side effects do not contaminate another case. Record predicate tuples and check that the third argument is the actual cache. To inspect storage and full recency without invoking get effects or hiding stale entries, use `LRUCache.unsafeExposeInternals(c)` read-only, mapping `indexes({ allowStale: true })` through `keyList`. Check TTL with `getRemainingTTL()`; do not mutate exposed structures.

Required public cases:

1. Cache default false, per-call true: insert fresh `f` with TTL 100 and then stale-to-be `s` with TTL 10 at time 100, advance to 120, and call an always-true predicate. It sees only `s`, returns its value, and the default stale-get behavior deletes `s`. The fresh value remains and retains 80 time units of TTL. This demonstrates the requested correction against the original repository.
2. Inheritance: for both cache defaults, separately exercise an omitted options argument, `{}`, and `{ allowStale: undefined }`. Use the same stale-MRU/fresh-older shape. With default false, only the fresh entry reaches a successful predicate and the stale entry remains stored. With default true and `noDeleteOnStaleGet: true` on the cache, the stale match is returned and retained. Include a case that changes the public `cache.allowStale` setting before searching to establish inheritance of the current setting.
3. Explicit false with a false-default cache: exclude the stale MRU, visit and return the older fresh match, and retain the excluded stale entry. A no-match variant records only fresh candidates and confirms unchanged membership, recency, and remaining TTL.
4. Compound scenario: at time 100, construct a false-default cache with max 5 and insert `old-stale`/`O` with TTL 10, `fresh`/`F` with TTL 100, then `new-stale`/`N` with TTL 10. At time 120 call `find` with `{ allowStale: true, noDeleteOnStaleGet: true }`, matching only `old-stale`. Expect callback order `new-stale, fresh, old-stale`, result `O`, storage order unchanged, size 3, stale TTLs -10, and fresh TTL 80. Next search with `{ allowStale: true, updateAgeOnGet: true }`, matching `fresh`. Expect callback order `new-stale, fresh`, result `F`, storage order `fresh, new-stale, old-stale`, size 3, fresh TTL 100, and stale TTLs still -10. This jointly checks option precedence, search ordering, retention, recency, and age effects.
5. Fresh-only cache: stop at the first match in MRU order, confirm normal promotion of an older match, and verify both enabled and disabled `updateAgeOnGet`. A rejecting predicate must not promote or refresh any visited entry.

The original `test/find.ts` already covers previous values during force refresh and pending fetches without previous values. Keep it unchanged and run the complete suite.

Public cases must remain identical in the two arms. They intentionally do not combine a true cache default, an explicit false per-call policy, and stale candidates. Do not add a generated option matrix that introduces this hidden combination. The visible contract still states the complete precedence requirement and source-review obligation.

## Defective twin

Begin with the reference, retaining the public tests byte for byte. Change only the candidate option expression from `getOptions.allowStale ?? this.allowStale` to `getOptions.allowStale || this.allowStale`. This is the sole target defect: a familiar fallback expression treats explicit false as absent during enumeration. Do not make any other semantic change.

With a true cache default and explicit false, the generator includes stale entries but the unchanged `#get` still honors false. If a stale MRU is a predicate match, `find()` therefore stops before the older fresh match, deletes the stale entry by the normal stale-get path, and returns undefined. All other hidden rows and every public scenario use combinations where the two resolution expressions agree, or contain no stale entry, so they pass in both arms.

## Verification and calibration

Run each declared public command unchanged from the writable repository root with its declared PATH assignment. `npm test -- -c -t0` runs `pretest`, whose `prepare` script invokes `tshy` and the configured build; this provides the configured TypeScript build checks. There is no separate `typecheck` script. `npm run lint` invokes the repository's fixer and its formatting follow-up; retain only authorized patch files after it runs.

Implement the hidden rows separately from the committed public test file. Collect results by row ID instead of aborting the whole oracle after its first failed assertion. Calibration must show that the reference passes every row, the twin fails exactly J2-W1, both arms pass both public commands, and both patches change exactly the same two paths. Report actual calibration results without substituting this design's predictions for execution evidence.
