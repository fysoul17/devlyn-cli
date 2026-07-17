# nodeg-20260717 — KILLED by Registration-v3 (VGC) F7 artifact gate (2026-07-17)

Cohort at runner `6d0e9f1` (VGC build landed), CLI pin 2.1.211. Row F7 reached
IMPLEMENT; artifact gate decided before any judge wall; run killed (row
exit=143 SIGTERM); run-id DEAD.

VGC LOAD VERIFIED in the workspace artifacts themselves: the generated
contract IS the new shape (below) — no synthesis existed for PLAN to read.

| v3 gate check | Observed (gate-fail-artifacts/) | Verdict |
|---|---|---|
| complexity=medium recorded | `pipeline.state.json` complexity="medium", source.type="generated" | PASS |
| extracted Goal == task.txt bytes | fenced Goal byte-identical, 674B == 674B (exact) | PASS |
| no binding synthesized R/C/O | criteria.generated.md = Goal (verbatim) + Context anchors (non-binding) + Verification only | PASS |
| canonical Verification parses | 4 verification_commands, tail-carrier extractor binds it | PASS |
| authorized_surface = two named files | `{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}` | PASS |
| (receipt) single ledger entry | state.criteria = [{id: C1, ref: "criteria.generated://goal", status: pending}] | PASS |
| PLAN includes BOTH carriers as work items | USAGE in Risks REFUSE list ("do not touch … `USAGE` text" — grouped with out-of-scope FILES package.json/server/); tests work item = json-path test ONLY, no unsupported-format test | **FAIL** |

**Registration v3 FALSIFIED per its own pre-stated CLEAN falsifier (third
valid-negative of iter-0072). All surfaces reverted per the frozen gate; no
rescue; STOP.**

Diagnostic: the falsifier fired CLEANLY — raw Goal was demonstrably the sole
scoping authority (all five information checks PASS; the criteria
transformation no longer exists) and PLAN, reading the verbatim goal, STILL
(a) classified the stale USAGE line inside the authorized `bin/cli.js`
(`bin/cli.js:8-13`: version row documents no `--format`) as untouchable
"unrelated code", and (b) planned only the goal's literal-minimum json-path
test, omitting the specified `--format yaml` exit-1 error path as a test work
item. Information preservation is hereby falsified as the mechanism class for
carrier refusal: the narrowing lives in PLAN's own scope reasoning, not in
upstream information loss. Partial deltas vs v2 (recorded, not claimed): no
freeze-list was synthesized, no "unrequested work" framing appeared, and the
plan quotes Goal clauses as binding — the refusal surface narrowed to exactly
the two carriers.

Next mechanism class per the frozen registration: **structural PLAN
scope-lock/policy** (e.g. PLAN may not emit refuse-lists contradicting Goal
clauses; IMPLEMENT binds Goal over plan Risks) — never more prose. Seat
predictions recorded pre-gate: Grok P(refusal persists) 0.40-0.50; Codex 0.40
— outcome within the predicted band.
