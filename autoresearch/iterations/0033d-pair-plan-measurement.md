---
iter: "0033d"
title: "PLAN-pair vs solo-PLAN — first L1-vs-L2 measurement on `/devlyn:resolve`"
status: PRE-REGISTERED
type: measurement — NEW Phase 4 cutover gate (replaces iter-0033c which closed FAIL)
shipped_commit: TBD
date: 2026-05-03
mission: 1
gates: iter-0034-Phase-4-cutover (sole gate; iter-0033a + iter-0033 C1 + iter-0033c all closed)
codex_r0_round3: 2026-05-03 (293s — verdict "유저 반박이 맞습니다"; round-2 ideate-solo verdict was burden-reversal; widened pair candidate set to ideate spec audit + PROJECT coherence + PLAN audit + VERIFY/JUDGE + CLEANUP-as-VERIFY-axis; PLAN-pair iter-0020-falsified framing in SKILL.md:80 is overreach (iter-0020 falsified Codex-BUILD, not PLAN-pair); honest "unmeasured" labels replace "solo wins"; PLAN-pair = first measurement priority)
codex_r05_round3: 2026-05-03 (230s — locked PLAN-pair-first sequence; PROJECT-coherence measurement design TBD via defect-class oracle (deferred to iter-0033e stub); NORTH-STAR carries both meta-policy + current-active state; ship-validated language tightened; commit shape compare.py-fix-first-then-policy)
---

# iter-0033d — PLAN-pair vs solo-PLAN measurement

## Why this iter exists (PRINCIPLES.md pre-flight 0)

iter-0033c closed FAIL. Phase 4 cutover deletes `/devlyn:auto-resolve`; without a validated L2 surface on NEW `/devlyn:resolve`, we ship Phase 4 with L2 unproven and the multi-LLM contract degraded.

User direction (2026-05-03): "**계획과 설계가 모든 파이프라인중에 가장 중요해.** 첫 단추가 잘못 끼이면 뒤에 아무리 둘이서 논의하고 북치고 장구쳐도 안된단말이지." Pair-mode investment belongs upstream (PLAN), not just downstream (VERIFY).

iter-0033c suite traced score regression to **upstream pair-awareness leakage** at orchestrator parse time (Codex R-final-suite Q2). PLAN-pair architecture has structural firewall — IMPLEMENT consumes only `.devlyn/plan.md` (clean contract artifact), never sees pair metadata. Different attack surface.

**User-visible failure being closed**: shipping Phase 4 with "two first-class user groups" NORTH-STAR commitment but zero validated L2 surface. Codex CLI users would get a harness whose pair-mode mechanics are documented but never measured.

## Mission 1 service (PRINCIPLES.md #7)

PLAN-pair measurement is single-task scope (one fixture at a time, no parallel-fleet). Mission 1 hard NOs untouched.

## Hypothesis

PLAN-pair (Claude proposer + Codex critic, structured HIGH/CRITICAL findings only, ≤3 rounds) produces a `.devlyn/plan.md` that leads to better IMPLEMENT outcomes than solo-Claude PLAN, **without IMPLEMENT seeing any pair metadata** (firewall mechanism makes leakage structurally impossible).

> Pair-PLAN improves the final implementation on high-value fixtures without leaking pair metadata or exhausting repair-loop budget.

### Falsifiable predictions (BEFORE run)

- Pair-PLAN wall ≈ 2× solo PLAN wall.
- Fix-loop iterations drop by ~50% (PLAN catches issues that would otherwise surface in VERIFY → fix-loop).
- Net run wall ≤ 1.5× solo baseline.
- Quality: pair-PLAN final implementation score ≥ solo-PLAN on every fixture (no regression worse than −3); ≥3/6 pair-eligible fixtures show material win (+5 score lift OR categorical rescue).

## Architecture (the structural firewall)

**Three-layer defense** (Codex round-2 R-final + round-3 R0.5):

1. **Two artifacts**: `.devlyn/plan.md` (clean contract — IMPLEMENT input only) + `.devlyn/plan.debate.json` (full transcript — staged out-of-worktree until IMPLEMENT completes, then copied to run archive). IMPLEMENT prompt is hard-coded to read ONLY `.devlyn/plan.md`.

