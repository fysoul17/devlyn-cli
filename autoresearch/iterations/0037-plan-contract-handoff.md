# iter-0037 — plan-contract handoff + phase-gated IMPLEMENT (corrective iter)

**Status**: CONVERGED — R0 Go-with-changes → R1 CONVERGED-GO (C1-C4) → R2 on C5
BLOCKED-on-one-point → both R2 findings adopted verbatim (outer-loop verdict
classification + unattended assume-and-log bound). Implementation complete on
disk; commit pending user go.
**Trigger**: OPERATIONAL-MILESTONE freeze unlock conditions (a)+(c) fired 2026-07-03.
User real-usage failure report (verbatim intent): even on the strongest model, large
conversational tasks produce (1) missed requirements, (2) unintended-direction
implementation, (3) undetected errors. Plus explicit user direction: "티키타카로
의도만 넘기면 검증까지 hands-free hybrid loop" — the user does not want to invoke
`/devlyn:ideate` / `/devlyn:resolve` manually; the orchestrating model should.

## Root cause (why-chain, stopped at 2 — surfaced)

1. Why do large conversational tasks miss/drift? → The agreed intent lives only in
   the orchestrating model's conversation context (compactable, invisible to the
   user), and execution is a single monolithic IMPLEMENT context verified only at
   the end (BUILD_GATE/VERIFY after the full diff).
2. Why does that produce misses? → **Violated invariant: agreed intent must survive
   as a durable contract and be checked at phase boundaries, not only at the end.**
   Inside the pipeline the contract exists (`spec.md` / `criteria.generated.md`,
   `.devlyn/plan.md`) but (a) the conversational path never produces it, and
   (b) `plan.md` has no execution decomposition — nothing is checked between
   IMPLEMENT start and BUILD_GATE.

Reference frame: IndyDevDan "Plan F3" (2026-06) — the one load-bearing idea adopted
is *plan as living, phase-gated contract*. Explicitly NOT adopted: HTML output,
image generation, metadata headers, new sub-workflow skills (presentation-layer /
overengineering; no observed failure mode they prevent; 2-skill surface is locked).

## Changes

### C1 — Conversational handoff convention (CLAUDE.md, orchestrator-level)

For large work discussed conversationally: the orchestrating model (not the user)
(1) writes the agreed contract to `docs/specs/<id>/spec.md` — ALWAYS a spec file
for large work, plus `spec.expected.json` when mechanical verifications exist
(R0 counter adopted: routing large agreed contracts through `--goal-file` would
hit `BLOCKED:large-needs-ideation` per free-form-mode.md:50-64; `--goal-file`
stays reserved for trivial/medium launcher input), (2) presents a one-screen
plan-contract summary in conversation (the user's single review checkpoint,
BEFORE the pipeline starts; autonomy contract inside the pipeline unchanged),
(3) on user go-ahead invokes `/devlyn:resolve --spec <path>` hands-free to
completion, (4) runs the per-task outer loop defined in C5.

Subtractive pairing: supersedes the user-operated "When to use which" framing in
CLAUDE.md Quick Start — table compressed; manual invocation remains possible but is
no longer the documented primary path.

### C2 — PLAN emits `## Execution phases` for large work (plan.md as living checklist)

