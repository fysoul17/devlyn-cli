# F37 Price events against the rule in effect at their own timestamp

## Failure mode

Detects implementations that get the point-in-time rule lookup right at
small, hand-written scale but reach for a data structure that stops
scaling once the number of revisions per category grows large — most
naturally, scanning a category's revisions linearly for every event to
find the greatest `effectiveAt <= timestamp`. That shape is
indistinguishable from the fully correct answer on any test an agent is
likely to hand-write, and only fails once each category carries many
thousands of revisions (Tier-2 axis: performance/scale — see
F36-cli-session-admission's NOTES.md for the suite-wide grep evidence
that no prior fixture measured wall-clock at all). Compounded with small-
scale correctness sub-traps so a fast-but-wrong shortcut and a
correct-but-slow shortcut both lose points independently: the inclusive
`effectiveAt <= timestamp` boundary, the same-`effectiveAt` tie-break by
greatest `id`, and the `unknown_category` vs. `no_effective_rule`
distinction (whether the category has zero revisions at all versus
revisions that just don't apply yet).

This is a distinct algorithmic shape from F36 (online interval admission
with expiry) — an offline/versioned point-in-time lookup, grouped by key
and searched by time. It replaces an earlier F37 design (multi-hop category
merge chains + dual-file rollback + idempotent rerun) that Codex R1 rejected
outright as too structurally similar to the already-failed
F35-cli-apply-journal / F26 / F32 rollback-and-idempotency family — see
Rounds below.

## Fairness

Every verifier assertion quotes a visible spec.md bullet via `contract_refs`
(lint-fixtures enforced). The 200,000-event performance requirement is
stated as a plain, numeric, visible spec bullet — no mechanism vocabulary
("group", "sort", "binary search", "index", "efficient") appears anywhere
in `spec.md` or `task.txt`; only the observable behavior (must finish
within the process timeout, must not change any event's outcome) is named.
`data/rule-revisions.json` being unsorted is stated as a plain data-shape
fact, not a hidden trap. The scale verifier's large revision set is
generated only inside the hidden verifier at measurement time (never
written to the persistent seed the arm develops against) specifically to
avoid forcing the arm to read a multi-megabyte file into its own context
during development — the setup.sh seed stays small and realistic.

## Pipeline phase(s) tested

BUILD_GATE / VERIFY: an agent's own test suite is overwhelmingly likely to
use a handful of hand-written revisions, so nothing in a normal iterative
dev loop surfaces the scale defect; only the hidden, harness-side scale
verifier (never visible to the arm) exercises it.

## Why another fixture can't cover this

No active or retired fixture in this suite measures wall-clock or
algorithmic complexity (see F36-cli-session-admission NOTES.md for the
grep evidence). This fixture's specific shape — a versioned/point-in-time
lookup keyed by category and searched by effective date — is also not
covered by any prior pricing fixture (F16, F25, F26, F32), all of which
price a single current state rather than resolving which historical rule
revision applies.

## When to retire or replace

If a headroom run shows solo_claude reliably recognizes and implements the
required efficient per-category structure even without prompting, retire
per the same honest-retirement contract used for F27/F28/F30/F34/F35 and
add this id to `pair-rejected-fixtures.sh` with the observed scores.

## Rounds — Codex GPT-5.5 collaboration (read-only, `codex-monitored.sh`)

**Round 1** (initial F37 design: multi-hop category-merge chain resolution,
cycle detection, dual-file write-back to `products.json` +
`migration-log.json`, idempotent-rerun requirement): Codex verdict
**reject-and-replace** — "It reads like F35/F26/F32 with new nouns:
rule-source pricing, idempotency/replay, validation-before-write,
rollback/unchanged files. The rejected registry shows solo already scored
97-98 on these families... I would not spend another headroom run on this
version." Codex proposed a concrete replacement direction instead of
softening the objection: "dated category/rule snapshots where each product
event must use the latest rule effective at or before its timestamp,
across 200k events and 50k rule revisions. Naive scan-all-rules-per-product
fails; correct solution groups by key and binary-searches or sweeps."

**Round 2** (fully replaced design, as above, presented alongside the
revised F36): Codex verdict **converge, no changes needed** — "F37 is
distinct enough. It is a different access pattern: point-in-time lookup
over versioned rules, not interval admission/capacity... I would not call
it a freebie in the same way as 'meeting rooms'; agents still have to
preserve input order, handle as-of boundaries, same-time tie-breaks, and
distinguish missing-category cases." Confirmed the tie-break/boundary rules
were unambiguous and the visible scale wording was fair (grounds
`contract_refs` in observable behavior without leaking grouping, sorting,
or binary search as required mechanisms).
