# F1 — Notes

## Purpose

Trivial-tier calibration. Every arm should one-shot this; it's here to catch
catastrophic regressions and to anchor the "saturation" end of the scoring
scale.

## Failure mode

- **Default-behavior regression.** Careless implementations add `--loud`
  handling but accidentally alter the default case (e.g., always uppercasing
  because the flag-check is misplaced). Verification commands 1 and 4 guard
  against that.
- **Scope creep.** Modifying unrelated code while "here" would be caught by
  both CRITIC design sub-pass and the `git diff --stat` spec requirement.

## Pipeline exercise

- Phase 0 routing: expected `standard` route (no risk keywords).
- Phase 1 BUILD: single-file edit.
- Phase 1.4 BUILD GATE: `node --check` + `node --test` both must pass.
- Phase 2 EVAL: minimal findings expected.
- Phase 3 CRITIC design: verifies diff surgical-ness.

## Rotation trigger

When both arms score > 95 for two consecutive shipped versions, replace with
a harder trivial fixture (e.g., one that requires handling a new flag
interacting with existing flag precedence).
