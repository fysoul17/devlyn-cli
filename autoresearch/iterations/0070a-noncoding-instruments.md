# iter-0070a — non-coding-axis instruments: admission kernel + Packet Utility Differential

status: **PRE-REGISTRATION DRAFT** (2026-07-11) — design three-way-converged
in `0070-loop-architecture-STUB.md` § "Non-coding exam corpus fold"
(Codex + Grok, 2026-07-10). **NOT ACTIVE**: per the 0070 STUB entry
condition, no cell RUNS until iter-0068 fully closes (admitted-set R1-gate →
A/C + no-suppression decision → closure) — active-experiment integrity, both
engines. This file authors the pre-registration ahead of that gate so
execution is instant on close; it runs no measurement. Amendable by the
0068 result (0068 itself was amended pre-gate).

## Why this exists (pre-flight 0)

One sentence: Block 8/10 says frontier coding saturates, so the harness's
differentiating value lives on the non-coding axes — this iter builds the
FIRST instrument that measures whether the harness produces a **better
work-packet for the next agent** (decomposition + meta-prompting + context
engineering, axis 2), measured mechanically by that next agent's outcome,
not by an LLM "good plan" rubric.

## Scope (this iter = kernel + ONE instrument)

1. **Non-Coding Admission Kernel** (shared substrate for all four 0070
   instruments; built here, reused by 0070b+).
2. **Packet Utility Differential** (the axis-2 measurement form — the one
   surface Block 10 named that had NO recorded instrument; Codex + Grok both
   flagged it as the genuine gap).

Counterfactual Intent Holdout (axis 1), Blind Design-Defect Differential
(axis 4), Root-Cause Recurrence rows (principles) are 0070b — designed in
the STUB, pre-registered later.

## Non-Coding Admission Kernel (the durable asset)

Fixtures are cohort-bound disposables; the kernel is the durable asset
(same lesson as 0068's bare-fails gate). Every 0070 instrument inherits:

- **Arms**: A (harness path) vs B (bare same-engine) + **C copycat**
  (bare-engine given the harness method) — C is REQUIRED for any moat claim
  (NORTH-STAR ops #17; A>B alone = method/harness lift, not a product moat).
- **Seats**: measured codex = `gpt-5.6-terra`, orchestrator/judge sonnet;
  sol is TEAM-ONLY, never a measured seat (seat correction 2026-07-10).
  fable never a test arm.
- **Calibration gate (pre-admission)**: a known-good and a planted-bad input
  must separate on the instrument's own oracle; no-op/base input must FAIL.
  Fails to separate ⇒ instrument is dead (not the fixtures).
- **Cohort identity**: CLI version + requested alias + runtime-resolved model
  + run id frozen into the manifest; alias/model drift ⇒ re-gate. A result
  is bound to its cohort; no "proves X forever" claim.
- **UNFAIR review** (0068 R-preFreeze rule): the oracle may assert only what
  the visible task/spec states or repo evidence determines — never punish
  spec-thinness the task never stated (that manufactures discrimination).
- **No-suppression controls**: a saturated/clean control on which the
  harness must NOT regress the engine's native outcome; quality claims ship
  only with the control clean (Block 8).

## Packet Utility Differential (design)

**Claim measured**: packet quality = next-agent outcome, mechanically.

- **Fixed downstream executor**, held identical across arms: a blinded
  mid-tier seat (codex-terra or sonnet; never fable). It consumes a
  work-packet and produces a solution scored by ONE hidden oracle.
- **Sole independent variable = who authored the packet**, schema-locked to
  the 0070 contract shape (`plan.md` LOCKED Original Intent + Project
  Acceptance + topologically-ordered task list + per-task acceptance stubs +
  intent digest). Schema-lock prevents the UNFAIR path-asymmetry confound
  (Grok: "A wins" must not mean "A emitted resolve-native paths bare
  couldn't").
  - **Arm A**: harness intake/decomposition path authors the packet.
  - **Arm B**: bare same-engine asked for the SAME schema.
  - **Arm C**: copycat — bare-engine given the packet-construction method.
- **Metrics, raw and separate** (never fused into one score until factors
  separate): downstream resolve rate, wall, violation count on the same
  hidden oracle. PLAN-DAG structural checks retained as DIAGNOSTIC
  attribution only, never the ship gate.

## Predictions (frozen before any run)

- **P1 (calibration — death gate)**: a minimally-different known-good packet
  vs a planted-bad packet must separate downstream outcomes on the fixed
  executor at N≥3. If they do not separate, the instrument measures executor
  noise, not packet quality → DEAD (report it; do not tune fixtures to force
  separation). N≥3 is a smoke/death gate, NOT final evidence.
- **P2 (harness delta)**: on ≥1 calibrated packet task, A-authored packet
  yields strictly better downstream outcome than B-authored (raw counts).
  NULL (A ≤ B) is a load-bearing finding: the harness's decomposition adds
  no next-agent value on this task.
- **P3 (moat)**: A > best_C ⇒ harness-method moat; C ≥ A ⇒ portable
  prompt-engineering (method lift, honestly labeled, not a product moat).

## Loss conditions

- **L1**: calibration fails to separate (P1) ⇒ instrument dead; do NOT ship
  a harness-delta claim on a noise-dominated executor (decisive criterion:
  **Mediated Causal Sensitivity**).
- **L2**: packet schema not locked ⇒ A/B differ in path shape not quality ⇒
  UNFAIR; fix the schema lock before any delta claim.
- **L3**: any moat claim on A>B alone without the C arm (ops #17 violation).
- **L4**: executor seat saturates (solves regardless of packet) ⇒ no
  headroom; pick a harder task or a different executor seat, report the
  saturation (do not claim discrimination).

## Deliverables (build after 0068 closes; Codex executes, orchestrator verifies)

1. **Executor seat calibration**: which fixed mid-tier seat is sensitive to
   packet-quality deltas without saturating — fresh measurement, not
   preference (UNRESOLVED from the STUB fold).
2. **Kernel runner**: A/B/C packet-authoring → fixed-executor downstream
   run → hidden oracle → raw resolve/wall/violation, with calibration +
   cohort-identity + no-op-fail baked in.
3. **≥2 packet fixtures**: each a repo state + a decomposable goal + ONE
   hidden oracle + a known-good/planted-bad calibration pair.

## Decisive criterion

**Mediated Causal Sensitivity** (Codex, R0 fold): the fixed downstream
executor must be provably sensitive to realistic packet defects while stable
on equivalent packets — else the instrument reports executor noise, not
context-engineering quality.

## Pair rounds

- R0 (pending, three-way): Codex-sol + Grok read this draft + the STUB fold +
  0068 fairness rules; return per contested point strongest-counter /
  strongest-form / synthesis + named criterion. Held: does drafting-ahead of
  0068 closure violate active-experiment integrity, or is a design-only
  pre-reg (no measurement) acceptable? Executor-seat-calibration design.
