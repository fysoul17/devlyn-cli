# iter-0070a — non-coding-axis instruments: admission kernel + intent/packet cells

status: **PRE-REGISTRATION DRAFT v2** (2026-07-11; three-way R0 folded —
Grok 4.5 + Codex-sol both GO-WITH-EDITS, archives
`/tmp/iter0070a-r0/{grok,codex}-response.log`, ephemeral; this file is the
durable record). **NOT ACTIVE / DORMANT**: per the 0070 STUB entry
condition, no cell RUNS until iter-0068 fully closes (admitted-set R1-gate →
A/C + no-suppression decision → closure). This file authors design only —
zero measurement, zero touch to the 0068 corpus/gate/sequencing.

**Versioned-amendment rule (Codex R0 Q1)**: this draft is frozen at commit
time. Any change after 0068 results are opened is a DATED amendment with a
NAMED delta, landed BEFORE 0070 calibration runs — never a silent post-hoc
edit. "Amendable by 0068" means exactly this, not open-ended mutability.

## Why this exists (pre-flight 0)

Block 8/10: frontier coding saturates, so the harness's differentiating
value lives on the non-coding axes. This iter builds the FIRST non-coding
instruments — does the harness (1) grasp the user's real intent without
guessing (axis 1), and (2) produce a better work-packet for the next agent
(axis 2, decomposition/meta-prompting/context-engineering) — measured
mechanically, never by an LLM "good plan" rubric.

## Scope + build order (Q2 adjudication — named delta)

Per the 0070 STUB, 0070a owns axes 1+2. Both cells are DESIGNED here; they
differ only in EXECUTION ORDER:

1. **Counterfactual Intent Holdout — FIRST executable cell.**
2. **Packet Utility Differential — designed now, SECOND executable cell**
   (runs after seat-calibration lands).

**Adjudication (orchestrator, not last-speaker deference).** R0 split: Grok
= Packet-first (criterion *Measurement-Gap × Causal Tractability* — Packet
is the largest uncovered vacuum); Codex = Intent-first (criterion *Shortest
Identifiable Causal Chain* — Intent's R/Q outcome is direct, Packet adds an
author→packet→executor→oracle mediation with two stochastic stages + an
unresolved seat). **Decisive criterion adopted: the first cell's job is to
VALIDATE THE KERNEL cleanly, so execution order is set by attribution
cleanliness, not gap size.** Named delta from my draft-v1 Packet-first: a
mediation-fragile instrument (Packet, L1 death risk) is a poor kernel
validator — it can die for reasons unrelated to the kernel. Intent is
direct-attribution → runs first. Grok's gap point is honored (Packet stays
fully in-scope and prominent, not deferred to 0070b); Grok itself conceded
Intent-first if seat calibration is slow. Codex's cleaner-attribution point
sets the order. No side capitulated: scope = both (Grok), order = Intent
first (Codex).

## Non-Coding Admission Kernel (the durable asset; fixtures disposable)

Every 0070 instrument inherits:

