# Plan — POST /items/import

<!-- devlyn:authorized-surface -->
## Files to touch

- `server/index.js` — `edit`: add `POST /items/import` route handler implementing validation (Req: "Add `POST /items/import`... Validate every item..."), distinct id allocation (Req: "distinct numeric `id` that does not collide with any existing item id"), all-or-nothing semantics (Req: "the items store must be left byte-for-byte unchanged (no partial append)"), and the exact 400/201 response contracts (Req: "Any-invalid path... Malformed request path...").
- `tests/server.test.js` — `edit`: add a `post` helper (raw `node:http`, mirroring existing `get` helper shape at `tests/server.test.js:13-24`) and >=2 new `test(...)` cases — one invalid-middle-item case asserting `GET /items` is unchanged before/after, one fully-valid import case (Req: "Update `tests/server.test.js`: keep existing tests passing; add >=2 new tests...").

```json
{"authorized_surface": ["server/index.js", "tests/server.test.js"]}
```

## Risks

- **Out-of-scope expansions to refuse**: no touching `web/`, `bin/cli.js`, no new persistence layer, no new npm dependencies, no new endpoints beyond `/items/import`, no refactor of existing `GET /items`, `GET /items/:id`, or `GET /health` handlers beyond what's needed to read `items`.
- **Malformed-body ambiguity, resolved strictly**: criteria lists three malformed cases — "empty body, missing `items`, or non-array `items`" — all map to a single `400 { error: 'invalid_body' }`, distinct from the per-item `400 { error: 'invalid_batch', index, field }` contract. An empty JSON body (`{}`) still parses via `express.json()`; `req.body` will be `{}`, so `items` is `undefined` → `invalid_body`. A missing `Content-Type`/empty request body will leave `req.body` as `{}` (Express default) → same path, no separate handling needed.
- **Empty `items` array (`{ items: [] }`)**: criteria does not list this as malformed (only "missing `items` or non-array `items`" is invalid_body) and does not list it as invalid_batch (no item to fail validation against). Strict reading: `[]` is a valid array, loop over zero items finds no first-invalid, so this falls into the all-valid path — `201 { inserted: 0 }`. No new branch required; the existing validate-loop naturally falls through. Not adding a special case for this — would be speculative robustness beyond the stated contract.
- **`qty` "positive integer" strictness**: use `Number.isInteger(item.qty) && item.qty > 0`. Do not accept numeric strings (`"3"`) or coerce — criteria says "must be a positive integer", not "coercible to". No `parseInt`/`Number()` coercion — that would silently accept malformed input, violating the no-workaround/no-silent-fallback rule.
- **`name` "non-empty string after trimming"**: `typeof item.name === 'string' && item.name.trim().length > 0`. A non-string `name` (number, null, missing) fails the `typeof` check and is reported as `field: 'name'`.
- **Validation must stop at the FIRST invalid item in input order**: implement as a single forward loop that breaks/returns on the first failing item — do not collect all errors (that would be unrequested extra behavior and also risks reporting a non-first index).
- **id allocation must not collide within the same batch**: compute the next id as `max(existing items ids, ids assigned so far in this batch) + 1` per item, or equivalently track a running `nextId` counter seeded from `Math.max(0, ...items.map(i => i.id)) + 1` and increment per appended item — do not use `items.length + 1` (collides after deletions; though this codebase has no delete endpoint, `items.length+1` is still fragile/incorrect if ids were ever non-sequential — seed data is `1, 2` so sequential works today, but `Math.max(...ids)+1` is the correct, still-minimal primitive). Sticking with `Math.max` avoids a class of collision bugs for zero extra complexity.
- **All-or-nothing must be enacted only after full-batch validation**: validate the entire batch first (loop 1), then append only if no invalid item was found (loop 2, or single pass building a staged array then splicing into `items`). This guarantees zero partial mutation of the shared `items` array on any invalid item, satisfying "byte-for-byte unchanged" without needing a deep-clone/restore workaround.
- **Route ordering**: Express matches `/items/:id` before a later-declared `/items/import` would only be a routing hazard if `POST /items/:id` existed — it does not (only `GET /items/:id` exists), and this is a distinct HTTP method (`POST` vs `GET`) on a distinct path shape, so no route-order conflict. Still, add the new route in a sensible place (after `GET /items/:id`, before `if (require.main === module)`) matching existing file structure — not a functional requirement, just readability, no line added for this beyond placement.
- **Known failure mode — Express body parsing**: `express.json()` is already registered (`server/index.js:5`); no additional middleware needed. If `Content-Type` isn't `application/json`, Express leaves `req.body` as `{}`, which is exactly the desired `invalid_body` trigger — confirmed this needs no extra handling.
- **Test helper `post`**: must mirror `get`'s existing promise/http shape (`tests/server.test.js:13-24`) — use `http.request` with method `POST`, write a JSON string body, set `Content-Type: application/json` header, and parse the JSON response the same way `get` does. This is a new helper because none of the same shape exists yet — an explicit spec requirement ("will need a `post` helper of the same shape"), so it is not speculative addition.

## Acceptance restatement

### Verbatim `## Requirements` (binding behavioral contracts)

- Add `POST /items/import` to `server/index.js` accepting `{ items: [...] }`.
- Validate every item: `name` must be a non-empty string after trimming; `qty` must be a positive integer. Validation stops at and reports the FIRST invalid item (in input order).
- All-valid path: append all items in input order, each receiving a distinct numeric `id` that does not collide with any existing item id; respond `201` with `{ inserted: <count> }`.
- Any-invalid path: respond `400` with `{ error: 'invalid_batch', index, field }` where `index` is the position of the first invalid item and `field` is `'name'` or `'qty'`; the items store must be left byte-for-byte unchanged (no partial append) — `GET /items` immediately after must equal `GET /items` immediately before.
- Malformed request path: empty body, missing `items`, or non-array `items` must respond `400` with `{ error: 'invalid_body' }`; items store unchanged.
- Update `tests/server.test.js`: keep existing tests passing; add >=2 new tests — one exercising an invalid middle item (asserting list unchanged before/after), one exercising a fully valid import request.

### Verbatim `## Verification`

- Valid batch: a fully-valid `{ items: [...] }` request to `POST /items/import` must append all items in input order, each with a distinct numeric `id` not colliding with any existing item id, and respond `201` with `{ inserted: <count> }`.
- Invalid batch (all-or-nothing): a mixed valid/invalid batch (invalid item not first) must respond `400` with `{ error: 'invalid_batch', index, field }` identifying the first invalid item, and `GET /items` immediately after must return exactly the same list `GET /items` returned immediately before the request (no partial append).
- Malformed body: an empty body, missing `items`, or non-array `items` must respond `400` with `{ error: 'invalid_body' }`, and `GET /items` must be unchanged.
- `npm test`
