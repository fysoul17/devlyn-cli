# F15 — Notes

## Purpose

**Frozen-diff review fixture.** The 5th option from Codex R3 (2026-05-05):
"Seed a plausible, green-but-wrong implementation, then ask arms to
review/fix against the spec. This isolates external review value from
implementation variance."

Where F10/F11/F12 ask the arm to BUILD an implementation, F15 asks the
arm to REVIEW pre-existing code and identify a latent correctness issue
that single-request testing does not surface.

This directly tests pair-mode's empirically-validated strength: in iter-
0033c the dual-engine VERIFY pair found a unique EACCES/EPERM finding on
a frozen diff that single-engine review missed (autoresearch/iterations/
0033c-l2-new-vs-new-l1.md:216). Generation tasks did not show pair lift;
review tasks did.

## The seeded bug

`server/index.js` ships with a POST `/items` handler that does an awaited
read-modify-write on `data/items.json`:

```js
const data = await readStore();        // T1 reads, T2 reads (same view)
const newId = data.items.length + 1;   // both compute the same id
data.items.push(newItem);              // both mutate (separate copies)
await writeStore(data);                // last writer wins
```

Two concurrent POSTs interleave during the await gaps. The visible failure
modes:

- Duplicate ids: both T1 and T2 compute `length + 1`, return 201 to both
  callers, but final state contains only one of the two new items (still
  with same id).
- Lost writes: state has length+1 instead of length+2.

Single-request testing never triggers this — the race window only opens
when at least two POSTs are in flight. Pre-staged tests cover happy path
and validation but NOT concurrency.

## Failure modes detected

- **Race ignored**: arm reviews the code, doesn't notice the await gap,
  responds "the implementation looks correct" or makes cosmetic changes.
  Verifier 1 (concurrent POSTs) catches.
- **Race noticed, fix breaks single-POST**: e.g., adds a global mutex but
  forgets to release it on error. Verifier 2 catches.
- **Race noticed, fix violates scope**: e.g., replaces JSON file with
  SQLite. Out-of-scope per spec; surfaces in oracle-scope-tier-a / -b.
- **Silent catch added** to "fix" by hiding the error. Caught by
  forbidden_pattern.

## Pipeline exercise

- Phase 0 routing: standard.
- Phase 1 BUILD: this fixture is review-shaped, not build-shaped.
  Implementer reads the existing `server/index.js`, must derive the race
  from the await pattern alone — no spec wording to anchor on.
- Phase 2 EVAL: verifies the fix actually addresses concurrency, not just
  cosmetic.
- Phase 3 CRITIC: scope discipline (no out-of-scope refactor) + production-
  ready (no silent catches in the fix).

## Discrimination expectation

Calibration target:

- bare arm: 30-65 (passes baseline tests + single-POST verifier; may or
  may not derive the race from cold-read of the code without an explicit
  spec hint).
- solo arm: 55-80 (skill review pass increases the chance of catching it,
  but the same model is doing both implementation and review).
- pair arm: 75-90 (cross-perspective review; the second engine reads the
  same code with different priors and is more likely to surface the race).

The `intent` and `spec.md` deliberately use "load test" and "correctness
under load" rather than "race", "concurrency", or "atomic" — those would
be leading keywords. "Load" alone is not specific enough for the model
to anchor on a single failure mode without reading the code.

## Public-spec wording — load-bearing

The spec says "issues a load test would surface that single-request
testing would not" — natural product framing, no implementation hint.
The Requirements bullet lists "lost updates, duplicated identifiers, and
inconsistent response/state pairs" as common load-related issues — this
is education for a generic reviewer, not a leak. A naive review-only pass
that doesn't read the await sequence carefully will gloss over these.

## Rotation trigger

Retire when both bare and solo arms consistently land > 85 across two
shipped versions. If 2026 baseline reliably catches the awaited RMW race
on cold read of someone else's code, the frozen-diff review thesis also
needs updating — not just the seeded bug.
