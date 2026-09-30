# J2 mechanism record

Interaction family: ordering/precedence.

## Mandatory clause

The normal-register requirement in `spec.md` states:

> `find(fn, getOptions)` uses an explicitly supplied `getOptions.allowStale` value, whether `true` or `false`, in preference to `cache.allowStale` when selecting candidates. An omitted or `undefined` value inherits the cache's current setting.

Its visible consequence is also mandatory:

> When the effective stale policy is false, expired entries do not reach the predicate; searching continues toward older eligible entries without deleting or refreshing the excluded entries.

## Trigger

The cache's current `allowStale` setting is true; the call supplies `{ allowStale: false }`; an expired MRU entry precedes a fresh older entry; and the predicate would accept both. The stale entry is an ordinary stored value, with no background fetch or retention override.

## Causal code path

The reference resolves candidate eligibility with `getOptions.allowStale ?? this.allowStale` inside `find()`. The twin substitutes `||` for `??`, making explicit false inherit true during enumeration. `#indexes` consequently yields the stale MRU, and `find()` calls the predicate on it. The predicate succeeds, so `find()` immediately delegates to `#get(key, getOptions)` and returns its result. `#get` correctly preserves explicit false, deletes the ordinary stale entry by its default stale-get policy, and returns undefined. The older fresh match is never visited.

The defect is the inconsistent precedence used to select candidates, not a defect in stale retrieval, expiry arithmetic, or MRU links. Approximate supporting locations in the pinned source are `find()` at `src/index.ts:1961`, `#indexes` at `src/index.ts:1815`, and `#get` at `src/index.ts:3023`. These locations support the causal account; the mechanism remains the explicit false value being lost during candidate policy resolution.

## Incorrect behavior and executable witness

Hidden oracle row **J2-W1** is the sole designated witness. At clock 100 insert fresh `F` with TTL 100, then stale-to-be `S` with TTL 10; at clock 120 search with an always-true predicate and per-call false on a true-default cache. The reference returns `F`, calls the predicate only for `F`, promotes it, and leaves `S` stored and expired. The twin calls only the predicate for `S`, returns undefined, and deletes `S`.

The executable JavaScript skeleton in `hidden/oracle.md` asserts return value, callback sequence, storage order, membership, size, and TTLs together in that one row. Its two values both satisfy the predicate, so merely asserting the absence of a returned stale value cannot accidentally pass the twin. All other oracle rows are non-witness controls expected to pass both arms.

## Near-miss exclusions

- Per-call true with a false cache default is handled correctly by both `??` and `||`; this is exercised publicly and by J2-H2.
- Omitted and undefined policies genuinely inherit the cache default in both arms; J2-H3 covers each default.
- Explicit false with a false cache default excludes stale entries in both arms; J2-H5 covers this with a nonmatching search.
- A true cache default and explicit false with only fresh entries has no observable stale-filtering difference; J2-H6 covers it.
- A predicate that rejects the stale entry can continue to a fresh match in the twin. J2-W1 therefore accepts both entries and records which entry reached the predicate.
- Testing only return values with `noDeleteOnStaleGet: true` would miss deletion evidence, and observing stale membership through `has()` would confuse storage with freshness. J2-W1 uses the ordinary deletion policy and nonmutating storage observations.
- Fetch placeholders and values during refresh are independent eligibility rules. J2-H7 and the existing find suite preserve their behavior; they are not part of the trigger.

## Calibration contract

Both arms change the same two files, with identical public tests. Only the option-resolution operator differs semantically. The reference must pass every public command and hidden row. The twin must pass every public command and every hidden row except J2-W1. This authoring record predicts those results; the separate implementer and model-free calibration step must produce execution evidence.
