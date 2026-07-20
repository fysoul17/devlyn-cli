# Generated criteria — POST /items/import

recommend: n/a (medium complexity, generated in-run)

## Requirements

- `POST /items/import` in `server/index.js` accepts a JSON body `{ items: [...] }`. Each item must have `name` (non-empty string after `.trim()`) and `qty` (positive integer).
- When every item in the batch is valid: append all items to the in-memory `items` store in input order, respond `201` with `{ inserted: <count> }`. Each appended row must receive a distinct numeric `id` that does not collide with any existing item id (existing items today: id 1, id 2).
- When any item is invalid: respond `400` with `{ error: 'invalid_batch', index, field }`, where `index` is the 0-based index of the FIRST invalid item and `field` is `'name'` or `'qty'` (whichever check failed first for that item). Do not mutate the `items` store — a subsequent `GET /items` must return exactly the same list it returned immediately before the `POST /items/import` request.
- When the request body is empty, missing `items`, or `items` is not an array: respond `400` with `{ error: 'invalid_body' }`. Do not mutate the `items` store.
- Update `tests/server.test.js`: keep all existing tests passing; add at least two new tests covering `/items/import` — one exercising an invalid middle item (asserting `GET /items` is byte-for-byte identical before and after the failed request), and one covering a fully valid import request.

## Constraints

- Only touch `server/index.js` and `tests/server.test.js`.
- No new npm dependencies (use `express` + Node's built-in `http`/`node:test`, matching existing patterns in these files).
- Follow the existing route style in `server/index.js` (plain Express handlers, `res.status(...).json(...)`, `module.exports = { app }` unchanged).

## Out of Scope

- Anything not in `server/index.js` or `tests/server.test.js` (e.g. `bin/cli.js`, `web/`, persistence beyond the existing in-memory array, other endpoints).

<!-- devlyn:verification -->
## Verification

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
