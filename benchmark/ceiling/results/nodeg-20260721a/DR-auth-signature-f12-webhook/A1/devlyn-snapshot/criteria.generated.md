# Generated criteria — signed webhook endpoint

## Requirements

- Add `POST /webhook` to `server/index.js`. Compute a lowercase-hex HMAC-SHA256 over the exact raw request body bytes using the shared secret at `data/webhook-secret.txt`, and compare it to the `X-Signature` header with `crypto.timingSafeEqual`. A mismatch (or malformed/missing header) responds 401 `{ error: 'invalid_signature' }`.
- Signature check runs before body-shape validation: a body that fails shape validation but carries a valid signature over that body returns 400 (not 401); a body whose signature does not match returns 401 regardless of body shape.
- Validate body shape `{ id, type, timestamp, data }`: `id` and `type` must be non-empty strings, `timestamp` a number, `data` an object. A body that fails this shape (after signature passes) returns 400 `{ error: 'invalid_body' }`.
- Track accepted event `id`s in memory. First valid delivery of a given `id` returns 200 `{ accepted: true, id }`. Any subsequent delivery of that same `id` (valid signature) returns 409 `{ error: 'duplicate_event', id }` — the second body's contents are irrelevant to this check.
- Update `tests/server.test.js` so the existing `/health`, `/items`, `/items/:id` tests still pass, and add at least 3 new tests: happy path (200 accepted), replay of the same `id` (409), and tampered body with the original signature (401).

## Constraints

- Touch only `server/index.js` and `tests/server.test.js`. No new npm dependencies (`package.json` currently declares only `express`; use Node's built-in `crypto`).
- `server/index.js` currently mounts `app.use(express.json())` globally, which parses and discards the raw body — HMAC verification needs the exact raw bytes the sender signed. The webhook route must capture the raw body before/instead of the global JSON parser applies to it (e.g. a route-scoped raw body reader) rather than re-serializing `req.body`, since re-serialization is not guaranteed byte-identical to what the sender signed.
- Match the existing route style in `server/index.js` (`app.METHOD(path, handler)`, `res.status(...).json(...)`), and the existing test style in `tests/server.test.js` (`node:test` + `node:http`, no new test framework).
- Run tests with the existing `npm test` script (`node --test tests/`); do not add a test runner or assertion library.

## Out of Scope

- Any file other than `server/index.js` and `tests/server.test.js`.
- Persisting accepted ids beyond process memory (no database or filesystem changes).
- Changing `data/webhook-secret.txt` or `data/_sample-event.json`.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "npm test", "exit_code": 0 }
  ]
}
```
