# Plan — POST /webhook endpoint

<!-- devlyn:authorized-surface -->
## 1. Files to touch

- `server/index.js` — edit — add `POST /webhook`: capture raw request-body bytes via a `verify` hook on the existing `express.json()` call, compute/compare an HMAC-SHA256 signature, validate body shape, and dedup by `id` (criteria.generated.md:7-12, 19-22).
- `tests/server.test.js` — edit — add ≥3 tests (happy path 200, replay 409, tampered body 401) covering `POST /webhook`, without modifying or removing the 3 existing `/health` / `/items` / `/items/:id` tests (criteria.generated.md:13).

```json
{"authorized_surface": ["server/index.js", "tests/server.test.js"]}
```

## 2. Risks

- **Out-of-scope expansions to refuse**: persisting accepted `id`s across restarts, rate limiting, request logging, or any change to `/health`, `/items`, `/items/:id`, `bin/cli.js`, or files outside the two named above (criteria.generated.md:25-29). None of this is touched.
- **Raw-body capture must not disturb existing routes.** `server/index.js:5` already has a single global `app.use(express.json())`. Per criteria.generated.md:19, the plan is to add a `verify: (req, _res, buf) => { req.rawBody = buf; }` option to that *existing* call rather than mount a second, `/webhook`-scoped body parser — one middleware stays the source of truth, and `verify` only fires when a request actually carries a body, so `/health`/`/items`/`/items/:id` (no bodies) are unaffected. Rejected alternative: a second raw-body middleware scoped to `/webhook` — adds a parallel body-parsing path for no behavioral gain over the `verify` hook, which the constraint itself lists as the preferred option (criteria.generated.md:19).
- **`crypto.timingSafeEqual` throws on length mismatch (criteria.generated.md:21).** `Buffer.from(headerValue, 'hex')` does not throw on invalid/odd-length hex — it silently truncates, which would produce a buffer whose length coincidentally could still differ from the 32-byte digest and get caught by a length check, but is fragile to reason about. Plan: validate the header against `/^[0-9a-f]{64}$/i` (64 hex chars = 32 bytes for SHA-256) before any buffer conversion or `timingSafeEqual` call; anything not matching (missing header, wrong length, non-hex chars) short-circuits straight to `401 { error: 'invalid_signature' }` without calling `timingSafeEqual` at all. This satisfies "must not throw an uncaught exception" without a `try/catch` (no-workaround: don't wrap a real bug in error handling — remove the possibility of the throw instead).
- **Secret file read (criteria.generated.md:20).** Read `data/webhook-secret.txt` once at module load via `fs.readFileSync(path.join(__dirname, '..', 'data', 'webhook-secret.txt'))`, used as the raw `Buffer`/UTF-8 content directly (no `trim()`, no assumption about trailing newline) — matches "read and use its contents without introducing a mismatch." Only `fs` and `path`/`crypto` built-ins; no new dependency.
- **Ambiguous ordering: duplicate check vs. body-shape validation.** criteria.generated.md:12 states a replay is 409 "regardless of the second body's shape or content," which is only satisfiable if the duplicate lookup happens on `body.id` *before* full shape validation (shape validation is criteria.generated.md:10, dedup is :11-12, and :12 explicitly overrides shape-validation ordering for the replay case). Strict interpretation applied: after signature passes, look up `body.id` in the accepted-`id` set first — if found, return 409 immediately without validating the rest of the body; only if not found does full shape validation run (400 on violation, else 200 + record `id`). This is the literal reading of "regardless of shape or content" and requires no new abstraction, just a reordering of two existing checks.
- **`data` "must be an object" (criteria.generated.md:10).** Interpreted strictly as `typeof data === 'object' && data !== null && !Array.isArray(data)` — a JSON object, not an array and not `null` (`typeof null === 'object'` in JS, which is not "an object" in the intended JSON-shape sense). No test in criteria.generated.md:13 exercises the array/null edge explicitly; this is the literal-English reading, not new scope.
- **No new tests beyond the three required.** criteria.generated.md:13 asks for "at least three new tests"; the plan adds exactly those three (happy/replay/tampered) — adding more (e.g., a fourth case for the shape-vs-duplicate ordering above) would be speculative robustness for a behavior not named as a required test case, so it is left uncovered by design per goal-locked scope, not an oversight.
- **Header read is case-insensitive** — use `req.get('X-Signature')`, matching the criteria's explicit assumption (criteria.generated.md:47).

## 3. Acceptance restatement

Verbatim from `.devlyn/criteria.generated.md`:

```json
{
  "verification_commands": [
    { "cmd": "npm test", "expect_exit_code": 0 }
  ]
}
```
