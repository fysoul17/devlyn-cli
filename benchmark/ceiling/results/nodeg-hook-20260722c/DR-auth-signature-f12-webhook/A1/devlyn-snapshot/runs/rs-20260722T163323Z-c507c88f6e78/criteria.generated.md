# Generated criteria — webhook signature verification endpoint

## Requirements
- Add `POST /webhook` to `server/index.js`.
- Verify the `X-Signature` request header: lowercase hex HMAC-SHA256 over the raw request body bytes, keyed with the shared secret stored at `data/webhook-secret.txt`, compared using `crypto.timingSafeEqual`. A missing/malformed/mismatched signature returns 401 with body `{ error: 'invalid_signature' }`.
- Signature verification runs before body-shape validation (a bad body with a valid signature is 400, not 401; a bad signature is 401 even if the body shape is also invalid).
- After the signature passes, validate the body shape: `id` and `type` must be non-empty strings, `timestamp` must be a number, `data` must be an object. A body that fails this shape returns 400 with `{ error: 'invalid_body' }`.
- Track accepted event `id`s server-side. The first accepted delivery of a given `id` returns 200 with `{ accepted: true, id }`. Any subsequent delivery carrying the same `id` (regardless of the second body's contents) returns 409 with `{ error: 'duplicate_event', id }`.
- No new npm dependencies. Only `server/index.js` and `tests/server.test.js` may be touched.
- Update `tests/server.test.js` so existing tests still pass, and add at least three new tests: happy path (200 + accepted), replay of the same `id` (409), tampered body with the original signature (401).

## Constraints
- `server/index.js` already mounts `express.json()` globally, which by default discards the raw body bytes. The HMAC must be computed over the exact bytes the provider signed, not a re-serialization of the parsed JSON (key order / whitespace can differ byte-for-byte). Capture the raw body via `express.json()`'s `verify` callback (or an equivalent raw-body capture scoped to this route) rather than re-stringifying `req.body`.
- Use Node's built-in `crypto` module only (`createHmac`, `timingSafeEqual`) — no new dependency.
- `crypto.timingSafeEqual` throws on unequal-length buffers; guard the length before calling it so a length mismatch resolves to "signature invalid" (401), not an uncaught exception (500).
- Read the secret from `data/webhook-secret.txt` each time (or once at startup); strip any trailing newline consistent with how the file is stored on disk.
- Duplicate-id tracking is in-memory (module-level state), matching the existing in-memory `items` array pattern already in `server/index.js`.

## Out of Scope
- Persisting accepted-event ids across process restarts.
- Any change to `/health`, `/items`, `/items/:id`, or `bin/cli.js`.
- New npm dependencies or `package.json` changes.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "node --test tests/", "exit_code": 0 }
  ]
}
```
