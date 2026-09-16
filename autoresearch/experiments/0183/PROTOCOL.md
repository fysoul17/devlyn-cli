# 0183 — easy work with verification and cleanup versus actual resolve

Owner clarification, 2026-09-16: resolve's engineering checks, scoped cleanup,
independent review and repair loops serve quality. The hypothesis is that easy
work can retain quality while avoiding the cost of the full phase graph.
0182 only compared direct instruction surfaces; it cannot answer this question.
The research owner's direct route does not prohibit executing resolve as a control.

## Treatments and prediction

- A: native execution, no project instruction addition.
- B: unchanged 0179 direct contract: implementation, required verification,
  scope review, own-debris cleanup and failure-driven repair/recheck.
- C: actual committed resolve, explicitly invoked with
  `--spec spec.md --no-pair --no-risk-probes`.
  PLAN, IMPLEMENT, BUILD_GATE, CLEANUP, independent same-model VERIFY, applicable
  internal repair, final report and archive are mandatory. No phase bypass.

This is a forced-full counterfactual for easy work, not today's automatic routing
(0172 already permits direct work). `--no-pair` isolates the phase-graph cost;
it does not remove the independent primary judge. Conditional OTHER-model risk
probes are also explicitly off for this easy-work isolation. OTHER-model contribution and
routing accuracy remain separate experiments. Supplied specs avoid conflating
requirements discovery or the free-form-only SURFACE_CLOSE with execution.

Prediction before draws: B and C complete the supplied easy cases without
unresolved high-severity defects; B uses less end-to-end native wall time than C
because it avoids repeated fresh-worker dispatch/context and phase bookkeeping.
This is a hypothesis, not an assumed quality equivalence or measured explanation.

## Cases and execution

Use the real `scripts/skill-token-gauge.py` at f6be1fb69e67b284fdb286a711c9c5bccb18ee00.
Two new, root-authored scoped developer-tool improvements: selectable repository
root and skill filtering. No production persistence, security or concurrency
change. Same original source and supplied acceptance inputs for every treatment;
requirements are read-only. These are source-backed tasks, not independently
sampled human requests or a representative workload. Exposed0180–0182 stay frozen.

Two fresh runs per case/treatment, sequential: root1 A/B/C; filter1 B/C/A;
root2 C/A/B; filter2 C/B/A. No treatment selection by earlier outcomes. All parent,
worker and primary judge requests use gpt-6-astra/high, same CLI version/native
auth, no personal instruction/config/memory contamination. Full workers keep
their canonical sandbox and wrapper contracts. All parent processes have the
same capabilities; treatment-specific instructions and worker count are intended.

Before registration, qualify the actual full workflow on a disposable unrelated
one-function task; retain all failures and preparation time separately. A failed
qualification stops quality launches until its cause is understood. The research
owner must not silently repair a quality product or complete its pipeline.

Each quality run has an equal 1800s native bound, with the existing controller's
1830s total bound. No reroll. Infrastructure/contract failure is reported as such
and stops later launches for diagnosis, rather than being a product-quality win.
Model-generated extra work counts. Preserve every prompt, command stream, receipt,
terminal result, source diff and declared setup hash. Do not use event-arrival gaps
as command duration. Report aggregate parent AND child usage without double counting;
if billing is unavailable, dollar cost is UNKNOWN.

## Assessment and decision

Seal outputs before external assessment; never feed held-out checks into a draw.
First score functional requirements, preserved regression behavior, scope and
task-created debris. Separately score treatment fidelity: a code pass with missing
C phases/archive is not a completed full-run comparison. Check pipeline receipt,
fresh judge, post-cleanup mechanical evidence and repair/recheck when triggered.

Report per-matched-run and total completion, native wall time through final reply,
external assessment time, all observed usage, phase spans and repair rounds.
Phase spans include worker activity and are not pure compute time. Verification/
cleanup performed within one B process may have no trustworthy separate duration;
keep it UNKNOWN instead of constructing a decomposition. Delivery of research and
preparation costs are reported separately from participant task completion.

Calibration must reject original missing features and representative broken
implementations and accept an independently written reference. Checks exercise
the actual CLI, including ordinary unchanged behavior and temporary fixture cleanup.
No product instruction promotion from this small screen alone. Repeated benefits
may justify a further fresh workload confirmation; regressions require investigation.
Independent OTHER-model review/repair needs a matched self-review/repair control
and includes false-positive harm. Do not infer its value from source advice alone.

## Custody

Research task receipt: 2137acb862ccbc4bb2ae8500. Disposable native homes live in
its owned scratch and are removed after writers stop. Participant source/Git and
pipeline evidence are retained outside scratch, with local-only task ownership.
No experiment product is published as a production fix. Original workspace WIP,
accepted0182 evidence and A16 are untouched.
