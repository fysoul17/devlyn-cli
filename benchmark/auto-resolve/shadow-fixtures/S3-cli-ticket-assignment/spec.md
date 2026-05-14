---
id: "S3-cli-ticket-assignment"
title: "Add ticket assignment command"
status: planned
complexity: high
depends-on: []
---

# S3 Add Ticket Assignment Command

## Context

Support operations need a deterministic CLI command that assigns tickets to
agents with matching skills and limited capacity. The command must process
higher-priority tickets first, apply a precise agent tie-breaker, preserve
remaining capacity only for accepted assignments, and emit an exact JSON shape.

## Requirements

- [ ] Add `assign-tickets` to `bin/cli.js`.
- [ ] Accept `--agents <json>` as a JSON array of agent objects. Each agent has keys `id`, `skills`, and `capacity`.
- [ ] Accept `--tickets <json>` as a JSON array of ticket objects. Each ticket has keys `id`, `skill`, `priority`, and `created_at`.
- [ ] Before processing any ticket, duplicate ticket ids are invalid input: exit `2`, write exactly one JSON error object `{ "error": "duplicate_ticket_id", "id": string }` to stderr, and write no stdout.
- [ ] Process tickets globally by `priority` descending, then `created_at` ascending, then original input order ascending.
- [ ] A ticket accepts only when at least one agent has the ticket skill and positive remaining capacity.
- [ ] When multiple agents can accept a ticket, assign it to the agent with the most remaining capacity, then `id` ascending.
- [ ] Accepted tickets decrement only the selected agent's remaining capacity by `1`.
- [ ] Rejected tickets do not change any agent capacity. Use reason `no_agent` when no eligible agent is available at that point in processing.
- [ ] `assigned` is ordered by processing order. Each row has keys `id`, `agent`.
- [ ] `unassigned` is ordered in the original input order. Each row has keys `id`, `reason`.
- [ ] `agents` is ordered by agent id ascending. Each row has keys `id`, `remaining`.
- [ ] On success, write exactly one JSON object to stdout and no stderr. Keys: `assigned`, `unassigned`, `agents`.

## Constraints

- Use only Node.js built-ins; add no npm dependencies.
- Touch only `bin/cli.js` and `tests/cli.test.js`.
- Do not silently catch JSON parse or validation errors. Surface invalid input as a user-visible error with nonzero exit.
- Do not persist assignments or capacity between command invocations.

## Out of Scope

- Reading input from files.
- Weighted skills, agent schedules, or SLA clocks.
- Changing `hello`, `version`, server routes, or package metadata.

## Verification

- `node --test tests/cli.test.js` passes.
- `node "$BENCH_FIXTURE_DIR/verifiers/priority-agent-assignment.js"` prints `{"ok":true}`.
- `node "$BENCH_FIXTURE_DIR/verifiers/duplicate-ticket-error.js"` prints `{"ok":true}`.
- Solo-headroom hypothesis: solo_claude is expected to miss the remaining-capacity tie-breaker or original-order unassigned rows under priority processing; observable command `node "$BENCH_FIXTURE_DIR/verifiers/priority-agent-assignment.js"` exposes the miss.
