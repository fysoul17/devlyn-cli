# Plan — webhook signature endpoint

<!-- devlyn:authorized-surface -->
## 1. Files to touch

- `server/index.js` (edit) — add `POST /webhook`: raw-body capture via `express.json({ verify })`, HMAC-SHA256 signature check against `data/webhook-secret.txt`, body-shape validation, in-memory duplicate-id tracking. Satisfies Requirements 1–3.
- `tests/server.test.js` (edit) — keep the three existing tests (`GET /health`, `GET /items`, `GET /items/:id`) passing unchanged; add ≥3 new tests: happy path (200), replay of same `id` (409), tampered body with stale signature (401). Satisfies Requirement 4.

```json
{"authorized_surface": ["server/index.js", "tests/server.test.js"]}
```

No other file changes. `data/webhook-secret.txt` (read at `data/webhook-secret.txt:1`, content `wh_test_secret_a3f9e1c2_d4b6e7`) is read-only input for the new endpoint (loaded from `server/index.js` at module load or lazily), not edited. `package.json` (read, `dependencies: { express: 4.19.2 }`, no devDependencies) needs no change — `crypto` and `fs` are Node core modules, satisfying "no new npm dependencies."

## 2. Risks

**Flagged gotchas (explicit):**

- **`crypto.timingSafeEqual` length-mismatch throws.** Per spec (`.devlyn/criteria.generated.md:18`), a wrong-length/malformed `X-Signature` must be treated as a mismatch → 401, never an uncaught exception → 500. IMPLEMENT must validate the header decodes to a buffer of the same byte length as the computed HMAC digest (32 bytes / 64 hex chars) *before* calling `timingSafeEqual`; a non-hex or wrong-length header short-circuits straight to 401 without calling it.
- **Raw-body capture.** `server/index.js:5` currently does `app.use(express.json())` with no `verify` option, so Express discards the raw buffer after parsing (`.devlyn/criteria.generated.md:17`). The HMAC must be computed over the *exact* raw bytes as received, not `JSON.stringify(req.body)` (re-serialization can change key order/whitespace and silently break every signature check). Fix: pass `verify: (req, _res, buf) => { req.rawBody = buf; }` to the existing single `express.json()` call — do not add a second body-parser middleware.

**Additional failure modes for this stack (Node/Express, node:test):**

- **Secret file trailing whitespace.** `data/webhook-secret.txt` is a plain text file; if it (or a future edit to it) ends in a trailing newline, an un-trimmed read would silently change the HMAC key. Read once with `fs.readFileSync(..., 'utf8').trim()`, consistent with "no config framework" style already in the codebase.
- **Shared module-level state across tests.** `node --test tests/` loads `server/index.js` once per process; the planned duplicate-id tracker is module-level (mirroring the existing `items` array pattern per `.devlyn/criteria.generated.md:19`). New tests must use distinct event `id`s per test case (except the intentional replay test, which reuses one deliberately) to avoid cross-test 409 collisions — this is a test-authoring risk, not a server bug.
- **Test-side signature computation must match server-side exactly.** Tests must compute their own HMAC over the literal raw bytes they send (the same `Buffer`/string passed to the HTTP request), using the *same trimmed* secret the server reads — not a hand-typed hex string — or the "happy path" test will spuriously fail with 401.
- **Header casing.** Node/Express normalizes all incoming header names to lowercase, so the header must be read as `req.headers['x-signature']` (or `req.get('X-Signature')`, which is case-insensitive) — either works, but the implementation must not assume header casing from the wire.
- **Do not record on rejected paths.** The accepted-id `Set`/tracker must only be written to on the success path (valid signature AND valid body), never on 400 or 401 responses — otherwise a malformed retry could poison the dedup state for a legitimate later delivery of the same `id`.

**Ambiguous spec sections — interpreted strictly:**

- **Check ordering for a replayed `id` with a malformed second body.** Requirement 2 states the order is signature → body-shape; Requirement 3 (duplicate tracking) is listed after both, and its wording ("responds `409` ... regardless of what the second body contains") describes the *content* of the duplicate response, not a reordering of prior checks. Strict interpretation: the pipeline is always signature-check → body-shape-check → duplicate-check → accept, in that fixed order. A second delivery with a good signature but a bad body shape gets `400`, not `409`, even though the `id` was already accepted. This is the literal reading of the requirement order as written; IMPLEMENT must not special-case duplicates to skip body validation.
- **`data` "an object."** Spec says `data` must be "an object" with no explicit exclusion of arrays. `typeof [] === 'object'` in JS. Strict interpretation: validate `typeof body.data === 'object' && body.data !== null` only — do not add an `Array.isArray` exclusion, since the spec does not ask for one and adding it would be an unrequested robustness check (Goal-locked: no speculative validation beyond what's stated).
- **Non-empty string for `id`/`type`.** Interpreted as `typeof v === 'string' && v.length > 0` (no additional trimming/whitespace-only rejection — not specified, and adding it would be speculative robustness beyond the stated contract).

**Out-of-scope refusals (explicit, per `.devlyn/criteria.generated.md:22-26`):**

- No changes to `web/index.html`, `bin/cli.js`, or existing `GET /health`, `GET /items`, `GET /items/:id` behavior.
- No rate limiting, retry backoff, or persistence of accepted ids across restarts — in-memory only, cleared on process restart, matching the existing `items` array pattern.
- No new npm dependency — `crypto` (core) for HMAC/timingSafeEqual, `fs` (core, already implicitly available) for reading the secret file.
- No `package.json` edit.

## 3. Acceptance restatement

Verbatim copy of `.devlyn/criteria.generated.md`'s `## Verification` block:

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
