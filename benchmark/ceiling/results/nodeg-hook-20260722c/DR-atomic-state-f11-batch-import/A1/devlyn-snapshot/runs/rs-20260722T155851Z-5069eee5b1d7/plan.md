# Plan — POST /items/import

<!-- devlyn:authorized-surface -->
## Files to touch

- `server/index.js` — edit: add `app.post('/items/import', (req, res) => { ... })` route after the existing `app.get('/items/:id', ...)` handler (server/index.js:20-28), following the same plain-handler style (server/index.js:12-28: no added middleware/abstraction). Implements Requirements 1–4 (endpoint, validation, success append with 201, failure paths with 400).
- `tests/server.test.js` — edit: add a `post` helper analogous to the existing `get` helper (tests/server.test.js:13-24), plus at least two new `test(...)` blocks for the import endpoint. Implements Requirement 5 (test coverage: invalid-middle-item case comparing `GET /items` before/after, and a fully-valid-batch case), while leaving the three existing tests (tests/server.test.js:26-58) untouched.

```json
{"authorized_surface": ["server/index.js", "tests/server.test.js"]}
```

## Risks

- **No added abstraction layer.** Constraint explicitly forbids added middleware/helper functions in `server/index.js` beyond the route handler itself (criteria.generated.md:16). Validation logic (name/qty checks) and id-generation must be written inline in the `app.post('/items/import', ...)` handler, matching the plain style of `app.get('/items/:id', ...)` (server/index.js:20-28) — no extracted `validateItem()` or `nextId()` helper function. This is a refusal point: the instinct to factor out a validator must be resisted per the "no new abstractions without an observed failure mode" principle.
- **Id collision avoidance without new module state.** Requirement 3 needs each newly appended item to get a distinct id that doesn't collide with any existing id. Subtractive-first: no new counter variable at module scope — compute the next id from the current `items` array's max id at request time (e.g. `Math.max(0, ...items.map((it) => it.id))`), then increment once per appended item within the batch. This avoids adding persistent state the codebase doesn't already have.
- **Validate-before-mutate ordering.** Requirement 4 requires that on any invalid item, *no* items are appended and a subsequent `GET /items` returns exactly the prior list. The handler must fully validate the whole batch (find the first invalid index/field) before doing any `items.push(...)` — not validate-and-append per item. Ambiguous-but-strict interpretation: validation is a first pass over the whole array; only after 100% pass does the append pass run.
- **Strict validation semantics (ambiguous spec wording, resolved strictly, no coercion):**
  - `name` invalid when: not a `string`, or `.trim()` is empty. No coercion from non-string types.
  - `qty` invalid when: not `Number.isInteger(qty)`, or `qty <= 0`. No coercion from strings like `"5"` — a positive-integer check means actual `number` type, not numeric-looking string.
  - First invalid item wins: `index` in the 400 response is the position of the *first* item (in input order) that fails either check; `field` is `'name'` if the name check fails first for that item, else `'qty'`.
- **Body-shape validation is a distinct failure path from item validation.** Requirement 5: if `req.body` is missing/empty, `req.body.items` is missing, or `req.body.items` is not an `Array`, respond `400 { error: 'invalid_body' }` — this check must run before per-item validation and must not touch `items`. `express.json()` (already `app.use`'d at server/index.js:5) may hand back `{}` for a body-less POST, so guard with `req.body && Array.isArray(req.body.items)` rather than assuming `req.body` is always an object.
- **Out-of-scope refusal.** Do not add PUT/DELETE/PATCH routes, do not add persistence beyond the existing in-memory `items` array, do not add locking/concurrency handling (criteria.generated.md:19-23). Do not touch any file other than `server/index.js` and `tests/server.test.js`.
- **Test style constraint.** New tests must use only `node:test`/`node:assert`/`node:http` and the existing `startServer`/`get` helper pattern (tests/server.test.js:6-24) — add one analogous `post(server, path, payload)` helper (mirroring `get`'s signature/shape: resolves `{ status, body }`) rather than introducing a new HTTP client or dependency (criteria.generated.md:14, 17). Existing three tests (tests/server.test.js:26-58) must keep passing unmodified.
- **Test-order independence.** Because `items` is shared in-memory state across tests in the same process, the "fully valid batch import" test and the "invalid middle item" test must not assume a specific starting `items` length/content beyond what `GET /items` reports *immediately before* that test's own request — matching Requirement 5's instruction to compare `GET /items` before and after, rather than hardcoding expected ids/counts.

## Acceptance restatement

```json
{"verification_commands": [{"cmd": "npm test", "expect_exit_code": 0}]}
```
