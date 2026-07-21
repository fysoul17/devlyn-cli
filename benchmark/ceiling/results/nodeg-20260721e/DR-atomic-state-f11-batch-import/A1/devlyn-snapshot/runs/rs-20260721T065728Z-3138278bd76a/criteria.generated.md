# Generated criteria — POST /items/import

## Requirements

- `POST /items/import` in `server/index.js` accepts a JSON body `{ items: [...] }`. Each item is valid only if `name` is a non-empty string after trimming, and `qty` is a positive integer.
- When every item in the batch is valid: append all items to the in-memory `items` store in input order, respond `201` with `{ inserted: <count> }`, and every appended row must receive a distinct numeric `id` that does not collide with any existing item id.
- When any item is invalid: respond `400` with `{ error: 'invalid_batch', index, field }`, where `index` is the position of the first invalid item and `field` is `'name'` or `'qty'` (whichever failed first). No items are appended — `GET /items` immediately after this response must return exactly the same list it returned immediately before the request.
- When the request body is empty, `items` is missing, or `items` is not an array: respond `400` with `{ error: 'invalid_body' }`. `GET /items` must be unchanged by this request.
- `tests/server.test.js` is updated so all existing tests still pass, plus at least two new tests covering `POST /items/import`: one exercising an invalid middle item (comparing the `GET /items` list before and after the response), and one covering a fully valid batch import.

## Constraints

- Only `server/index.js` and `tests/server.test.js` may be touched.
- No new npm dependencies — reuse `express` and `express.json()` already wired in `server/index.js`.
- Follow the existing route style in `server/index.js` (`app.get`/`res.json`/`res.status(...).json(...)`, in-memory `items` array as the single source of truth).
- New ids must not collide with any existing item id (existing seed data uses ids `1` and `2`; a simple max-plus-increment or running counter satisfies this without a new dependency).

## Out of Scope

- Anything not in `server/index.js` or `tests/server.test.js`.
- New routes, new dependencies, or persistence beyond the existing in-memory `items` array.

<!-- devlyn:verification -->
## Verification

- `npm test` — runs `node --test tests/`; must pass, including the new `POST /items/import` tests.

```json
{"verification_commands": [{"cmd": "npm test", "exit_code": 0, "stdout_contains": ["# fail 0"]}]}
```
