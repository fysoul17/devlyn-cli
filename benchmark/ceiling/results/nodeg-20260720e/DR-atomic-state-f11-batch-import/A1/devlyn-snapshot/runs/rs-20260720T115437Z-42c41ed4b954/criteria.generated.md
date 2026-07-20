# Generated criteria — POST /items/import

## Requirements

- Add `POST /items/import` to `server/index.js` accepting `{ items: [...] }`.
- Validate every item: `name` must be a non-empty string after trimming; `qty` must be a positive integer. Validation stops at and reports the FIRST invalid item (in input order).
- All-valid path: append all items in input order, each receiving a distinct numeric `id` that does not collide with any existing item id; respond `201` with `{ inserted: <count> }`.
- Any-invalid path: respond `400` with `{ error: 'invalid_batch', index, field }` where `index` is the position of the first invalid item and `field` is `'name'` or `'qty'`; the items store must be left byte-for-byte unchanged (no partial append) — `GET /items` immediately after must equal `GET /items` immediately before.
- Malformed request path: empty body, missing `items`, or non-array `items` must respond `400` with `{ error: 'invalid_body' }`; items store unchanged.
- Update `tests/server.test.js`: keep existing tests passing; add >=2 new tests — one exercising an invalid middle item (asserting list unchanged before/after), one exercising a fully valid import request.

## Constraints

- Only touch `server/index.js` and `tests/server.test.js`. No new npm dependencies (use only `express`, already a dependency, and Node's built-in `node:test`/`node:assert`/`node:http` already used by the test file).
- Follow existing code style in `server/index.js` (plain Express handlers, `res.status().json()` pattern already used by `GET /items/:id`'s 404 path) and `tests/server.test.js` (raw `node:http` requests via the existing `startServer`/`get` helpers — will need a `post` helper of the same shape).
- `id` allocation must not collide with any existing or just-appended id in the same batch; existing seed data uses ids `1, 2`.

## Out of Scope

- Anything not in `server/index.js` or `tests/server.test.js`.
- `web/`, `bin/cli.js`, other endpoints, persistence beyond the existing in-memory `items` array.

<!-- devlyn:verification -->
## Verification

- Valid batch: a fully-valid `{ items: [...] }` request to `POST /items/import` must append all items in input order, each with a distinct numeric `id` not colliding with any existing item id, and respond `201` with `{ inserted: <count> }`.
- Invalid batch (all-or-nothing): a mixed valid/invalid batch (invalid item not first) must respond `400` with `{ error: 'invalid_batch', index, field }` identifying the first invalid item, and `GET /items` immediately after must return exactly the same list `GET /items` returned immediately before the request (no partial append).
- Malformed body: an empty body, missing `items`, or non-array `items` must respond `400` with `{ error: 'invalid_body' }`, and `GET /items` must be unchanged.
- `npm test`

```json
{"verification_commands":[{"cmd":"npm test","exit_code":0}]}
```
