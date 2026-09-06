# 0121 — Missing-output PLAN failure lifecycle

2026-09-07 KST — **ACCEPTED AND PUSHED**, `bb29173d51fdef001e64ae6199d6976b4d6952b0` on `origin/main`. Owner: [committed spec](../../docs/specs/0121-blocked-plan-output/spec.md). This scoped repair used the authorized plain-conversation pinned Codex route; it is not a full resolve acceptance.

## Accepted repair

Pre-flight 0 / Mission 1: actual 0120 R1 worker initialization failed before `plan.md`, then output hashing rejected the prescribed BLOCKED completion. The violated invariant was a truthful completed failure record. Principles: **No workaround**, **No overengineering**, **No guesswork**, **Production ready**.

Schema3 PLAN with explicit BLOCKED and lexically absent output now records completion time, duration and null digest while preserving existing session/receipt failure semantics and null effective model. Only FINAL_REPORT lifecycle may follow; work dispatch, surface events and durability enforcement reject that missing-output state. Existing output integrity, successful-path requirements and finish-gate precedence remain intact. The three canonical writer/SKILL/schema files and their tracked mirrors are the six-file product change; the SKILL wording refers to the schema rather than duplicating its exception.

## Validation and advice

[Acceptance](../../.devlyn/0121-blocked-plan-output/accepted.json) binds passing state/receipt self-tests, retained red and deletion checks, and final required full skill lint: exit 0, **183.8078s**. Native MEDIUM `NATIVE-0121-1` is closed: all five special-event CLI regressions reject with unchanged state. Supplemental schema3 Claude/no-session checks pass all 12 assertions; the unchanged finish gate on an owned R1 copy exits 1 for missing authorized surface. These are synthetic/source-failure checks, not Claude/provider acceptance.

Actual Grok requested `grok-4.6`, emitted `grok-4.6-build`, returned final canonical **PASS, zero findings** after reading the sealed packet. Actual Fable `claude-fable-5-1` found only a LOW mirror-binding evidence gap, supplied by [the addendum](../../.devlyn/0121-blocked-plan-output/final-r1/mirror-evidence-addendum.json). Its extra recap invalidates the canonical envelope; retain it as advice, never a judge PASS. Root made the final scoped acceptance decision; earlier NEEDS_WORK, invalid formats and raw findings remain preserved.

## Evidence custody

Raw receipts are under `.devlyn/0121-blocked-plan-output/`. Durable [OUTPUT.json](/Users/aipalm/.local/share/nx01/iter0121/20260906T184359Z-accepted-plan-failure-j61w7pke/OUTPUT.json), SHA `b708a7dee796b3e66983fdf923027c9ea852ac39a4e4a42cd4f8be646f7a147f`, verifies **396 files + 120 directories, 5,839,711 bytes**, including all evidence, nine canonical/mirror source copies and two committed spec files. Only the reproducible nested `node_modules` tree is excluded. The earlier `20260906T183910Z-accepted-plan-failure` directory remains preserved with an INCOMPLETE marker after stopping at its dependency symlink. [Completion pointer](../../.devlyn/0121-blocked-plan-output/custody.completed.json) binds the new custody.

Seven external implementation/advice calls have a known **79,601 OUTPUT-token subtotal**, reasoning included once where observable. [Usage receipt](../../.devlyn/0121-blocked-plan-output/usage-known-subtotal.json) retains per-call identities and raw hashes. Interactive root, native collaborators and unobserved activity are not fully metered: whole-task output and billed cost remain unknown.

## Limits and next step

R1 remains immutable archived BLOCKED with its [independent assessment and custody](0120-model-adaptation-direction.md#ordinary-entry-r1--archived-blocked). Fresh R2 staging on runtime `bb29173` preserved the F1 inputs and invoked no models; subsequent registration/launch status belongs to `entry-calibration-r2/` receipts and HANDOFF. No full-pipeline, performance or release-readiness claim follows. A16 stays parked, the reporting candidate stays rejected, and version 3.0.0 has not been tagged or published.
