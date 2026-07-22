# Generated criteria — POST /webhook signature-verified endpoint

recommend: /devlyn:ideate first (large complexity, best-effort spec synthesized from free-form goal; review `## Assumptions` before trusting scope)

## Requirements

- Add a `POST /webhook` route to `server/index.js`.
- Capture the exact raw request-body bytes (not the Express-parsed/re-serialized object) so the HMAC is computed over precisely what the client sent.
- Read the shared secret from `data/webhook-secret.txt` and compute `HMAC-SHA256` over the raw body, hex-encoded (lowercase — Node's `.digest('hex')` is already lowercase).
- Compare the computed digest to the request's `X-Signature` header using `crypto.timingSafeEqual`; a length mismatch between the two must not throw and must be treated as a signature failure.
- Signature check runs first, before body-shape validation. Mismatch → `401` with exactly `{ error: 'invalid_signature' }`.
- After the signature passes, validate body shape: `{ id, type, timestamp, data }` where `id` and `type` are non-empty strings, `timestamp` is a number, and `data` is an object. Invalid shape → `400` with exactly `{ error: 'invalid_body' }`. A bad body with a valid signature is `400`, not `401`.
- Track accepted event `id`s across requests. After an `id` has been accepted once, any later delivery of that same `id` → `409` with exactly `{ error: 'duplicate_event', id }` — the second request's `type`/`timestamp`/`data` do not affect this outcome.
- First valid, non-duplicate delivery → `200` with exactly `{ accepted: true, id }`, and the `id` is then recorded as accepted.
- No new npm dependencies; use only Node built-ins (`crypto`, `fs`) and the already-present `express`.
- Touch only `server/index.js` and `tests/server.test.js`.
- Update `tests/server.test.js`: the 3 existing tests (`GET /health`, `GET /items`, `GET /items/:id`) must keep passing. Add at least 3 new tests: (a) happy path — valid signature + valid body → `200 { accepted: true, id }`; (b) replay — same `id` delivered twice → second delivery → `409 { error: 'duplicate_event', id }`; (c) tampered body with the original (now-stale) signature → `401 { error: 'invalid_signature' }`.

## Constraints

- Raw-body capture: use `express.json()`'s `verify` option (e.g. stash the raw `Buffer` on the request during parsing) — `express.json()` is already mounted ahead of any new route and replaces the body stream, so this is the idiomatic way to keep both the parsed body and the exact bytes.
- Read `data/webhook-secret.txt` via `fs`, trimmed of a trailing newline.
- Accepted-id tracking is in-memory (e.g. a module-scoped `Set`), scoped to the running process — no persistence layer exists in this repo and none may be added (no new deps, no new files).
- `crypto.timingSafeEqual` requires equal-length `Buffer`s — guard the length check before calling it so a short/long header value fails closed as `invalid_signature` rather than throwing.

## Out of Scope

- Any change to the existing `/health`, `/items`, `/items/:id` routes.
- Any change to `data/webhook-secret.txt`, `data/_sample-event.json`, `package.json`, `package-lock.json`, or any file other than `server/index.js` and `tests/server.test.js`.
- Persistence, rate limiting, logging, retries, or any other provider-side concern not named in the goal.

## Assumptions

- `data` must be a plain JSON object per the goal's `data is an object` — `null`, arrays, and non-object primitives are rejected as `invalid_body`; `{}` (empty object) is accepted.
- Duplicate-id detection runs after both the signature check and the body-shape check succeed: the shape check is what establishes a trustworthy `id` to key the duplicate-check on, and only then does "the second body is irrelevant" apply (i.e. a duplicate delivery with an otherwise-malformed body is not specified by the goal and is out of scope for this run).
- A missing or malformed `X-Signature` header is treated the same as a mismatched one (`401 invalid_signature`) — the goal defines only `invalid_signature` and `invalid_body` as failure shapes, with no third error class for a missing header.
- `timestamp` only needs to satisfy `typeof timestamp === 'number'` (finite) — no freshness/staleness window is implied by the goal text.

<!-- devlyn:verification -->
## Verification

```json
{"verification_commands": [{"cmd": "npm test", "description": "run full test suite (existing tests + new webhook tests: happy path, replay 409, tampered-body 401)"}]}
```
