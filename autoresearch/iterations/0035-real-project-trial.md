---
iter: "0035"
title: "Real-project trial — Mission 1 terminal gate (NORTH-STAR test #15)"
status: STUB
type: real-project measurement; Mission 1 terminal gate
shipped_commit: TBD
date: 2026-05-04
mission: 1
gates: Mission 1 unblock → Mission 2 (parallel-fleet substrate)
parent_design_iters: iter-0034 SHIPPED 2026-05-04 (Phase 4 cutover — 2-skill product surface clean, solo PLAN empirically world-class per iter-0033 (C1) + Gate 5 re-replication)
---

# iter-0035 — Real-project trial (Mission 1 terminal gate)

## STATUS: STUB — pre-registration deferred to the session that runs the trial

This file is a placeholder pre-registration. The session that picks up the trial MUST draft full hypothesis, gates, predictions, and risk register BEFORE running anything. Pre-registration is non-negotiable per PRINCIPLES.md #2.

## Why this iter exists (PRINCIPLES.md pre-flight 0)

NORTH-STAR.md operational test #15 is the Mission 1 terminal gate — the loop does NOT terminate until ONE fresh real-project trial passes without manual context-engineering rescue. Benchmark fixtures are calibrated targets; passing them confirms the harness behaves *as designed against known cases*, not that it serves the actual user goal. iter-0034 Phase 4 cutover SHIPPED the 2-skill product surface and confirmed L1 numbers unchanged on the 9-fixture suite, but that is necessary-not-sufficient for Mission 1 close. iter-0035 closes the gap.

User-visible decision unlocked: with iter-0035 PASS, Mission 1 closes and Mission 2 (parallel-fleet substrate) opens. With iter-0035 FAIL, the failure mode classifies the next harness iter (e.g. PLAN drift, IMPLEMENT contract bug, BUILD_GATE missing a real-project framework, VERIFY false-pass).

## NORTH-STAR test #15 (verbatim)

> **Final stop condition for Mission 1** — even if all of #1-#14 pass on the 9-fixture suite, the loop does NOT terminate until **one fresh real-project trial passes without manual context engineering**. Definition: a developer who has not tuned the harness picks a real (not fixture) feature/bug from a real (not test) codebase, runs `/devlyn:resolve "<spec or goal>"` end-to-end, and the output ships without human prompt-engineering rescue. Pass = (a) no human edits to skill prompts mid-run, (b) no manual phase re-runs, (c) the produced code passes the project's existing test suite + the developer's spec acceptance check, (d) wall-time within budget for the layer the user paid for.

## Hand-off contract (FROM iter-0034 SHIPPED)

The session that picks up iter-0035 MUST:

1. **Read iter-0034 §"CLOSURE" first.** The 5-gate evidence + raw numbers are the empirical baseline that says "L1 is world-class; iter-0035's job is to verify this transfers off-fixture."
2. **Pick a real project.** Not the devlyn-cli repo itself; not a fixture from `benchmark/auto-resolve/fixtures/`. Candidate sources: a small open-source project the developer has not contributed to before, OR a fresh side-project with at least one real bug/feature in flight, OR a non-trivial library the developer maintains.
3. **Pick a real task.** Real bug or feature, with a verifiable acceptance criterion the developer would normally accept (existing test suite passes + the developer's own check that the bug is fixed / feature works).
4. **No prompt-engineering rescue.** The trial is `/devlyn:resolve "<spec or goal>"` end-to-end — single invocation, hands-free. If the run halts, that is data; do NOT re-prompt or edit skill prompts mid-run. A halt is recorded as a Mission 1 failure mode.
5. **Pre-register**: NEW hypothesis + 4 NORTH-STAR #15 sub-criteria as gates (a–d) + predicted directions filled BEFORE the run + risk register including (a) framework-detection miss in BUILD_GATE, (b) test-suite running cost vs project budget, (c) Codex/Claude availability mid-run.
6. **Pre-register decision tree**: PASS → Mission 1 closes, Mission 2 opens (HANDOFF rotates accordingly). FAIL → classify failure (which gate broke, which phase produced it, was it PLAN / IMPLEMENT / BUILD_GATE / CLEANUP / VERIFY) and queue the corrective iter.

## Suggested gates (next session refines)

- **Gate (a) Hands-free invariant**: zero human edits to skill prompts mid-run. Verify via `git status` on `~/.claude/skills/` immediately post-run. Any modification to a tracked skill file = FAIL.
- **Gate (b) Single-invocation invariant**: zero manual phase re-runs. The run is one invocation of `/devlyn:resolve`. If the session interrupts and the user resumes, that is also a FAIL (not real hands-free).
- **Gate (c) Code quality**: produced code passes the project's existing test suite + the developer's spec acceptance check. Run the project's `npm test` / `pytest` / `cargo test` / equivalent and verify zero new failures.
- **Gate (d) Wall-time**: within budget for the layer the user paid for. Default budget: layer-cost-justified per PRINCIPLES.md #6. Concrete budget set in pre-reg (e.g. `--engine claude` should complete in < 60min for a typical bug fix).

## Risk register (sketch — refine in pre-reg)

- R1: BUILD_GATE framework auto-detection misses the project's tooling (e.g. `make test` instead of `npm test`). Mitigation: pre-reg includes a manual smoke of `python3 _shared/spec-verify-check.py --check` and the project's main test command before the trial, separate from the run itself.
- R2: VERIFY fresh-subagent fails to load project context. Mitigation: VERIFY phase is structurally findings-only with no code-mutation tools — the worst case is FAIL on Gate (c), not silent corruption.
- R3: PLAN over-scopes (touches files outside the bug surface). Mitigation: pre-reg captures `git diff --stat` and the developer's "should have touched" list; PLAN drift = FAIL classification with iter-0036 corrective candidate.

## Pointers

- Design baseline: `iterations/0034-phase-4-cutover.md` § "CLOSURE" (post-Gate-5 raw numbers proving L1 unchanged on 9-fixture suite).
- NORTH-STAR test #15: `autoresearch/NORTH-STAR.md` § "Real-project trial gate".
- MISSIONS Mission 1 unblock criteria: `autoresearch/MISSIONS.md` § "Mission 1 unblocks Mission 2 only when".
- Codex pair-collab plan: R0 on pre-reg before the trial; R-final on raw numbers after.

## Definition of "done"

- 4 gates a-d each have raw evidence cited (project name, task description, test command output, wall-time, git diff).
- iter-0035 closure committed.
- Mission 1 closes (HANDOFF rotates: iter-0036 candidate becomes next active).
- Mission 2 (parallel-fleet substrate) opens per MISSIONS.md "Mission 1 unblocks Mission 2 only when" criteria.
- DECISIONS appended.

## Forbidden under iter-0035 scope

- Do NOT use a fixture or test-repo as the "real project" — that voids #15 by definition.
- Do NOT prompt-engineer mid-run — failure during the run is data, not a problem to fix on the fly.
- Do NOT count a partial run (interrupted, resumed) as PASS — the trial is one hands-free invocation.
- Do NOT skip Codex R0 / R-final pair-collab steps.
