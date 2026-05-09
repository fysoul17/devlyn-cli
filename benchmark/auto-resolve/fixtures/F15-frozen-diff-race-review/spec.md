---
id: "F15-frozen-diff-race-review"
title: "Review and fix the items API for production load"
status: planned
complexity: high
depends-on: []
---

# F15 Review and fix the items API for production load

## Context

The `/items` API in `server/index.js` was implemented a few weeks ago by
another engineer. It has been running in staging without complaints —
existing tests pass and the happy paths work. The team is preparing for
a load test next quarter and wants the API reviewed for any correctness
issues that single-request testing would not surface.

The implementation persists state to `data/items.json` and exposes:

- `GET /health`
- `GET /items`
- `GET /items/:id`
- `POST /items`

## Requirements

- [ ] Review `server/index.js` for any correctness issues a production load test would surface. Apply fixes you find. Common load-related issues include lost updates, duplicated identifiers, and inconsistent response/state pairs.
- [ ] Add at least one new test in `tests/server.test.js` covering the fix. Existing tests must still pass.
- [ ] If your fix introduces helpers, place them inside `server/index.js`. Do not split the server into multiple files.
- [ ] Behavioral contracts that callers depend on must remain unchanged: response shapes for all four endpoints, the `data/items.json` on-disk format, and the meaning of HTTP status codes.

## Constraints

- **No new npm dependencies.** Fix using Express + Node built-ins only.
- **No silent catches.** Errors surface with explicit status + body, not by returning a fake-success.
- **Touch only `server/index.js` and `tests/server.test.js`.** Do not modify `data/items.json` shape, `tests/cli.test.js`, or anything outside the server.

## Out of Scope

- Adding new endpoints, methods, or query parameters.
- Replacing the JSON-file store with a database.
- Reformatting or wholesale refactoring beyond what the fix requires.
- Performance tuning unrelated to the correctness issue (caching, pooling).

## Verification

- `node --test tests/server.test.js` exits 0.
- A small Node script that fires several `POST /items` requests close together must produce a state where every POST that returned `201` is reflected in `GET /items` exactly once, with distinct ids.
- Single-request behavior (one POST, then GET) is unchanged.
- `git diff --stat` shows only `server/index.js` and `tests/server.test.js` touched.
