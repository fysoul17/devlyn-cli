# Generated criteria — free-form goal (medium)

Source: `.devlyn/goal.raw.txt` (sha256 58e149bd9cbe6be89e214600420416b3ba17ecd83c523dd6d1d787b1cf1900e3)

## Requirements

- Add `POST /webhook` to `server/index.js`. Requests carry an `X-Signature` header: lowercase hex HMAC-SHA256 over the raw request body, keyed with the shared secret in `data/webhook-secret.txt`. Compute the same HMAC server-side and compare with `crypto.timingSafeEqual`; on mismatch (or missing/malformed header) respond `401` with `{ error: 'invalid_signature' }`.
- Signature check runs before body-shape validation. After signature passes, validate body shape `{ id, type, timestamp, data }`: `id` and `type` must be non-empty strings, `timestamp` must be a number, `data` must be an object. On shape failure respond `400` with `{ error: 'invalid_body' }` — this applies even when the signature is valid (bad body + valid sig = 400, not 401).
- Track accepted event `id`s across requests. First valid delivery of a given `id` returns `200` with `{ accepted: true, id }` and records the `id` as seen. Any later delivery of the same `id` (regardless of body/signature over that later payload, as long as it independently reaches the duplicate check — i.e. passes signature and shape validation for its own request) returns `409` with `{ error: 'duplicate_event', id }`; the second delivery's body content beyond `id` is irrelevant to the response.
- Use Node's built-in `crypto` module (`crypto.timingSafeEqual` for the signature comparison, `crypto.createHmac('sha256', secret)` for computing it). No new npm dependencies.
- Only `server/index.js` and `tests/server.test.js` are touched.

## Constraints

- Existing routes (`GET /health`, `GET /items`, `GET /items/:id`) and their current tests must keep passing unmodified in behavior.
- `express.json()` is already mounted; HMAC must be computed over the exact raw request bytes, so the route needs access to the raw body (e.g. a raw-body-capturing JSON parser option) rather than `JSON.stringify`'ing the parsed object, since re-stringification is not guaranteed byte-identical to what the sender signed.
- `crypto.timingSafeEqual` requires equal-length buffers; a length mismatch (e.g. malformed/short header) must be handled as a signature failure (401), not a thrown/uncaught exception.
- Secret is read from `data/webhook-secret.txt` (already present in the repo, single line, no trailing-newline handling assumptions — trim if needed).
- Existing test helper `get()` in `tests/server.test.js` only issues GET requests; a POST helper (with custom headers/body) is needed for the new tests.

## Out of Scope

- No new npm dependencies or changes to `package.json`.
- No changes to files other than `server/index.js` and `tests/server.test.js`.
- No persistence of accepted-id state beyond process memory (in-memory dedup set is sufficient; no goal-stated requirement for durability across restarts).

<!-- devlyn:verification -->
## Verification

- `npm test` (runs `node --test tests/`) must pass, including the 3 existing tests plus at least 3 new tests: happy path (valid signature + valid body → 200 `{ accepted: true, id }`), replay of the same `id` → 409 `{ error: 'duplicate_event', id }`, tampered body with the original signature → 401 `{ error: 'invalid_signature' }`.

```json
{"verification_commands": [{"cmd": "npm test", "exit_code": 0}]}
```
