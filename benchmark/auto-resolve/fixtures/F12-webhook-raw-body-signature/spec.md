---
id: "F12-webhook-raw-body-signature"
title: "Webhook signature verification endpoint"
status: planned
complexity: high
depends-on: []
---

# F12 Webhook signature verification endpoint

## Context

A third-party provider sends event notifications via webhook. Each
delivery is signed: the provider computes HMAC-SHA256 over the body
bytes using a shared secret and includes the lowercase hex-encoded
result in the `X-Signature` header.

The provider may retry a delivery (network blip, ack lost). When it
does, it sends the same payload with the same `id` field — the server
must accept the event at most once and respond `409` on a re-delivery.

The shared secret is stored at `data/webhook-secret.txt` (single line,
no trailing newline).

## Requirements

- [ ] `POST /webhook` accepts JSON-shaped bodies of the form `{ id, type, timestamp, data }` where `id` and `type` are non-empty strings, `timestamp` is a number, and `data` is an object.
- [ ] On valid signature + first delivery of a given `id`: respond `200` with `{ accepted: true, id }`.
- [ ] On valid signature + re-delivery of an already-seen `id`: respond `409` with `{ error: 'duplicate_event', id }`. The body of the duplicate is irrelevant — once an `id` is accepted, the same `id` is permanently rejected for the lifetime of the server process.
- [ ] On missing or invalid `X-Signature`, or signature does not match the body: respond `401` with `{ error: 'invalid_signature' }`. Verification compares the signature the provider sent against an HMAC-SHA256 the server computes the same way the provider did.
- [ ] On a body that fails the shape check (missing fields, wrong types, empty `id`/`type`): respond `400` with `{ error: 'invalid_body' }`. Sig check still runs first — a bad body with a valid sig is still 400, not 401.
- [ ] `tests/server.test.js` is updated. Existing assertions still hold AND at least three new tests cover: happy path, replay (same id) → 409, tampered body with stale signature → 401.

## Constraints

- **No new npm dependencies.** Express + Node `crypto` + Node built-ins only.
- **No silent catches.** Errors in the verification path surface as `500` with a clear body.
- **Use `crypto.timingSafeEqual` for the signature comparison.** A non-constant-time `===` between hex strings leaks information about the true MAC byte-by-byte.
- **No breaking change** to existing `/items`, `/items/:id`, `/health`.
- **Lifecycle note.** The harness's DOCS phase flips this spec's frontmatter `status` after implementation completes — that is benchmark lifecycle bookkeeping, not a scope violation.

## Out of Scope

- Authentication beyond signature verification.
- Rate limiting, replay window TTL (the seen-id set is process-lifetime only).
- Persistence of seen-ids across restarts.
- Touching `bin/cli.js`, `web/`, or `tests/cli.test.js`.

## Verification

- `node --test tests/server.test.js` exits 0.
- A POST with the provider's sig over the exact body bytes returns 200.
- A second POST with the same `id` returns 409 even if the signature is valid.
- A second POST with the same accepted `id` returns 409 even if the duplicate
  body would otherwise fail shape validation; duplicate id wins after acceptance.
- A POST whose body has been modified after signing (or whose `X-Signature` was computed against different bytes than the body now contains) returns 401.
- A POST with a missing or malformed `X-Signature` header returns 401.
- `git diff --stat` shows only `server/index.js` and `tests/server.test.js` touched.
