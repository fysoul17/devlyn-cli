---
id: "F37-cli-rule-lookup"
title: "Price events against the rule in effect at their own timestamp"
status: planned
complexity: high
depends-on: []
---

# F37 Price events against the rule in effect at their own timestamp

## Context

`bench-cli` gets a `price-events` command that prices a batch of purchase
events using the pricing rule revision that was actually in effect for that
event's category at the event's own timestamp — not the newest rule, and
not the same rule for every event in a category. Rule revisions arrive from
a seeded, unsorted file with many revisions per category. Downstream
billing tools parse stdout as JSON, and they replay very large event
batches, so the lookup must stay exact and the command must finish in
reasonable time.

## Requirements

- [ ] `bench-cli price-events --input <path>` reads JSON shaped as `{ "events": [{ "id": string, "categoryId": string, "timestamp": number, "basePrice": number }] }`.
- [ ] Pricing rule revisions come from `data/rule-revisions.json`, shaped as an array of `{ "id": string, "categoryId": string, "effectiveAt": number, "discountPct": number, "minPrice": number }`. Revisions in that file are not sorted by category or by time. The command must not modify `data/rule-revisions.json`.
- [ ] For each event, consider every revision whose `categoryId` equals the event's `categoryId` and whose `effectiveAt` is less than or equal to the event's `timestamp`. Among those, the one with the greatest `effectiveAt` applies — an exact match (`effectiveAt` equal to the event's `timestamp`) counts as eligible, not just strictly earlier ones.
- [ ] If more than one eligible revision for that category shares the greatest `effectiveAt`, the one with the greatest `id` (plain string comparison) applies.
- [ ] If the event's `categoryId` has zero revisions anywhere in `data/rule-revisions.json`, the event is rejected with reason `unknown_category`.
- [ ] If the event's `categoryId` has at least one revision but none with `effectiveAt` less than or equal to the event's `timestamp`, the event is rejected with reason `no_effective_rule`.
- [ ] An accepted event's price is `Math.max(rule.minPrice, Math.round(event.basePrice * (100 - rule.discountPct) / 100))`.
- [ ] `bench-cli price-events` must finish processing the 200,000-event verification input (see `## Verification`) against the seeded revision set within its process timeout, without changing the priced or rejected outcome for any event compared to a smaller input processed the same way.
- [ ] Validation happens before any pricing. `events` must be an array; every event needs a non-empty string `id` and `categoryId`, an integer `timestamp`, and a non-negative integer `basePrice`; every event `id` must be unique. Invalid input exits `2` and writes exactly one JSON error object to stderr, printing nothing to stdout: a malformed field uses shape `{ "error": "invalid_input", "reason": string }`; a duplicate event `id` uses shape `{ "error": "duplicate_event_id", "id": string }`.
- [ ] On success, write exactly one JSON object to stdout and no stderr. Keys: `priced` (array of `{ "id": string, "ruleId": string, "price": number }` rows) and `rejected` (array of `{ "id": string, "reason": string }` rows). Each event appears in exactly one of the two arrays; within each array, rows keep the original input event order.
- [ ] `tests/cli.test.js` is updated. Existing tests still pass AND at least two new tests cover `price-events`: one where two revisions for the same category apply to different events depending on each event's own timestamp, and one rejection.

## Constraints

- **No new npm dependencies.**
- **No silent catches.** If parsing or file reading fails, emit a visible JSON error to stderr and exit `2`.
- **No extra stdout/stderr text** on the success path; downstream tooling parses stdout as JSON.
- `server` and `web` directories are unrelated to this command; do not add files there.

## Out of Scope

- Persisting priced results between command invocations.
- Adding, editing, or reordering rule revisions in `data/rule-revisions.json`.
- Changing server routes, web UI, or any file outside `bin/cli.js` and `tests/cli.test.js`.
- Touching `server/`, `web/`, or `tests/server.test.js`.

## Verification

- `node --test tests/cli.test.js` exits 0.
- Two revisions for the same category with different `effectiveAt` values each apply to the correct event depending on that event's own `timestamp`, including the exact-match boundary — `node "$BENCH_FIXTURE_DIR/verifiers/correctness-small.js"` exposes misses on this, the same-`effectiveAt` tie-break, and the `unknown_category`-versus-`no_effective_rule` distinction above.
- Malformed input, non-unique event ids, and non-integer/negative fields are all rejected before any pricing decision, per the exact error shapes above — `node "$BENCH_FIXTURE_DIR/verifiers/validation.js"` exposes misses.
- A 200,000-event input priced against a large seeded revision set completes within the process timeout and produces the exact priced/rejected outcome for every event — `node "$BENCH_FIXTURE_DIR/verifiers/scale.js"` exposes misses on both timing and correctness.
- `git diff --stat` shows only `bin/cli.js` and `tests/cli.test.js` touched.

## Solo-headroom hypothesis

A capable solo_claude baseline is expected to reach for a lookup approach
that is correct on typical hand-written examples but does not stay fast as
the number of revisions per category grows — for example, scanning a
category's revisions linearly for every event instead of using a structure
that stays fast as that list grows — which is correct at small scale but
does not finish the 200,000-event input in time; observable command
`node "$BENCH_FIXTURE_DIR/verifiers/scale.js"` exposes the miss.
