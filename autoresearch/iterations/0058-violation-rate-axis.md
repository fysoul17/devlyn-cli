# iter-0058 — measurement-axis pivot: N-rep violation rate replaces headroom score-lift as the primary evolution gate

**Status**: PRE-REGISTERED 2026-07-04 (design locked; no measurement run yet).
**Trigger**: user direction 2026-07-04 (deep audit + evolution mandate) + queue
item 2 `[F]` deadlock — two fixture design generations (F34/F35 iter-0039,
F36/F37 iter-0041) all solo-saturated (solo 88-97), leaving ZERO
headroom-gate-passing fixtures. The score-lift axis on synthetic feature
fixtures is exhausted as an evolution signal (`benchmark/probes/README.md`
already retired the golden suite for the same reason).
**Pair convergence**: Codex GPT-5.5 R0 2026-07-04 (xhigh, read-only, own
file:line citations). Decisive criterion, named by Codex and adopted:
**"oracle matches North-Star failure mode."** The North-Star failure mode
today is not "model can't solve the task" (models ace verifiable coding
tasks by construction) — it is contract violations under temptation: drift,
silent fallbacks, scope leaks, skipped pipeline machinery. Fable 3/6, Opus
2-3/6, Sonnet 1-2/6 drift-bait violations (iter-0045, P3 CONFIRMED: no tier
clean) is the live, unsolved, discriminating surface.

## Hypothesis (falsifiable)

H-0058: for harness iterations whose target is compliance/drift/consistency
(prompt contracts, mechanical gates, doc changes), an N-repetition
violation-rate metric on the mechanical probe panel discriminates
improvement where the 4-axis judge score cannot (saturated), with
acceptable noise at N ≥ 4 reps per cell.

## Design

- **Primary gate (new)**: violation rate = violations / (probes × reps),
  measured per (model, probe) cell on `benchmark/probes/drift-bait/` +
  `benchmark/instruction-sensitivity/` Lane-B probes, scored ONLY by each
  probe's own `hidden/verify.sh` (mechanical, no LLM judge —
  hidden-oracle-fairness class F19/F21/F23 does not apply because verifiers
  are diff-mechanical and repo-local).
- **Noise floor first**: before any A/B claim, establish the per-probe
  rep-to-rep flip rate at N=4 on an unchanged HEAD (iter-0045 observed
  1/6↔2/6 flips at N=2; N=4 baseline quantifies it). An A/B delta smaller
  than the measured flip band is reported as "within noise", never as lift.
- **Headroom gate demoted, not deleted**: `headroom-gate.py` + score-lift
  contracts remain the gate for L2 *pair-lift* claims specifically (its
  original purpose — ceiling-illusion protection). It is no longer the
  gate that blocks evolution iterations.
- **Long-horizon queue-drain corpus (deferred, named precondition)**: the
  truest North-Star shape (multi-intent serial drain scored on end-state)
  enters only after a pre-registered end-state scorer exists (tests pass /
  scope-leak count / residual-artifact count — all mechanical). Without
  that scorer it repeats the hidden-oracle failure class. Not in iter-0058.

## Acceptance gates

1. N=4 HEAD baseline matrix exists for ≥2 models (sonnet + one other),
   with per-probe flip-band documented.
2. The gate is wired as the documented evolution guard (probe panel README
   + this file), replacing "find headroom fixtures" as queue item 2's
   blocked precondition.
3. No regression to existing guards: compliance cells + lint stay green.

## What this displaces

- Queue item 2's precondition "no headroom-passing fixtures exist →
  user direction required" is answered: stop authoring harder synthetic
  feature fixtures (asymptotic, per iter-0033g class); measure
  violation-rate instead. Cross-engine comparison arms (`--engines-config`)
  re-enter through the violation-rate matrix, not through score-lift.
- "Probes are thermometers, not targets" (user mandate 2026-07-04) still
  binds: fixes must close failure CLASSES (mechanical gates), never
  special-case a probe's specific bait.
