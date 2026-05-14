# F8 — Notes

## Purpose

The known-limit fixture. Documents where the harness may NOT beat bare. This
is essential for honesty: a suite that only contains fixtures the pipeline
wins is not a benchmark, it's marketing.

## Expected outcome

Margin ∈ [-3, +3] is the expected range. Both arms should produce small,
reasonable improvements. The judge may slightly prefer one or the other
based on taste.

Pair-candidate status: rejected by design. F8 is a known-limit ambiguity
barometer whose expected margin is a tie range, not pair-lift evidence.

Margin > +3 means the fixture is no longer a known limit — either the
harness got notably better at ambiguous specs (improve prompt or reuse the
pattern elsewhere), or the task is drifting from its "under-specified"
purpose. Either way, revisit.

Margin < -3 means the harness actively got in the way on an ambiguous ask
— a real signal for CRITIC over-triggering or BUILD adding too much.

## Failure modes detected

- **Sweeping refactor.** Arm rewrites the whole CLI in response to a
  vague ask. Spec constraints catch it (no breaking changes, no new
  subcommands).
- **Silent inaction.** Arm outputs "no changes needed" without doing
  anything. Ship-gate catches via zero-diff → 0 score on multiple axes.
- **Over-scope interpretation.** Adding three unrelated features "because
  they'd all be improvements".

## Pipeline exercise

- Phase 0 routing: standard.
- Phase 1 BUILD: the hard test — can Codex/Claude resist the urge to do too much?
- Phase 3 CRITIC scope discipline axis: penalizes over-scope.

## Why this fixture is allowed to tie or lose

Ambiguity is genuinely hard. An expert human would ask a clarifying question
first. Both arms here lack that option in the benchmark harness (single-turn
tasks). The fixture is a BAROMETER, not a pass/fail gate.

## Rotation trigger

If the pipeline consistently beats bare by > +3 on this fixture for two
shipped versions, the fixture has stopped being a known limit — either
replace with a harder ambiguity, or graduate the pipeline's ambiguity-
handling into a proper feature of the harness.
