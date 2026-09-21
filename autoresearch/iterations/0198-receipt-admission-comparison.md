# 0198 — both review routes close two findings; a branch defect remains

2026-09-21 KST. Root direct, no resolve including controls. Ten actual Astra/high
calls completed once: two initial implementations, each with continued (S) and
fresh (F) static review, then identically configured fresh repair workers.
[Protocol](../experiments/0198/PROTOCOL.md) and [request](../experiments/0198/request.md)
were committed at `d493f92` before draws;56 input hashes remained sealed.
The task is previously unmeasured history-lifecycle R1 receipt binding, from the
same feature/source family as0197, not an unrelated holdout or independent field task.

## Observed result and decision

Both routes found and closed two substantiated defects, one per initial product.
Fresh context added no observed closure benefit. All four repair workers reproduced
their supplied claim before fixing it (`REPAIR-RED-EVIDENCE.json` cites the actual
pre-patch failed commands in each `runs/*-repair/stdout`); no unsupported native finding was emitted.
Initial2's Unicode-branch defect remained after both repairs, missed by its S and F
reviews. The observed trace connects review, reproduction and repair; without a no-review
repair arm, it does not isolate the added reviewer's causal effect or establish
fresh-context/full-phase necessity.

All six products pass the frozen46/46 rows (43 actual CLI cases, baseline and
candidate self-test commands, and one supplied/added unittest command) and file scope. These are
oracle-complete products, not product-complete results. Both witness columns below
require correct usable-receipt binding AND COMPLETE-receipt refusal.

| Product | Frozen rows + scope | Trailing NBSP | Branch/tag collision |
| --- | --- | --- | --- |
|1-initial|46/46 PASS|wrong identity|correct|
|1-S|46/46 PASS|correct|correct|
|1-F|46/46 PASS|correct|correct|
|2-initial|46/46 PASS|wrong identity|wrong identity|
|2-S|46/46 PASS|wrong identity|correct|
|2-F|46/46 PASS|wrong identity|correct|

The frozen checks omit two valid branch-identity counterexamples, and the reference
also fails them. Keep primary scores and post-seal finding witnesses separate; no
retrospective primary regrade, overall completion-rate ranking, policy adoption or
production readiness claim. One task/two initials and one repair per review cannot
prove equivalence or isolate repair sampling noise; no no-review repair arm exists.
No lifecycle feature, routing/default change, generic reminder or npm release ships.

## Reproduced finding closures

- Initial1 reads the full symbolic ref but applies `str.strip()` at bootstrap:327.
  A valid branch ending in U+00A0 is shortened before hashing. Its actual allocated
  receipt is missed: usable tasks remain unbound and COMPLETE tasks are admitted.
  Both1-S and1-F replace stripping with removal of the record newline and fix it.
- Initial2 inherits `git symbolic-ref --short` at bootstrap:316. With an identically
  named tag, Git returns `heads/task/x` instead of `task/x`; the wrong hash again
  bypasses its actual receipt. Both2-S and2-F read the full ref and remove only the
  `refs/heads/` prefix. Both retain `.strip()`, so the Unicode defect remains.

`SUPPLEMENTAL-PREDICTIONS.md` precedes42 actual-CLI replays: normal, trailing-NBSP
and branch/tag-collision cases, each owned and COMPLETE, across six products and
the reference. Every fixture uses the unmodified real allocator; terminal tests
then change only receipt status. Git accepts the exact branch names and the raw
full/short outputs are retained. The same witness fails on the initial and passes
on its corresponding repairs. Later failures within some native red test runs
cascade from prior state; closure counts use these42 separate fresh-fixture replays.
These are exploratory adjudication, not new draws.
Fable's neutral-labelled review independently substantiates all four native claims,
finds the same residual defects and finds no HIGH/CRITICAL issue; execution, not
reviewer agreement, supplies the closure evidence. Fable rates the findings and
residual MEDIUM. Static review is not completeness. Each route found2 of3 known
defect instances across the initials; this is post-seal recall, not a frozen metric.

## Admission corrected before draws

Actual allocate receipts in normal and linked worktrees have `task:string`, distinct
from the proposed state's `task:object|null`. Actual `complete --local-only` without
acceptance writes `local_only:true`, leaving status/acceptance absent. The request
separates these real forms from future/synthetic terminal states; no0197 ambiguity
is rewritten. Normal producer receipts are consumed byte-for-byte, not reserialized.

