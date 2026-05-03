---
iter: "0034"
title: "Phase 4 cutover — ship 2-skill harness solo default + delete 14+ legacy skills + label L2 PLAN-pair research-only"
status: PRE-REGISTERED-STUB
type: cleanup + product-surface ship; Mission 1 cutover (NOT terminal gate — that's iter-0035 real-project trial per NORTH-STAR test #15)
shipped_commit: TBD
date: 2026-05-03
mission: 1
gates: iter-0035-real-project-trial (Mission 1 terminal gate; NORTH-STAR test #15)
parent_design_iters: iter-0033 (C1) PASS evidence (5/5 headroom fixtures, suite-avg L1−L0 +6.43) + iter-0033d/iter-0033f/iter-0033g CLOSED-DESIGN (PLAN-pair measurement deferred to research-only)
unblock_evidence: solo PLAN empirically world-class (iter-0033 (C1) PASS 5/5 headroom fixtures); L2 PLAN-pair measurement deferred per Claude+Codex independent big-picture review (option VI); see iter-0033g §"CLOSURE" for full rationale
---

# iter-0034 — Phase 4 cutover (2-skill harness solo default + legacy deletion)

## STATUS: STUB — full pre-registration deferred to the session that picks up implementation

This file is a placeholder pre-registration. The session that picks up impl MUST draft full hypothesis, gates, predictions, and risk register BEFORE writing any code. Pre-registration is non-negotiable per PRINCIPLES.md #2.

## Why this iter exists (PRINCIPLES.md pre-flight 0)

Three iters of design work (iter-0033d/iter-0033f/iter-0033g) attempted to measure PLAN-pair vs solo-PLAN cleanly. All three closed as design-iters because the threat model (child filesystem inspection) produces unbounded leak surfaces under filesystem-only isolation. Codex big-picture review found ZERO empirical evidence of subagent introspection in 6 months of benchmark logs. Claude+Codex independent verdict: ship Phase 4 cutover with solo PLAN default (already empirically world-class) + label L2 PLAN-pair research-only.

iter-0034 is the cutover iter that actually ships the 2-skill product surface. It is mostly DELETION work — removing legacy skills that no longer match the 2-skill design — plus doc updates. Solo PLAN behavior does NOT change.

## Hand-off contract (FROM iter-0033g §"CLOSURE" §D)

The session that picks up iter-0034 MUST:

1. **Read iter-0033g §"CLOSURE" first**, especially §D hand-off contract + §G principles-aligned closure rationale. The big-picture pivot is load-bearing.
2. **Pre-register a NEW hypothesis**. Cannot recycle iter-0033d/f/g hypotheses — this iter is product-surface ship + cleanup, NOT pair-mode measurement.
3. **Pre-register NEW gates**. Suggested structure (next session refines):
   - Gate 1: solo PLAN behavior unchanged pre/post Phase 4 cutover. Smoke: F1 + F2 + F9 single-fixture run on each side, scores byte-equal or within ±2.
   - Gate 2: legacy skill deletion complete. Lint/grep verify no references to deleted skills in `config/skills/`, `.claude/skills/`, `bin/devlyn.js`, `README.md`, `CLAUDE.md`.
   - Gate 3: doc surface updated. `/devlyn:resolve` SKILL.md PHASE 1 line 80 ("PLAN-pair unmeasured at HEAD") replaced with research-only label + unblock conditions cited. NORTH-STAR Phase 4 done. HANDOFF Mission 1 progress reflects cutover.
   - Gate 4: optional-skills/ directory contains `/devlyn:reap`, `/devlyn:design-system`, `/devlyn:team-design-ui` (per Phase 5 plan in HANDOFF).
   - Gate 5: post-cutover bench suite re-run on iter-0033 (C1) fixtures shows L1 numbers within variance of pre-cutover (proves no regression in solo behavior).
4. **Pre-register NEW wall budget**. Estimated ~6-8h: deletion + doc updates + suite re-run + closure.
5. **Sequence implementation**:
   1. Codex R0 on iter-0034 pre-reg (against iter-0033g §"CLOSURE" + iter-0033 (C1) PASS evidence as design baseline). Verdict expected CONVERGED (no adversarial threat model to find new classes against).
   2. Doc updates first (lowest risk, easiest revert): SKILL.md research-only label, NORTH-STAR Phase 4 done, HANDOFF Mission 1 progress, README, CLAUDE.md.
   3. Skill deletion: remove from `config/skills/` AND `.claude/skills/` mirror. Update `bin/devlyn.js` to remove references.
   4. optional-skills/ migration (if applicable for `/devlyn:reap`, `/devlyn:design-system`, `/devlyn:team-design-ui`).
   5. Mirror sync (`bin/devlyn.js -y`) + lint.
   6. Smoke runs on F1/F2/F9 (Gate 1) — verify solo behavior unchanged.
   7. Bench suite re-run (Gate 5) — pre/post comparison at same SHA.
   8. R-final + closure verdict.
   9. Commit per repo conventions. iter-0035 real-project trial unblocked.

## L2 PLAN-pair research-only label — explicit unblock conditions

iter-0034 ships the L2 PLAN-pair label. The label MUST cite explicit unblock conditions (not vague "future work"):

- **Unblock condition A**: container/sandbox infrastructure justified by other product needs (e.g. user-facing isolation feature, or third-party adapter sandboxing). When such infra ships for product reasons, PLAN-pair measurement gets it for free; iter-0033h+ becomes feasible at low marginal cost.
- **Unblock condition B**: empirical probe demonstrates subagent introspection in production. Methodology: run a fixture with leak surfaces present + prompt the IMPLEMENT subagent to "determine your arm via any introspection method." Observe whether claude actually executes `readlink /dev/fd/1` / `ps aux` / `/tmp` enumeration. If empirically observed, threat model is load-bearing and container infra justifies itself.

Until either condition triggers, L2 PLAN-pair stays research-only. The label is honest (not a workaround) per PRINCIPLES #3.

## Deletion list (per HANDOFF "Outstanding housekeeping")

To delete in Phase 4:
- `/devlyn:auto-resolve`
- `/devlyn:resolve` (OLD focused-debug variant, replaced by 2-skill `/devlyn:resolve`)
- `/devlyn:implement-ui`
- `/devlyn:design-ui`
- `/devlyn:team-design-ui` (→ optional-skills/ in Phase 5)
- `/devlyn:design-system` (→ optional-skills/ in Phase 5)
- `/devlyn:clean`
- `/devlyn:update-docs`
- `/devlyn:preflight`
- `/devlyn:evaluate`
- `/devlyn:review`
- `/devlyn:team-review`
- `/devlyn:team-resolve`
- `/devlyn:browser-validate` (→ kernel runner)
- `/devlyn:product-spec`
- `/devlyn:feature-spec`
- `/devlyn:recommend-features`
- `/devlyn:discover-product`
- `/devlyn:reap` (→ optional-skills/ in Phase 5)

End state: 2 product skills (`/devlyn:resolve` + `/devlyn:ideate`) + optional-skills/ for power-user surfaces.

## Suite (carry-forward, frozen for Gate 5 pre/post)

Bench suite identical to iter-0033 (C1): F1, F2, F3, F4, F5, F6, F7, F8, F9 + optional smoke set. Pre-cutover run captured at iter-0033 (C1) commit (`3bc86dd` + iter-0033b carrier fix); post-cutover run at Phase 4 cutover commit. Compare per-fixture scores within ±2 axes (variance band per iter-0027 N=5 evidence).

## Phase 5 forward queue (NOT in iter-0034 scope)

After Phase 4 cutover:
- iter-0035 — real-project trial (NORTH-STAR test #15, Mission 1 terminal gate)
- iter-0036+ — VERIFY-pair frozen-diff measurement (highest-priority L2 candidate per iter-0033g §H)
- iter-0033e PROMOTE — PROJECT-pair after defect-class oracle is ready
- ship-gate.py reframe (+5 floor → categorical reliability gate)
- F3/F6/F7 fixture-rotation (RUBRIC saturation rule)
- VERIFY MECHANICAL test-diff silent-catch scan (Codex R3 §3, deferred until N≥2 evidence)

## Mission 1 service (PRINCIPLES.md #7)

Single-task scope (cutover iter, no parallel-fleet, no worktree-per-task model). Mission 1 hard NOs untouched.

## Why this is not score-chasing (PRINCIPLES.md #0)

This iter ships an empirically world-class solo PLAN (iter-0033 (C1) +6.43 suite-avg) + cleans up legacy surface area. NO new measurement claim, NO L2 ship. Phase 4 closes a long-running cleanup commitment to user. Real-project trial (iter-0035) is the actual quality gate.

## Codex pair-collab plan

- **R0**: Codex reads iter-0034 pre-reg + iter-0033 (C1) PASS evidence + iter-0033g §"CLOSURE" directly. Falsification ask: any deletion that breaks something the 2-skill design still depends on? any doc update that would mislabel L2 status? Verdict expected CONVERGED.
- **R-smoke**: after Gate 1 smoke runs (F1/F2/F9 pre/post). Verify solo behavior byte-equal.
- **R-final**: after Gate 5 suite re-run. Verify L1 numbers unchanged within variance band.

## Pointers

- Design baseline 1: `iterations/0033-quality-ab-new-resolve-vs-old-auto-resolve.md` (iter-0033 (C1)) — solo PLAN PASS evidence.
- Design baseline 2: `iterations/0033g-pair-plan-impl-pmo.md` § "CLOSURE" — meta-strategic pivot to option VI.
- Design baseline 3: `iterations/0033d-pair-plan-measurement.md` + `iterations/0033f-pair-plan-impl.md` closures — full 28-item leak surface enumeration (preserved for if/when container infra ships).
- Memory lesson file: `~/.claude/projects/-Users-aipalm-Documents-GitHub-devlyn-cli/memory/project_iter0033g_asymptotic_firewall_lesson_2026_05_03.md`.
- Successor iters: `iterations/0035-real-project-trial.md` (TBD, post-cutover) + `iterations/0036+` (L2 candidates by priority).
