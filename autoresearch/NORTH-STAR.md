# NORTH-STAR — what we are optimizing, in one place

This file is the single source of truth for the project's goal. Every other doc references this one. If a future session is uncertain about scope, contract, or direction, **read this file first** — do not infer from code, do not assume from older docs, and do not hallucinate intent.

Last refined: 2026-05-07 (2-skill redesign locked: `/devlyn:ideate` + `/devlyn:resolve` + internal kernel; verify folded into resolve as fresh-subagent final phase; pair-mode confined to gated VERIFY's JUDGE; schema = LLM-agnostic decoupler).

---

## The ultimate goal (why this skill exists)

**devlyn-cli is not a benchmark exercise. It is the foundation for an autonomous AI Agent organisation — the kind that lets a single human plant an idea and walk away while 5-10+ tasks run in parallel to completion, then composes into a pyx-style self-operating system.**

The user's working contract, in their own framing:
- "Plant an idea or goal as a prompt; agents take it end-to-end without me touching engineering."
- "Run 5-10+ tasks in parallel — at minimum."
- "Eventually compose into a single AI Agent organisation that operates autonomously, pyx-style."

For that to be real, the harness has to be **overwhelmingly better than bare prompting**. Marginally better is a research curiosity. The gap has to be wide enough that spawning 5-10 parallel runs is *trivially obvious value* over a single human prompting Claude or Codex once.

**This is what every iter ultimately serves**. The 3-layer performance contract below (L0 / L1 / L2) is the *measurement frame* that lets us tell whether a given iter moves us toward this ultimate goal. The contract is in service of the goal, not the other way around.

### Mission sequencing — see [`MISSIONS.md`](MISSIONS.md)

Day-to-day work is gated by the **active mission** in `MISSIONS.md`:

- **Mission 1 (active 2026-04-29 →)**: single-task skill excellence. Make the harness *extremely* better than bare prompting before any parallel work begins.
- **Mission 2 (deferred)**: parallel-fleet readiness — `git worktree`-per-task substrate, resource leases, N≥5 simultaneous runs.
- **Mission 3 (deferred, long-horizon)**: autonomous AI Agent organisation — inter-agent coordination, self-replanning, failure containment, audit accountability.

The 5 hard NOs in `MISSIONS.md` Mission 1 list are absolute during Mission 1.

---

## The product surface (locked 2026-04-30)

After 16 skills of accretion-driven landscape, the user-facing surface compresses to **2 skills + 1 internal kernel + 1 utility**. This is the canonical shape from this date forward; any deviation requires explicit user direction.

### User skills (2)

- **`/devlyn:ideate`** — OPTIONAL. Used for greenfield, multi-feature projects, or when the user wants a formal spec before building. Output: `spec.md` (human contract) + `spec.expected.json` (mechanical verifications). Modes: `default` | `--quick` (assume-and-confirm) | `--from-spec <path>` (lint+normalize external spec) | `--project` (plan.md index + N specs). spec lint mandatory. `spec.kind = feature | spike | prototype` escape hatch.
- **`/devlyn:resolve`** — REQUIRED. Single entrypoint for all work-doing: new feature, modify, debug, refactor, chore, PR review. Inputs: free-form goal OR `--spec <path>` OR `--verify-only <diff>`. Internal phases: PLAN → IMPLEMENT → BUILD_GATE → CLEANUP → **VERIFY (fresh subagent context, findings-only)**.

### Internal kernel (`_shared/`, NOT a user skill)

`expected.schema.json` (load-bearing LLM-agnostic decoupler), `run.state.json` (pipeline state), `spec-verify-check.py`, `forbidden-pattern-check.py`, `scope-check.py`, `complexity-classifier.py` (NEW — for resolve PLAN trivial/medium/large branching), `browser-runner.sh`, `engine-routing.md`, `adapters/<model>.md` (per-engine prompt deltas).

### Utility (1)

- **`/devlyn:reap`** — lives in `optional-skills/` (moved 2026-05-04 in iter-0034 Phase 4 cutover). Process hygiene only.

### What dies (16)

`/auto-resolve` `/resolve` (both → new `/resolve`) `/implement-ui` `/design-ui` `/team-design-ui` `/design-system` `/clean` `/update-docs` `/preflight` `/evaluate` `/review` `/team-review` `/team-resolve` `/browser-validate` (→ kernel runner) `/product-spec` `/feature-spec` `/recommend-features` `/discover-product` `/ideate` (→ new `/ideate`).

Optional plugins (creative capabilities, non-hot-path): `/design-system`, `/team-design-ui`.

### Multi-LLM evolution direction (binding for `/devlyn:resolve`)

`/devlyn:resolve` and `/devlyn:ideate` are **the surfaces where multi-LLM mixing keeps evolving**. Today: Claude (Opus 4.x) + GPT-5.5 (Codex CLI). Tomorrow: a **pi-agent** abstraction that lets the skills swap in additional LLMs (Qwen, Gemini, Gemma, future frontier models) wherever empirical evidence shows lift.

**Architectural commitments**:
- Pair-mode is **measurement-gated, not architecturally defaulted**. The Pair-mode policy section below names the candidate phases, the deterministic-vs-judgment distinction, and the gate every shipped pair surface must clear.
- The schema decoupler (`expected.schema.json`) + per-model adapters (`_shared/adapters/<model>.md`) are the load-bearing invariants that let new LLMs slot in without touching skill bodies.
- The pi-agent surface is the future hook for swappable LLM backends. NOT designed yet (Mission 2/3 territory). Today's commitment: don't bake assumptions that prevent it.

**No-xxx / worldclass non-negotiable** in every multi-LLM addition:
- **No overengineering** — pair-mode wires only where measurement shows lift. No always-on pair, no speculative multi-agent scaffolding.
- **No guesswork** — every additional LLM/phase combination requires falsifiable acceptance gate before it ships.
- **No workaround** — silent fallbacks, hardcoded model names, `any`-typed adapter slots, etc. are rejected in coordination layer just as they are in product code. Required unavailable engines fail closed with `BLOCKED:<engine>-unavailable`.
- **Worldclass production-ready** — zero CRITICAL findings on multi-LLM coordination paths. Pair-mode failures (Codex unavailable, model drift, API rate-limit) must surface user-visible, not silently degrade.
- **Best practice** — adapter files follow each model's official prompt-engineering guide (Anthropic guide for Claude, OpenAI guide for GPT). When a third model is added, its official guide is the contract.

This block is the standing commitment. Any redesign Phase that contradicts it is a defect.

### Migration approach: hybrid (status, 2026-05-04)

1. ✅ Kernel extraction (iter-0029).
2. ✅ New `/devlyn:resolve` (greenfield interface, learned mechanisms preserved); A/B against `/devlyn:auto-resolve` PASSED at iter-0033 (C1) — 5/5 headroom-available fixtures, suite-avg L1−L0 +6.43.
3. ✅ New `/devlyn:ideate` (iter-0031/0032; F9 redesigned to 2-skill contract iter-0033a).
4. ✅ Cutover + deprecation — iter-0034 SHIPPED 2026-05-04: 15 user skills deleted, 3 (reap / design-system / team-design-ui) moved to `optional-skills/`, `bin/devlyn.js DEPRECATED_DIRS` extended to force-remove stale legacy skills from downstream installs.
5. ⏳ Optional plugin separation — partially shipped via Phase 4 (3 skills moved to `optional-skills/`); remaining work is Mission 2/3 boundary if any.

Real-project trial (iter-0035, NORTH-STAR test #15) is the Mission 1 terminal gate post-cutover.

### Closing principle (Codex R1 verdict)

> **"Greenfield the interface. Do NOT greenfield the learned mechanisms."**

The repo already contains the hard-won pieces: mechanical spec verification, state discipline, browser validation, one-spec-at-a-time planning. The redesign deletes skill surface area while preserving those mechanisms behind sharper contracts.

---

## The goal in one sentence (mid-level, in service of the ultimate)

**The harness composes frontier LLMs (and eventually local models like Qwen / Gemma) into a hands-free pipeline that delivers engineer-quality software for users who do not know context engineering, with each layer of composition justifying its own additional cost over the layer below — and the full pair-mode (or future multi-agent) experience must be _overwhelmingly_ better than bare prompting, not marginally.**

Two user groups, both first-class:

1. **Single-LLM users** (Opus alone, GPT-5.5 alone, Qwen alone, etc.) — they get the harness solo. The harness must beat their bare LLM **on quality and on efficiency**.
2. **Multi-LLM users** (Claude + Codex installed today, future + Qwen / Gemma / Gemini local-or-frontier) — the harness uses pair / multi-agent patterns where they are worth the cost. The pair must beat the same harness running solo on the strongest available model, **also on quality and on efficiency** — and on the parallel-task axis: 5-10 simultaneous runs without per-run quality collapse.

---

## The 3-layer performance contract

| Layer | Composition | Quality contract | Efficiency contract |
|---|---|---|---|
| **L0 — bare** | Single LLM, no harness, single direct invocation | Baseline | Baseline |
| **L1 — solo harness** | Single LLM + this harness, no pair patterns active | **Materially better than L0** on the four judge axes (Spec / Constraint / Scope / Quality) | **Wall-time and token cost not worse than running L0 enough times to match L1's quality.** Concretely: L1 must beat `bare-best-of-N` baseline (L0 invoked N times, best/median taken), where N is the wall-time ratio. |
| **L2 — pair harness** | 2+ LLMs (Claude + Codex today; profile-neutral so future swaps are possible). Pair-mode is conditional-default only for `/devlyn:resolve` VERIFY/JUDGE on measured triggers; PLAN/IMPLEMENT/BUILD_GATE/CLEANUP stay solo by default. iter-0020 falsified Codex-BUILD/IMPLEMENT, NOT pair-mode generally. iter-0033d/f/g closed PLAN-pair as research-only. | **Materially better than L1** on quality axes — by lifting fixtures L1 ties or loses on, not by re-confirming fixtures L1 already wins | **Pair budget must out-earn `L1-best-of-M`**, where M is the wall-time ratio of L2 to L1. If pair takes 3× the wall-time, the quality gain must beat the gain from running L1 three times. |

The efficiency contract applies equally to L1 and L2. **"Slower but more thoughtful" is not free** — at every layer, the alternative "just run the cheaper layer N more times" must be empirically worse.

---

## Why bare-best-of-N is the right efficiency baseline

User insight (verbatim, 2026-04-27): *"속도, 즉 효율도 좋아야해. 너무 느리면 오히려 bare를 여러번 돌리는게 나을수도 있잖아?"*

Translation: if L1 takes 10× the wall-time of L0, the user could have invoked L0 ten times and selected the best output. That is L1's true competitive baseline, not single-shot L0. Same logic for L2 vs L1.

This does not refute the pair hypothesis. It refutes "always-on pair" as a default. Pair has to be gated to the phases where the multi-model decision provably out-earns running the cheaper layer more times. The shipped product gate is `/devlyn:resolve` **VERIFY/JUDGE conditional pair**.

---

## Operational tests

A change ships only if it can answer all of these with concrete numbers:

### L0 → L1 contract (release blocker — single-LLM users are first-class)

1. **Quality (L1 vs L0)**: L1 arm beats L0 (bare) arm by suite-avg margin ≥ +8 (preferred) or ≥ +5 (floor) on the 4-axis judge rubric, across ≥ 7 of 9 fixtures (F8 known-limit excepted), F9 ≥ +5 (novice flow load-bearing).

   **Headroom amendment (added 2026-05-02 per iter-0033 R4 Codex collab)**: "≥ 7 of 9 fixtures with margin ≥ +5" applies to **gated fixtures with enough score headroom to express a +5 L1-over-L0 lift**. A fixture is excluded from this count for the current release decision when ALL of: `100 - L0_score < 5` AND `L1_score >= 95` AND the L1 arm has no disqualifier, no CRITICAL/HIGH finding, no watchdog timeout, and no regression worse than the existing per-fixture floor (gate #3 + per-fixture −5). Excluded fixtures still count for hard-floor safety gates and become fixture-rotation candidates if the RUBRIC two-shipped-version saturation rule is met. Iter-0033 (C1) was the precipitating data: F3 saturated (L0=100, L1=100), F6 saturated (mean L0=L1=96.3 across N=3), F7 marginal (L0=97 caps lift at +3); 5/5 headroom-available fixtures (F1, F2, F4, F5, F9) cleared ≥+5.
2. **Efficiency (L1 vs L0)**: `L1-vs-L0-best-of-N` is the economic baseline — N is the wall-time ratio `L1_wall / L0_wall` per fixture. **Dominance rule**: if L1 ties or loses on quality AND wall ratio ≥ 1.0, fail without invoking best-of-N.
3. **No hard floor violations**: zero L1 disqualifier, zero L1 CRITICAL/HIGH findings, zero L1 watchdog timeouts.
4. **Categorical reliability (added 2026-04-30 per user)**: on adversarial-spec fixtures (silent-catch, scope leak, etc.), L1 disqualification rate < bare disqualification rate by ≥ 30 percentage points. This is the *real* quality gate; suite-avg margin is reporting only.

### L1 → L2 contract (release blocker for L2 product surface; L1 must pass first)

5. **L1 must pass its own gates** (1–4) before L2 ships. L2 passing vs L0 while L1 fails is not acceptable — single-LLM users are not allowed to be a degraded second-class experience.
6. **No regression**: L2 must not regress any fixture's margin materially vs L1 (no fixture L1→L2 delta worse than −3 axes).
7. **Pair lift on high-value fixtures**: L2 must beat L1 by ≥ +5 on **pair-eligible / high-value fixtures** (where L1 was tied or lost vs L0, OR where the spec touches security / scope / spec-compliance regions where pair_critic/consensus would plausibly help). L2 ≈ L1 on easy fixtures is acceptable.
8. **L2 efficiency**: `L2-vs-L1-best-of-M` is the economic baseline (M = `L2_wall / L1_wall`). Same dominance rule as #2.
9. **Short-circuit discipline**: VERIFY's JUDGE only fires the pair audit when first-model fails a deterministic checklist or coverage gate. `coverage_failed=true` triggers escalate-to-pair regardless of severity counts.

### Measurement validity (added 2026-04-30 from iter-0027/0028 lesson)

10. **Oracle correctness comes before mechanism cleverness.** If a fixture's `expected.json` regex over-matches or under-matches, every downstream conclusion is invalid. Before any iter ships a mechanism that depends on an oracle, the oracle must be smoke-tested against a curated positive/negative case set. iter-0027/0028 cost an entire mechanism cycle by violating this rule — F2's silent-catch regex was over-matching legitimate structured-error returns (38/38 narrow=0 in retrospect).

### Tool-lift vs deliberation-lift (separate signals)

11. Pair lift attribution: tool-lift (deterministic phases firing) vs deliberation-lift (second-model JUDGE producing different conclusions than first-model) must be empirically separated. If the lift is mostly tool-attached and not deliberation-attached, the pair-mode design space changes (cheaper, more solo-default, deliberation only when tool gates fire ambiguous).

### Model-agnostic axis (upgraded 2026-04-30)

12. **First-class via schema + adapter, not promised via inline rewrites.** The 2-skill redesign's `expected.schema.json` is the load-bearing LLM-agnostic decoupler — it must stay stable across model upgrades. Per-model prompt deltas live in `_shared/adapters/<model>.md` as small files, not in skill body rewrites. Cross-model fixtures (Qwen / Gemini / Gemma variant arms) become real once an adapter ships for that model. Until then, the *measured claim* must not exceed the data: "Claude Opus 4.x + GPT-5.5 today; adapter-ready for swap-in."

### Honest claim boundary (Codex R3 + R4)

13. The **contract** in this file requires single-LLM (Opus alone, GPT-5.5 alone) to be first-class. The **measurable product promise** today is Claude-only on the L1 arm — there is no non-Claude orchestrator path yet. The contract stays first-class for both groups; the *measured claim* must not exceed the data.
14. **L2-vs-L1 compression risk**. Evidence must be L2 vs L1, not L2 vs L0. If L1 lands at +9 over L0, then L2's effective lift over L1 must be measured *over L1*, not aliased through L0.

### Real-project trial gate (Codex R2, 2026-04-28)

15. **Final stop condition for Mission 1** — even if all of #1-#14 pass on the 9-fixture suite, the loop does NOT terminate until **one fresh real-project trial passes without manual context engineering**. Definition: a developer who has not tuned the harness picks a real (not fixture) feature/bug from a real (not test) codebase, runs `/devlyn:resolve "<spec or goal>"` end-to-end, and the output ships without human prompt-engineering rescue. Pass = (a) no human edits to skill prompts mid-run, (b) no manual phase re-runs, (c) the produced code passes the project's existing test suite + the developer's spec acceptance check, (d) wall-time within budget for the layer the user paid for.

This gate exists because benchmark fixtures are calibrated targets — passing them confirms the harness behaves *as designed against known cases*, not that it serves the actual user goal. Without #15, the loop can hit perfect 1-14 and ship a benchmark-tuned harness that fails real users on day one.

### Parallel-fleet gate (Mission 2 axis — DEFERRED)

16. **Mission 2 stop condition: parallel-fleet trial.** Pass = the user runs N ≥ 5 simultaneous `/devlyn:resolve` invocations on independent specs, walks away, and on return finds: (a) all N completed without human rescue, (b) per-task quality matches the single-task baseline, (c) aggregate wall-time materially shorter than serialised baseline, (d) zero data crosstalk.

Why this is the Mission 2 gate (not Mission 1): #16 is meaningless if Mission 1 hasn't already delivered overwhelm-level single-task value. **During Mission 1, #16 binds nothing.**

---

## Pair-mode policy (round-3 redesign, 2026-05-03)

Pair-mode is gated by per-phase measurement evidence, not by architectural default. Pair candidates are LLM-judgment phases where upstream mistakes propagate: ideate spec audit, ideate PROJECT coherence audit, resolve PLAN audit, resolve VERIFY/JUDGE, and CLEANUP residual audit as a VERIFY finding axis. Pure-script phases (`archive_run.py`) and LLM-orchestrated mechanical gates (`BUILD_GATE`, `VERIFY-MECHANICAL`) are deterministic gates: command output is truth, and their findings may trigger adjacent model-judgment audits but are not pair-judgment phases themselves. A phase ships pair-mode only after L1-vs-L2 evidence shows quality lift on pair-eligible cases, no unacceptable wall-time regression, no hard-floor regression, and no phase-contamination leak.

As of iter-0036 (2026-05-10): `/devlyn:resolve` remains solo for PLAN / IMPLEMENT / BUILD_GATE / CLEANUP. VERIFY/JUDGE ships as conditional-default pair on measured triggers: verify-only, high-risk specs, risk probes, mechanical warnings, coverage gaps, high/large complexity, or explicit `--pair-verify`. `frozen-verify-gate.py` PASSes on two gated internal runs (F12 `20260505T173913Z-9986cd3-frozen-verify`, F10 `20260505T230215Z-9986cd3-frozen-verify`) and on an eleven-run SWE-bench Lite fixed-diff pilot with durable gate artifacts at `benchmark/auto-resolve/results/swebench-lite-proof-gate-n11.{json,md}`. The SWE-bench gate accepts either external solo-vs-pair verdict lift or internal pair lift (`pair_judge` stricter than the pair run's primary judge) to avoid stochastic primary-judge confounding, and the n11 artifact enforces `--max-pair-solo-wall-ratio 3` with average pair/solo wall ratio 1.87x. The first25 plus bounded 26-50 partial SWE-bench matrix preserves thirty-seven non-gate rows, including no-lift rows, recall-only/advisory rows, `django__django-11422` as a verdict-lift row excluded by wall ratio, `astropy__astropy-14995` as solo-mechanical-dominated, bounded timeout rows, and rows 41-49 as additional controls. F11 `20260506T000258Z-9986cd3-frozen-verify` is recall-only, not gate evidence: pair fired and found MEDIUM/LOW issues, but `pair_verdict_lift=false`.

Full-pipeline L2 now has a clean three-fixture `bare < solo < pair` aggregate proof on the `l2_risk_probes` path. `20260510-f16-f23-f25-combined-proof/full-pipeline-pair-gate.{json,md}` PASSes with F16 at 50 / 75 / 96 (+21, wall 1.28x), F23 at 33 / 66 / 97 (+31, wall 2.25x), and F25 at 25 / 75 / 99 (+24, wall 1.65x), average pair/solo wall ratio 1.73x under the 3.0 cap. This closes the small-suite harness proof for full-pipeline `bare < solo < pair`; it still does not prove broad product superiority across arbitrary user tasks. F21 remains an oracle-control fixture after `priority-blocked.js` was corrected to accept valid later placement. F26-F29 are controls/rejects: F26 failed by solo ceiling, F27/F28 failed because bare solved them 4/4, and F29 failed after hidden-oracle fairness correction at bare 25 / solo 92. F22 exact-error rerun failed by ceiling (bare 94 / solo 98), and F9 fresh headroom failed because bare was disqualified for a silent fallback.

SWE-bench is attached as an external fixed-diff review corpus path through `prepare-swebench-frozen-case.py` / `prepare-swebench-frozen-corpus.py`, with `run-swebench-solver-batch.sh` and `swebench-frozen-matrix.py` supporting larger bounded pilots; it extends the frozen VERIFY gate surface and does not substitute for official SWE-bench solve-rate evaluation. PLAN-pair remains research-only; PROJECT-pair and broader multi-LLM via pi-agent remain future candidates.

### Why this replaces the prior "VERIFY/JUDGE only" table

iter-0020 falsified **Codex-BUILD/IMPLEMENT** routing, NOT pair-mode generally. The "PLAN pair-mode is iter-0020-falsified" framing in `/devlyn:resolve` SKILL.md was overreach — PLAN-pair was iter-0022 infra-only, never measured with real models. The prior table also mislabeled CLEANUP / ideate ELICIT/QUICK/PROJECT as "solo wins"; honest label is "unmeasured".

iter-0033c L2 product run (full 9-fixture suite, 2026-05-02) showed full-pipeline `--pair-verify` regressed scores (l2_gated mean Δ −2.0 vs solo, Gates 2/3/8 FAIL). Codex pair-collab R-final-suite diagnosed root cause as **pair-awareness leakage from PHASE 0 parse-time to IMPLEMENT subagent prompt** — orchestrator's awareness of pair changed how IMPLEMENT reasoned about completeness/defensiveness. Fix: structural firewall (pair runs upstream, IMPLEMENT consumes only the resulting clean contract artifact, no pair metadata).

### Convergence record (round-3 Codex pair-collab)

- **Round 1** (2026-05-02): R0+R0.5+R-final converged on "pair on VERIFY/JUDGE only, frozen-diff post-audit; iter-0033d = 6-fixture verify-only mini-suite". User REJECTED — pair belongs upstream where errors compound, not just downstream audit.
- **Round 2** (2026-05-03): R0+R0.5+R-final converged on "pair-PLAN default with structural firewall; IMPLEMENT consumes only contract; pair-VERIFY = internal fault containment". User REJECTED — verdicts on cleanup/verify-judge/ideate were burden-reversal ("no evidence pair needed" ≠ "evidence solo wins").
- **Round 3** (2026-05-03): R0+R0.5 converged on "measurement-gated; honest unmeasured labels; PLAN-pair first iter to validate; PROJECT-pair second; deterministic 3-way split (pure-script / LLM-orchestrated mechanical-gate / rules-based selection)." Codex 정직: "유저 반박이 맞습니다."

Round-3 is the locked policy.

### Iteration-loop pair vs product pair

Per Codex R2 (2026-04-27): **same vocabulary, different thresholds**.

- **Iteration-loop pair** (R0 reviews, cross-model deliberation on harness changes): human-supervised; pair freely when stakes are above "single-line text edit". Cost amortized over every future run.
- **Product pair** (L2 surface in `/devlyn:resolve` and `/devlyn:ideate`): currently **none shipped** post iter-0034 Phase 4 cutover. iter-0033d/f/g closed PLAN-pair as research-only. Next measurement candidate: VERIFY-pair frozen-diff (iter-0036+); then PROJECT-pair (iter-0033e once defect-class oracle is built); PLAN-pair re-enters scope when unblock condition A or B fires.

Both reuse `solo` / `pair_critic` / `pair_consensus` as the policy vocabulary.

---

## What this North Star displaces / supersedes

- The 16-skill landscape pre-2026-04-30. Replaced by `/devlyn:ideate` + `/devlyn:resolve` + kernel.
- Per-phase pair-mode tables that included BUILD/EVAL/CRITIC pair as separate decisions: superseded by the round-3 measurement-gated policy above.
- The "pair-mode confined to VERIFY/JUDGE only as opt-in/frozen-diff-only" policy: superseded by the iter-0036 conditional-default VERIFY/JUDGE policy after the three-fixture risk-probe aggregate PASS. PLAN-pair remains research-only after iter-0033d/f/g found no empirical subagent-introspection evidence.
- `autoresearch/PRINCIPLES.md` 5 principles + Layer-cost-justified: **unchanged**. Still per-iteration doctrine.
- Deferred memos (multi-LLM orchestration modes, benchmark cross-mix arms, model-agnostic): remain deferred, but model-agnostic upgrades to first-class via the new schema + adapter mechanism in the redesign.

---

## Read order for a new session continuing this work

1. **This file** — what we're optimizing (and the locked product surface).
2. `autoresearch/HANDOFF.md` — current branch state, in-flight work, redesign migration phase.
3. `autoresearch/PRINCIPLES.md` — per-iteration doctrine.
4. `autoresearch/DECISIONS.md` — append-only ship/revert log.
5. Memory: `project_2_skill_harness_redesign_2026_04_30.md` — full redesign decision record.
6. `benchmark/auto-resolve/RUBRIC.md` — judge rubric + ship gates.
7. Most recent iter file (HEAD-adjacent).

If any of those files contradicts this one, **this one wins** until updated. Open a doc-fix iter.