Root initially supplied two malformed inline-spec fixtures. Fable then identified
missing self-test support, an accidental undefined reference-test variable, the
required exact-state `task:null` expectation update and producer reserialization.
Raw failed calibration/source remains retained. All were corrected before draws.
Final admission: original0/43 CLI rows; reference43/43; common-dir mutant42/43;
empty-acceptance and late-admission mutants41/43 each. Original self-tests pass,
original new smoke fails, and reference self-tests/smoke all pass. Final reference
baseline/candidate self-tests took21.780/22.655s under their300s ceilings. Raw files:
`CALIBRATION.json`, `CALIBRATION-FINAL.json`, `REGRESSION-CALIBRATION.json` and
`REGRESSION-FINAL.json`.

A final Fable MEDIUM exposed candidate-dependent assessment aborts. Malformed state,
CLI timeout and changed test-injection boundary now produce explicit failed rows;
actual malformed-state and simulated timeout/boundary controls verify this before
freeze. Fixture/host setup errors remain infrastructure failures. Both participant
and oracle Git environments disable global/system config with the same settings.
Fable's final admission advice was PASS with limitations; root closed its concrete
conditions. Grok returned init only and timed out at600s (native124,605.107s observed):
NO_ADVICE, not PASS, no retry or substitute. Peer advice was not a unanimity gate.

Generic `BLOCKED:init-failed` satisfies blocked rows; paired success rows prevent an
always-crashing implementation from passing. Lock placement, avoiding other-receipt
scans, unreadable/non-UTF-8 receipts, missing keys, dangling container links, unknown
status and linked-worktree refusal are not all independently exercised by the43
external CLI cases; candidate-added tests and source review cover some. The shared review producer excerpt is partial
and has mid-expression boundaries, an input limitation identical for both arms.

## Timing, usage and fidelity

| Added review + repair across two initials | Native seconds | Incremental output tokens |
| --- | ---: | ---: |
| S continued |277.046|5,831|
| F fresh |364.652|8,746|

Shared initial generation:564.630s and13,646 output tokens. Total1206.328 native
seconds. These exclude preparation, root assessment/replays, peer advice and delivery;
they are not total verified-completion time or a general speed/billing result.
S/F input tokens726,917/754,451 include492,288/545,792 cached. Resumed counters are
cumulative; subtract the sealed initial and check against native last_token_usage.
`METRICS.json` verifies both deltas. Reasoning is included in output, not added twice.

All calls report Astra/high, all four reviews have zero tool events and identical
paired packet hashes, with no observed compaction. All ten log the same native warning about the
under-development skip_host_skill_discovery feature and exit0. Current continuation
qualification (resumed token retained, fresh correctly returns UNKNOWN) and six
reused launcher regression tests pass (`QUALIFICATION.json`,
`runner-tests.log`). Root inspected75 native
commands and15 patch events: no observed reference/sibling/publication access.
Isolation is instructional with full-access tools, not a filesystem sandbox.
All six product seals/modes and frozen0197 input pins match; original five WIP files
match (`REGISTRATION.json`, `AUDIT.json`, `PRESERVED.json`). AST audit preserves
bootstrap main/pathname/admission/self-test functions, except the declared
`task:null` expected-state addition (`BASELINE-ASSERTIONS.json`); scope checks also
preserve the original smoke file. This is one macOS host; older Git was not tested
(`HOST.json`). Raw evidence is `.devlyn/0198`; participant
source/Git is retained in `../0198-participants`. Delivery/cleanup: `.devlyn/0198/FINAL.md`.

## Remaining frontier

Actual producer compatibility is now exercised, but it did not make the finite
oracle complete. Both0197 and0198 support validated review/repair without showing
fresh-context lift; they are related root-adapted tasks and must not be pooled as
independent field confirmation. Do not rerun these exposed tasks as confirmation.
Any future R1 request/reference/oracle must carry both branch witnesses. The
observed receipt bypass is in unshipped R1 code; harm to current shipped behaviour
was not established. A production helper repair needs that separate diagnosis. Mission1, field gate15 and
unrelated untouched confirmation remain OPEN. Preserve A16 and prior NO-GO results.
