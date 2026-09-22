# 0206 — prospective development tasks and budgets

2026-09-22 amendment: [approved observational contract](../0210/AMENDMENT.md)
supersedes its explicitly named enforcement and advancement clauses before any draw.

2026-09-22 KST. Continues0201 step3 after0205/PR86. Root direct, no resolve.
This registration fixes task selection, requirements, arm policy, ceilings and
decision rules. **No participant may launch from this document alone.** The
execution seal described below must first bind the actual runner, evaluators,
calibration and accounting controls. This is not a spending approval, launch
receipt, complete experimental apparatus or product adoption.

## Selection before outcomes

Four public requests in two real upstream codebases, outside the installer and
completion-receipt research family. `tasks.json` is the frozen caller contract;
its clarifications are benchmark requirements, not upstream-maintainer decisions.
Use the full pinned repository, not an extracted miniature. These are selected
development tasks, not an untouched confirmation cohort or a field trial.

| Task | Stratum | Interaction determining difficulty before draws |
| --- | --- | --- |
| D1 Commander2614 | routine | Unicode placeholder recognition while preserving existing separator syntax |
| D2 Click2740 | medium | inherited and overridden error rendering, stream routing, color and exit behavior |
| D3 Commander2530 | hard | two parsers across a real child-process boundary, delimiter position, repeated delimiters and existing in-process behavior |
| D4 Click2645 | hard | deferred FIFO opening, real writer/reader synchronization, ordinary-file early errors and resource ownership |

Selection inspected issue bodies and current source, not linked solution PRs.
Public issue bodies contain suggested fixes; all arms receive the same source
material and clarifications. Model pretraining exposure is unknown. A repository
search found Commander2530 was considered, not run, in0135. Click3362 was actually
run in0137 and was excluded before selection. No native failure outcome selected
these tasks. `baseline-probes.py` checks task existence, not model difficulty.
No task is replaced based on a participant result. If a baseline fails to
reproduce or a requirement cannot be evaluated, amend before any draw, or stop.

## Arms and common capabilities

A: strong native task execution. Supply original request and common execution
contract; native inspection, tests, repairs, independent review and subagents are
available. Do not force a weak one-shot or forbid A from choosing a reviewer.

B: same request/common contract plus the byte-identical0204 `owner.md` candidate.
Its owner selects review from observed interactions; no separate PLAN, BUILD or
CLEANUP models. No new resolve invocation in any arm.

C: same native task execution as A, plus a mandatory independent final review,
repair of actionable findings and fresh review after any repair. Use the same
review capability available to A/B. A review without source/check evidence is
not completion. C is a simple workflow alternative, not a test of one phase.

Owner requested identity: Codex `gpt-6-astra`, effort `high`. Same-model native
children use that identity. Independent reviewer: Claude `claude-fable-5-1`,
effort `medium`, max240s/call. These are requested identities, not evidence of
availability: retain native identity/usage and fail closed on mismatch. No Grok
substitution in a draw. Actual Fable/Grok advice on registration is outside draws.

Each cell has one owner session and at most four descendant model invocations,
counting all generations of native children and reviewers together. An invocation
is a dispatched session (redispatch/resume consumes another slot); provider turns
within it count toward usage, not extra session slots. At most two independent
reviews, within that same pool. After the second review, confirmed actionable
findings leave the cell PRODUCT_INCOMPLETE; no third review or unreviewed repair.
Tools are not model invocations.
No owner restart/retry, top-up or replacement draw. A may use the entire pool;
B/C gain no extra calls or tokens. Missing lineage or unauthorized model calls
invalidate accounting and stop further collection. Limits apply recursively.

Common tools: shell, local read/write/search, Git, native subagents and identical
review transport. All receive the same pinned repo, issue text, caller contract,
public tests and dependency environment. No network research or access to other
participants, oracle/reference, private user repos, solution PRs, memory or
installed devlyn instructions. Use isolated native configuration and transcript
audit; do not call instruction-level separation an OS security boundary. Explicit
model/pin routes fail closed. No push, release, upstream comment or user-config edit.

## Finite budget and serial order

Two repetitions, four tasks, three arms =24 maximum whole-task cells. Each task
uses serial A/B/C then C/B/A, with task order D1,D2,D3,D4. Identical limits apply
within a task. Fixed order is auditable but does not eliminate temporal/cache bias.

| Stratum | Per-cell wall seconds | OUTPUT tokens | Input tokens, cache included |
| --- | ---: | ---: | ---: |
| routine | 900 | 20,000 | 400,000 |
| medium | 1,200 | 30,000 | 800,000 |
| hard (each) | 1,800 | 50,000 | 1,200,000 |
| All24 cells | 34,200 (9.5h) | 900,000 | 21,600,000 |

Wall time starts at owner dispatch and ends only after owner and all descendants
are quiescent, including review, repair, checks and termination cleanup. A child
uses only the owner's remaining time; reviews also have the240s limit.
Reserve termination/reaping time inside these limits, never as an added allowance. Parent wall contains
child wall; never add overlapping spans. A deadline failure remains a failure,
not a fast solution. No efficiency metric for incomplete products.

Token ceilings count every owner/child/reviewer, failed call and retry (if one
occurs, it also violates policy). Use terminal per-call totals, deduplicated by
response/session lineage; never sum cumulative stream samples. OUTPUT includes
reasoning once. Input includes cached reads/writes once under each provider's
documented counters, with those components also reported separately. Do not add
a parent's inclusive child total again. Unsupported accounting is UNKNOWN.

