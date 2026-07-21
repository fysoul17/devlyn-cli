<!-- devlyn:authorized-surface -->
## Files to touch

- `server/index.js` — edit — add the `POST /items/import` route: body validation, per-item `name`/`qty` validation, id generation, and batch append, placed alongside the existing routes (server/index.js:12-28) and before the `module.exports` at server/index.js:37.
- `tests/server.test.js` — edit — add at least two new `node:test` cases covering `POST /items/import` (invalid middle item with before/after `GET /items` comparison; fully valid batch import), following the existing `startServer`/`get` helper pattern (tests/server.test.js:6-24) and the existing `test(...)` shape (tests/server.test.js:26-58).

```json
{"authorized_surface": ["server/index.js", "tests/server.test.js"]}
```

## Risks

- **Scope creep to refuse**: no new routes beyond `/items/import`, no new npm dependencies (`express` 4.19.2 is already the only dependency per package.json), no persistence beyond the existing in-memory `items` array (server/index.js:7-10), no refactor of `GET /items` / `GET /items/:id` / `GET /health` even though they sit in the same file.
- **Empty/invalid body interpretation**: only `express.json()` is wired (server/index.js:5), no `express.urlencoded()`. With Content-Type `application/json` and an empty body, body-parser sets `req.body` to `{}`; without a JSON Content-Type, `req.body` is `undefined`. Both cases, plus `{ items: <non-array> }` and `{}` (missing `items`), must resolve to `400 { error: 'invalid_body' }`. Do not add new middleware to normalize this — handle it with a plain guard (`!req.body || !Array.isArray(req.body.items)`).
- **First-invalid-item semantics**: must scan items in input order and stop at the first item that fails validation, checking `name` before `qty` for that item (matches the Requirement's listed order: "`name` is a non-empty string ... and `qty` is a positive integer"). The reported `index`/`field` must be for that first failing item only, not a full-batch error list.
- **Two-pass validate-then-append**: the whole batch must be validated before any mutation of `items`, so that an invalid item anywhere in the batch (including after valid items) leaves `items` byte-for-byte unchanged — validate all items first, only push once the full batch passes.
- **`qty` positive integer**: reject `0`, negative numbers, non-integers (e.g. `1.5`), `NaN`, and non-number types (string, boolean, null, undefined) — `Number.isInteger(qty) && qty > 0`.
- **`name` non-empty after trim**: reject non-string types and whitespace-only strings — `typeof name === 'string' && name.trim().length > 0`. Store the trimmed or original string — Requirements don't specify which; store as provided (no trim-on-write requirement stated, only trim-for-validation), to avoid inventing unrequested normalization behavior.
- **Id collision avoidance**: use a max-plus-increment over current `items` ids (constraint-mandated approach) computed at request time, not a module-level counter that could drift from the array; must not collide with either seed id (`1`, `2`) or ids inserted by prior successful imports in the same test run.
- **Response shape literalness**: success is exactly `201 { inserted: <count> }`; batch-invalid is exactly `400 { error: 'invalid_batch', index, field }`; body-invalid is exactly `400 { error: 'invalid_body' }` — no extra fields, matching the existing route style (`res.status(...).json(...)` / `res.json(...)` at server/index.js:13,17,24,27).
- **Existing tests are contract**: the three current tests (tests/server.test.js:26-58) must keep passing unmodified in behavior; only additive test cases are in scope.

## Acceptance restatement

## Verification

- `npm test` — runs `node --test tests/`; must pass, including the new `POST /items/import` tests.
