# F12 — Notes

## Purpose

Pair-discriminating high-risk fixture targeting **platform/domain
blindspots** rather than spec-prose-derivable invariants. Codex R3
(2026-05-05) pivot: after F10/F11 pilot showed 2026 bare derives spec-
hidden invariants from English prose at the same level as pair-mode, the
discriminator must move from "synonym hiding" to "Node/Express/security
semantics that the prose does not tutor."

The fixture has 5 mechanical verifiers covering 3 distinct domain
blindspots:

1. **Idempotency** (replay protection). Naive HMAC-correct impls forget
   the seen-id set and respond 200 on a re-delivery. Webhook providers
   retry — pair catches.

2. **Raw-body verification**. Naive impls write `crypto.createHmac(...)
   .update(JSON.stringify(req.body)).digest('hex')` because Express's
   `express.json()` middleware is the obvious body-parsing path. The
   re-serialized form may match a canonical signature, but it does not
   verify the actual bytes the client sent — same parsed object, different
   on-wire bytes pass naive verification.

3. **Timing-safe comparison**. Naive impls `===` the hex strings.
   Production webhook libraries (Stripe, GitHub) use `crypto.timing
   SafeEqual` because non-constant-time compare leaks the true MAC
   byte-by-byte. Spec mentions this directly to bias the model toward
   correctness; the forbidden_pattern slot is reserved if needed.

## Failure modes detected

- **Replay accepts**: returns 200 on the second delivery of the same id.
  Verifier 2 catches.
- **JSON.stringify roundtrip accept**: HMAC over re-serialized req.body
  matches a canonical-signature for non-canonical bytes. Verifier 5
  catches.
- **Tampered-body accept**: would only happen with a broken impl; verifier
  3 documents the obvious case for completeness.
- **Missing-sig accept**: 200 instead of 401. Verifier 4.
- **Silent catch** wrapping crypto.timingSafeEqual (which throws on length
  mismatch). Caught by forbidden_pattern.

## Pipeline exercise

- Phase 1 BUILD: implementer must derive (a) maintain a seen-id set,
  (b) use `express.raw({ type: 'application/json' })` or hand-parse so the
  raw bytes are kept, (c) `crypto.timingSafeEqual` for comparison.
- Phase 2 EVAL: scrutinizes whether new tests cover replay AND raw-body
  cases, not just happy + tampered.
- Phase 3 CRITIC: production-readiness on the security claims.

## Discrimination expectation

Calibration target:

- bare arm: 50-75 (passes 2-4 of 5; likely ace of happy + tampered +
  missing-sig; misses replay if no seen-id set, misses raw-body if uses
  JSON.stringify).
- solo arm: 65-85 (skill review pass may catch one of the two complex
  blindspots, may miss the other).
- pair arm: 80-95 (cross-perspective derivation of both replay AND
  raw-body invariants).

If bare scores 5/5 here too, the "domain blindspot" thesis also dies
and we re-evaluate strategy at iter level.

## Public-spec wording

Spec mentions `crypto.timingSafeEqual` directly (production constraint,
not a leak — bare in 2026 will likely already use it). Spec describes
replay protection as "the provider retries on network failure" — natural
language, no leak of "idempotency" / "deduplication" / "seen-set"
keywords. Raw-body trap is intentionally left without explicit
"use express.raw" hint — that's the discrimination axis.

## Rotation trigger

Retire when both arms consistently land > 90 across two shipped versions
on this fixture. If the raw-body verifier (#5) becomes saturated faster
than the others, replace it with a different platform blindspot rather
than retiring the whole fixture.
