# Plan — webhook signature verification endpoint

<!-- devlyn:authorized-surface -->
## Files to touch

- `server/index.js` — **edit**. Add `POST /webhook` route, HMAC signature verification, body-shape validation, and in-memory duplicate-id tracking (Requirements: criteria.generated.md lines 4–9). Currently (server/index.js:1-37) the file only requires `express`, mounts `app.use(express.json())` with no `verify` option (server/index.js:5), and defines `/health`, `/items`, `/items/:id`. No `crypto`, `fs`, or `path` requires exist yet — all three are Node built-ins, so adding them is not a new dependency.
- `tests/server.test.js` — **edit**. Add a raw-body-aware `post()` helper (the existing file only has a `get()` helper for GET requests — tests/server.test.js:13-24 — there is no way to send a POST with a custom header and exact raw bytes today) and at least 3 new `test()` blocks: happy path (200), replay of the same `id` (409), tampered body with the original signature (401). Existing 3 tests (tests/server.test.js:26-58) are left byte-for-byte unchanged.

```json
{"authorized_surface": ["server/index.js", "tests/server.test.js"]}
```

## Risks

**Out-of-scope expansions to refuse:**
- No changes to `/health`, `/items`, `/items/:id`, `bin/cli.js`, or `package.json` (criteria.generated.md Out of Scope). The one shared line that must change is `app.use(express.json())` (server/index.js:5) — adding a `verify` callback there to capture raw bytes onto `req.rawBody`. This does not alter parsed-body behavior for the three existing GET routes (none of them read `req.rawBody`), so it does not count as "changing" those routes.
- No new npm dependency, no `package.json` edit — `crypto`, `fs`, `path` are Node built-ins already available (Node ≥18 per `package.json` `engines`, confirmed running v20.19.0 locally).
- No id-persistence across restarts (module-level `Set`/array only, matching the existing `items` array pattern at server/index.js:7-10).
- No admin/reset endpoint for the dedup store, no GET `/webhook` — not asked for; tests will avoid cross-test id collisions by using unique ids per test instead of adding a reset mechanism.

**Ambiguous spec sections — strict interpretation decisions:**
- **Only a 200-accepted delivery marks an id "seen."** Order in the handler is: verify signature (401 on failure) → validate shape (400 on failure) → dedup check/insert (409 or 200). An id that previously failed shape validation (400) was never inserted, so a later valid delivery of that same id is still a fresh 200 — this is the only reading consistent with "after accepting an id" in the requirement (criteria.generated.md line 8: "Track accepted event ids... After the signature passes, validate the body shape... Track accepted event ids").
- **Missing/absent `X-Signature` header → 401 `invalid_signature`**, not a separate error shape — criteria.generated.md line 5 groups "missing/malformed/mismatched" under the same 401 response.
- **Malformed (non-parseable) JSON body is out of scope for custom handling.** `express.json()`'s `verify` callback fires before `JSON.parse`, so raw bytes are captured even when the body is syntactically invalid JSON, but Express's own body-parser then calls `next(err)` on a `SyntaxError` before our route handler runs, producing Express's default error response. None of the 3 mandated tests exercise this path and criteria.generated.md does not mention it; adding custom JSON-parse-error middleware would be speculative robustness beyond the ask, so it is deliberately left as Express default behavior.
- **`req.rawBody` fallback to `Buffer.alloc(0)` if somehow undefined** (e.g. a request without `Content-Type: application/json`, which body-parser doesn't run `verify` for). Without this guard, `crypto.createHmac(...).update(undefined)` throws a `TypeError` → uncaught exception → 500. The criteria explicitly names "not an uncaught exception (500)" as the wrong outcome for a related edge case (buffer-length mismatch, line 15); this one-line fallback generalizes that same explicit acceptance requirement to keep the whole signature-verification path exception-free, not an invented feature.
- **Test module state persists across the whole test file.** `tests/server.test.js` does `require('../server')` once at file load, so the module-level dedup `Set` inside `server/index.js` is shared by every `test()` block in the run — same pattern the existing `items` array already relies on. New tests must use ids not reused elsewhere in the file (e.g. `evt_happy_1`, `evt_replay_1`, `evt_tamper_1`); no reset hook will be added since that's unrequested infrastructure.

**Known failure modes for Node/Express in this exact task:**
- `crypto.timingSafeEqual` throws `RangeError` on unequal-length buffers — guard by comparing `Buffer.byteLength` (or `.length`) of the computed vs. provided signature buffers first; treat any mismatch as invalid (401), never let it throw (criteria.generated.md line 15, verbatim).
- `Buffer.from(hexString, 'hex')` silently truncates at the first invalid hex character instead of throwing, so a malformed `X-Signature` value could decode to a shorter buffer — the length guard above must run on the *decoded buffer lengths*, not on the raw header string length, so a truncated decode is caught as a length mismatch rather than accidentally passing to `timingSafeEqual` on matching-length garbage.
- Express lowercases incoming header names, so the header must be read as `req.headers['x-signature']`.
- `crypto.createHmac('sha256', secret).digest('hex')` already yields lowercase hex; `Buffer.from(hex, 'hex')` hex-decoding is case-insensitive regardless, so no extra case-normalization step is needed even though the provider is documented to send lowercase.
- Secret file `data/webhook-secret.txt` is 30 bytes with **no trailing newline** (confirmed via `od -c` and `wc -c`), holding `wh_test_secret_a3f9e1c2_d4b6e7`. Still apply `.replace(/\r?\n$/, '')` on read per the constraint's general instruction ("strip any trailing newline consistent with how the file is stored on disk") rather than hardcoding "no strip needed" — this keeps the code correct if the file is ever re-saved with a trailing newline, without over-trimming (no `.trim()`, which would also strip meaningful leading/interior whitespace that isn't part of the stated constraint).

## Acceptance restatement

Verbatim from `.devlyn/criteria.generated.md`:

## Verification

````json
{
  "verification_commands": [
    { "cmd": "node --test tests/", "exit_code": 0 }
  ]
}
````
</content>
