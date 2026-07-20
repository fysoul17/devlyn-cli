---
complexity: medium
---

# Generated criteria — webhook signature endpoint

## Requirements

- Add `POST /webhook` to `server/index.js`. Verify the `X-Signature` request header (lowercase hex HMAC-SHA256 over the raw request body, keyed by the shared secret in `data/webhook-secret.txt`) using `crypto.timingSafeEqual`. A signature that does not match (including a header of the wrong length/format) responds `401` with `{ error: 'invalid_signature' }`.
- The signature check runs before body-shape validation. After the signature passes, validate the body is `{ id, type, timestamp, data }` with `id`/`type` non-empty strings, `timestamp` a number, and `data` an object. A body that fails this shape responds `400` with `{ error: 'invalid_body' }` — even when the signature is valid (bad body + valid sig = 400, not 401).
- Track accepted event `id`s. The first delivery of a given `id` (valid signature + valid body) responds `200` with `{ accepted: true, id }`. Any subsequent delivery of the same `id` responds `409` with `{ error: 'duplicate_event', id }` regardless of what the second body contains.
- Update `tests/server.test.js`: the three existing tests (`GET /health`, `GET /items`, `GET /items/:id`) must still pass. Add at least three new tests covering: happy path (valid signature + valid body → 200 accepted), replay of the same `id` → 409, and a tampered body with the original (now-stale) signature → 401.
- No new npm dependencies. Only `server/index.js` and `tests/server.test.js` change.

## Constraints

- Compute the HMAC over the exact raw request bytes, not a re-serialized/parsed body — re-serializing JSON can change byte-for-byte content (key order, whitespace) and break the signature check. `express.json()`'s default body parser discards the raw buffer, so the raw body must be captured (e.g. via the `verify` option) before JSON parsing.
- `crypto.timingSafeEqual` throws when the two buffers differ in length — a wrong-length/malformed `X-Signature` header must be handled explicitly (treated as a mismatch, not an uncaught exception / 500).
- Duplicate-id tracking is in-memory (module-level state), matching the existing `items` array pattern; no persistence layer exists in this project.
- Read `data/webhook-secret.txt` once (module load or lazily), consistent with the existing style (no config framework in this codebase).

## Out of Scope

- `web/index.html`, `bin/cli.js`, and existing `GET` routes — no behavior changes there.
- Rate limiting, retry backoff, or persistence of accepted ids across process restarts.
- Any new npm dependency.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "npm test",
      "exit_code": 0,
      "stdout_contains": ["# fail 0"],
      "stdout_not_contains": []
    }
  ]
}
```
