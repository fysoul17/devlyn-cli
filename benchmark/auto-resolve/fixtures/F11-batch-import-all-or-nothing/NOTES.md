# F11 — Notes

## Purpose

Pair-discriminating high-risk fixture. Adds a batch-import write endpoint
with an all-or-nothing guarantee. The pair-edge mechanism: implementers
who validate-as-they-go produce a partial-write bug — by the time the
invalid item is hit and 400 returned, prior items have already been
appended. The natural shape:

```js
app.post('/items/import', (req, res) => {
  for (const it of req.body.items) {
    if (!valid(it)) return res.status(400).json(...);
    items.push({ id: nextId(), ...it }); // already mutated
  }
  res.status(201).json({ inserted: req.body.items.length });
});
```

This passes the "happy path" test trivially and the "all-bad" test trivially.
It fails only on the discriminating case: one bad item mid-batch — store
ends up with the prefix already inserted while the response says 400.

A reviewer with fresh eyes asking "what does the store look like after the
failure response?" catches it; the same model that wrote the loop tends to
focus on the response correctness without re-examining the store delta.

## Failure modes detected

- **Partial inserts** before validation failure (the core discriminator).
- **Order swap** — implementer inserts at wrong index or sorts unexpectedly.
- **Id collision** — implementer reuses ids when batch validation rejects.
- **Silent catch** wrapping `JSON.parse` or validation. Caught by
  forbidden_pattern.

## Pipeline exercise

- Phase 1 BUILD: implementer must derive that "all or nothing" requires
  validating the entire batch before any mutation, OR using a
  copy-on-write pattern that rolls back on validation failure.
- Phase 2 EVAL: scrutinizes whether the new tests assert the
  store-unchanged invariant after a failed batch, not just the 400.
- Phase 3 CRITIC: production-readiness on the "all or nothing" claim.

## Discrimination expectation

Calibration target (set in pyx-memory project memory 2026-05-05):

- bare arm: 45-65 (passes spec text, fails the store-unchanged verifier
  on mid-batch failure).
- solo arm: 65-78 (review pass may catch the store-delta issue if the
  reviewer re-reads the spec; coin-flip).
- pair arm: 78-90 (cross-perspective derivation of the rollback or
  validate-first pattern).

## Public-spec wording — load-bearing

The spec uses "accepted as a whole or rejected as a whole" and "left
exactly as it was" instead of trigger keywords. If the spec said
"transactional", "atomic", or "rollback", a single-pass solo arm would
keyword-match the answer pattern and ace the fixture. The English prose
forces invariant derivation — the discriminating axis.

## Rotation trigger

Headroom run `20260507-f10-f11-tier1-full-pipeline` rejected this fixture as
pair-lift evidence: bare scored 98 and solo_claude scored 97. Keep it as an
atomic batch control unless the visible contract is reworked to expose lower
bare/solo ceilings.

Retire when both `bare` and `solo_claude` consistently land > 90 across two
shipped versions, OR when "all-or-nothing batch" becomes a recognized pattern
such that solo arm reliably validates-first on the initial implementation pass.
Whichever comes first.
