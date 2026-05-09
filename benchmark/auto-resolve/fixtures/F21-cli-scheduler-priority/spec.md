---
id: "F21-cli-scheduler-priority"
title: "Priority appointment scheduler"
status: planned
complexity: high
depends-on: []
---

# F21 Priority appointment scheduler

## Context

Add a `bench-cli schedule --input <path>` command that assigns appointment
requests to resource availability windows using priority, submitted order,
blocked intervals, and earliest-fit placement while producing exact JSON
accept/reject results.

The scheduler is used by downstream automation, so output shape, ordering, and
failure reasons must be deterministic.

## Requirements

- [ ] `bench-cli schedule --input <path>` reads JSON shaped as `{ "resources": Array<Resource>, "requests": Array<Request> }`.
- [ ] Each resource has `{ "id": string, "windows": [{ "start": "HH:MM", "end": "HH:MM" }], "blocked": [{ "start": "HH:MM", "end": "HH:MM" }] }`. `blocked` may be empty.
- [ ] Each request has `{ "id": string, "resource": string, "start": "HH:MM", "duration_min": number, "priority": number, "submitted_at": string }`.
- [ ] Times are same-day 24-hour clock minutes. A range is half-open: `[start, end)`. A request ending exactly at a window end is allowed; overlapping a blocked range by one minute is not allowed.
- [ ] Process requests globally by `priority` descending, then `submitted_at` ascending, then `id` ascending.
- [ ] For each request, place it on the requested resource at the earliest start minute that is greater than or equal to the request's requested `start`, fits wholly inside one availability window, does not overlap any blocked interval, and does not overlap any already accepted request on that resource.
- [ ] Do not move a request to a different resource.
- [ ] If no placement exists, reject with `{ "id": string, "reason": "no_slot" }`.
- [ ] If the request references an unknown resource, reject with `{ "id": string, "reason": "unknown_resource" }`.
- [ ] Invalid top-level shape, invalid time strings, non-positive or non-integer `duration_min`, or duplicate request ids exits `2`, writes exactly one JSON error object to stderr, and writes nothing to stdout.
- [ ] On success, write exactly one JSON object to stdout and no stderr. Keys: `scheduled`, `rejected`.
- [ ] `scheduled` is ordered by actual scheduled start time ascending, then resource id ascending, then request id ascending. Each row has keys `id`, `resource`, `start`, `end`.
- [ ] `rejected` is ordered in the original request input order. Each row has keys `id`, `reason`.
- [ ] `tests/cli.test.js` is updated. Existing tests still pass AND at least two scheduler tests cover one success case and one rejection case.

## Constraints

- **No new npm dependencies.**
- **No silent catches in implementation or tests.** Invalid input and file-read failures must surface as JSON errors with exit `2`; test cleanup should use explicit safe primitives such as `fs.rmSync(path, { force: true })`, not `catch { /* ignore */ }`.
- **No mutation of the input file.**
- **No extra stdout/stderr text** on the success path; downstream tooling parses stdout as JSON.
- **Touch only `bin/cli.js` and `tests/cli.test.js`.**

## Out of Scope

- Multiple-day scheduling.
- Time zones.
- Recurring appointments.
- Persisting scheduled results.
- Touching `server/`, `web/`, or `tests/server.test.js`.

## Verification

- `node --test tests/cli.test.js` exits 0.
- A higher-priority later-submitted request can take the first slot, forcing a lower-priority earlier-submitted request to the next non-overlapping slot.
- A request may end exactly at a window end, but any one-minute overlap with a blocked interval is rejected or moved later.
- Unknown resources are reported in `rejected` without aborting the whole run.
- Duplicate request ids are invalid input: exit `2`, one JSON error to stderr, no stdout.
- `git diff --stat` shows only `bin/cli.js` and `tests/cli.test.js` touched.
