---
iter: "0033c"
title: "NEW L2 vs NEW L1 — pair-mode lift on `/devlyn:resolve` VERIFY/JUDGE"
status: PROPOSED
type: measurement — third gate for Phase 4 cutover
shipped_commit: TBD
date: 2026-04-30
mission: 1
gates: iter-0034-Phase-4-cutover (paired with iter-0033a + iter-0033 C1)
codex_r05: 2026-04-30 (256s §G — adopt: NEW L2 vs NEW L1, NOT vs L0; gate on no-regression + lift on pair-eligible fixtures + efficiency)
---

# iter-0033c — NEW L2 vs NEW L1 on the `/devlyn:resolve` skill surface

## Why this iter exists (PRINCIPLES.md pre-flight 0)

Phase 4 cutover deletes `/devlyn:auto-resolve`. Post-cutover, OLD L2 (Codex BUILD/FIX + Claude orchestrator) is gone forever. NORTH-STAR.md "two user groups, both first-class" requires **L2 to be measurable on the NEW skill surface** before the OLD surface is deleted — otherwise we ship Phase 4 with the L2 contract claim degraded to "unproven/disabled".

Codex R0.5 §G (2026-04-30): "If you skip iter-0033c, Phase 4 can only honestly ship an L1 cutover while marking L2 unproven/disabled. That conflicts with the current NORTH-STAR first-class L2 contract."

User adjudication 2026-04-30: include iter-0033c (= keep L2 first-class).

The user-visible failure this closes: shipping Phase 4 without L2 measurement = silently downgrading the multi-LLM-pair experience for users who installed Codex CLI. They get a harness whose pair-mode mechanics are documented in NORTH-STAR but never measured on the surface they're invoking.

## Mission 1 service (PRINCIPLES.md #7)

L2 measurement is single-task scope (one fixture at a time, no parallel-fleet). Mission 1 hard NOs untouched.

## Hypothesis

NEW `/devlyn:resolve` confines pair-mode to **VERIFY/JUDGE only** (per iter-0020 falsification + NORTH-STAR pair-vs-solo policy table, 2026-04-30 lock). The hypothesis under test:

> **For fixtures where L1 was tied or lost vs L0** (the "pair-eligible" set), enabling L2 (`--pair-verify` or coverage-failed-triggered pair-JUDGE) materially lifts judge-axis margins via second-model deliberation in VERIFY, without regressing easy fixtures or violating wall-time efficiency.

This is the empirical question NORTH-STAR test #11 ("tool-lift vs deliberation-lift") is set up to answer. If pair-JUDGE produces conclusions different from solo-JUDGE often enough to shift the verdict on hard fixtures, L2 earns its budget. If pair-JUDGE merely re-confirms solo, L2 is theatre.

**Falsifiable predictions (BEFORE run):**

