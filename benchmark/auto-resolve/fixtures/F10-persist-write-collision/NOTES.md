# F10 — Notes

## Purpose

Pair-discriminating high-risk fixture. Adds a write endpoint with persistent
storage. The pair-edge mechanism: when an implementation reads-modifies-
writes a JSON file in response to async requests, multiple in-flight POSTs
can interleave during the await gap between read and write — producing
duplicate ids or lost writes. A single-pass implementer typically writes
the natural shape:

```js
const data = JSON.parse(await fs.readFile(...));
data.items.push({ id: data.items.length + 1, ...body });
await fs.writeFile(...);
```

This passes single-POST tests trivially. The failure only surfaces when
multiple POSTs are in flight together. A reviewer with fresh eyes asking
"what happens if two of these run at once?" catches it; the same model
reviewing its own work tends to anchor on the "happy path" view.

## Failure modes detected

- **Duplicate ids** from `length + 1` after concurrent reads.
- **Lost writes** from last-writer-wins overwrite of in-flight POSTs.
- **No persistence** — implementer keeps in-memory only, ignoring the
  restart-survival requirement. Caught by `data/items.json` byte check.
- **Silent catch** wrapping the write path. Caught by forbidden_pattern.

## Pipeline exercise

- Phase 1 BUILD: implementer must derive that an awaited file read-modify-
  write under parallel requests requires either serialization (mutex /
  queue) or a unique-id source independent of array length.
- Phase 2 EVAL: scrutinizes whether the new tests exercise the close-
  together POST case rather than just single-POST happy path.
- Phase 3 CRITIC: scope discipline + production-ready invariant on the
  consistency claim.

## Discrimination expectation

Calibration target (set in pyx-memory project memory 2026-05-05):

- bare arm: 40-65 (passes spec wording verbatim, fails parallel verifier).
- solo arm: 60-78 (review pass may catch one mode, may miss another).
- pair arm: 75-90 (cross-perspective derivation of the consistency
  invariant from the English "close together" wording).

## Public-spec wording — load-bearing

The spec deliberately uses "close together" and "remain consistent"
instead of trigger keywords. If the spec were to say "race condition",
"concurrent", "atomic", or "lock", a single-pass solo arm would
keyword-match the answer pattern and ace the fixture. The English
prose forces invariant derivation, which is where pair has the edge.

## Rotation trigger

Headroom run `20260507-f10-f11-tier1-full-pipeline` rejected this fixture as
pair-lift evidence: bare scored 75 and solo_claude scored 94. Keep it as a
concurrent persistence control unless the visible contract is reworked to
expose lower bare/solo ceilings.

Retire when both `bare` and `solo_claude` consistently land > 90 across two
shipped versions, OR when "close-together-write" becomes a recognized pattern
such that solo arm reliably reaches for a serializing mechanism on first read.
Whichever comes first.
