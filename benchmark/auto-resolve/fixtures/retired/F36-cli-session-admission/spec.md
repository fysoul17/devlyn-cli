---
id: "F36-cli-session-admission"
title: "Session admission command with a global concurrency cap"
status: planned
complexity: high
depends-on: []
---

# F36 Session admission command with a global concurrency cap

## Context

`bench-cli` gets an `admit` command that decides which of a batch of
scheduling sessions can run at all, given a single global limit on how many
sessions may be concurrently active. Downstream capacity-planning tooling
parses stdout as JSON and replays the verification input at production
scale, so the decision must be exact and the command must finish in
reasonable time even on large batches.

## Requirements

- [ ] `bench-cli admit --input <path>` reads JSON shaped as `{ "capacity": number, "sessions": [{ "id": string, "start": number, "end": number }] }`.
- [ ] Sessions become eligible for admission in ascending order of `start`; ties are broken by the session's position in the input `sessions` array (the earlier entry is eligible first).
- [ ] Sessions are considered for admission one at a time, in that eligibility order. A session is admitted unless, at the moment it is considered, the number of already-admitted sessions whose interval has not yet ended is already equal to `capacity` — in that case it is deferred instead. A session's interval `[start, end)` is half-open: an admitted session whose `end` equals the candidate's `start` has already ended and does not count against it.
- [ ] Each deferred row reports `blocking`: the ids of the currently-active admitted sessions preventing its admission, in the order those sessions were themselves admitted (not a final or static list, and not the list for any other candidate).
- [ ] `bench-cli admit` must finish processing the 150,000-session verification input (see `## Verification`) within its process timeout, without changing which sessions are admitted or deferred compared to a smaller input processed under the same rule.
- [ ] Validation happens before any admission decision. `capacity` must be a positive integer; `sessions` must be an array; every session needs a non-empty string `id`, integer `start`, and integer `end` with `start < end`; every `id` must be unique across the whole input. Invalid input exits `2` and writes exactly one JSON error object to stderr, printing nothing to stdout: a malformed capacity/session field uses shape `{ "error": "invalid_input", "reason": string }`; a duplicate `id` uses shape `{ "error": "duplicate_session_id", "id": string }`.
- [ ] On success, write exactly one JSON object to stdout and no stderr. Keys: `admitted` (array of admitted session ids, in eligibility order) and `deferred` (array of `{ "id": string, "reason": "over_capacity", "blocking": [string, ...] }` rows, in eligibility order).
- [ ] `tests/cli.test.js` is updated. Existing tests still pass AND at least two new tests cover `admit`: one where a session listed earlier in the file but starting later must not be admitted ahead of a session listed later but starting earlier, and one deferral.

## Constraints

- **No new npm dependencies.**
- **No silent catches.** If parsing or file reading fails, emit a visible JSON error to stderr and exit `2`.
- **No extra stdout/stderr text** on the success path; downstream tooling parses stdout as JSON.
- `data`, `server`, and `web` directories are unrelated to this command; do not add files there.

## Out of Scope

- Persisting admission results between command invocations.
- Retrying, rescheduling, or suggesting alternate times for deferred sessions.
- Changing server routes, web UI, or any file outside `bin/cli.js` and `tests/cli.test.js`.
- Touching `server/`, `web/`, or `tests/server.test.js`.

## Verification

- `node --test tests/cli.test.js` exits 0.
- Given three sessions where the second-admitted session's interval ends before the first-admitted session's interval ends, a fourth session starting after the second has ended but before the first has ended is correctly admitted (its admission depends on evicting the second, not the first, from the active set) — `node "$BENCH_FIXTURE_DIR/verifiers/correctness-small.js"` exposes misses on this and the eligibility-order, half-open-boundary, and `blocking` rules above.
- Malformed input, non-unique ids, and a non-positive capacity are all rejected before any admission decision, per the exact error shapes above — `node "$BENCH_FIXTURE_DIR/verifiers/validation.js"` exposes misses.
- A 150,000-session input with `capacity` set low relative to heavily overlapping session durations completes within the process timeout and produces the exact admitted/deferred sets — `node "$BENCH_FIXTURE_DIR/verifiers/scale.js"` exposes misses on both timing and correctness.
- `git diff --stat` shows only `bin/cli.js` and `tests/cli.test.js` touched.

## Solo-headroom hypothesis

A capable solo_claude baseline is expected to reach for a data structure
that is correct on typical hand-written examples but does not stay fast as
the number of concurrently active sessions grows — for example, keeping
admitted sessions in a plain list and scanning or filtering it on every new
candidate — which is correct at small scale but does not finish the
150,000-session input in time; observable command
`node "$BENCH_FIXTURE_DIR/verifiers/scale.js"` exposes the miss.