Scope gate (all must hold, else plan.md keeps today's 3 sections byte-identical):
- spec frontmatter `complexity: high` (legacy `large` accepted) OR free-form
  `state.complexity == "large"` (i.e. `--continue-on-large` runs), AND
- PLAN judges the work spans multiple subsystems or >~8 files, AND
- each phase boundary has at least one runnable gate command.

When it fires: plan.md gains section 4 `## Execution phases` — 2-5 phases, each
`### Phase k — <title>` with task checkboxes, `gate:` line (1-2 runnable commands,
exit-code truth), and the files it owns. Status legend `[ ]` pending / `[WIP]` /
`[x]` done / `[F]` failed. Default bias: single phase (= today's behavior) unless
the decomposition test passes. Trivial/medium paths untouched — measured L1 surface
unchanged.

### C3 — Phase-gated IMPLEMENT loop (orchestrator-driven, deterministic gates)

When plan.md has `## Execution phases` with >1 phase (R0 verdicts Q1-Q3 adopted):
- **Contract/progress split**: phase DEFINITIONS live only in plan.md (written
  once by PLAN — the immutable contract); phase PROGRESS lives only in
  `state.phases.implement.exec` = `{ total, current, statuses: [], commits: [] }`
  — the routing truth. Orchestrator routes on state, never on plan.md checkbox
  parsing. Checkboxes in plan.md are a display mirror the orchestrator updates
  best-effort at gate boundaries for human mid-run visibility (the observed
  failure mode is user-invisible drift); they carry no routing weight.
- Orchestrator spawns IMPLEMENT once per phase. Per-phase prompt input overrides
  the implement body's `base_ref.sha` framing: current worktree after the prior
  phase commit + `git diff <base_ref.sha>...HEAD` summary + this phase's plan.md
  section + prior gate outputs (R0 Q1: fresh subagents must not re-plan against
  stale base state).
- After each phase returns: orchestrator runs that phase's `gate:` commands
  directly (deterministic, exit-code truth). Gate PASS → checkpoint
  `git commit -m "chore(pipeline): implement phase <k>/<N>"`, update state +
  mirror. Gate FAIL → NO checkpoint commit; one fix respawn for that phase
  (increments `rounds.global`, shares `max_rounds`); second FAIL → halt
  `BLOCKED:phase-gate-exhausted` (R0 Q3: commit only after gate PASS).
- After the last phase's gate PASS: `implement_passed_sha` is set as today;
  `cumulative.patch` is defined as `base_ref.sha..HEAD`; BUILD_GATE still runs
  in full (phase gates are earlier slices, not replacements).
- `rounds.global` doc updated: phase-gate fix respawns also consume the shared
  budget (state-schema.md previously named only BUILD_GATE/VERIFY loops).

Single-phase plans take today's exact path — no loop, no new state, no phase
metadata in any prompt (R0 Q4 isolation: `Execution phases` / `exec` / phase
index / gate output text appear nowhere unless the multi-phase gate fired).

### C5 — Loop-engineering contract: per-task outer loop + intent queue (orchestrator-level)

User direction 2026-07-03 (mid-iter, verbatim intent): "검증까지 계속 해주고 내가
자는동안 쭉 해주는.. 나는 계속 의도나 목표나 개선사항이나 추가 기능들을 큐에
쌓아주고. 그게 루프 엔지니어링." Two loops, both engineered around durable disk
state — fresh contexts are disposable, artifacts are the loop's memory:

- **Per-task outer loop**: after `/devlyn:resolve` returns (post PHASE 6
  archive), the orchestrator reads the terminal verdict. PASS → done. Only
  verdicts backed by spec/verification findings (NEEDS_WORK, verify/build-gate
  exhaustion) are amend-and-rerun eligible: orchestrator adjudicates the
  findings, amends the spec contract (amendment recorded in the spec file —
  living artifact; spec stays read-only INSIDE a run), and re-invokes
  `/devlyn:resolve --spec`. Bounded: 3 outer iterations per task, then surface
  to the user with the findings trail. Infrastructure, invalid-input,
  engine-availability, and implement-empty BLOCKED verdicts are NOT
  spec-amendable — mark `[F]` / surface immediately (R2 caveat adopted).
  Every iteration re-enters through durable artifacts (spec.md, findings JSONL,
  run archive), never through conversation memory.
- **Intent queue (across tasks, unattended)**: `docs/specs/queue.md` — an
  ordered checklist the user (or the orchestrator during conversation) appends
  intents to. Drain contract: strictly SERIAL (Mission 1 binding — single task
  at a time; parallel drain is Mission 2 territory; no queue instrumentation).
  Per item: spec it (C1 steps 1-2; when running unattended the queue entry
  itself is the user's go-ahead, so assume-and-log replaces the interactive
  review checkpoint), run the per-task outer loop, mark `[x]` done / `[F]`
  blocked with reason, continue to the next item. A blocked item never halts
  the queue. **Assume-and-log bound (R2 blocker adopted verbatim)**: unattended
  assumptions may only take scope-narrowing, reversible, non-user-visible
  defaults. Material ambiguity — user-visible behavior, data/state semantics,
  mission boundaries, new files/scripts/flags, implementation surface — marks
  the item `[F] needs-review` and the drain continues. End-of-drain report
  summarizes per-item verdicts + logged assumptions.

No new skill, flag, or script: the queue is a file convention; the loop runner
is whatever the user already has (a long session, `/loop`, or devlyn-agent
later — the convention is the contract any of them follow).

### C4 — Deletion: stale archive artifact enumeration in resolve SKILL.md

PHASE 6 step 4's parenthetical artifact list duplicates `archive_run.py`
`PER_RUN_PATTERNS` and is already stale (missing `plan.md`, `final-report.md`,
`cumulative.patch`, `verify-judge-*`). Replace enumeration with a pointer to the
script. Net-negative pairing for C2/C3's additions.

## Rejected alternatives

- New `/devlyn:handoff` or `/devlyn:plan` skill — violates locked 2-skill surface.
- HTML plan output / image embedding / metadata headers — presentation layer, no
  observed failure they prevent.
- New flag (`--phase-gates`) — flags admit wrong defaults; trigger is
  complexity-derived and PLAN-judged with single-phase bias.
- Always-phase-gated (all complexities) — regresses measured trivial/medium L1
  wall-time for no observed failure there.
- Pair machinery expansion — headroom-first rule binds; this iter adds zero pair
  surface.

## Benchmark / freeze safety (falsifiable claims)

- P1: trivial/medium free-form runs and single-phase spec runs produce
  byte-identical plan.md structure and identical phase sequence vs HEAD.
- P2: existing pair-proof fixtures (F16/F23/F25-class: single-feature CLI specs)
  decompose to 1 phase under C2's test → measured L2 path unchanged.
- P3: `scripts/lint-skills.sh` passes post-edit.
- No new engine routing, no pair-mode change, no `_shared/` script behavior change
  except the additive `state.phases.implement.exec` field (schema doc updated).

## R0 record (2026-07-03, Codex GPT-5.5 via monitored wrapper)

Verdict: **Go-with-changes.** Adopted: ship-list items 1-6 (spec-always for large
handoff; byte-identical non-firing paths; routing truth in state not checkboxes;
current-worktree input for per-phase spawns; commit-only-after-gate-PASS; C4
deletion). Named deltas vs R0 on two points, for R1 adjudication:

- **Δ1 (vs ship-item 3 "delete plan checkbox status")**: checkboxes KEPT as a
  display-only mirror, routing weight zero. Delta cited: the triggering failure
  mode is *user-invisible* drift on large runs — mid-run human visibility is the
  requirement C2 exists to serve; deleting the mirror deletes the requirement.
  Codex's underlying concern (mutable artifact as routing state) is fully closed
  by the contract/progress split instead.
- **Δ2 (vs ship-item 7 "add lint/smoke coverage")**: NO new lint check shipped.
  Delta cited: lint-skills.sh checks are static text assertions; asserting
  "phase metadata absent from trivial/medium prompts" against prose that an LLM
  assembles at runtime is a fragile prose-shape test, not a mechanical guard
  (iter-0033g lesson: no infra for threats without an observed instance). The
  binding guard is structural — the phase-gate block lives in a conditional
  section that single-phase runs never receive — plus existing G4 bare-case
  modal regression smoke (F1+F6) on the next benchmark occasion, plus P1-P3
  falsifiable claims above.

## R1 question

Does the contract/progress split + Δ1 + Δ2 close your counters, or does either
delta re-open a failure mode you can name concretely?
