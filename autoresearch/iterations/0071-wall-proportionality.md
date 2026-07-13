# iter-0071 — proportional escalation + wall attribution (attack-the-wall lane B)

status: PRE-REGISTERED 2026-07-13 (three-way R0+R1: Grok 4.5 + Codex sol;
archives `/tmp/iter0071-r0/`, ephemeral — this file is the durable record).
Supersedes the "B. Wall-shave mechanism" branch of
`0068-attack-the-wall-STUB.md` (that fork was adjudicated corpus-pivot-first;
0068 ran to VALID-NEGATIVE, unlocking this lane). Design frozen BEFORE any
lever lands; measured claims only after the pre-registered re-measure.

## Why this exists (pre-flight 0)

Third independent over-tightening confirmation (DECISIONS 0068.9): 0064 LC3
4.32×, 0067 8.33×, nodeg-20260713 7.7-30.4× (median ~8.9×) — the harness pays
a structural wall multiple on tasks bare engines solve in 67-344s, violating
the no-suppression directive (HANDOFF Block 8: the harness must AMPLIFY;
over-tightening is the live risk, and wall is its best-evidenced axis).

## Measured decomposition (nodeg-20260713 A-arms; DEVELOPMENT EVIDENCE pending
re-emission through the repaired verdict gate — see Integrity note)

| task | A wall | B wall | plan | probe | impl | gate | cleanup | verify | gap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F7 | 2035 | 67 | 95 | 346 | 337 | 136 | 68 | 487 | 566 |
| F11 | 1957 | 123 | 79 | 347 | 265 | 331 | 61 | 444 | 431 |
| F12 | 1778 | 224 | 177 | 262 | 248 | 99 | 49 | 408 | 520 |
| F23 | 3051 | 344 | 175 | 369 | 180 | 132 | 150 | 585 | 1437 |
| F25 | 3600(TO) | 263 | 159 | 327 | 93 | 176 | 65 | n/r | 2779 |
| F26 | 2227 | 259 | 102 | 338 | 338 | 161 | 68 | 518 | 682 |
| FS1 | 2402 | 310 | 265 | — | 152 | 513 | 76 | n/r | 1395 |

Facts verified at source (2026-07-13 session): complexity="large" 7/7 — every
task.txt >80 words (102-489) and the `free-form-mode.md` Large branch fires on
`goal_length > 80` ALONE (any-one condition); high_risk=true 6/7 from
SKILL.md:104 domain vocabulary (no scale signal); probe_derive ~332s mean on
6/7; pair judge sequential-after-primary (SKILL.md:293) and forced by
`run-ceiling-arm.sh:148` (`--pair-verify` always — executor=codex convention);
rows with rounds.global=1 (F25/F23/FS1) are exactly the max-gap rows — phase
re-entries overwrite `started_at`/`completed_at`, so fix-loop work hides in
"gap". Prior corroboration: 0067 VERIFY 488-800s with pair changing 0/3
verdicts; gaps 235-1604s (`0068-attack-the-wall-STUB.md`).

## Root cause (refined by R0 — both engines attacked and narrowed the
classifier-only story)

Violated invariant: **escalation cost must track expected failure surface, not
vocabulary or specification length.** But the classifier is CONTRIBUTORY, not
the whole wall: forced pair-verify, the phase-ceremony floor, and orchestrator
gaps are independent terms (Codex, criterion *Arithmetic Closure of Causal
Levers*: deleting probes alone leaves median ~7.8×; deleting plan+probe+verify
still leaves every completed row >3×). 0071 therefore ships the
proportionality levers it can justify AND the attribution instrumentation that
makes the next lever selectable on evidence — no prediction the arithmetic
forbids.

## Ship-set (frozen)

1. **L-A (subtractive classifier repair)**: delete `goal_length > 80` as a
   SUFFICIENT Large trigger in `free-form-mode.md` (scope/verb/zero-signal
   conditions remain). Risk labels are NOT scale-downgraded: high_risk stays
   consequence-based (a small auth/money change still has high failure
   impact). Scale gates the RESPONSE (probes, pair), not the label.
2. **L-B (post-PLAN probe proportionality)**: auto risk-probes fire from the
   PLAN-known failure surface, not PHASE-0 keyword risk alone. **Frozen
   deterministic predicate (Codex R1 requirement — frozen here, before any
   implementation)**: `probe_scale_small := len(plan.authorized_surface) <= 2
   AND no entry ends in "/**"`, computed from the mechanical
   `<!-- devlyn:authorized-surface -->` JSON block BUILD_GATE already enforces
   (`references/phases/plan.md:18`). Auto-probes fire iff
   `high_risk AND NOT probe_scale_small`. Explicit `--risk-probes` unchanged
   (promise semantics). Probes remain an independent findings-as-checks phase
   (NOT folded into PLAN). The `<=2` constant is a designed choice recorded
   here; amendable only by dated amendment on evidence.