2. **Schema separation**: `pipeline.state.json` exposes only `state.plan.contract_path` (the clean plan.md location) to IMPLEMENT. Debate path is NEVER in live state. New field `state.rounds.pair_plan` (capped at 3) — distinct from `state.rounds.global` (BUILD_GATE/VERIFY fix-loops).

3. **Pre-IMPLEMENT validator**: orchestrator hard-fails IMPLEMENT spawn if `.devlyn/plan.md` is missing, malformed, or contains reserved metadata tokens (`accepted_invariants`, `model_stamps`, `planning_mode`, `pair-plan`, `plan.debate`, `claude_draft_sha256`, `codex_draft_sha256`, `<round\s*\d+>`). Lint rule `lint-skills.sh` Check 15 (NEW): `references/phases/implement.md` must NOT reference debate artifacts or pair-plan metadata. Same lint rule applies to benchmark prompts in `run-fixture.sh`.

**Convergence rule** (Codex round-2 R0.5):
- Asymmetric proposer/critic: Claude proposes plan.md → Codex critiques structured HIGH/CRITICAL findings → Claude revises plan.md → Codex re-critiques.
- Stop when Codex emits **0 HIGH/CRITICAL** findings, OR `state.rounds.pair_plan == 3`, OR `wall_seconds > pair_plan_wall_budget`.
- At cap with unresolved HIGH/CRITICAL: BLOCKED PLAN, do NOT leak known-bad plan to IMPLEMENT.

**Codex availability**: missing → solo-Claude PLAN downgrade with `engine downgraded: codex-unavailable` banner per existing `_shared/engine-preflight.md` contract.

## Method

### Pre-suite smokes (cheap, gate the suite)

- **Smoke 1a (firewall validator)**: synthetic `.devlyn/plan.md` containing each reserved metadata token → pre-IMPLEMENT validator must hard-fail with the matched token name. ~10s.
- **Smoke 1b (Codex availability)**: `command -v codex` fail-fast at top of `scripts/run-iter-0033d.sh`. <1s.
- **Smoke 1c (lint)**: `bash scripts/lint-skills.sh` Check 15 — assert NO reserved metadata tokens in `references/phases/implement.md` or any benchmark prompt. <5s.
- **Smoke 1d (round-cap)**: synthetic plan with persistent Codex HIGH (mock) → orchestrator must hit cap-3 and emit `BLOCKED:plan-pair-unresolved`. ~30s.

### Suite arms

Per fixture in `{F2, F3, F4, F6, F7, F9}` (pair-eligible set, frozen from iter-0033c manifest):

| arm | description |
|---|---|
| `solo_plan` | `--engine claude` (no pair); equivalent to current solo_claude L1 baseline |
| `pair_plan` | structural firewall + Codex critic in PLAN; IMPLEMENT consumes only `.devlyn/plan.md` |

**Same HEAD, same env, same IMPLEMENT engine** (Claude). Only PLAN differs. Benchmark prompts are **byte-identical across arms** (Codex R-final round-2 lock); plan-mode selection is harness-internal, never appears in `.devlyn/plan.md`, live state consumed by IMPLEMENT, or IMPLEMENT prompts.

### Wall budget estimate

- Solo PLAN per fixture: ~5-10 min
- Pair PLAN per fixture (~3 rounds): ~10-20 min
- IMPLEMENT + BUILD_GATE + VERIFY same as iter-0033c (~5-30 min depending on fixture)
- Suite total: ~6 hr serial (Mission 1, no parallel-fleet)

## Acceptance gates (pre-registered)

