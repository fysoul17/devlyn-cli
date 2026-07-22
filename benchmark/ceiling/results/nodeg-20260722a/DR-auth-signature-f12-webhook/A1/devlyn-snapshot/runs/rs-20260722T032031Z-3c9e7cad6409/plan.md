# Plan — POST /webhook signature-verified endpoint

<!-- devlyn:authorized-surface -->
## 1. Files to touch

- `server/index.js` — **edit** — add `POST /webhook`: raw-body capture via `express.json()`'s existing `verify` hook (server/index.js:5, `app.use(express.json())`), secret load from `data/webhook-secret.txt`, HMAC-SHA256 signature check via `crypto.timingSafeEqual`, body-shape validation, in-memory duplicate-`id` tracking. Implements every bullet under criteria `## Requirements`.
- `tests/server.test.js` — **edit** — add a `post()` HTTP helper (mirrors the existing `get()` at tests/server.test.js:13) plus a signing helper (`crypto` + `fs`, reading `data/webhook-secret.txt`), and at least 3 new tests: (a) happy path → `200 { accepted: true, id }`, (b) replay same `id` twice → second delivery `409 { error: 'duplicate_event', id }`, (c) tampered body + stale signature → `401 { error: 'invalid_signature' }`. Keep the 3 existing tests (`GET /health`, `GET /items`, `GET /items/:id`) unmodified and passing. Implements criteria bullet "Update `tests/server.test.js` ... Add at least 3 new tests."

```json
{"authorized_surface": ["server/index.js", "tests/server.test.js"]}
```

## 2. Risks

**Out-of-scope expansions to refuse:**
- No changes to `/health`, `/items`, `/items/:id` (server/index.js:12-28).
- No changes to `data/webhook-secret.txt`, `data/_sample-event.json`, `package.json`, `package-lock.json`, or any file besides the two authorized paths.
- No new npm dependency — signing/reading in tests uses only `crypto` and `fs` (Node built-ins), same as the route.
- No persistence, rate limiting, logging, or retry logic — accepted-id tracking is a plain module-scoped `Set`, matching the existing `items` module-scoped array precedent (server/index.js:7).

**Ambiguous spec sections — locked interpretation, no re-litigating during IMPLEMENT:**
- Check order is fixed: signature (401) → body shape (400) → duplicate id (409) → accept (200, then record id). Per criteria: "Signature check runs first, before body-shape validation" and Assumptions: "Duplicate-id detection runs after both the signature check and the body-shape check succeed."
- `id`/`type`: `typeof x === 'string' && x.length > 0`. No trimming/whitespace-only rejection — not stated in criteria, would be unrequested validation.
- `timestamp`: `typeof timestamp === 'number' && Number.isFinite(timestamp)` — per Assumptions "(finite)"; NaN/Infinity rejected.
- `data`: `typeof data === 'object' && data !== null && !Array.isArray(data)` — per Assumptions, `{}` accepted, `null`/arrays/primitives rejected.
- Missing/malformed `X-Signature` header → `401 invalid_signature`, same code path as a mismatch (Assumptions bullet 3) — do not invent a third error shape.
- Duplicate check keys strictly on `id`; a duplicate delivery's `type`/`timestamp`/`data` are ignored once shape validation has passed (criteria bullet 13).

**Known failure modes for this language/framework:**
- `crypto.timingSafeEqual` throws `RangeError` on unequal-length buffers — guard `digestBuf.length === sigBuf.length` before calling it (Constraints, cited verbatim: "guard the length check before calling it so a short/long header value fails closed as `invalid_signature` rather than throwing").
- `Buffer.from(undefined, 'hex')` throws `TypeError` — guard for a missing/empty `X-Signature` header before converting to a Buffer, folding into the same 401 path.
- `express.json()`'s `verify` callback only fires when the request's `Content-Type` matches (default `application/json`); if it doesn't fire, `req.rawBody` is `undefined` and `crypto.createHmac(...).update(undefined)` would throw. Treat a missing `req.rawBody` as a signature failure (401) rather than letting it throw into Express's default error handler — this is a direct consequence of the signature-check-first requirement, not new scope.
- Reuse the single existing `app.use(express.json())` mount (server/index.js:5) by adding its `verify` option in place — do not add a second body-parser mount, which would double-consume the request stream.
- Read `data/webhook-secret.txt` once at module load into a module-scoped constant (mirrors the `items` array precedent), not per-request, to avoid redundant `fs` I/O — trimmed of trailing newline per Constraints.
- Build the secret file path via `__dirname` string concatenation rather than `require('path')` — Constraints names only `crypto` and `fs` as the built-ins in play for the route; avoid introducing an unlisted built-in when a one-line string join suffices.

## 3. Acceptance restatement

Verbatim copy of criteria `## Verification` block:

<!-- devlyn:verification -->
## Verification

```json
{"verification_commands": [{"cmd": "npm test", "description": "run full test suite (existing tests + new webhook tests: happy path, replay 409, tampered-body 401)"}]}
```