3. **L-D (gap attribution, instrumentation only)**: phase re-entries APPEND
   per-entry records instead of overwriting timestamps, and inter-phase time
   is attributed — EXTENDING the existing instruments
   (`benchmark/ceiling/scripts/interphase-turns.py`, iter-0066 rounds
   surface), not duplicating them (Codex R1). No obligation deletion in 0071.
4. **nodeg driver attestation repair**: `run-nodeg-cell.sh:75` stages the A
   artifact_dir in-repo → `opaque_paths` attestation structurally fails
   (`run-ceiling-arm.sh:700-708`). Repair = stage under the opaque external
   root during the attempt, copy back post-attempt (the F12-supplement
   convention, 0068:703-706).

## Explicitly BLOCKED on user adjudication (pre-registered, not shipped)

**L-C′ (VERIFY shape)**: when executor=codex, make the PRIMARY judge the OTHER
engine (cross-engine review with ONE judge); the second judge fires only on
escalation — primary non-PASS / coverage.failed / mechanical-or-judge
warnings, NOT `risk.high` alone (which would keep two judges on 6/7 current
rows). Three-way position: this preserves the convention's INTENT (no
codex-on-codex solo self-review, memory
`feedback_executor_codex_always_pair_verify`) but changes the user-established
always-`--pair-verify` MECHANISM and judge count → user decision. Measured
motivation: VERIFY 408-585s on saturated rows; pair changed 0/3 verdicts
(0067). The forced `--pair-verify` in `run-ceiling-arm.sh:148` is a registered
CONFOUND: until L-C′ is adjudicated, the nodeg re-measure evaluates L-B
(+ partial L-A) only — VERIFY-shape savings are invisible by construction.

## Predictions (frozen BEFORE implementation)

- **P1**: post-repair re-measure keeps objective 7/7 PASS.
- **P2′ (phase-causal)**: on re-measured rows where the frozen
  `probe_scale_small` predicate holds, probe_derive does not fire; per-phase
  deltas show no substitute phase absorbing the removed time (totals alone
  insufficient).
- **P3′ (attribution)**: L-D instrumentation accounts ≥80% of former "gap"
  time into named activities (fix-loop re-entries, state ceremony, subagent
  spawn) on the re-measure.
- **P4 (no-suppression guard)**: violation-matrix + compliance-cell
  instruments show no regression vs current baseline.
- Wall ratios are REPORTED, not gated, for L-A/L-B: 3.0 remains the
  registered PRODUCT bar (0070a addendum-2 E1 registration), not a prediction
  for these levers.

## Loss conditions

- **L1**: probes still fire on `probe_scale_small` rows post-L-B → L-B failed
  (no retuning; report).
- **L2**: any categorical-reliability instrument regresses → revert lever
  (smallest unit), re-smoke; 2× fail → surface.
- **L3**: P3′ <80% → attribution design inadequate; next lever selection stays
  evidence-starved; report honestly.
- **L4**: fixture-literal tuning detected in any lever diff (thermometer
  discipline) → revert.

## Integrity note (binding; three-way convergent)

nodeg-20260713's recorded objective/wall numbers (DECISIONS 0068.9) were
computed OUTSIDE the fail-closed `verdict()` path (dies at nodeg-cell.py:494
missing judge aggregate + :512 E2 opaque check; all 7 A attempts carry
`opaque_paths.passed=false` from the driver staging defect). Materiality
probe: engine prompt has zero in-repo paths; all other isolation checks true;
engine-visible surfaces fully opaque → attestation-layer defect, not engine
contamination. Numbers are DEVELOPMENT EVIDENCE until re-emitted through the
repaired gate with the deviation block (0068 Closure addendum 3 defines the
replay protocol). The wall-lever motivation is unaffected (0064/0067
independently establish the class).

## Execution order (Codex R1 amendment, adopted)

1. Docs land (this file + 0068 addendum 3 + 0070a addendum 9 + DECISIONS).
2. Codex sol builds in an isolated worktree (guardrail block mandatory):
   (a) nodeg staging repair + binding-manifest writer + deviation-flag
   support + selftests; (b) `classify-defect-family.py` + microcases +
   manifest routing block (per-pair regression labels include credential
   good-a↔bad-dependency = INELIGIBLE — orchestrator byte-verified, 33 mixed
   path deltas); then (c) L-A/L-B/L-D skill edits + lint + token gauge +
   selftests + 3-mirror sync.
3. Grok audits landed diffs.
4. Judge-only replay AFTER 2(a) lands and the binding manifest is physically
   written; verdict re-emitted with deviations[].
5. Author-export materialization → Grok byte audit → opus authoring (0070a).
6. nodeg re-measure (fresh window) AFTER levers land — the P1/P2′/P3′ gate.

