# Generated criteria — free-form goal

## Requirements

- Add `POST /items/import` to `server/index.js`. It accepts a JSON body `{ items: [...] }`.
- Validate every item in the batch: `name` must be a non-empty string after trimming; `qty` must be a positive integer.
- If every item is valid: append all items to the in-memory `items` list in input order. Each newly appended row receives a distinct numeric `id` that does not collide with any existing item id. Respond `201` with `{ inserted: <count> }`.
- If any item is invalid: respond `400` with `{ error: 'invalid_batch', index, field }`, where `index` is the position of the first invalid item and `field` is `'name'` or `'qty'`. No items are appended — a subsequent `GET /items` must return exactly the same list it returned immediately before the request.
- If the body is empty, `items` is missing, or `items` is not an array: respond `400` with `{ error: 'invalid_body' }`. `GET /items` must likewise be unchanged.
- Update `tests/server.test.js`: keep all existing tests passing, and add at least two new tests for the import endpoint — one exercising an invalid middle item (comparing `GET /items` before and after the request), and one covering a fully valid batch import.

## Constraints

- No new npm dependencies — use only `express` (already a dependency) and Node's built-in `node:test`/`node:assert`/`node:http`.
- Only touch `server/index.js` and `tests/server.test.js`.
- Follow the existing route style already in `server/index.js` (plain `app.<verb>(path, (req, res) => { ... res.status(...).json(...) })` handlers, no added middleware/abstraction layers).
- Follow the existing test style already in `tests/server.test.js` (`node:test` + `node:assert`, the `startServer`/`get` helper pattern — add an analogous `post` helper rather than introducing a new HTTP client).

## Out of Scope

- Any endpoint other than `POST /items/import` (no PUT/DELETE/PATCH additions).
- Persistence beyond the existing in-memory `items` array.
- Concurrency/locking beyond what a single synchronous request handler already provides.

<!-- devlyn:verification -->
## Verification

```json
{"verification_commands": [{"cmd": "npm test", "expect_exit_code": 0}]}
```
