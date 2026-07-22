# Generated criteria — POST /items/import

recommend: /devlyn:ideate first

Free-form goal classified `large` (file_scope_signals = 11, > 10 threshold). The
goal text itself is well-specified (exact endpoint, exact response shapes, exact
error contract) so this best-effort spec narrows only the details the goal left
implicit; see `## Assumptions`.

## Requirements

1. Add `POST /items/import` to `server/index.js`.
2. Request body must be `{ items: [...] }`. If the body is empty, `items` is
   missing, or `items` is not an array, respond `400` with
   `{ error: 'invalid_body' }` and leave the in-memory item list unchanged.
3. Validate every item in `items` before mutating any state:
   - `name` must be a string that is non-empty after `.trim()`.
   - `qty` must be a positive integer.
   - The first invalid item (by input-order index) determines the response:
     `400` with `{ error: 'invalid_batch', index, field }`, where `field` is
     `'name'` or `'qty'` (whichever fails first, `name` checked before `qty`
     when both fail on the same item). No items are appended in this case;
     `GET /items` must return exactly the same list it returned immediately
     before the request.
4. If every item is valid, append all of them to the in-memory item list in
   input order and respond `201` with `{ inserted: <count> }`, where
   `<count>` equals `items.length`.
5. Each appended row must receive a distinct numeric `id` that does not
   collide with any existing item id (pre-request or newly assigned within
   the same batch).
6. Update `tests/server.test.js`: keep existing tests passing, add at least
   two new tests for `/items/import`:
   - One exercising an invalid *middle* item (not first, not last) that
     captures `GET /items` before and after the `POST` and asserts the list
     is byte-for-byte unchanged.
   - One exercising a fully valid multi-item request that asserts the `201`
     response and that the new items are present via `GET /items`.

## Constraints

- Only `server/index.js` and `tests/server.test.js` may be touched.
- No new npm dependencies (`package.json` `dependencies` / `devDependencies`
  must be unchanged).
- Reuse the existing in-memory `items` array and its existing id scheme
  (sequential numeric ids starting at 1 in the current seed data).
- Follow the existing route style in `server/index.js` (plain Express
  handlers, `res.status(...).json(...)`, no added framework/middleware).

## Out of Scope

- Persistence beyond the in-memory `items` array.
- Changes to `GET /items`, `GET /items/:id`, or `GET /health`.
- Authentication, rate limiting, or request size limits.
- `bin/cli.js`, `web/index.html`, or any file other than the two listed above.

## Assumptions

Every assumption below is scope-narrowing and reversible (a stricter/narrower
reading of an already-implied behavior, not an invented feature).

1. **id assignment** — new ids are assigned as `(max existing id at request
   start) + 1, +2, ...` in input order, so ids stay sequential and
   deterministic and never collide with existing or newly-inserted rows.
2. **`qty` type** — "positive integer" means a JS `number` that is
   `Number.isInteger(qty) && qty > 0`; a numeric string (e.g. `"5"`) is
   invalid (`field: 'qty'`), matching the strict typing implied by the spec
   text rather than a permissive coercion.
3. **Extra item fields** — if a client sends extra keys on an item object,
   only `name` (trimmed) and `qty` are copied into the stored row alongside
   the generated `id`; extra keys are dropped.
4. **Empty `items` array** — `{ items: [] }` is a valid array (passes the
   `invalid_body` check) and is vacuously "every item is valid", so it
   responds `201` with `{ inserted: 0 }` and appends nothing.
5. **`name` field storage** — the stored `name` is the trimmed string (not
   the raw untrimmed input), consistent with "non-empty string after
   trimming" being the validation rule.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "npm test", "exit_code": 0 }
  ]
}
```
