# iter-0070+ — loop architecture ladder (STUB, design frozen 2026-07-10)

status: STUB — three-way converged design (Fable + Codex + Grok 4.5), NOT
started. Source: user directive HANDOFF Block 9; round archives
`/tmp/iter0068-direction/{codex,grok}-looparch-response.log` (ephemeral —
this file + Block 9 are the durable record). **Entry condition: iter-0068
fully closed first** (admitted-set R1-gate → A/C + no-suppression decision →
closure) — active-experiment integrity, both engines.

## Converged design (both engines, adjudicated by orchestrator)

1. **No new intake skill.** Evolve `/devlyn:ideate --project`: intent →
   decomposition → `docs/specs/<project-id>/plan.md` + N specs. Team-design
   inside intake is measurement-gated (ladder rung 5), not always-on.
2. **`plan.md` is the root context contract**: add LOCKED `## Original
   Intent` + `## Project Acceptance` sections (immutable after user
   go-ahead; only decomposition/task sections evolve). No separate
   intent.md. Per-task acceptance stays in child `spec.md` +
   `spec.expected.json`; project outcomes map to task IDs in plan.md.
3. **Loop wiring = one command**: `/devlyn:queue add-plan <plan.md>` —
   deterministically appends topologically-ordered plan-linked spec entries
   + the locked-intent digest. Project creation does NOT imply execution
   authority (go-ahead required). "Second agent" = replaceable next consumer
   of the artifact, not a persistent role (Mission-2 boundary: serial,
   single-worktree).
4. **Per-spec `/devlyn:resolve` VERIFY unchanged** (task-level correctness).
5. **Project intent-closure after drain**: fresh-context verify of aggregate
   outcome vs locked Original Intent/Project Acceptance; reopen only
   finding-backed tasks; redo cap 2 rounds (per-item outer loop stays 3).
6. **Off-resolve (plain conversation) uses the same shared `INTENT_CLOSURE`
   kernel**: lock `.devlyn/intent.contract.md` BEFORE the first material
   action; before claiming done, a fresh read-only verifier compares locked
   intent vs actual diff/side-effects/behavioral evidence. NEVER the
   iter-0009 Stop-hook/regex class (criterion: semantic artifact boundary —
   bind locked intent + behavioral evidence, not words/transcripts).
   "Measured" (0069.4 unfreeze bar): on the probe corpus, every planted
   "build-green, feature-absent" cell blocked + clean controls pass without
   rework + 100% checkpoint coverage on ordinary invocation. If ordinary
   conversation cannot reach 100% coverage, that RESULT unlocks the M1.5
   semantic-completion-runner seam — it does not license more contract
   prose (0069.3 stands).
7. **Team (pair) design + team closure ship LAST** — only on pre-registered
   solo-vs-team lift + clean-control/no-suppression evidence.
8. **No-suppression**: every loop layer must not regress saturated bare
   coding; measure on the no-degradation controls when quality claims ship.

## Ladder (run in order; instruments before mechanisms)

- **0070 — intent/decomposition instruments** (Block 8 axes 1+2): planted
  multi-feature intent-drift cells + plain-conversation false-done cells
  ("build green, feature absent"). Defines "measured" for the closure
  class. Design-rigor axis instrument: named, deferred.
- **0071 — plan.md context contract + queue wiring**: locked sections,
  structural lint, `queue add-plan` (idempotent, topological, intent
  digest). No quality claim.
- **0072 — project intent-closure loop** (solo): post-drain verify + ≤2
  re-queue rounds; measured on 0070 cells; ship-or-adjust.
- **0073 — plain-conversation INTENT_CLOSURE checkpoint** experiment:
  ship-or-revert on the 0070 bar; failure result names the M1.5 seam.
- **0074 — team-design/team-closure pair surfaces** — ONLY if 0072/0073
  measure solo miss rates high enough (measurement-gated pair policy).
