# Plan — POST /webhook signature-verified event intake

Source: `.devlyn/criteria.generated.md` (generated criteria, free-form mode, complexity medium)
Base ref: `d5e479312b6f9573373bd2057e630bba7d22c608` (branch `master`)

<!-- devlyn:authorized-surface -->
## 1. Files to touch

| Path | Change | Rationale |
|---|---|---|
| `server/index.js` | edit | Add `POST /webhook`: capture raw request bytes via `express.json({ verify })`, load+trim the shared secret from `data/webhook-secret.txt` once at module load, verify `X-Signature` with `crypto.createHmac`/`crypto.timingSafeEqual` (Requirement 1), validate body shape `{id,type,timestamp,data}` after signature passes (Requirement 2), track accepted `id`s in an in-memory `Set` for dedup → 409 on replay (Requirement 3, 409 result). |
| `tests/server.test.js` | edit | Add a `post()` helper (existing `get()` is GET-only per `tests/server.test.js:13-24`) that can set `X-Signature`/`Content-Type` headers and a JSON body, plus ≥3 new tests: happy path → 200, replay same `id` → 409, tampered body with original signature → 401 (Verification block). Existing 3 tests (`server.test.js:26-58`) stay unmodified. |

```json
{"authorized_surface": ["server/index.js", "tests/server.test.js"]}
```

## 2. Risks

**Refuse (out of scope per criteria):**
- No persistence for the accepted-id set — in-memory `Set`, process lifetime only (criteria "Out of Scope" line 25). Do not add a file/db-backed store "for durability."
- No new npm dependency, no `package.json` edit (criteria line 23) — `crypto`, `fs`, `path` are Node built-ins already implicitly available; no `require`-time addition needed.
- No files touched besides `server/index.js` and `tests/server.test.js` (criteria line 24) — do not touch `data/webhook-secret.txt`, `package.json`, or add new test/helper files.
- No handling added for malformed-JSON bodies (body-parser `SyntaxError` → Express default 500 handler) — this is pre-existing behavior of the already-mounted `express.json()` (`server/index.js:5`) for every route, not something this task's Requirements ask to change, and it is not in the required test list. Do not add an error-handling middleware "just in case."
- No signature-header case-normalization logic needed beyond what Express already gives: `req.get('X-Signature')` is case-insensitive by construction (standard Express API) — do not hand-roll header lookup.

**Ambiguities resolved strictly against the criteria text:**
- Check order is fixed: signature → body-shape → duplicate. Criteria line 8 pins signature-before-shape explicitly ("sig check still runs first"); criteria line 9's phrasing "as long as it independently reaches the duplicate check — i.e. passes signature and shape validation for its own request" pins duplicate-check after shape validation. Implementation must not reorder for convenience.
- Duplicate check keys only on `id` — "the second delivery's body content beyond `id` is irrelevant" (criteria line 9). The dedup `Set` stores accepted `id` strings only; it does not compare or store the rest of the payload.
- Secret loading: read `data/webhook-secret.txt` once at module load (`fs.readFileSync(..., 'utf8').trim()`), not per-request — file is static, "no trailing-newline handling assumptions" (criteria line 18) means trim, not that the file changes at runtime.
- `data` shape check: "must be an object" is interpreted as non-null, non-array `typeof === 'object'` — arrays and `null` are technically `typeof 'object'` in JS but are not "an object" in the shape-contract sense; reject both as `invalid_body`.

**Known failure modes for this stack (Express 4.19.2 / Node `crypto`):**
- `crypto.timingSafeEqual` throws `RangeError` on unequal-length buffers instead of returning `false` — the malformed/short/missing-header case (criteria line 17) must be short-circuited with an explicit length check *before* calling `timingSafeEqual`, never inside a try/catch used as flow control (no silent catch, per repo's no-workaround rule).
- `Buffer.from(headerValue, 'hex')` does not throw on invalid hex characters — it silently stops decoding at the first invalid nibble, producing a shorter-than-expected buffer. Relying on a thrown exception to catch malformed headers would miss this; the explicit length-equality check against the computed 32-byte HMAC digest covers it correctly.
- Re-serializing `req.body` with `JSON.stringify` before hashing is not guaranteed byte-identical to what the client sent (key ordering is generally stable in V8 for string keys but whitespace/number formatting is not preserved) — `server/index.js:5`'s `express.json()` must gain a `verify: (req, res, buf) => { req.rawBody = buf; }` option so the HMAC is computed over the exact received `Buffer`, not a re-encoded string.
- `express.json()`'s `verify` callback only fires when `Content-Type` matches `application/json` (its default `type` option) — new tests must set that header explicitly via the new `post()` helper or `req.rawBody` will be `undefined` and every signature check will fail.

## 3. Acceptance restatement

Verbatim from `.devlyn/criteria.generated.md` `## Verification`:

> - `npm test` (runs `node --test tests/`) must pass, including the 3 existing tests plus at least 3 new tests: happy path (valid signature + valid body → 200 `{ accepted: true, id }`), replay of the same `id` → 409 `{ error: 'duplicate_event', id }`, tampered body with the original signature → 401 `{ error: 'invalid_signature' }`.
