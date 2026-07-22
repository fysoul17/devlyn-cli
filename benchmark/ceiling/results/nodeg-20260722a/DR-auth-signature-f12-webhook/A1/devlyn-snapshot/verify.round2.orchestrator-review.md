# Orchestrator review of VERIFY round-2 primary-judge (Codex) findings

Before merging, each HIGH finding from the round-2 primary judge was independently
reproduced or refuted with direct command output, per the harness's
"Evidence over claim" / "No guesswork" contract.

## Excluded: `webhook-unframed-empty-body` (HIGH) — REFUTED, empirically false

Claim: "the correct HMAC of zero bytes returns 401 invalid_signature instead of
the required 400 invalid_body" for an empty body with no Content-Length/Transfer-Encoding.

Reproduced directly (`node -e` scratch script, `data/webhook-secret.txt` secret,
HMAC of the empty string as `X-Signature`, POST with (a) `Content-Length: 0`,
(b) no Content-Length header at all, (c) no Content-Type/Content-Length at all):
all three cases return `400 {"error":"invalid_body"}`, exactly as the spec
requires — NOT 401. `express.raw()` sets `req.body` to an empty `Buffer` even
for a zero-byte request, so the signature check succeeds (empty-string HMAC
matches) and shape validation correctly rejects the empty/unparseable body as
`invalid_body`. This finding does not reproduce under any tested condition and
is excluded from the merge as a factual error.

## Excluded: `webhook-parser-preempts-signature` (HIGH) — reproduced, but out of the spec's stated scope

Claim: a body over `express.raw()`'s default 100 KB limit returns an unhandled
`413 Payload Too Large` (Express's own HTML error page) instead of the app's
401/400 JSON shapes.

Reproduced directly: a 102401-byte body does return `413` with an HTML body.
This is real, but it is **pre-existing standard Express/body-parser behavior**,
not a regression introduced by the fix — the round-1 implementation used
`express.json()`, which carries the *same* default 100 KB limit, so this
exact interaction existed in round 1 too and was not flagged then. The
goal (`.devlyn/criteria.generated.md`) never mentions payload size or asks
for unbounded body acceptance; the "signature check runs first" requirement
is about the ordering between the app's *own* signature and shape validation
for a delivered webhook payload, not a mandate to override a standard
framework-level DoS protection for arbitrarily large requests. Per the VERIFY
judge's own instructions ("do not widen a scoped clause into a global
invariant... a finding based on a widened invariant is a false positive and
must not drive the fix loop"), this finding widens "sig check runs first" into
an unstated "the server must accept unbounded payloads," which is out of
scope. Removing or raising the body-size limit to accommodate this would be
speculative robustness for a case the user never asked about, and would trade
away a sensible default security protection. Excluded from the merge as
out-of-scope; not actioned.

## Retained: `webhook-raw-parser-constraint` (MEDIUM) and `live-interaction-not-exercised` (LOW)

Both retained in `.devlyn/verify.findings.jsonl` verbatim. The MEDIUM finding's
"should have used the express.json() verify-option" framing reflects this run's
own (later-superseded) `criteria.generated.md` Constraints suggestion — not a
requirement from the original user goal — and the round-1→round-2 fix that
replaced it was the correct root-cause resolution to the round-1 HIGH findings.
Its concrete factual observation (the `express.json()` `verify` callback on
`server/index.js:8` still captures `req.rawBody`, which is no longer read
anywhere) is accurate leftover dead code from round 1, but per the merge rule
a MEDIUM finding is only verdict-binding when it identifies a concrete
behavioral regression — this one does not, so it stays advisory
(`PASS_WITH_ISSUES`), not verdict-binding. Not actioned in this run to avoid
opening another fix round for a purely cosmetic, non-binding item; flagged
here for visibility in the final report.

The LOW finding is Codex's own read-only-sandbox limitation (cannot bind
localhost sockets) — informational only, not a code defect, not actioned.