| Gate | Threshold | Source |
|---|---|---|
| 1a firewall validator smoke | reserved-token plan.md → hard-fail with matched-token error | round-2 R-final + round-3 R0.5 |
| 1b Codex availability | hard `command -v codex` fail-fast | round-2 |
| 1c lint Check 15 | NO reserved tokens in implement.md OR benchmark prompts | round-2 R-final |
| 1d round-cap smoke | persistent HIGH → BLOCKED:plan-pair-unresolved at cap-3 | round-2 R0.5 |
| 2 No-regression | every fixture: `(pair_plan − solo_plan) ≥ −3` | NORTH-STAR test #6 |
| 3 Material wins (SHIP-BLOCKER) | ≥3/6 fixtures show `+5` score lift OR categorical rescue | round-2 R0.5 (tightened from ≥2/6) |
| 4 Hard-floor | zero new disqualifier on previously-clean l1; zero new HIGH/CRITICAL `design.*`/`security.*` on previously-clean l1; zero pair-induced timeout | iter-0033c 3-bucket carryover |
| 5 Aggregate wall | `aggregate(pair_plan_wall) / aggregate(solo_plan_wall) ≤ 1.5×` | round-2 R0.5 |
| 6 Per-fixture wall ceiling | NO fixture `pair_plan_wall / solo_plan_wall > 2.0×` UNLESS categorical rescue | round-2 R-final + round-3 R0.5 |
| 7 Hold-zone | `1.5× < aggregate wall ≤ 1.7×` = HOLD/root-cause; do NOT ship Phase 4 | round-2 R-final |
| 8 Firewall artifact contract | for every fixture: `.devlyn/plan.md` exists; `.devlyn/plan.debate.json` is in run archive (not live state); IMPLEMENT prompt log shows zero reserved tokens | round-3 R0.5 |

**Ship-blockers**: 1a, 1b, 1c, 1d, 2, 3, 4, 8.
**Quality gates**: 5, 6, 7 (failure → root-cause iter; Phase 4 holds).

## Phase 4 cutover dependency

iter-0034 Phase 4 cutover **gates on iter-0033d ALL ship-blockers PASS**:
- ALL ship-blockers PASS → Phase 4 ships PLAN-pair as first product L2 surface; OLD `/devlyn:auto-resolve` deletion proceeds; NORTH-STAR amends "shipped pair surface = PLAN".
- Any ship-blocker FAIL → Phase 4 ships solo-PLAN only; NORTH-STAR records L2 as "research-only, no shipped pair surface yet"; `--engine` and `--pair-verify` flags removed (still no pair product).

## Implementation scope (this iter)

### Ships in this iter

1. **`/devlyn:resolve` SKILL.md edits**:
   - PHASE 1 PLAN body: add proposer/critic mechanism (Claude proposes → Codex critiques structured HIGH/CRITICAL → Claude revises; ≤3 rounds; firewall outputs `.devlyn/plan.md` clean + `.devlyn/plan.debate.json` debate-only).
   - PHASE 0: REMOVE `--pair-verify`, `--engine` flag parsing (Codex round-2 R0.5 verdict). Update flag table.
   - PHASE 2 IMPLEMENT body: explicit "consumes ONLY `.devlyn/plan.md` + spec; reserved-token validator runs pre-spawn".
   - Strike "PLAN pair-mode is iter-0020-falsified" overreach at line 80.
2. **`references/state-schema.md` edits**: add `state.plan.contract_path`, `state.rounds.pair_plan` (capped at 3); document firewall contract.
3. **`scripts/lint-skills.sh` Check 15 (NEW)**: scan `references/phases/implement.md` and benchmark prompts in `run-fixture.sh` for reserved metadata tokens; fail with matched-token list.
4. **`benchmark/auto-resolve/scripts/run-fixture.sh`**: add `solo_plan` and `pair_plan` arms (mirror solo_claude env shape); DELETE `l2_gated` and `l2_forced` arms; benchmark prompt body byte-identical across solo_plan and pair_plan (only harness-internal arm name differs); skill invocation no longer carries `--engine` or `--pair-verify`.
5. **`benchmark/auto-resolve/scripts/judge.sh`**: ARMS_PRESENT discovery includes `solo_plan` and `pair_plan`; remove `l2_gated`/`l2_forced` from list.
6. **`benchmark/auto-resolve/scripts/run-iter-0033d.sh`** (NEW orchestrator): smoke 1a-d → suite per-fixture interleaved (solo_plan then pair_plan) → judge per fixture → manifest reuse from iter-0033c → `iter-0033d-compare.py` emits gate table.
7. **`benchmark/auto-resolve/scripts/iter-0033d-compare.py`** (NEW): 8-gate evaluator with the thresholds above.
8. **`.claude/skills/` mirror sync** of all skill changes.
9. **Codex pair-collab**: R0 (BEFORE implementation) on the firewall mechanism + lint Check 15 + run-iter-0033d.sh design; R-final-smoke (AFTER smokes) if surprises; R-final (AFTER suite) on raw numbers.

