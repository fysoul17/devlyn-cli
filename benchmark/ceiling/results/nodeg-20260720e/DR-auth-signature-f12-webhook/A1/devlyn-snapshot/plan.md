# Plan — webhook signature + replay endpoint

<!-- devlyn:authorized-surface -->
## Files to touch

- `server/index.js` — edit — add `POST /webhook`: mount `express.json({ verify })` to capture raw request-body bytes (Req 1), compute `HMAC-SHA256` over those raw bytes using the secret from `data/webhook-secret.txt` and compare via `crypto.timingSafeEqual` with a pre-check length guard (Req 2), validate parsed body shape only after signature success (Req 3), and track accepted `id`s in a module-scoped in-memory `Set` for replay detection (Req 4).
- `tests/server.test.js` — edit — add 3 new tests (happy-path 200, replay 409, tampered-body 401) that compute real HMAC-SHA256 signatures against `data/webhook-secret.txt` over the literal raw bytes sent, the same way the implementation does; keep the 3 existing tests unmodified (Req 5).

```json
{"authorized_surface": ["server/index.js", "tests/server.test.js"]}
```

## Risks

- **Raw-body capture with `express.json()` already mounted.** `server/index.js:5` currently has `app.use(express.json())` with no options. The built-in mechanism named by the constraint is the `verify` callback: `express.json({ verify: (req, _res, buf) => { req.rawBody = buf; } })`. This replaces the existing `app.use(express.json())` line in place (same middleware, same position) — not a second body parser, so `/items`/`/items/:id` behavior is unaffected. `verify` only fires when Content-Type matches `application/json` *and* a body is present; a bodyless POST to `/webhook` would leave `req.rawBody` `undefined`, and `crypto.createHmac(...).update(undefined)` throws. Guard with `const rawBody = req.rawBody || Buffer.alloc(0);` before hashing — this is a one-line guard against a real, always-reachable input (any client can POST with no body), not speculative robustness for an unreachable case.
- **`timingSafeEqual` length-mismatch throw.** Per Req 2, build both sides as `Buffer.from(str, 'utf8')` (the hex digest string and the raw `X-Signature` header value, defaulted to `''` when the header is absent), compare `.length` first, and only call `crypto.timingSafeEqual` when lengths are equal; a length mismatch (including a missing header, whose buffer has length 0) is itself an "invalid_signature" result, never an uncaught throw. The length check happening before the constant-time compare is the standard, documented use of this API — not a new attack surface, since the digest length space is fixed (64 hex chars) and an attacker gains nothing from probing header length against a fixed target.
- **Ordering.** Handler must short-circuit with `return` after each response so a later check is never reached once an earlier one has already responded: signature check (401) → body-shape check (400) → replay check (409) → accept (200). Body-shape validation (`id`/`type` non-empty strings, `timestamp` number, `data` a non-null, non-array object) must not run before the signature is confirmed valid, per Req 3 — this also means a shape-invalid body with a *bad* signature must still return 401, not 400.
- **Exact response contracts (Req 2/3/4).** No extra fields, no renamed keys: `401 { error: 'invalid_signature' }`, `400 { error: 'invalid_body' }`, `409 { error: 'duplicate_event', id }`, `200 { accepted: true, id }`. Matches the existing literal-body style already used at `server/index.js:24` (`{ error: 'not_found', id }`).
- **Secret loading.** `data/webhook-secret.txt` currently has no trailing newline (verified with `xxd`), but reading it with `fs.readFileSync(..., 'utf8').trim()` is the standard, low-cost way to load a text-file secret and avoids a silent signature mismatch if the file is ever re-saved with a trailing newline — this is not scope creep, it is the same file being read for its one stated purpose (Req 2).
- **Replay-tracking data structure.** Req 4 says "consistent with the existing in-memory `items` pattern," meaning module-scoped, in-memory, no persistence — it does not mandate the same `Array` shape. A `Set<string>` is used for O(1) membership/insert, which is the idiomatic structure for an id-membership check; `items` is a array of records, a different shape for a different purpose, so there's no existing pattern being contradicted.
- **Out of scope, refused:** no rate limiting, no persistence across restarts, no changes to `bin/cli.js` or `web/`, no new npm dependency (only `node:crypto`, already-present `node:fs`/`node:path`, and the existing `express` are used).
- **Test isolation.** `tests/server.test.js` tests in one file share one `require('../server')` module instance (Node's test runner caches requires within a process), so the new webhook tests must use distinct `id` values per test (e.g. `evt_test_1`, `evt_test_2`, `evt_test_3`) to avoid an unintended 409 from cross-test replay-state leakage — this mirrors how the existing tests already share `items` state safely by only reading it.
- **Scope discipline.** Req 5 names exactly three new tests (happy path 200, replay 409, tampered-signature 401). No additional tests (e.g. missing-header, invalid-body-shape) will be added — "at least 3" is satisfied by the 3 named cases; adding more is unrequested scope per Goal-locked discipline.

## Acceptance restatement

```json
{
  "verification_commands": [
    { "cmd": "npm test", "expect_exit": 0 }
  ]
}
```
