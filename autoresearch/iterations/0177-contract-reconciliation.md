# 0177 — source-contract reconciliation execution screen

2026-09-15 KST. Mission 1 / intent coverage and repair closure.

## Why this unit exists

Pre-flight 0: this unit decides whether source-contract reconciliation wording
merits disjoint confirmation before changing the shipped PLAN/IMPLEMENT prompts.
Mission-bound (#7): it advances Mission 1's single-task intent-completeness gate;
no routing, model default, fleet, OS or memory dependency change is proposed.

The frozen H trace found valid-domain narrowing in a generated PLAN and tests.
Existing IMPLEMENT already says the spec outranks the plan, while PLAN and
IMPLEMENT call existing tests contract without distinguishing their origin.
This is a candidate influence, not proof of historical prompt causation.
Read-only evidence: `.devlyn/H-followup-20260915/TRACE.md` and `sources.json`.

## Registered comparison

Two new standard-library tasks cover Unicode length-framed labels and exact
Decimal sums. Each has an initial authoring task and an independent seeded-repair
task. Baseline/candidate use identical task inputs and native GPT-6 Astra/high
settings, with balanced serial order: eight fresh sessions, one per cell,
240 seconds each. The candidate replaces only “Existing tests are contract.” in each
phase with source/derived-artifact reconciliation and retains the other test protections; it is stored only in research
artifacts. Product prompts remain unchanged.

These are actual planning, coding, generated-test and focused-test executions,
using canonical PLAN/IMPLEMENT bodies as component guidance. They do not invoke
resolve or exercise full orchestration, BUILD_GATE, CLEANUP or independent VERIFY.
The repair seeds deliberately reproduce the failure class; they are independent
of authoring outputs. These are development tasks, not held-out confirmation.
No bare/solo/pair ranking, H rerun or full-resolution timing claim follows.

Prediction: candidate wording reduces valid-domain rejection/altered-result
failures while retaining invalid-input rejection, original tests and scope.
Any candidate regression or no paired correctness improvement means no promotion.
A positive exploratory result permits only separately registered disjoint,
repeated confirmation. No rerolls, favorable task replacement or mid-run tuning.
Infrastructure, identity or custody failures stop collection visibly.

Original tests are immutable; generated regression tests and plans have explicit
provenance and may be corrected within the authorized surface. Root's independent
checker is kept outside participant workspaces and is applied only after observed
writer quiescence. Calibration passes 36/36 text and 20/20 Decimal assertions on
positive implementations; both known-defect seeds and invalid-admission mutants
fail. This finite calibration does not prove completeness for unbounded inputs.

`debug prompt-input` lacks `--ignore-user-config`; its initial argument failure
is preserved. Corrected nonexecuting renders show zero Devlyn cards and 24
identical other cards. Runtime `exec` ignores user config and project documents,
disables specified extensions and uses workspace-write. Exact runtime catalog
isolation is not established. HOME and CODEX_HOME are unchanged.

## Result

**INCOMPLETE; no promotion.** Registration `c7b4ef40aa4d9c84ef25581bf238a03ff61e5a53b97e7ab83a7f6155dc8bd912`
was frozen before the first execution. Native headers report GPT-6 Astra/high.

| Cell | Independent checks | Native result | Component seconds |
| --- | --- | --- | ---: |
| Text author baseline | 36/36 | Exit 0; suite and scope pass | 136.901 |
| Text author candidate | 36/36 | Exit 0; suite and scope pass | 140.817 |
| Decimal author candidate | Ineligible | 240s timeout; exit 124 | 245.732 |
| Remaining five cells | NOT_RUN | Registered stop | — |

Both completed products preserve original tests and include 10 generated test
methods; all 12 tests pass in each suite. Text is a tie on the registered checks,
not evidence of equivalence in general. Times measure native component work,
not end-to-end verified completion. Whole-run output and monetary cost are unknown.
The Decimal candidate wrote a PLAN but left the implementation stub. Its raw
0/20 assessment is retained as an incomplete-artifact diagnostic, never a quality
loss. The controller observed all owned writers quiescent; no further draw ran.

### Post-timeout fixture diagnosis

The candidate's own native boundary probe (`decimal-author-candidate/stderr:215–230`)
showed an unrepresentable result at Decimal's internal exponent limit. Root then
predicted and reproduced a ten-input counterexample without editing the frozen
reference: ten finite `Decimal((0, (1,), MAX_EMAX))` inputs require the exact sum
`1e(MAX_EMAX+1)`. Both direct result construction and the registered nominal
positive raise `InvalidOperation` (`DECIMAL-REPRESENTABILITY.json`).

The [Python Decimal documentation](https://docs.python.org/3/library/decimal.html#decimal-objects)
confirms that exceeding the C implementation's internal limits can invalidate
construction. Thus this fixture's unconditional exact-Decimal-output promise
cannot be met over its stated input domain in the tested runtime. Initial 20/20
calibration was insufficient; this is an owner-authored fixture defect, not a
proven harness/model failure. The boundary probe preceded timeout, but its causal
contribution to timeout is unproven. Neither the spec nor the original scores
were rewritten to make the run pass.

### Review and preservation

Admission Fable/Grok advice was NEEDS_WORK. Root accepted ambiguous-scoring and
test-protection findings before admission: froze a conjunctive per-cell decision,
restored skip/disable/assertion-count restrictions, required preserved original
bytes and positive/correct-negative repair coverage, and supplied missing custody
checks. The original draft and advice remain in `pre-admission-v0/` and
`admission-review/`. Unsupported bytearray/Decimal-constructor objections were
rejected with the actual spec and calibration evidence. Those reviewers did not
identify the later output-representability counterexample.

Final native Fable5.1 and Grok4.6 reviews returned PASS_WITH_ISSUES on this
no-go record. Root verified62 sealed inputs, final inventories, raw assessments
and equal actual launch selectors in `FINAL-SOURCE-CHECKS.json`. Reviewers did
not receive raw assessment/calibration/qualification bodies; their supplied-source
review is not independent execution. The selector came from0175 without its own
registration seal, so complete runtime isolation remains unclaimed. Candidate
PLAN excludes the planning artifact from its product scope; the component task
separately permits it. This is not a full BUILD_GATE result. Grok's final claim
that its admission verdict was not NEEDS_WORK is contradicted by its original
admission output:3; root retains that original verdict. `ADJUDICATION.json`
records the dispositions; no unresolved HIGH/CRITICAL remains on the shippable
record. Raw evidence is under `.devlyn/0177/`;
`STOP.json` separates operational stop, invalid fixture and absent comparison.
Product prompts, routing and model settings remain unchanged. Frozen H sources
and original-workspace WIP remain byte-identical. Delivery status is separate
from this unsuccessful experiment.

## Principles and continuation

Pre-flight 0 and #7 pass for the honest no-go record, not a product improvement.
#1 No overengineering: no production rule or phase added; #2 No guesswork:
original draws, timeout and disconfirming reference result remain visible;
#3 No workaround: no reroll, narrowing, rescore or promotion; #4 Worldclass:
the invalid fixture disqualifies comparison and must be replaced before another
study; #5 Best practice: standard Python primitives and the existing bounded
controller; #6 Layer-cost-justified: no efficiency or added-layer value claimed.
Removing the stop or counterexample from the report would conceal distinct
failures; no additional product prose is justified.

Mission 1 remains active. The actual seeded-repair comparison was not reached.
Before another registered comparison, calibrate required output representation
as well as allowed input boundaries, and justify runtime bounds prospectively.
Replace the invalid fixture in new work; preserve0177 and do not resume its cells.
No generic prompt addition, H fixture polish, routing change or successful core
improvement follows from this record.
