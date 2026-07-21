# Generated criteria (free-form, large)

recommend: /devlyn:ideate first — this goal was classified `large` (12 file/symbol scope signals) and resolved via a best-effort generated spec rather than an elicited one.

## Requirements

- Add `POST /webhook` to `server/index.js`.
- Verify the `X-Signature` request header: lowercase hex HMAC-SHA256 over the raw request body bytes, keyed with the shared secret stored at `data/webhook-secret.txt`, compared with `crypto.timingSafeEqual`. On mismatch, respond `401` with JSON body `{ error: 'invalid_signature' }`.
- Validate body shape `{ id, type, timestamp, data }`: `id` and `type` must be non-empty strings, `timestamp` must be a number, `data` must be an object. On shape failure, respond `400` with JSON body `{ error: 'invalid_body' }`. Signature verification always runs first — a bad body with a valid signature is `400`, not `401`; a bad signature (regardless of body shape) is `401`.
- Track accepted `id`s. The first delivery of a given `id` (signature valid, body valid) responds `200` with `{ accepted: true, id }`. Any subsequent delivery of that same `id` responds `409` with `{ error: 'duplicate_event', id }` — the second delivery's body is not re-validated for shape once the id is already known to be a duplicate. (Per the goal: "the second body is irrelevant.")
- Update `tests/server.test.js` so all pre-existing tests continue to pass, and add at least three new tests: (1) happy-path `POST /webhook` accepted, (2) replaying the same `id` returns `409`, (3) a tampered body sent with the original (now-stale) signature returns `401`.
- Touch only `server/index.js` and `tests/server.test.js`. No new npm dependencies — use Node's built-in `crypto`/`fs` and the existing `express`.

## Assumptions

- Raw-body capture: `express.json()` by default discards the raw bytes after parsing, but HMAC verification must run over the exact bytes the provider signed. Assumption: use `express.json({ verify: (req, _res, buf) => { req.rawBody = buf; } })` (or an equivalent raw-capture technique) scoped to this route/app only — narrower and reversible, no new dependency.
- Secret loading: read `data/webhook-secret.txt` via `fs.readFileSync(..., 'utf8')`, trimming only a trailing newline if present (the current file has none). Read once at module load, not per-request — narrower than re-reading on every call, reversible if a future requirement needs hot-reload.
- Duplicate tracking store: an in-memory `Set` (or `Map`) of accepted `id`s scoped to the running process. Assumption: no cross-restart persistence requirement was stated, so in-memory is sufficient and is the narrowest option; reversible if durability is later required.
- Signature comparison safety: hex-decode both the computed and provided signatures to `Buffer`s before `crypto.timingSafeEqual`; if lengths differ (e.g. malformed header), treat as `invalid_signature` (401) rather than letting `timingSafeEqual` throw on a length mismatch.
- Route scope: `express.json()`'s raw-capture change must not alter behavior of the existing `/health`, `/items`, `/items/:id` GET routes (they carry no body).

## Out of Scope

- Any endpoint, middleware, or file other than `server/index.js` and `tests/server.test.js`.
- Persistence of accepted-id state across process restarts.
- Rate limiting, request logging, or other webhook-adjacent hardening not named in the goal.
- Changes to `data/webhook-secret.txt` or `data/_sample-event.json`.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "npm test", "exit_code": 0 }
  ]
}
```
