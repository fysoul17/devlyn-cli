# Generated criteria (free-form, medium complexity)

## Requirements

- Add `POST /webhook` to `server/index.js` that verifies an `X-Signature` header: lowercase hex HMAC-SHA256 over the exact raw request body, computed with the shared secret in `data/webhook-secret.txt`, compared via `crypto.timingSafeEqual`. Mismatch (or malformed/missing header) responds `401` with `{ error: 'invalid_signature' }`.
- Signature check runs before body-shape validation: an invalid body with a valid signature is `400`; any body (valid or invalid) with an invalid signature is `401`.
- Validate body shape `{ id, type, timestamp, data }`: `id` and `type` non-empty strings, `timestamp` a number, `data` an object. Shape failure (after signature passes) responds `400` with `{ error: 'invalid_body' }`.
- Track accepted event `id`s in memory. First delivery of a given `id` responds `200` with `{ accepted: true, id }` and records the id as accepted. Any subsequent delivery of the same `id` responds `409` with `{ error: 'duplicate_event', id }`, regardless of the second request's body content.
- Update `tests/server.test.js`: keep existing GET tests passing, and add tests for happy path (200), replayed id (409), and tampered body with the original signature (401).

## Constraints

- No new npm dependencies — use Node's built-in `crypto` module only.
- Only touch `server/index.js` and `tests/server.test.js`.
- HMAC must be computed over the exact raw bytes of the request body as received, not a re-serialization of parsed JSON (key order / whitespace would change the byte sequence and break signature verification). `express.json()`'s default parsing discards the raw bytes, so the route needs access to the raw body via a `verify` callback or a dedicated raw-body reader ahead of JSON parsing.
- Existing routes (`GET /health`, `GET /items`, `GET /items/:id`) must keep working unchanged.

## Out of Scope

- Any change to `bin/cli.js`, `scripts/lint-json.js`, `web/`, or `data/_sample-event.json`.
- Persisting accepted ids beyond process memory (no database/file-backed idempotency store).
- Signature/replay logic for any route other than `POST /webhook`.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "node --test tests/", "expect_exit": 0 }
  ]
}
```
