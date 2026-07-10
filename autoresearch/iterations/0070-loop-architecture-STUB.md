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

## Full-loop alignment amendments (2026-07-10, second three-way round —
Codex ALIGNED-with-6 + Grok ALIGNED-with-5, adjudicated; archives
`/tmp/iter0068-direction/{codex,grok}-fullloop-response.log`)

1. **Team = target semantics, promotion = measured** (criterion: target
   semantics vs default-activation policy): team intake/closure surfaces
   appear WITH their stage as explicit-request or pre-registered-trigger
   experiments (0071/0072); rung 0074 decides PROMOTION to default. Never
   always-on unearned.
2. **Enqueue**: explicit `queue add-plan <plan.md>` stays (creation ≠
   execution authority); after the user's go-ahead the ORCHESTRATOR invokes
   it. Entries bind plan path + task/spec id + dependency order +
   locked-intent digest; idempotent seeding; drain recomputes the digest
   and fails closed if the locked intent changed. After ideate --project,
   print the exact next command.
3. **Dual execution path**: drain items may run via `/devlyn:resolve` OR
   orchestrator-direct; BOTH emit a common verdict/evidence bundle (spec
   met, tests, cleanup, scoped commits) before `[x]`.
4. **Closure evidence = acceptance-carrying, bound to the final SHA**:
   project + off-resolve INTENT_CLOSURE consume final-SHA diff,
   side-effect, test, hygiene evidence; UI-touching work adds route/browser
   evidence + screenshots when a real browser is available (curl tier =
   explicitly limited fallback); BUILD_GATE browser evidence is reused only
   when content-bound to the post-cleanup SHA, else replayed.
5. **Terminal ship**: per-item scoped commits stay; after aggregate PASS,
   only a scoped finalization commit of plan/queue/closure artifacts; push
   ONCE only with explicit authority + named remote/branch + clean verified
   HEAD + fast-forward safety; never force; otherwise report
   `READY_TO_PUSH`.

## Non-coding exam corpus fold (2026-07-10, third three-way round — Codex +
Grok both GO-WITH-EDITS, adjudicated; archives
`/tmp/noncoding-axes-r0/{codex,grok}-response.log`, ephemeral — this section
is the durable record)

User directive (HANDOFF Block 10) pulled the axis-instrument design round
forward while the 0068 gate ran; ladder order + live gate UNTOUCHED. Rung
0070's instrument cells are now design-converged. All four consume one
shared **Non-Coding Admission Kernel** (the durable asset; fixtures are
cohort-bound disposables): A/B arms (+C copycat required for any moat
claim, NORTH-STAR ops test #17), known-good + planted-bad calibration,
bare-fails admission, cohort identity + mandatory re-gate on engine/model
drift, UNFAIR fairness review, no-op-must-fail, saturated no-suppression
controls.

1. **Packet Utility Differential** (meta-prompting/context-engineering —
   the directive's one genuinely uncovered surface; measurement FORM of
   axis 2, not a sixth axis): packet quality = next-agent outcome.
   Schema-locked packet (plan.md locked sections + ordered specs + intent
   digest) as the sole independent variable; fixed blinded mid-tier
   executor (codex/sonnet, never fable); raw resolve/wall/violations
   reported separately, never fused until factors separate. Known-good vs
   planted-bad separation at N≥3 = smoke/death gate only, never final
   evidence. Supersedes iter-0033e QUEUED-STUB — its "downstream scoring
   too blunt before a defect-class oracle" warning stands: calibration
   first. Criterion: Mediated Causal Sensitivity.
2. **Counterfactual Intent Holdout** (axis 1): paired repo variants — R
   (evidence uniquely determines the action; unnecessary halt FAILS) and Q
   (evidence narrows but cannot resolve; only the specifically
   discriminating question passes). Generic question, generic assumption
   disclosure, and silent plausible guess all FAIL. Supersedes
   `benchmark/instruction-sensitivity` B1 (its `hidden/verify.sh:14` regex
   rewards always-halt/generic ambiguity talk). Criterion: Counterfactual
   Identifiability — flipping only the intent-bearing repo evidence must
   flip the correct terminal behavior.
3. **Blind Design-Defect Differential** (axis 4): predeclared defect
   taxonomy (unsupported assumption / missed repo invariant / broken
   dependency / absent failure mode); the artifact oracle must separate
   known-good/bad controls BEFORE downstream implementation is admitted
   even as a secondary metric.
4. **Root-Cause Recurrence rows** (principles/why-chain axis): EXTEND the
   existing drift-bait/violation panel — no new family. Planted symptom
   patch passes the happy path but FAILS a second manifestation of the same
   violated invariant; gold invariant-level fix passes all manifestations;
   no-op fails; forbidden_patterns demoted to narrow secondary
   disqualifiers (current `DB-silent-catch-root-cause/hidden/verify.sh` is
   a syntax proxy; its own comment admits aliased fallbacks are missed).
   Criterion: Invariant Recurrence Prevention.

Adjudications: anti-saturation standing prose CUT from NORTH-STAR (substance
already at `NORTH-STAR.md:47-54`; enforcement = the kernel's mandatory
manifest fields — Durable-Gate Locality). Axis 3
(collaboration/allocation) NOT silently dropped: solo cells must produce
replay-ready artifacts so 0074 can measure team-vs-solo lift without
redesigning cells; task-to-agent allocation ownership (0070 vs 0074) is an
explicit 0074-scope decision. Design-time UNRESOLVED (need fresh
measurement, not more rounds): executor seat calibration for packet-defect
sensitivity; post-smoke replication/variance rule (violation-matrix N=4 is
the precedent candidate); ≥2 intent fixture pairs proving
evidence-determination; design-rigor oracle staging.

## Ladder (run in order; instruments before mechanisms)

- **0070 — intent/decomposition/design-rigor instruments** (Block 8 axes
  1+2+4): the four design-converged instrument cells + shared Non-Coding
  Admission Kernel (fold above) + plain-conversation false-done cells
  ("build green, feature absent"; defines "measured" for the closure
  class) + design-rigor admission metric for team-design promotion (Codex
  amendment 2). Split 0070a/0070b only if each half keeps its own
  falsifier + immediate downstream decision; packet calibration never
  separates from the packet-utility measurement it validates.
- **0071 — plan.md context contract + queue wiring**: locked sections,
  structural lint, `queue add-plan` (idempotent, topological, intent
  digest, digest revalidation at drain). Explicit-request team-design
  experiment surface. No quality claim.
- **0072 — project intent-closure loop** (solo default): post-drain verify
  + ≤2 re-queue rounds; final-SHA evidence incl. browser/screenshots for
  UI; measured on 0070 cells; ship-or-adjust. Pre-registered-trigger team
  closure experiment surface.
- **0073 — plain-conversation INTENT_CLOSURE checkpoint** experiment:
  ship-or-revert on the 0070 bar; failure result names the M1.5 seam.
- **0074 — team promotion decision** — promote team-design/team-closure to
  default ONLY where 0071-0073 experiments measure solo miss rates high
  enough (measurement-gated pair policy) + no-suppression clean-control
  evidence.
