# Plan — POST /webhook (HMAC signature verification, replay detection)

Read before planning: `.devlyn/criteria.generated.md` (full Requirements/Assumptions/Out-of-Scope/Verification contract), `server/index.js:1-37` (current Express app: global `app.use(express.json())` at line 5, three GET routes, `module.exports = { app }` at line 37), `tests/server.test.js:1-58` (existing `startServer`/`get` helpers, three `GET` tests using `node:test`), `data/webhook-secret.txt` (confirmed via `xxd`: exactly 30 bytes, `wh_test_secret_a3f9e1c2_d4b6e7`, **no trailing newline** — matches criteria Assumption "the current file has none"), `package.json` (dependencies: only `express@4.19.2`; test script `node --test tests/`; no devDependencies — confirms no new npm dependency is available or needed, Node's built-in `crypto`/`fs`/`http` cover everything required).

<!-- devlyn:authorized-surface -->
## 1. Files to touch

- `server/index.js` — **edit**. Add `crypto`/`fs`/`path` requires, capture raw body bytes via the existing `app.use(express.json())` call (add its `verify` option), read+trim the webhook secret once at module load, add an in-memory accepted-id `Set`, and add the `POST /webhook` route implementing signature check → duplicate check → shape check → accept, in that order. Rationale: this is the only file that defines routes/middleware (Requirements bullets 1–4, 5).
- `tests/server.test.js` — **edit**. Add a raw-payload POST helper + HMAC signer, then three new `test(...)` blocks (happy path, replay → 409, tampered-body-with-stale-signature → 401), leaving the three existing `GET` tests untouched. Rationale: Requirement bullet 5 ("Update `tests/server.test.js` ... add at least three new tests").

```json
{"authorized_surface": ["server/index.js", "tests/server.test.js"]}
```

## 2. Risks

**Out-of-scope expansions to refuse:**
- Do not touch `data/webhook-secret.txt` or `data/_sample-event.json` (explicit Out of Scope).
- Do not add persistence for accepted ids across restarts, rate limiting, or request logging (explicit Out of Scope) — the in-memory `Set` scoped to module load is final, not a stepping stone.
- Do not add any npm dependency (`package.json` has zero devDependencies today; adding one, e.g. a body-parser variant or a UUID/validation lib, is an unauthorized addition — `crypto`, `fs`, `path`, `http` are all Node built-ins already implicitly available).
- Do not touch any file besides the two authorized above (e.g. do not add a new `routes/webhook.js` module — that would be an unrequested abstraction the goal doesn't ask for, and it isn't in the authorized-surface list).
- Do not add error-handling middleware for malformed (non-JSON-parseable) request bodies. Express's default JSON-parse-error behavior is unchanged; the criteria only specifies behavior for well-formed JSON bodies that fail *shape* validation, not for bodies that aren't valid JSON at all. Handling that case is speculative robustness not named in the goal.

**Ambiguous spec sections to interpret strictly:**
- **Ordering is a hard contract, not a suggestion**: (1) signature check first — invalid → `401` regardless of body shape; (2) duplicate-id check second, against the *raw, unvalidated* `req.body.id` — if it matches a previously-accepted id, respond `409` and skip shape validation entirely, per criteria bullet 4's explicit "the second body is not re-validated for shape" / "the second body is irrelevant"; (3) shape validation third — invalid → `400`; (4) only then accept, add id to the Set, respond `200`. Implementing shape validation before the duplicate check (a natural but wrong instinct) would violate this.
- **`data must be an object`**: interpreted as a plain non-null, non-array JS object (`typeof data === 'object' && data !== null && !Array.isArray(data)`), since JSON/JS Schema conventionally distinguish `object` from `array` even though arrays are technically objects in JS. This is the literal, narrower reading of the word "object" in the requirement, not an added defensive check.
- **Hex-decode before `timingSafeEqual`**: `Buffer.from(str, 'hex')` does not throw on malformed hex — it silently truncates at the first invalid character, which would otherwise let a malformed/short header slip past a naive length check or crash `timingSafeEqual` on mismatched buffer lengths. Per criteria Assumption 4, compare decoded buffer lengths first; on mismatch, treat as `invalid_signature` (`401`) without calling `timingSafeEqual`.
- **Raw-body capture scope**: criteria Assumption 1 says to scope the `verify` capture "to this route/app only." Since the app already has exactly one global `app.use(express.json())` (line 5) and the existing GET routes carry no body (criteria Assumption 5 confirms this must stay inert), the plan adds the `verify` option to that single existing call rather than introducing a second body-parser instance mounted only on `/webhook` — the latter would be a new abstraction (two JSON parsers) to solve a problem the single shared one already solves harmlessly.
- **Secret trim**: read once at module load via `fs.readFileSync(..., 'utf8')`, stripping only a single trailing `\n` (or `\r\n`) if present — not a full `.trim()` — per criteria Assumption 2. The current file has neither, so this is a no-op today but must be implemented as specified for correctness against the literal contract.
- **Known failure mode (Node/Express)**: `crypto.timingSafeEqual` throws `RangeError` on unequal-length buffers rather than returning `false` — must never be called without an equal-length guard first (see hex-decode point above).

## 3. Acceptance restatement

Verbatim copy of `.devlyn/criteria.generated.md`'s `## Verification` block:

```json
{
  "verification_commands": [
    { "cmd": "npm test", "exit_code": 0 }
  ]
}
```
