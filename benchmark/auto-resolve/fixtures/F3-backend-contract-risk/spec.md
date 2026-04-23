---
id: "F3-backend-contract-risk"
title: "Paginate GET /items response"
status: planned
complexity: high
depends-on: []
---

# F3 Paginate `GET /items`

## Context

`server/index.js` currently returns `{ items: [...] }` for `GET /items` with
no pagination metadata. As the dataset grows, clients need a `total` and
paging information. The task: wrap the existing response in a pagination
envelope, accept `?page` and `?per_page` query parameters, and update tests
so existing assertions continue to pass alongside new paging assertions.

## Requirements

- [ ] `GET /items` (no query) returns `{ items, total, page, per_page }` where:
  - `items` is the full list (baseline repo has 2 items).
  - `total` is the full item count.
  - `page` is `1`.
  - `per_page` is the full item count when no pagination was requested.
- [ ] `GET /items?page=1&per_page=1` returns the first item wrapped in the envelope with `items.length === 1`, `total === 2`, `page === 1`, `per_page === 1`.
- [ ] `GET /items?page=2&per_page=1` returns the second item similarly.
- [ ] `GET /items?page=99&per_page=1` returns `items: []`, `total === 2`, `page === 99`, `per_page === 1` (out-of-range page is allowed — bare empty array, never a 404).
- [ ] `GET /items/:id` behavior unchanged (the per-item route does NOT get paginated).
- [ ] `tests/server.test.js` is updated so every existing assertion still holds (semantically) AND the new paging behavior is covered by at least two new tests.
- [ ] `GET /health` continues to return `{ status: 'ok' }` unchanged.

## Constraints

- **No new npm dependencies.** Use only Express + built-ins already in the repo.
- **No silent catches.** Invalid `page` or `per_page` (non-numeric, zero, negative) must respond 400 with `{ error: 'invalid_query', field }`.
- **No breaking change to `/items/:id`.** The per-item route must keep its current contract (the fixture explicitly does NOT paginate single-item lookups).
- **Backward-compat note**: clients that previously read `response.items` MUST still get the array at the same key inside the new envelope.

## Out of Scope

- Caching, rate limiting, authentication.
- Converting `items` to a database-backed list.
- Touching `bin/cli.js`, `web/`, or `tests/cli.test.js`.
- Adding a new route.

## Verification

- Server start: `node server/index.js` listens on port 3000 (exit via SIGINT).
- `curl -s http://127.0.0.1:3000/items | jq '.total'` returns `2`.
- `curl -s 'http://127.0.0.1:3000/items?per_page=1&page=2' | jq '.items[0].name'` returns `"beta"`.
- `curl -s 'http://127.0.0.1:3000/items?per_page=abc' -o /dev/null -w '%{http_code}'` returns `400`.
- `node --test tests/server.test.js` passes; must include ≥ 2 new paging tests.
- `git diff --stat` shows only `server/index.js` and `tests/server.test.js` touched.
