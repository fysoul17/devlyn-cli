# Generated criteria — webhook signature + replay endpoint

Source: `.devlyn/goal.raw.txt` (free-form goal, complexity=medium).

## Requirements

- Add `POST /webhook` to `server/index.js`. Read the raw request body bytes (not the re-serialized JSON) so HMAC verification is computed over exactly what the client sent.
- Compute `HMAC-SHA256(secret, rawBody)` as lowercase hex using the shared secret read from `data/webhook-secret.txt`, and compare it to the request's `X-Signature` header via `crypto.timingSafeEqual` (guard the length check before calling `timingSafeEqual`, which throws on mismatched buffer lengths — a length mismatch must be treated as "not equal", not an uncaught throw). Mismatch or missing header → `401 { error: 'invalid_signature' }`.
- Signature check runs before body-shape validation. Only once the signature is valid, validate the parsed body is `{ id, type, timestamp, data }` where `id` and `type` are non-empty strings, `timestamp` is a number, and `data` is an object. Shape failure → `400 { error: 'invalid_body' }`.
- Track accepted `id`s (in-memory, module-scoped, consistent with the existing in-memory `items` pattern). Once shape validation passes: if `id` was already accepted, respond `409 { error: 'duplicate_event', id }` regardless of the new body's contents; otherwise record the `id` and respond `200 { accepted: true, id }`.
- Update `tests/server.test.js`: keep the 3 existing tests passing, and add at least 3 new tests — happy path (200), replay of the same `id` (409), tampered body with the original (now-mismatched) signature (401). Tests must compute real HMAC signatures against `data/webhook-secret.txt` the same way the implementation does.

## Constraints

- No new npm dependencies — use Node's built-in `crypto` module and the existing `express` dependency only.
- Only touch `server/index.js` and `tests/server.test.js`.
- `express.json()` is already mounted globally in `server/index.js` (`app.use(express.json())`); capturing the raw body requires either a `verify` callback on that middleware or an equivalent built-in mechanism — do not add a body-parsing library.
- Preserve existing routes (`/health`, `/items`, `/items/:id`) and existing test behavior unchanged.

## Out of Scope

- Persisting accepted event ids across process restarts (in-memory tracking is sufficient per the goal).
- Rate limiting, request logging, or other webhook hardening not named in the goal.
- Changes to `bin/cli.js`, `web/`, or other files not named in the goal.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "npm test", "expect_exit": 0 }
  ]
}
```
