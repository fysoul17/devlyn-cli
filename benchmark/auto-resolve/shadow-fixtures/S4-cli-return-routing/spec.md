---
id: "S4-cli-return-routing"
title: "Add return routing command"
status: planned
complexity: high
depends-on: []
---

# S4 Add Return Routing Command

## Context

Operations needs a deterministic CLI command that routes product returns to
restock, refurbish, or dispose destinations. The command must combine category
policy, condition/window rules, priority ordering, destination capacity mutation,
and exact machine-readable output.

## Requirements

- [ ] Add `route-returns` to `bin/cli.js`.
- [ ] Accept `--policies <json>` as a JSON array of policy objects. Each policy has keys `category`, `restock_window_days`, and `destinations`.
- [ ] Each `destinations` object has keys `restock`, `refurbish`, and `dispose`, whose values are destination ids.
- [ ] Accept `--capacity <json>` as a JSON object mapping destination ids to non-negative integer remaining capacity.
- [ ] Accept `--returns <json>` as a JSON array of return objects. Each return has keys `id`, `category`, `condition`, `days_since_purchase`, and `priority`.
- [ ] Before routing any return, duplicate return ids are invalid input: exit `2`, write exactly one JSON error object `{ "error": "duplicate_return_id", "id": string }` to stderr, and write no stdout.
- [ ] Process returns globally by `priority` descending, then original input order ascending.
- [ ] A return with an unknown category rejects with reason `unknown_category` and does not change capacity.
- [ ] For a known category, choose the target destination by this rule order: `damaged` condition routes to `dispose`; otherwise, if `days_since_purchase` is greater than `restock_window_days`, route to `dispose`; otherwise `sealed` routes to `restock`; otherwise `opened` routes to `refurbish`.
- [ ] A return rejects with reason `unsupported_condition` when condition is not `sealed`, `opened`, or `damaged`, and does not change capacity.
- [ ] A return accepts only when the chosen destination exists in `capacity` and has positive remaining capacity. On accept, decrement that destination by `1`.
- [ ] A return rejects with reason `destination_full` when the chosen destination is absent from `capacity` or has zero remaining capacity.
- [ ] `routed` is ordered by processing order. Each row has keys `id`, `destination`.
- [ ] `rejected` is ordered in the original input order. Each row has keys `id`, `reason`.
- [ ] `capacity` is an object whose keys are sorted alphabetically and whose values are remaining capacities.
- [ ] On success, write exactly one JSON object to stdout and no stderr. Keys: `routed`, `rejected`, `capacity`.

## Constraints

- Use only Node.js built-ins; add no npm dependencies.
- Touch only `bin/cli.js` and `tests/cli.test.js`.
- Do not silently catch JSON parse or validation errors. Surface invalid input as a user-visible error with nonzero exit.
- Do not persist destination capacity between command invocations.

## Out of Scope

- Reading input from files.
- SKU catalogs, refund amounts, shipping labels, or warehouse zones.
- Changing `hello`, `version`, server routes, or package metadata.

## Verification

- `node --test tests/cli.test.js` passes.
- `node "$BENCH_FIXTURE_DIR/verifiers/priority-return-routing.js"` prints `{"ok":true}`.
- `node "$BENCH_FIXTURE_DIR/verifiers/duplicate-return-error.js"` prints `{"ok":true}`.
- Solo-headroom hypothesis: solo_claude is expected to miss destination policy precedence or capacity mutation under priority routing; observable command `node "$BENCH_FIXTURE_DIR/verifiers/priority-return-routing.js"` exposes the miss.