The launch seal must demonstrate live whole-tree budget observation and bounded
termination using non-model controls. Counter updates can overshoot at most the
last observed event; record actual overshoot, mark the cell BUDGET_EXCEEDED and
stop collection. Never describe an event-granularity cap as exact token control.
Missing or delayed-unbounded usage observation blocks launch, not merely reporting.
Max120 total model invocations; actual counts include native descendants. Total
caps are ceilings, not quotas to consume. Billing/USD remains UNKNOWN unless
complete actual billing can be attributed; token ceilings are not dollar caps.

External blinded assessment gets at most one Fable240s call per sealed cell
(8,000 OUTPUT/call;24 calls,5,760s,192,000 OUTPUT) plus deterministic checks max120s/cell (2,880s).
Assessment is outside participant budgets and cannot feed repairs. Assessment
input is capped at400,000/cell (9,600,000 total); missing usage stops assessment.
Collection plus assessment ceilings:42,840s,1,092,000 OUTPUT,31,200,000 input,
144 model invocations. Root preparation, registration review and delivery are
separate/UNKNOWN, so these are not all-project cost totals. The48 confirmation
ceiling is reserved only: no tasks, execution budget or permission inferred here.

## Completion and prospective decision

Prediction: B preserves every A-completed matched cell and every stratum's A
completion count, then earns one of the two gates below. Passing checks alone
is not semantic completion. Require the whole caller contract, unchanged
protected files, scoped product/tests/docs, credible executed regression evidence,
truthful claims and zero unresolved HIGH/CRITICAL findings. Candidate-added
destruction, constraint violation or false completion blocks advancement.

Report COMPLETE, PRODUCT_INCOMPLETE, JUSTIFIED_REFUSAL, INFRA_INVALID,
BUDGET_EXCEEDED and NOT_RUN separately; only COMPLETE counts as success.
Seal product/diff/transcript before assessment. Give assessors anonymous source,
request and actual checks, removing arm instructions, timings and other verdicts.
Root's transcript/scope audit is explicitly not blind. Retain potential source
style leakage. Reviewer agreement does not replace executed counterexamples.

Development advancement requires the quality floor above, no missing telemetry,
and routine paired medians for B/A time and OUTPUT <=1.10 with no unnecessary
delegate on routine cells (judge its task-specific purpose, not its label). Both
D1 A/B pairs must be COMPLETE; otherwise this screen stops INCONCLUSIVE. Then either:

1. Quality: B fully solves at least one more of the four hard cells than A.
   B's summed all-attempt time, OUTPUT and input must each be <=C's corresponding
   sum for the hard cells. Compare failures as well as successes.
2. Efficiency: B preserves every A- and C-completed cell, and four B/C complete
   pairs across both hard tasks exist. Across all matching COMPLETE B/C cells
   (all four tasks), median paired B/C time or OUTPUT <=0.70,
   the other <=1.00, and summed all-attempt input <=C. Full attributable billing,
   if available, must not worsen; absent billing permits only time/OUTPUT
   advancement, never a total-cost adoption claim.

For paired medians, compute per-task/per-repetition ratios on matching COMPLETE
cells, then the ordinary median (average the two middle values for even counts).
Always publish all-cell completion and consumption alongside paired results.
The C selection rule takes precedence over both advancement gates: if C
preserves all A and B completions without extra safety failures, satisfies the
same routine gate using C/A, and has four COMPLETE hard B/C pairs across both
tasks, compare C/B over all B-completed matched cells. If both time/OUTPUT
medians are <=1.00 with one <=0.70 and all-attempt time/OUTPUT/input totals
are no worse than B, select the simpler route. Otherwise evaluate B against
its stated floor and gates. If quality saturates
and no material efficiency gate passes, stop; a saturated quality tie alone is
not positive evidence. Negative/inconclusive stops this screen. No automatic
task replacement or additional screen. A single targeted redesign is possible
only under0201's separately registered new budget/material.

Advancement permits a separately sealed untouched confirmation cohort, not
adoption. Preserve0201's confirmation +2/8 hard quality and30% efficiency gates,
second-engine contract checks, installation/migration and Mission1/gate15 OPEN.
No full-resolve equivalence, Windows portability or broad domain superiority.

## Required execution seal, before the first model draw

Commit hashes for this registration, candidate/common/arm prompts, issue snapshot,
full upstream Git tree, dependency locks, actual binaries/config, permissions,
order and task scopes. Freeze executable public/heldout evaluators, positive
reference and named incomplete mutants for every requirement, with raw calibration
results. Verify real child dispatch for D3 and real FIFO handshakes/cleanup for D4;
unit mocks alone cannot qualify. No solution/reference enters owner context.

Freeze runner and accounting/descendant termination tests; demonstrate equal
capabilities including A native subagents, mandatory C review and B adaptive
selection. Record actual available identities, environment and whole-call usage
before collection. Any change after a draw preserves old results, stops collection
and needs a named prospective amendment; never regrade the old cohort silently.
These are remaining execution-admission checks, not permission to grow a new
scheduler or fix unrelated product residuals. Reuse existing bounded transport.

Principles: **No guesswork** fixes predictions and thresholds before outcomes;
**No overengineering/Optimized** reuse the candidate and transport;
**Production ready/No workaround** make unavailable accounting block dispatch.
