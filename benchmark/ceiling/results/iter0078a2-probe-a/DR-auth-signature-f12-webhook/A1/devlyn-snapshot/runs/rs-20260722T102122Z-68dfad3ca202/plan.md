# Plan — POST /webhook signature verification + replay protection

<!-- devlyn:authorized-surface -->
## Files to touch

- `server/index.js` — edit — add `POST /webhook`: HMAC-SHA256 signature verification over the raw request body (Requirement 1), signature-before-shape ordering (Requirement 2), body-shape validation (Requirement 3), in-memory accepted-id replay tracking (Requirement 4). Also edit the existing `app.use(express.json())` call in place (add a `verify` callback) to capture the raw body bytes needed for HMAC — this is the only change to existing code; `GET /health`, `GET /items`, `GET /items/:id` are otherwise untouched.
- `tests/server.test.js` — edit — add a POST helper + three new tests: happy path 200, replayed id 409, tampered body with original signature 401 (Requirement 5). The three existing GET tests are left byte-for-byte unchanged.

```json
{"authorized_surface": ["server/index.js", "tests/server.test.js"]}
```

## Risks

**Out-of-scope work to refuse (per Constraints/Out of Scope):**
- No edits to `bin/cli.js`, `scripts/lint-json.js`, `web/`, or `data/_sample-event.json`.
- No new npm dependency — only Node's built-in `crypto` (and `fs`/`path`, already-built-in, to load the secret file), matching the existing require style in `server/index.js`.
- No persistence for accepted ids beyond an in-process `Set` — no file/DB-backed store.
- No signature/replay logic added to any route other than `POST /webhook`.

**Ambiguous spec points, resolved:**
1. **Check order is signature → body-shape → duplicate-id.** The duplicate check needs a valid `id` string to key off of, so shape must be validated before duplicate tracking runs; this is the only order consistent with Requirement 2 ("signature check runs before body-shape validation") and Requirement 4 ("regardless of the second request's body content" — i.e. duplicate detection is a business-logic step that runs after auth + structural checks pass, not before).
2. **`timestamp` shape check is `typeof timestamp === 'number'` only.** The spec says "a number" — not adding `Number.isFinite`/NaN-rejection since that's unrequested extra validation (avoid speculative robustness).
3. **Signature well-formedness = `/^[0-9a-f]{64}$/`.** Spec requires "lowercase hex HMAC-SHA256"; a header that's missing, non-string, wrong length, or contains uppercase/non-hex characters is "malformed" per the spec's own wording and short-circuits to `401 {error:'invalid_signature'}` without calling `crypto.timingSafeEqual`. Since a SHA-256 hex digest is always exactly 64 lowercase-hex characters, this regex pre-filter also guarantees the provided and expected buffers are always equal-length by the time `timingSafeEqual` is called — `timingSafeEqual` throws (does not return false) on length mismatch, so this ordering is load-bearing, not stylistic.
4. **Secret is read once at module load via `fs.readFileSync(...).trim()`.** Verified via `xxd data/webhook-secret.txt`: file is exactly 30 bytes with no trailing newline today, so `.trim()` is a no-op now — but it removes a class of "every signature check silently fails because someone's editor appended a trailing newline" bug for free. One line, standard practice for secret/config files, not a new abstraction.
5. **Test additions are exactly the three cases Requirement 5 names** (happy path 200, replay 409, tampered-body-same-signature 401) plus the minimal POST/signing helper needed to write them. No speculative extra cases (missing header, invalid shape, etc.) — not requested by the criteria.
6. **Malformed (syntactically-invalid) JSON body is left to Express's existing default behavior** (its own error path, not our JSON error shapes). This is pre-existing `express.json()`/body-parser behavior on every JSON route, not something this change introduces, and the criteria only specifies behavior for missing/malformed signature headers and structurally-shaped-but-wrong bodies — handling raw JSON-parse failures specially would be unrequested scope expansion.
7. **Test isolation via distinct ids.** `server/index.js` is `require`'d once by the test file, so the module-level accepted-id `Set` persists across all tests in that file (only the HTTP server per test is fresh). Each new test must use its own distinct `id` so tests can't accidentally collide on replay state.

**Known failure modes to avoid:**
- Adding a second/parallel body-parsing layer instead of adding `verify` to the existing `express.json()` call — would either lose raw-byte access or double-parse the body. Fix is a single-line edit to the existing middleware call.
- Calling `crypto.timingSafeEqual` before guaranteeing equal-length buffers (see point 3) — throws `ERR_CRYPTO_TIMING_SAFE_EQUAL_LENGTH` instead of just failing the check.
- In the new test POST helper: build the JSON body string once and reuse that exact string both for computing the test's own HMAC and for the request body — re-serializing (e.g. calling `JSON.stringify` twice, or parsing-then-restringifying) can change byte-for-byte content (key order/whitespace) and desync the signature from what's actually sent, per Constraints' explicit warning.

## Acceptance restatement

Verbatim from `.devlyn/criteria.generated.md`:

```json
{
  "verification_commands": [
    { "cmd": "node --test tests/", "expect_exit": 0 }
  ]
}
```