## Execution addendum 1 (2026-07-13) — ship-set LANDED; baseline verdict complete

All four ship-set items SHIPPED same day (three-way loop): packet 1
`57f7f27` (staging repair + binding manifest + strict deviations +
classifier), git() porcelain hotfix `2ef3a1b` (+ regression selftest in
packet 2), packet 2 `18c5320` (L-A/L-B/L-D, net −5 lines, lint + token
gauge + selftests + mirrors), dev3 `fca4d1d` (third deviation type).
Judge replay executed under protocol a′ → **frozen baseline verdict**
(0068 closure addendum 4): objective 7/7 PASS, quality 0/7 FAIL, wall 0/7
FAIL. The P1/P2′/P3′ re-measure now has its gate-emitted baseline; the
quality axis (bare's diffs blind-preferred on every row) is added evidence
that suppression is not wall-only — candidate quality levers are NOT in
0071 scope (design three-way first; note F7 delta: bare updated USAGE +
added error-path test, pipeline patch did neither).

## Execution addendum 2 (2026-07-13) — L-C′ USER-ADJUDICATED: escalation-only REJECTED

User verdict (verbatim intent): one engine repeatedly catches what the other
misses — reducing the second judge to warning/failure-triggered escalation
carries real risk. Named delta accepted by the orchestrator: the 0/3
verdict-change evidence (iter-0067) is n=3 on saturated rows; the
complementary-detection evidence is broader and this-session-measured (T1
seat×defect override matrix: catalog admits only sonnet, credential only
terra, both risk-diff 1.0; judge disagreement terra 28/28 vs sonnet 20/28 on
identical diffs; Grok-only and Codex-only catches in the same round).
**L-C′ escalation-only is dead. Both judges stay, always (when pair
triggers fire).** Replacement wall lever under three-way review: run the
two judges CONCURRENTLY (wall ≈ max instead of sum) with zero coverage
change — see addendum 3 when adjudicated.

## Execution addendum 3 (2026-07-13/14) — replacement lever CONVERGED: concurrent dual-judge (design frozen, ship-gated)

Three-way round on the packet `/tmp/iter0071-r0/parallel-judge-packet.md`
(archives `{grok,codex}-pj.log`, ephemeral): **Grok GO-WITH-EDITS + Codex
GO-WITH-EDITS, convergent.** Design: when ≥1 OUTCOME-INDEPENDENT canonical
pair reason holds at VERIFY start (mode.*, complexity.*, spec.*, risk.high,
risk_probes.*), spawn primary and OTHER-engine judge CONCURRENTLY on the
same frozen diff (foreground parallel tool dispatch — never background
shells, iter-0009); outcome-dependent reasons (coverage.failed,
mechanical.warning, judge.warning) keep the sequential escalation path;
merge/verdict rule unchanged (worst-source-verdict, no vote counting —
verify-merge-findings.py:824 region). Wall on pre-known-trigger runs:
max(primary, pair) instead of sum. Coverage unchanged — user adjudication
0071.1 honored; a concurrent pair on a primary-blocker run now ADDS its
findings to the fix round instead of being skipped.

Combined MUST-EDIT list (both engines, orchestrator-verified citations):
1. verify-merge-findings.py: `primary_judge_blocker` currently EXCUSES
   missing pair output (:561,:573) — for pre-known triggers it must not;
   +3 validator tests (pre-known+primary-HIGH+missing-pair → BLOCKED;
   pre-known+primary-HIGH+pair-present → merged; no-pre-known+blocker →
   today's sequential skip stays legal).
2. Sequencing pins replaced across SKILL.md (:284,:293), references/phases/
   verify.md pair section, state-schema.md, all 3 mirrors, and
   lint-skills.sh:1321 (currently requires wait-for-primary evidence).
3. pair_trigger write-order: pre-known reasons at spawn; outcome-dependent
   reasons appended after primary; final object must satisfy the unchanged
   merge contract (validator checks shape only — orchestrator-verified).
4. Per-judge duration split added to sub_verdicts (today only aggregate
   VERIFY duration exists — savings otherwise unmeasurable).
5. Probe/runtime isolation: judges execute scenarios against the same
   project root — concurrent DESTRUCTIVE probes can contend (ports/DB/tmp).
   Rule: concurrency of judging, not of destructive shared-side-effect
   runners — read-only checks preferred; exclusive-state probes serialize.
6. Engine-neutral fallback: an orchestrator that cannot issue parallel
   dispatch falls back to today's sequential shape (safe degradation).

**Ship gate (accepted falsifier, both engines)**: a frozen-diff
solo-vs-concurrent canary — either judge's normalized findings changing
because it observed sibling artifacts or contended on runtime state, or a
pre-known-trigger primary-blocker run completing without pair evidence,
flips this to NO-GO. Implementation = next Codex build packet (worktree,
guardrails) at a fresh budget window; NOT landed in this session.
