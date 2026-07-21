# Generated criteria — rs-20260721T150755Z-a9adaef3f560

recommend: /devlyn:ideate first

## Requirements

- Add `POST /webhook` to `server/index.js`.
- Compute a lowercase hex HMAC-SHA256 over the exact raw request body bytes, keyed with the shared secret read from `data/webhook-secret.txt`, and compare it against the request's `X-Signature` header using `crypto.timingSafeEqual`. On mismatch (including a length mismatch that would make `timingSafeEqual` throw), respond `401` with JSON body `{ "error": "invalid_signature" }`.
- Signature check runs before body-shape validation: an invalid signature is always `401`, even when the body also fails shape validation.
- After a valid signature, validate the body shape: `id` and `type` must be non-empty strings, `timestamp` must be a number, `data` must be an object. Any violation responds `400` with JSON body `{ "error": "invalid_body" }`.
- Track accepted `id` values server-side (in-memory is sufficient — no persistence requirement stated). The first delivery of a given `id` (valid signature + valid body) responds `200` with `{ "accepted": true, "id": "<id>" }` and marks that `id` as accepted.
- Any subsequent delivery of an already-accepted `id` (valid signature) responds `409` with `{ "error": "duplicate_event", "id": "<id>" }` regardless of the second body's shape or content — signature still must be valid first, but body-shape/content of the replay is irrelevant to the 409 decision.
- Update `tests/server.test.js`: keep all existing tests passing, and add at least three new tests: (1) happy path — valid signature + valid body returns 200 `{ accepted: true, id }`; (2) replay — a second delivery of the same `id` with a valid signature returns 409 `{ error: 'duplicate_event', id }`; (3) tampered body — a body modified after signing (so the original signature no longer matches) returns 401 `{ error: 'invalid_signature' }`.
- No new npm dependencies — use Node's built-in `crypto` module.
- Only `server/index.js` and `tests/server.test.js` may be modified.

## Constraints

- Express's default `express.json()` re-serializes/parses the body; computing HMAC over `JSON.stringify(req.body)` is not guaranteed byte-identical to what the client actually sent and would produce false signature mismatches. Capture the raw request body bytes (e.g. via the `express.json({ verify })` hook, or a raw-body middleware scoped to `/webhook`) and compute the HMAC over those exact bytes.
- Read `data/webhook-secret.txt` as the HMAC key; the file has no trailing newline (verified: 30 bytes, no `\n`), but the implementation should not assume that — read and use its contents without introducing a mismatch.
- `crypto.timingSafeEqual` requires equal-length buffers; a header of the wrong length must not throw an uncaught exception — treat any length mismatch as an invalid signature (401), not a 500.
- Do not add new npm dependencies (`crypto` is a Node built-in, not an npm package).
- Do not touch files other than `server/index.js` and `tests/server.test.js`.

## Out of Scope

- Persisting accepted `id`s across process restarts.
- Rate limiting, request logging, or other webhook-adjacent hardening not named in the goal.
- Changes to `/health`, `/items`, `/items/:id`, `bin/cli.js`, or any file outside the two named above.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "npm test", "expect_exit_code": 0 }
  ]
}
```

## Assumptions

- The classifier routed this goal to the `large` branch on `file_scope_signals > 10` (12 quoted-symbol/path matches in the goal text), not because the goal is actually under-specified — the goal text is precise and self-contained. Assumptions below are narrow, scope-preserving restatements of what the goal already states, not new scope.
- "the same `id` may arrive twice" is read as: dedup is scoped to `id` values accepted after this server process started (in-memory Set/Map), since the goal does not mention persistence or a datastore.
- HMAC comparison: the computed digest and the header value are compared as equal-length buffers per `crypto.timingSafeEqual`'s requirement; unequal lengths are treated as `401 invalid_signature` rather than a thrown error, since the goal specifies signature mismatches uniformly resolve to 401.
- `X-Signature` header is read case-insensitively (Node's `req.get('X-Signature')` / `req.headers['x-signature']`), consistent with HTTP header semantics; the goal does not state a case requirement.
- No assumption narrows or reinterprets any explicit line of the goal text; where the goal is explicit (status codes, error bodies, verification order, file scope, no new dependencies), it is taken verbatim.
