---
id: "F11-batch-import-all-or-nothing"
title: "Batch import endpoint"
status: planned
complexity: high
depends-on: []
---

# F11 Batch import endpoint

## Context

`server/index.js` only allows fetching items today. The task: add
`POST /items/import` that accepts a batch of items in a single request
and appends them to the existing list. The endpoint is intended for bulk
loads where users send a CSV-derived JSON array.

The product requirement: a batch must be accepted as a whole or rejected
as a whole. If any item in the batch is invalid, the response is `400`
and the stored list is left exactly as it was before the request.

## Requirements

- [ ] `POST /items/import` accepts JSON body `{ items: Array<{ name: string, qty: number }> }`.
- [ ] On full success: respond `201` with `{ inserted: <count> }`. The new items appear in `GET /items` in the order given. Each receives a unique numeric `id` not used by any existing item.
- [ ] Per-item validation: `name` must be a non-empty string after `trim()`; `qty` must be a positive integer (`> 0`). Any item failing either check makes the batch invalid.
- [ ] On batch invalidity: respond `400` with `{ error: 'invalid_batch', index: <0-based index of first invalid item>, field: 'name' | 'qty' }`. After the response, `GET /items` returns the same list it would have returned before the import was sent.
- [ ] Empty body, missing `items`, or `items` not an array → `400` with `{ error: 'invalid_body' }`. Same store-unchanged guarantee.
- [ ] `tests/server.test.js` is updated. Existing assertions still hold AND at least two new tests cover import: one happy path, one with an invalid element mid-batch that asserts the prior list is unchanged after the failed call.

## Constraints

- **No new npm dependencies.**
- **No silent catches.**
- **No partial updates.** A batch with N items must produce either N inserts or 0 inserts.
- **No breaking change** to existing `GET /items` and `GET /items/:id`.

## Out of Scope

- Authentication, rate limiting.
- File-based persistence (the store stays in-memory for this fixture).
- CSV parsing or any non-JSON payload.
- Touching `bin/cli.js`, `web/`, or `tests/cli.test.js`.

## Verification

- `node --test tests/server.test.js` exits 0.
- A POST with one valid + one invalid item returns `400`, AND a subsequent `GET /items` returns the same list as before the import.
- A POST with all-valid items returns `201`, and the items appear in `GET /items` in order with distinct ids.
- `git diff --stat` shows only `server/index.js` and `tests/server.test.js` touched.