- **No regression**: every fixture in F1-F8 (F9 included once iter-0033a passes): `(NEW L2) − (NEW L1) ≥ −3` axes.
- **Lift on pair-eligible fixtures**: on the subset `{fixture | NEW L1 - L0 ≤ 0 in iter-0033}`, `(NEW L2) − (NEW L1) ≥ +5` on at least 50% of those fixtures (or +3 on at least 75%, whichever is empirically more sensitive).
- **No hard-floor violations**: zero NEW L2 disqualifier on previously-clean L1 fixtures; zero NEW L2 CRITICAL/HIGH `design.*` / `security.*` findings on previously-clean L1 fixtures; zero L2 watchdog timeouts.
- **Efficiency**: `L2_wall / L1_wall ≤ M` per fixture, where M is set so that a quality lift of `(L2 − L1) ≥ +3` justifies the wall-time delta on the per-fixture-best-of-M test (NORTH-STAR test #8 dominance rule). Concrete starting threshold: `M ≤ 2.0` (L2 may be up to 2× L1 wall-time); fixtures where pair-JUDGE fired AND (L2 − L1) > +5 may relax to `M ≤ 3.0`.
- **Tool-lift attribution** (NORTH-STAR test #11): the diff between L1 JUDGE and L2 pair-JUDGE conclusions is recorded per fixture; if the lift is mostly from a deterministic short-circuit fire (coverage_failed=true rerouting findings) and NOT from second-model deliberation differences, the result narrows the L2 design space (cheaper, more solo-default) and is recorded as data, not a fail.
- **Pair short-circuit discipline** (NORTH-STAR test #9): pair fires only when `coverage_failed=true` OR design.*/constraint.* findings present OR spec ambiguity flag set. No vibe-confidence pair fires.

## Predicted directions (filled BEFORE run)

- Easy fixtures (F1, F5, F8): L2 ≈ L1 within ±2. Pair short-circuits to solo most rounds.
- Pair-eligible fixtures (F2 silent-catch, F3 contract-risk, F7 out-of-scope-trap): L2 lifts L1 by +3 to +6 on at least 2 of these.
- Wall-time: L2 / L1 ratio ≈ 1.3-1.7× on average; spike to ~2× on F4 (browser) and F6 (dep-audit) where pair-JUDGE has more axes to evaluate.
- Tool-lift dominance: ~60% of L2's positive delta comes from deterministic gates firing differently (coverage triggers); ~40% from genuine second-model deliberation. (Numbers fabricated as null hypothesis; the iter measures the actual ratio.)

## Scope (locked)

### Ships in this iter

1. **L2 mode wiring verification**: confirm NEW `/devlyn:resolve` `--pair-verify` flag triggers VERIFY/JUDGE pair as documented in `references/phases/verify.md`. Smoke test: single fixture run with `--pair-verify` produces `state.phases.verify.sub_verdicts.pair_judge` populated AND archive contains a second JUDGE log from the second model.
2. **Harness arm**: extend `run-fixture.sh` to support a NEW L2 invocation. Two options (Codex R-final smoke decides):
   - Option A: existing `variant` arm under `--resolve-skill new` already invokes pair-verify when `--engine codex` is set on `/devlyn:resolve` (since pair-mode in NEW design picks the OTHER engine for fresh-subagent JUDGE).
   - Option B: add explicit `--pair-verify` flag to the NEW prompt for the variant arm, regardless of `--engine`.
   - Pick Option A if smoke confirms it triggers pair-JUDGE; otherwise B.
3. **Single suite pass at the same SHA as iter-0033 (C1)**: `iter-0033c-new-l2`, `--resolve-skill new`, F1-F8 (F9 included if iter-0033a passes), all 3 arms — `bare`, `solo_claude` (NEW L1, re-run), `variant` (NEW L2). Re-running NEW L1 in this pass keeps the L2-vs-L1 comparison paired (same env, same judge invocation).
4. **Tool-lift vs deliberation-lift split** (NORTH-STAR test #11): post-run analysis script reads each fixture's L2 archive. For each L2-vs-L1 delta, classify as "tool-attached" (delta explained by a different mechanical finding count) or "deliberation-attached" (delta explained by a different judge axis score with no mechanical finding change). Emits a per-fixture attribution row in the comparison artifact.
5. **Comparison artifact**: extend `scripts/iter-0033-compare.py` (or new `scripts/iter-0033c-compare.py`) to emit the L2-vs-L1 gate table.

### Does NOT ship in this iter

- BUILD pair-mode (iter-0020-falsified, NORTH-STAR-locked).
- L2 vs L0 comparison (Codex R0.5 §G — must be vs L1 to avoid compression risk per NORTH-STAR test #14).
- Changes to NEW skill prompts (this is measurement, not tuning).
- Phase 4 cutover.

### Subtractive-first check (PRINCIPLES.md #1)

- Could we skip iter-0033c entirely and ship Phase 4 with L2-disabled? **Possible** but requires explicit NORTH-STAR contract amendment ("L2 first-class on Codex" → "L2 will be re-enabled post-cutover when measurable on the NEW surface"). User adjudicated 2026-04-30 against this. iter-0033c is the cheaper path.
- Could we use diagnostic data already collected from iter-0033 (C1) variant arm? **Partially**, but iter-0033 (C1) variant is non-gated and not paired-against-L1-in-same-run. iter-0033c needs a clean paired run for honest L2-vs-L1 comparison. The iter-0033 (C1) variant data informs hypothesis priors, doesn't substitute for the gated run.

## Codex pair-review plan

- **R0** (BEFORE harness change): send this design + Option A/B decision + tool-lift attribution script outline. Falsification ask: does the predicted-direction match what we know from iter-0020 + iter-0028 evidence? Is the +3 no-regression / +5 lift threshold the right place on the curve? Does Option A actually trigger pair-JUDGE in NEW design (verify by reading `references/phases/verify.md`)?
- **R-final smoke** (AFTER L2 mode wiring smoke): if smoke surprises (e.g. `pair_judge` not populated even with `--pair-verify`), open root-cause iter for the NEW skill before proceeding.
- **R-final** (AFTER suite run): raw numbers + tool-lift split + my draft conclusion.

## Acceptance gate (pre-registered)

| Gate | Threshold | Source |
|---|---|---|
| 1. L2 mode smoke | `state.phases.verify.sub_verdicts.pair_judge` populated; second-model JUDGE log archived | hypothesis |
| 2. No regression vs L1 | every fixture: `(NEW L2) − (NEW L1) ≥ −3` axes | NORTH-STAR test #6 + Codex R0.5 §G |
| 3. Lift on pair-eligible fixtures | on `{NEW L1 - L0 ≤ 0}` subset: ≥ 50% have `(L2 − L1) ≥ +5` OR ≥ 75% have `(L2 − L1) ≥ +3` | NORTH-STAR test #7 |
| 4. Hard-floor violations | zero L2 disqualifier on previously-clean L1 fixtures; zero L2 CRITICAL/HIGH `design.*`/`security.*` on previously-clean L1; zero L2 watchdog timeouts | PRINCIPLES.md #4 |
| 5. Efficiency | per-fixture `L2_wall / L1_wall ≤ 2.0` (3.0 ceiling on fixtures where (L2 − L1) > +5) | NORTH-STAR test #8 |
| 6. Pair short-circuit discipline | pair fires only on documented triggers (coverage_failed / design+constraint findings / spec ambiguity); no vibe-confidence fires recorded in archive | NORTH-STAR test #9 |
| 7. Tool-lift vs deliberation-lift attribution | per-fixture attribution row emitted; raw split recorded for design-space update | NORTH-STAR test #11 |
| 8. Artifact contract | inherits iter-0033 Gate 9 contract for L2 arm; PLUS `state.phases.verify.sub_verdicts.pair_judge` non-null on fixtures where pair fired | iter-0033 mirror + iter-0033c L2-specific |

**Gates 1, 2, 4 are ship-blockers.** Gates 3, 5, 6, 8 are quality gates (failure → root-cause). Gate 7 is data-gathering, not pass/fail.

## Phase 4 cutover dependency

iter-0034 Phase 4 cutover gates on **all three**:
- iter-0033a Gates 1-8 PASS.
- iter-0033 (C1) Gates 1-9 PASS.
- iter-0033c Gates 1, 2, 4 PASS (ship-blockers); Gates 3, 5, 6, 8 PASS or root-caused with documented disposition.

## Why this is not score-chasing (PRINCIPLES.md #0)

This iter cannot move benchmark margins on its own; it measures an L2 product surface that the cutover needs measured. Real shipping decision (Phase 4 cutover) — case (b) of pre-flight 0.

## Risk register

| Risk | Mitigation |
|---|---|
| L2 mode wiring smoke fails (NEW skill doesn't actually trigger pair-JUDGE) | Gate 1 catches this. Failure → root-cause iter for NEW skill VERIFY phase prompt. iter-0033c suite run blocked until smoke passes. |
| Tool-lift dominates deliberation-lift (≥ 80% of L2 lift is tool-attached) | Gate 7 records this. NOT a fail — it narrows the L2 design space (NORTH-STAR test #11). Documented in HANDOFF as future iter-0036+ trigger. |
| Pair fires on every fixture (short-circuit broken) | Gate 6 catches this. Failure → tune VERIFY/JUDGE short-circuit conditions in NEW skill. |
| Wall-time blows past efficiency gate on multiple fixtures | Gate 5 catches this. Failure → tune pair-JUDGE prompt for terminal verbosity, or narrow short-circuit. iter-0033c re-runs after fix. |
| L2 lifts on easy fixtures but not on pair-eligible (the "expensive theatre" failure mode) | Gate 3 specifically targets pair-eligible fixtures. Failure here means L2 isn't earning its budget on the cases that supposedly need it. Phase 4 cutover blocks; design-space rethink iter opens. |

## Principles check

- **#0 pre-flight**: ✅ closes user-visible failure (L2 contract claim).
- **#7 mission-bound**: ✅ Mission 1 single-task L2 surface measurement.
- **#1 no overengineering**: ✅ measurement-only; the L2 mode wiring already exists in NEW skill — this iter validates and gates it.
- **#2 no guesswork**: ✅ predictions filled BEFORE run; gates pre-registered.
- **#3 no workaround**: ✅ root-cause framing for failures.
- **#4 worldclass**: ✅ enforced via gate 4.
- **#5 best practice**: n/a (no skill code change).
- **#6 layer-cost-justified**: ✅ — this is the iter that operationalizes layer-cost-justified for L2.

## Open questions (resolve in R0)

1. Option A vs B for L2 invocation in `run-fixture.sh`: depends on whether `--engine codex` on NEW skill auto-triggers pair-JUDGE (`fresh subagent uses OTHER engine` rule, NEW SKILL.md:35) or whether explicit `--pair-verify` is required. Smoke #1 answers.
2. F9 inclusion: iter-0033a sequenced first; if F9 NEW passes there, include F9 in iter-0033c suite; if F9 NEW fails iter-0033a, iter-0033c runs F1-F8 only and F9 L2 is deferred.
3. Tool-lift attribution heuristic: how strict is "delta explained by a different mechanical finding count"? Concrete rule: if `len(verify-mechanical.findings) − len(L1 verify-mechanical.findings)` is non-zero AND the judge axis delta correlates (sign-aligned), attribute as tool-lift. Otherwise deliberation-lift. R0 to validate.

## Deliverable execution order

1. **R0** with Codex on this design + Option A/B + attribution heuristic.
2. Run L2 mode wiring smoke (single fixture, F1, with `--pair-verify` or `--engine codex`).
3. If smoke passes → harness change (Option A or B). If smoke fails → root-cause iter for NEW skill VERIFY phase.
4. Run iter-0033c suite at same SHA as iter-0033 (C1).
5. Apply ship-gate via attribution-extended comparison script.
6. **R-final** with Codex on raw numbers + tool-lift split.
7. Update HANDOFF.md + DECISIONS.md.
8. Combined with iter-0033a + iter-0033 (C1), file iter-0034 Phase 4 cutover.
