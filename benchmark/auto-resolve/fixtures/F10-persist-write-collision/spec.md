---
id: "F10-persist-write-collision"
title: "Add POST /items with persistent store"
status: planned
complexity: high
depends-on: []
---

# F10 Add POST /items with persistent store

## Context

`server/index.js` currently keeps `items` in an in-memory array that
resets on restart. The task: add `POST /items` that appends a new entry
and persists the full list to `data/items.json` so state survives
restarts. Read paths (`GET /items`, `GET /items/:id`) load from the same
persisted file.

The list and every saved item's `id` must remain consistent when
multiple POSTs arrive close together — no duplicate ids, no lost writes.

## Requirements

- [ ] `POST /items` accepts JSON body `{ name: string, qty: number }` and returns `201` with `{ item: { id, name, qty } }` on success.
- [ ] `id` is a unique numeric value. Every successful POST returns an id no other item has, past or present.
- [ ] After multiple POSTs (single or many at once), `GET /items` reflects every successful POST exactly once — `items.length` equals starting count plus successful POST count.
- [ ] `data/items.json` on disk reflects the same state. Restarting the server preserves the items.
- [ ] `GET /items` and `GET /items/:id` read from the persisted file (or from state initialized from it at startup, with all writes persisted before the response is returned).
- [ ] Invalid body (missing `name`, missing `qty`, `qty` not a positive number) → respond `400` with `{ error: 'invalid_body', field: '<name>' }`. The persisted store must be unchanged after a 400 response.
- [ ] `tests/server.test.js` is updated. Existing assertions still hold AND at least two new tests cover POST behavior, including a test that fires several POST requests close together and verifies the resulting list contains every item with distinct ids.

## Constraints

- **No new npm dependencies.** Use only Express + Node built-ins (`fs/promises`).
- **No silent catches.** Any `try/catch` in the write path must surface failure as `500` with a clear body, not return a fake success.
- **No hardcoded ids.** Existing baseline ids (1, 2) remain valid; new ids must not collide with any past or present id.
- **No breaking change** to `GET /items` shape or `GET /items/:id` semantics.

## Out of Scope

- Authentication, rate limiting, validation libraries.
- Database integration. The store is a single JSON file by design.
- Touching `bin/cli.js`, `web/`, or `tests/cli.test.js`.

## Verification

- `node --test tests/server.test.js` exits 0 and the new tests cover POST.
- Several POSTs sent close together produce a list with every item, each with a distinct id — assertable from a small Node script that POSTs in parallel and reads back `GET /items`.
- After server restart, items posted before the restart are still present in `GET /items`.
- An invalid POST returns `400` and the persisted file is byte-identical to its pre-request contents.
- `git diff --stat` shows only `server/index.js` and `tests/server.test.js` touched (the `data/items.json` seed comes from setup, not the arm).
