---
iter: "0033f"
title: "PLAN-pair vs solo-PLAN — implementation iter (consumes iter-0033d closure as design baseline)"
status: PRE-REGISTERED-STUB
type: implementation — Phase 4 cutover gate (replaces iter-0033d as the gate after iter-0033d closed-design)
shipped_commit: TBD
date: 2026-05-03
mission: 1
gates: iter-0034-Phase-4-cutover (sole gate; iter-0033d closed as design-iter)
design_baseline: iterations/0033d-pair-plan-measurement.md §"CLOSURE — design-iter, no implementation, hand-off to iter-0033f"
parent_design_iter: iter-0033d (Codex R0+R0.5+R0.6 + principles-decision pair convergence on option B)
---

# iter-0033f — PLAN-pair implementation (full firewall design adopted from iter-0033d closure)

## STATUS: STUB — full pre-registration deferred to the session that picks up implementation

This file is a placeholder pre-registration. The session that picks up impl MUST draft full hypothesis, gates, predictions, and risk register BEFORE writing any code. Pre-registration is non-negotiable per PRINCIPLES.md #2 — the no-guesswork rule cannot be relaxed because the design baseline is already documented.

## Why this iter exists (PRINCIPLES.md pre-flight 0)

iter-0033d (PLAN-pair measurement) closed as design-iter on 2026-05-03 after Codex R0+R0.5+R0.6 enumerated 18+ structural leak surfaces the original spec had assumed away. Phase 4 cutover stays blocked on a measured PLAN-pair vs solo-PLAN comparison. iter-0033f is the implementation iter that consumes iter-0033d's closure as the locked design baseline and ships the measurement.

## Hand-off contract (FROM iter-0033d closure §D)

The session that picks up iter-0033f MUST:

1. **Read iter-0033d's CLOSURE section first** (`iterations/0033d-pair-plan-measurement.md` § "CLOSURE — design-iter, no implementation, hand-off to iter-0033f"). All 18 leak surfaces in §A are ship-blockers for iter-0033f. Each must either be closed by mechanism OR explicitly accepted as residual with documented inference impact.