- **Arms**: A (harness path) vs B (bare same-engine) + **C copycat** (bare
  engine given the frozen public method card). **Moat predicate =
  `A > best_B AND A > best_C`** (Codex omission #2; 0068 contract
  `:190`) — A>B alone is method/harness lift, never a product moat
  (NORTH-STAR ops #17). Comparison is **blind, matched-wall, best-of-N**
  (NORTH-STAR `:165`,`:232`) — naming C is not enough.
- **Seats**: measured codex = `gpt-5.6-terra`; orchestrator/judge sonnet;
  sol TEAM-ONLY, never measured; fable never a test arm. Arm identities
  explicit per cell (who authors B/C, what A stack runs, and the downstream
  executor seat — which must not overlap a packet author; Codex #7).
- **Bare-fails admission** (Grok/Codex HIGH — was omitted in v1): a row is
  admitted only if end-to-end B-path fails it on the fixed executor; rows
  where B resolves become the **saturated no-suppression controls** (not
  discarded).
- **Calibration ⟂ scored fixtures** (Codex #4): calibration fixtures are
  DISJOINT from scored A/B/C fixtures — no selection/tuning leakage.
- **Cohort identity**: CLI version + requested alias + runtime-resolved
  model + run id, PLUS C's frozen method snapshot (prompt hash, author
  model/runtime, sampling params, resource envelope — Codex #9). Drift ⇒
  re-gate.
- **UNFAIR review** (audit all three: visible task, known-good packet,
  planted-bad mutation — Codex #5, 0068 `:325`): oracle asserts only what
  the visible task / repo evidence / shared packet determines; known-good
  packets carry no hidden adversarial values or solution mechanisms.
- **No-suppression — EXECUTABLE bars** (Codex #6; not declarative): on the
  saturated controls the harness must (i) preserve B's objective outcome,
  (ii) not lose the blind quality standing, (iii) stay within the wall cap
  (HANDOFF `:166`).

## Calibration — T0/T1/T2 (Q3 convergent; establishes Mediated Causal Sensitivity)

N≥3 is a smoke/death gate ONLY — insufficient to ESTABLISH sensitivity
(both engines). Pre-registered tiers:

- **T0 smoke (death)**: known-good vs ≥1 planted-bad separate on the primary
  metric; no-op fails; N≥3; NO fixture retuning on failure.
- **T1 establish (admit the instrument+seat)**: per candidate seat, ≥2
  calibration fixtures, each with 2 semantically-equivalent known-good
  packets + 2 minimally-different planted-bad packets covering DISTINCT
  realistic defects (e.g. a dependency defect and an evidence/constraint
  defect). **Each fixed packet run 16× blinded, randomly interleaved,
  identical tools/limits/prompt, fresh workspaces.** Admit only if per
  fixture: each good ≥12/16, each bad ≤4/16, good−bad risk difference ≥0.50
  with a positive 95% interval, and equivalent-good packets differ ≤2/16
  (equivalent-packet stability). Independently-authored packets — NOT
  executor reruns — are the inferential unit; reruns estimate mediator
  noise, never pseudo-replicate. Checked-in power calc ≥80% for the declared
  minimum effect; freeze packet count + executor repeats in the manifest.
- **T2 harness delta**: A vs B on admitted fixtures only; C required for any
  moat. If T1 held-out confirmation fails → instrument DEAD; do NOT switch
  seats/defects after opening scored results.

## Cell 1 — Counterfactual Intent Holdout (first executable)

Paired repo variants, same visible goal (supersedes B1, whose
`hidden/verify.sh:14` rewards always-halt/generic-ambiguity talk):
- **Variant R**: repo evidence uniquely determines the action — unnecessary
  halting FAILS.
- **Variant Q**: repo evidence narrows but cannot resolve one decisive
  choice — only the specifically discriminating question passes; a generic
  question, generic assumption disclosure, or silent plausible guess FAILS.
- **Criterion: Counterfactual Identifiability** — flipping ONLY the
  intent-bearing repo evidence must flip the correct terminal behavior; else
  the hidden intent is author opinion.

## Cell 2 — Packet Utility Differential (designed; second executable)

Packet quality = next-agent outcome, mechanically. Fixed blinded downstream
executor (seat = calibration output, terra|sonnet, never fable, never a
packet author). **Sole IV = who authored the packet**, on ONE neutral
canonical JSON schema `pud-1` (Codex Q4 — not differing filesystem shapes):

```json
{ "schema_version": "pud-1",
  "project_acceptance": [ { "id": "...", "observable": "..." } ],
  "tasks": [ { "id": "...", "objective": "...", "depends_on": ["..."],
      "context_refs": [ { "path": "...", "line_start": 1, "line_end": 1, "claim": "..." } ],
      "scope": { "may_change": ["..."], "must_preserve": ["..."] },
      "acceptance": [ { "id": "...", "observable": "..." } ], "handoff": "..." } ],
  "open_questions": [ { "question": "...", "blocking": true, "evidence_refs": ["..."] } ],
  "assumptions": [ { "statement": "...", "evidence_refs": ["..."] } ] }
```

- **B** receives only the JSON field/type contract (content-in-contract —
  measures packet quality, not template invention). **C** receives the
  frozen public method card. **A** receives the harness path. Schema syntax
  shared; method is the experimental variable. Any unstructured bare arm =
  diagnostic only.
- **Runner (not the author)** supplies the original task verbatim, repo/base
  SHA, fixture identity, downstream invocation; computes the intent digest;
  validates structure but never reorders tasks, repairs dependencies, or
  enriches content.
- **Metrics raw + separate**, objective-first predicate (Codex #8): compare
  resolve → violations → wall lexicographically; never a fused score.
  PLAN-DAG checks are diagnostic attribution only, never the ship gate.

## Predictions (frozen)

- **P0 (calibration/death)**: T0 separates known-good vs planted-bad; else
  the cell is dead (report; no fixture tuning).
- **P1 (harness delta)**: on ≥1 admitted fixture, A's outcome strictly beats
  B on the objective-first predicate. NULL (A≤B) is load-bearing (harness
  adds no value on that axis/task). **Single-fixture positive = pilot
  signal, NOT a product moat** (Grok #7; 0068 pilot discipline).
- **P2 (moat)**: `A > best_B AND A > best_C` on a blind matched-wall
  best-of-N comparison ⇒ product moat; C≥A ⇒ portable method lift, honestly
  labeled.

## Loss conditions

- **L1**: T1 held-out confirmation fails (executor noise ≥ good–bad gap) ⇒
  instrument dead (Mediated Causal Sensitivity / Separable Mediated
  Sensitivity).
- **L2**: schema not neutral ⇒ A/B differ in path shape not quality (UNFAIR)
  ⇒ fix the lock before any delta claim.
- **L3**: any moat claim without the C arm on a matched-wall best-of-N (ops
  #17).
- **L4**: executor seat saturates (solves regardless of packet) ⇒ no
  headroom; report saturation, do not claim discrimination.
- **L5**: calibration and scored fixtures overlap ⇒ selection leakage ⇒
  invalid.

## Deliverables (build after 0068 closes; Codex executes, orchestrator verifies)

1. **Executor seat calibration FIRST** (not design-answerable — both
   engines): screen `{terra, sonnet}` on the disjoint T0/T1 set; pick the
   Held-Out Maximin Sensitivity seat (worst-case good–bad separation,
   non-saturating, equivalent-packet stable; lower wall = frozen
   tie-breaker). Terra is a candidate, not the answer.
2. **Kernel runner**: A/B/C authoring → fixed-executor downstream → hidden
   oracle → raw objective-first metrics, with calibration + cohort identity
   + bare-fails admission + no-op-fail + no-suppression bars baked in.
3. **Intent Holdout fixtures** (Cell 1): ≥2 R/Q pairs + calibration set.
4. **Packet fixtures** (Cell 2): ≥2 scored + a DISJOINT calibration set,
   each with known-good/planted-bad pairs.

## Decisive criteria (named)

Active-Experiment Non-Interference (Q1) · Shortest Identifiable Causal Chain
(Q2 order) · Separable Mediated Sensitivity (Q3) · Interface Neutrality /
Consumer-Schema Necessity (Q4) · Held-Out Maximin Sensitivity (Q5).

## Pair rounds

- **R0 (2026-07-11, three-way): Grok GO-WITH-EDITS + Codex-sol
  GO-WITH-EDITS.** Both: design-ahead legitimate while dormant
  (measurement-boundary / non-interference); N≥3 underpowered → T0/T1/T2
  (Codex gave the 16×, ≥12/16 good, ≤4/16 bad, risk-diff ≥0.50 numbers);
  minimal neutral consumer schema (Codex `pud-1` JSON adopted over full
  plan.md lock — Grok's structure-subsidy-leak concern); seat calibration
  first (maximin); bare-fails admission field added; oracle↔UNFAIR binding;
  moat = A>best_B ∧ A>best_C; calibration⟂scored fixtures; no-suppression
  executable bars; objective-first predicate; C method frozen; versioned
  amendment rule. **Contested: Q2 order — adjudicated Intent-first (scope =
  both, order by attribution cleanliness), see Scope section.** All folded
  into this v2. Kept unchanged: A/B/C arms, terra/sol seats, no-run-until-
  0068, Mediated Causal Sensitivity as death criterion.
- R1 (pending): on the frozen 0068 admitted set, reconcile the pre-declared
  0068-amend-hook list (which fields may change when no-suppression controls
  land) before any 0070 calibration.
