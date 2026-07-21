---
complexity: medium
---

# Generated criteria — POST /items/import

## Requirements

- [ ] R1: Add `POST /items/import` to `server/index.js`. It accepts `{ items: [...] }`; every item must have a `name` that is a non-empty string after trimming and a `qty` that is a positive integer.
- [ ] R2: When every item is valid, append all of them in input order and respond `201` with `{ inserted: <count> }`. Every appended row must receive a distinct numeric `id` that does not collide with any existing item id.
- [ ] R3: If an item is invalid, respond `400` with `{ error: 'invalid_batch', index, field }`, where `index` identifies the first invalid item and `field` is `name` or `qty`. After that response, `GET /items` must return exactly the same list it returned immediately before the request.
- [ ] R4: An empty body, missing `items`, or a non-array `items` value must return `400` with `{ error: 'invalid_body' }`; `GET /items` must likewise be unchanged.
- [ ] R5: Update `tests/server.test.js` so the existing tests still pass and add at least two import tests: one exercising an invalid middle item (comparing the list before and after the response), another covering a fully valid request.

## Constraints

- Only touch `server/index.js` and `tests/server.test.js`.
- No new npm dependencies.
- Follow the existing Express handler patterns already in `server/index.js` (in-memory `items` array, `res.json`/`res.status().json`).

## Out of Scope

- Any endpoint or file other than `POST /items/import` in `server/index.js` and the corresponding tests in `tests/server.test.js`.
- `bin/cli.js`, `web/index.html`, and `tests/cli.test.js` are untouched.

<!-- devlyn:verification -->
## Verification

- When every item is valid, append all of them in input order and respond `201` with `{ inserted: <count> }`. Every appended row must receive a distinct numeric `id` that does not collide with any existing item id.
- If an item is invalid, respond `400` with `{ error: 'invalid_batch', index, field }`, where `index` identifies the first invalid item and `field` is `name` or `qty`. After that response, `GET /items` must return exactly the same list it returned immediately before the request.
- An empty body, missing `items`, or a non-array `items` value must return `400` with `{ error: 'invalid_body' }`; `GET /items` must likewise be unchanged.
- Update `tests/server.test.js` so the existing tests still pass and add at least two import tests. One must exercise an invalid middle item and compare the list before and after the response; another must cover a fully valid request.

```json
{
  "verification_commands": [
    {
      "cmd": "node --test tests/server.test.js",
      "exit_code": 0
    }
  ]
}
```