2. **Pre-register a NEW hypothesis** (cannot recycle iter-0033d's hypothesis verbatim). The threat model is materially different post-leak-enumeration; the hypothesis statement must reflect that.

3. **Pre-register NEW gates** that incorporate items 1-18 of §A as ship-blockers. The 8-gate structure (1a-d smokes + 2/3/4 + 5/6/7 + 8) carries forward; thresholds restate; Gate 8 expands per §A items 12-14 (artifact persistence, archive lifecycle, IMPLEMENT prompt scan).

4. **Pre-register NEW wall budget**. Floor: ~19h per iter-0033d §B. Ceiling: iter-0033f may add 1-2h slack, no more.

5. **Cite iter-0033d closure §A items by number** in iter-0033f's gates so the design context survives across sessions.

6. **Sequence implementation per iter-0033d closure §D step 5**:
   1. SKILL.md cleanse (PHASE bodies free of pair-mode mention)
   2. Standalone `scripts/validate-plan.py` (deterministic schema + reserved-token script)
   3. Expanded Check 15 in `scripts/lint-skills.sh` (full scan list per §A item 11)
   4. `archive_run.py` updates (explicit moves per §A items 13-14) + IMPLEMENT-prompt-persistence (§A item 12)
   5. `run-fixture.sh` anon-WORK_DIR refactor (§A items 3-7)
   6. `judge.sh` + `iter-0033f-compare.py` anon-aware (resolve via out-of-tree anon-map.json written post-child-exit)
   7. `run-iter-0033f.sh` orchestrator + smokes 1a-d (mktemp per §A item 17)
   8. Suite (6 fixtures × 2 arms, ~6h serial)

7. **Codex pair-collab budget**: at minimum R0 on the implementation plan (against iter-0033d closure as design baseline), R-smoke after smokes 1a-d, R-final on suite raw numbers. Plan for additional R0.5/R0.6 if R0 surfaces 3+ blockers.

8. **Honest fallback** (PRINCIPLES.md anti-산으로-가지마): if R0 on iter-0033f surfaces a NEW structural blocker class not in items 1-18, escalate to user adjudication BEFORE drafting R0.5. Avoid the asymptotic-discovery pattern that made iter-0033d a design-iter.

## Suite (carried from iter-0033d, frozen)

- Fixtures: `{F2, F3, F4, F6, F7, F9}` (pair-eligible set, frozen from iter-0033c manifest).
- Arms: `solo_plan` (`--engine claude` no pair) + `pair_plan` (full firewall + Codex critic in PLAN; IMPLEMENT consumes only `.devlyn/plan.md`).
- Same HEAD, same env (anon WORK_DIR + RESULT_DIR), same IMPLEMENT engine (Claude). Only PLAN differs.

## Phase 4 cutover dependency

Same as iter-0033d, gated on iter-0033f outcome:
- iter-0033f ALL ship-blockers PASS → Phase 4 ships PLAN-pair as first product L2 surface.
- Any ship-blocker FAIL → Phase 4 ships solo-PLAN only; NORTH-STAR records L2 as research-only; `--engine` and `--pair-verify` flags removed.

## Mission 1 service (PRINCIPLES.md #7)

Single-task scope (one fixture at a time, no parallel-fleet). Mission 1 hard NOs untouched.

## Why this is not score-chasing (PRINCIPLES.md #0)

This iter measures whether multi-LLM pair-mode in PLAN improves IMPLEMENT outcomes vs solo. The measurement is the deliverable; benchmark margin movement is downstream of the measurement, not the goal.

## Risk register (carry-forward + new)

Carries forward iter-0033d's risk register entries (firewall leak, critic over-constrains, wall blowup, round-cap unresolved, Codex unavailable, score regression, Check 15 over-match) — see iter-0033d. NEW entries to add at full pre-registration:

- **Risk: implementation slips beyond ~19h** — mitigation: hard-cap at 24h; if exceeded, surface to user for option B-style design-iter close on iter-0033f itself.
- **Risk: unforeseen leak surface (item 19+) discovered mid-implementation** — mitigation: pause + Codex R-pause; if surface is structural, escalate to user before continuing.
- **Risk: anon WORK_DIR refactor breaks existing iter-0033c re-runnability** — mitigation: refactor lives behind a `--anon` flag in run-fixture.sh; pre-iter-0033f arms keep the legacy arm-named WORK_DIR.

## Principles check (carry-forward, restated for iter-0033f scope)

- **#0 pre-flight**: ✅ closes user-visible failure (Phase 4 cutover with unproven L2 surface).
- **#1 no overengineering**: ⚠️ now-substantial implementation (~11h) BUT each piece is justified by an iter-0033d §A item (no speculative additions).
- **#2 no guesswork**: ✅ predictions to be filled BEFORE run; gates pre-registered per item 3 of hand-off contract.
- **#3 no workaround**: ✅ structural firewall (anon paths + scrubbed state + standalone validator + IMPLEMENT prompt persistence + archive lifecycle stash); not silent strip.
- **#4 worldclass**: ✅ Gate 4 enforces zero new HIGH/CRITICAL on pair_plan arm vs previously-clean solo_plan arm.
- **#5 best practice**: enforced via existing CRITIC findings in VERIFY (carryover) + structural validator at PHASE 2 entry.
- **#6 layer-cost-justified**: ✅ Gates 5/6/7 measure wall budget; Gate 3 measures quality lift. ~19h infra cost for L2 layer is itself a layer-cost data point — if L2 fails Gate 3, the layer-cost argument falsifies and Phase 4 ships solo-only.
- **#7 mission-bound**: ✅ Mission 1 single-task scope.

## Pointers

- Design baseline (load-bearing): `iterations/0033d-pair-plan-measurement.md` § "CLOSURE — design-iter, no implementation, hand-off to iter-0033f".
- Codex round transcripts (in /tmp at iter-0033d close, may be purged): `/tmp/codex-iter0033d-r0/`. Distillation in iter-0033d §A is canonical.
- Sibling stub (PROJECT-coherence pair, separate measurement): `iterations/0033e-project-coherence-stub.md`.