### Does NOT ship in this iter

- Pair-mode in any phase other than PLAN.
- Pair-mode in `/devlyn:ideate` (deferred to iter-0033e stub).
- pi-agent abstraction (Mission 2/3 territory).

## Codex pair-review plan

- **R0** (BEFORE implementation): firewall mechanism design + smoke 1a-d shapes + run-iter-0033d.sh structure. Falsification ask: any leak surface I missed? Any reserved-token category missing? Is round-cap-3 the right ceiling?
- **R-smoke** (AFTER smokes 1a-d): if any smoke fails, root-cause iter before suite.
- **R-final** (AFTER suite): raw numbers + 8-gate verdict.

## Risk register

| Risk | Mitigation |
|---|---|
| Firewall leak (e.g. orchestrator inlines `pair_rounds_used` into IMPLEMENT prompt for completeness) | Pre-IMPLEMENT validator + lint Check 15 + smoke 1a synthetic test |
| Codex critic over-constrains plan (raises spurious HIGH from sandbox-only premise) | Critic findings must cite spec/expected.json/code evidence; speculative defensive expansion stays in debate archive only |
| Pair PLAN wall blowup (>2× per fixture) | Gate 6 catches per-fixture; Gate 5 catches aggregate; round-cap-3 hard limit |
| Round-cap-3 hits with unresolved HIGH | BLOCKED:plan-pair-unresolved verdict; no leak to IMPLEMENT; counts as fixture failure |
| Codex unavailable | Existing `engine downgraded: codex-unavailable` banner; solo-Claude PLAN proceeds |
| Score regression on quality axis (over-defensive plan → over-defensive code) | Gate 2 (no-regression −3) + Gate 4 (zero new HIGH/CRITICAL) |
| Lint Check 15 over-matches legitimate plan content | Reserved-token list is restrictive (not regex on `pair`/`codex`); only metadata-shape tokens |

## Principles check

- **#0 pre-flight**: ✅ closes user-visible failure (Phase 4 cutover with unproven L2).
- **#1 no overengineering**: ✅ measurement + minimum firewall (3-layer); no speculative abstractions.
- **#2 no guesswork**: ✅ predictions filled BEFORE run; gates pre-registered.
- **#3 no workaround**: ✅ structural firewall (artifact + schema + validator), not silent strip.
- **#4 worldclass**: ✅ Gate 4 enforces zero new HIGH/CRITICAL.
- **#5 best practice**: enforced via existing CRITIC findings in VERIFY (carryover).
- **#6 layer-cost-justified**: ✅ Gates 5/6/7 measure wall budget; Gate 3 measures quality lift.
- **#7 mission-bound**: ✅ Mission 1 single-task scope.

## Why this is not score-chasing (PRINCIPLES.md #0)

This iter cannot move benchmark margins on its own; it validates a measurement that the cutover needs. Real shipping decision (Phase 4 cutover with PLAN-pair as first product L2 surface) — case (b) of pre-flight 0.

## Deliverable execution order

1. R0 with Codex on firewall mechanism + smokes + orchestrator design.
2. SKILL.md + state-schema edits + lint Check 15 + run-fixture.sh + judge.sh edits + run-iter-0033d.sh + iter-0033d-compare.py.
3. `.claude/skills/` mirror sync; lint-skills.sh PASS.
4. Smokes 1a-d (~1 min total).
5. R-smoke if any smoke fails.
6. Suite (~6 hr).
7. R-final on raw numbers.
8. Update HANDOFF.md + DECISIONS.md + iter-0033d closure verdict.
9. iter-0034 Phase 4 cutover (gated on iter-0033d ALL ship-blockers PASS).
