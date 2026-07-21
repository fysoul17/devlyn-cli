# Plan — signed webhook endpoint

<!-- devlyn:authorized-surface -->
## Files to touch

- `server/index.js` (edit) — insert a route-scoped `express.raw({ type: '*/*' })` middleware for `/webhook`, mounted before the existing global `app.use(express.json())` (server/index.js:5), plus a new `app.post('/webhook', ...)` handler implementing HMAC-SHA256 verification, shape validation, and in-memory replay dedup. Satisfies Requirements 1–4.
- `tests/server.test.js` (edit) — add an HTTP POST helper (mirroring the existing `get()` helper at tests/server.test.js:13-24) and 3 new `test()` blocks: happy path (200), replay (409), tampered body (401). Satisfies Requirement 5.

```json
{"authorized_surface": ["server/index.js", "tests/server.test.js"]}
```

## Risks

**Out-of-scope expansions to refuse**
- No new files, no `package.json` changes, no touching `data/webhook-secret.txt` or `data/_sample-event.json` (Out of Scope, criteria.generated.md:20-22).
- Requirement 5 names exactly 3 test scenarios ("at least 3": happy path/replay/tampered). A 4th test covering the `400 invalid_body` shape-failure path (described in Requirement 3, criteria.generated.md:7) is tempting for completeness but is not named in Requirement 5 and not required by the `npm test` verification gate. Decision: ship exactly the 3 named tests; do not add a 4th under "for completeness" — that is the exact rationalization the harness contract forbids (CLAUDE.md Anti-rationalization clause). If VERIFY flags missing 400 coverage as a real gap, that is an amendable finding, not a pre-emptive addition here.
- Do not add persistence (DB/file) for accepted ids — explicitly Out of Scope (criteria.generated.md:21); a plain in-process `Set` is correct and sufficient.

**Ambiguous spec sections to interpret strictly**
- "`data` a[n]... object" (criteria.generated.md:7): interpreted to exclude `null` and arrays, since `typeof null === 'object'` and `typeof [] === 'object'` in JS but neither is a JSON "object" in the shape sense the spec intends. Shape check: `data !== null && typeof data === 'object' && !Array.isArray(data)`.
- Malformed JSON body (raw bytes that fail `JSON.parse`) after a *valid* signature: not explicitly named as its own test, but Requirement 3's "fails this shape" language is read to cover it — the handler wraps `JSON.parse` in try/catch and returns `400 { error: 'invalid_body' }` on parse failure, consistent with (not expanding) the shape-validation contract. This path previously would have been handled implicitly by the global `express.json()` parser; removing global JSON parsing for `/webhook` means the route must own this case explicitly.
- Secret file trailing whitespace: verified via `wc -c data/webhook-secret.txt` (30 bytes) and `xxd` that the file has no trailing newline — the raw content is exactly the 30-char secret. Decision: read with `fs.readFileSync(..., 'utf8')` and use as-is, no `.trim()`. Adding a defensive trim for a byte pattern that does not exist in the file is the kind of "just in case" speculative robustness the harness contract forbids; Out of Scope also forbids changing this file, so its current exact bytes are the durable contract.

**Known failure modes for this language/framework**
- **Raw-body capture ordering is load-bearing.** Verified in `node_modules/body-parser/lib/read.js:46` (`req._body = true` after a successful parse) and checked in both `node_modules/body-parser/lib/types/json.js:102` and `node_modules/body-parser/lib/types/raw.js:56` (`if (req._body) { ...skip... }`): body-parser refuses to re-parse a body once any earlier body-parser instance has already consumed it. This means the route-scoped `express.raw()` for `/webhook` MUST be registered (via `app.use('/webhook', express.raw({ type: '*/*' }))`) *before* the existing global `app.use(express.json())` (server/index.js:5) in file order. If IMPLEMENT places it after, or relies on `req.body` re-serialization instead, the global parser will consume the stream first and the raw bytes needed for HMAC verification will be gone — this is exactly the byte-fidelity failure the criteria's Constraints section (criteria.generated.md:14) calls out.
- `express.raw()` must use `{ type: '*/*' }` (not the module default `application/octet-stream`), otherwise a request whose `Content-Type` doesn't match will silently skip raw capture and leave `req.body` empty, producing a signature check against zero bytes instead of a clear error.
- `crypto.timingSafeEqual` throws `RangeError` on unequal-length buffers rather than returning `false`. The provided `X-Signature` header must be hex-decoded and length-compared against the expected 32-byte HMAC digest *before* calling `timingSafeEqual`; a missing, non-hex, or wrong-length header must short-circuit straight to `401 { error: 'invalid_signature' }` without ever invoking `timingSafeEqual` on mismatched lengths (which would otherwise surface as an uncaught 500, not the required 401).
- Confirmed `express.raw`/`express.json` are bundled with the already-declared `express@4.19.2` dependency (`node -e "require('express').raw"` → `function`; `node_modules/express/lib/express.js:78,80` re-exports `bodyParser.json`/`bodyParser.raw`) — no new npm dependency is introduced, satisfying the Constraints section (criteria.generated.md:13).
- The in-memory dedup `Set` lives on the `app` module singleton, which every `test()` block in `tests/server.test.js` shares (each test only opens a fresh `http.createServer(app)`, not a fresh `app`). The 3 new tests must use distinct event `id` values per scenario (except the replay test, which intentionally reuses one `id` twice) so cross-test state doesn't produce spurious 409s unrelated to the replay assertion.
- HMAC must be computed over the literal raw bytes of the request body the test sends — the new `post()` test helper must write a raw string (not `JSON.stringify` a JS object at request time, since a second `JSON.stringify` of the same object is not guaranteed byte-identical to the first) and must derive the `X-Signature` header from `crypto.createHmac('sha256', secret).update(thatExactString).digest('hex')` using the real secret loaded from `data/webhook-secret.txt`.

## Acceptance restatement

```json
{
  "verification_commands": [
    { "cmd": "npm test", "exit_code": 0 }
  ]
}
```
