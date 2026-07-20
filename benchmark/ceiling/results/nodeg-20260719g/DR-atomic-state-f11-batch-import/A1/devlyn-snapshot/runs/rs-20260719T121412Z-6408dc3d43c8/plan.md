# Plan — POST /items/import

<!-- devlyn:authorized-surface -->
## 1. Files to touch

- `server/index.js` — edit — add `POST /items/import` route (Requirements: validate batch, append on all-valid, `400 invalid_batch`/`400 invalid_body` on failure, distinct non-colliding `id`s), placed after the existing `GET /items/:id` handler (server/index.js:20-28) and before the `require.main === module` block (server/index.js:30).
- `tests/server.test.js` — edit — add a `post(server, path, body)` helper mirroring the existing `get(server, path)` helper (tests/server.test.js:13-24), plus ≥2 new `test(...)` cases for `/items/import` (Requirement: invalid-middle-item test comparing `GET /items` before/after, and a fully-valid-import test), appended after the existing `GET /items/:id returns 404 for missing` test (tests/server.test.js:49-58).

```json
{"authorized_surface": ["server/index.js", "tests/server.test.js"]}
```

## 2. Risks

- **Out-of-scope expansions to refuse**: no persistence layer, no changes to `bin/cli.js` or `web/`, no new npm dependency (e.g. a body-validation library) — Express's built-in `express.json()` (already mounted at server/index.js:5) is sufficient. No new routes beyond `/items/import`. No refactor of the existing `GET /items`, `GET /items/:id`, or `GET /health` handlers.
- **Ambiguous spec sections, interpreted strictly**:
  - "first invalid item" → iterate items in input order (`Array.prototype.some`/`for` loop with early break), return the index of the first item where validation fails; do not collect all errors.
  - Field-check order per item is unspecified beyond "field is name or qty (whichever check failed first for that item)" — check `name` before `qty` per item (matches the object's own field order `{ name, qty }` used elsewhere, e.g. server/index.js:8-9), so a row invalid on both fields reports `field: 'name'`.
  - "non-empty string after trimming" → `typeof item.name === 'string' && item.name.trim().length > 0`. Reject non-string `name` (including `null`/`undefined`/numbers) as a `name` failure.
  - "positive integer" for `qty` → `typeof item.qty === 'number' && Number.isInteger(item.qty) && item.qty > 0`. Reject non-number, non-integer (e.g. `1.5`), zero, and negative values as a `qty` failure. Do not coerce strings ("3") — `qty` must already be a JS number.
  - "distinct numeric `id` that does not collide with any existing item id" → compute `nextId = Math.max(0, ...items.map(i => i.id)) + 1` once per request, then assign sequential ids (`nextId`, `nextId + 1`, ...) to the validated batch in input order before pushing — matches the existing manually-assigned sequential ids (1, 2) at server/index.js:7-10.
  - "empty body" → Express with `express.json()` parses a body-less POST as `{}`, so `items` will be `undefined` — this is covered by the same "missing `items`" check, no separate branch needed.
  - `items` array being empty (`[]`, present and is an array) is not itemized in the spec as an error case; since there's nothing to validate and nothing invalid, treat it as a valid batch of size 0 → `201 { inserted: 0 }` (falls out naturally from "every item is valid" being vacuously true over an empty array — no special-case code needed).
- **Known failure modes for this language/framework**:
  - Mutating `items` before validation completes would violate "GET /items must return exactly the same list" on the invalid-batch path — validate the entire batch first in a separate pass (or build the array of new rows) before any `items.push`.
  - Off-by-one in id assignment if `Math.max` is computed after partial mutation, or if computed per-item instead of once — compute once from the pre-request `items` state.
  - `express.json()` throws/produces a parse error for malformed JSON bodies before the handler runs; Express's default error handler returns its own error shape, not `{ error: 'invalid_body' }` — this is existing behavior, out of scope per the spec (spec only requires `400 invalid_body` for empty/missing/non-array `items`, not malformed JSON syntax), so no new JSON-parse error handler is added.
  - `res.status(...).json(...)` is the established response idiom (server/index.js:24, 27) — reuse it verbatim rather than `res.json(...)` + separate `res.status`.

## 3. Acceptance restatement

```json
{
  "verification_commands": [
    {
      "cmd": "npm test",
      "exit_code": 0,
      "stdout_contains": ["# fail 0"]
    }
  ]
}
```
