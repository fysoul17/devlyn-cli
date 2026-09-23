# 0216 — make the repository format gate executable, declared and evaluated

2026-09-23. User: design the formatting direction together with Astra. Root direct,
no resolve. Opus and Astra (gpt-6-astra/high, read-only) wrote independent R0s,
both chose option (c); Astra returned FREEZE in round 1. Design only: nothing dispatched.

## Root cause

In [0215](../0215/RESULT.md) the color detour disappeared, but review 1 flagged
two test lines as likely Prettier failures. The owner's Prettier probe exited 127
(not installed; the clone has no `node_modules`), so it measured widths by hand
(g12–14, 26,592 + 27,132 + 27,500 = 81,224 input, a sensitivity figure only),
reformatted and needed the mandatory fresh review, which crossed 400,000.
0213 B repeated the same repair. Why-chain: second review ← post-review repair ←
formatting was neither executable nor declared, so it surfaced only as an
unverifiable review claim. Separately, the evaluator
([check_cell.py](../0211/check_cell.py)) never checks formatting, so 0214 A was
graded COMPLETE while failing the repository's own `check:format` gate.

## Intervention (one bundled contract)

- Supply Prettier 3.8.3 (the commander lockfile version, sha512 integrity
  verified) read-only at `/control/prettier`; repository `.prettierrc.js` applies.
- Add one declared D1 public check, identical for owner and evaluator:
  `node /control/prettier/bin/prettier.cjs --check --no-error-on-unmatched-pattern lib/option.js tests/options.variadic.test.js tests/option.test.js`
  (exactly the D1 allowed paths; `tests/option.test.js` does not exist at base).
- New 0216 wrappers: preparation around `0215/prepare.py`; evaluation around
  `0211/check_cell.py`, which runs the same command in the same pinned container
  and conjoins it into `product_check_pass` and `checks.json` (so the blinded
  assessment sees it). Archives stay byte-identical; historical verdicts are not
  regraded, and prospective COMPLETE is reported as a separate, stricter predicate.
- No new owner instruction: [common.txt](../0211/common.txt) already requires
  running supplied public checks and the review packet already carries that
  evidence. Checking before review 1 is a prediction, not an enforced gate. Keep
  0215's color prefixes; no auto-format, review exemption or other change.

Availability alone would isolate cause better, but (c) was chosen because success
must mean independently verified quality. No component-level causal claim.

## Model-free precheck (done)

Pinned image, `NO_COLOR=1`, exact command above (`.devlyn/0216/precheck.txt`):
unmodified base, 0213 A, 0214 B and 0215 B final code pass; 0213 B and 0214 A
(graded COMPLETE) fail on `tests/options.variadic.test.js`.
Before dispatch still verify: prompt/argv/caller/hash bindings, and that a
format failure blocks prospective completion.

## Validation and prediction (stated before any run)

One fresh diagnostic-only D1 B cell under the 0215 setup, budgets and first-breach
stops; no retry, C cell or cohort promotion. Prediction: review 1 receives a
passing format result for its exact source; no later formatting repair; prospective
COMPLETE with known terminal owner-plus-review input **< 400,000**. Missing or stale
format evidence, a later format repair, quality failure, UNKNOWN usage or a
breach refutes the corresponding prediction. A pass shows feasibility only.

Evidence: `.devlyn/0216/` in the retained base checkout (facts, both Opus and
Astra rounds, precheck).
