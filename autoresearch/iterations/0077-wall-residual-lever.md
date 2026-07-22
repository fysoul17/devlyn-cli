# iter-0077 — wall lever: residual (startup + interphase) skeleton absorption (REGISTERED-FROZEN 2026-07-21)

**Why (pre-flight 0)**: wall is the last failing bar and the frozen next target
(HANDOFF item 2 after 0076 CLOSED). User-visible failure: hands-free runs cost
5.9-28.3x bare wall (median 11.324x, bar cap 3.0x/row, nodeg-20260721e). 0075 P-B
(CONFIRMED) named the component: startup + interphase gaps dominate residual
(clean-row -21e shares 90.4-97.0%). Unlock: the go/no-go on whether
orchestrator-turn overhead moves into the deterministic skeleton without degrading
quality or completion — the decision that gates any later M1.5 discussion.
Mission 1, ceiling addendum (efficiency is a ceiling axis; single-task work).

**Round record**: three-way R0+R1 2026-07-21 (packets + logs
/tmp/threeway-0077-r0/). R0: Grok GO-WITH-EDITS, Codex OBJECT-to-shape with
narrowed v2; every seat receipt correction orchestrator-verified at the cited
files before adoption. R1: both seats CONFIRM FREEZE + Q1 fold + Q2 fail-open,
zero wording changes. Orchestrator named deltas vs its own R0 packet: withdrew
W-T prompt-skeleton emission (Decision-Ownership Boundary + two-sources-of-truth
— references/phases/*.md stay the single prompt source) and W-W (receipt
corrected); adopted relative prediction bars (0076 gate-(iii) lesson: never
freeze an absolute bar against an uncorrected baseline).

## Receipts (all orchestrator-opened; cohort nodeg-20260721e unless noted)

- Decomposition (attribution.json): startup 157-422s, interphase 204-811s, tail
  0-93s per row; zeroing startup+interphase on clean rows saves 25.0-46.0% of
  elapsed (honest bound — 3.0x bar is out of reach this iter).
- Session receipts (transcript.txt result lines): duration_api/duration 0.70-0.87
  on verify-complete rows; num_turns 135-173 (F23 incomplete 192; FS1 transcript
  pathological — excluded). The wall is model-turn time, not I/O or idle.
- Gap anatomy (claude-debug.log vs state spans, /tmp/threeway-0077-r0/
  gap-anatomy.json): startup->plan on ALL 7 rows = 21-38 API streams + 14-27
  shell spawns; PHASE 0 (SKILL.md:73-106) executes as ~25-35 LLM turns of
  mechanical bootstrap. Bare (frozen B) solves whole rows in 67-344s — startup
  alone often exceeds it.
- Post-hoc stamping (intermittent, phase-general): F12 probe_derive 106ms vs
  actual ~392s work; F26 probe_derive honest 409,045ms; plan stamped 90ms (F11) /
  75ms (F23) — F11/F23 "startup" contains real PLAN work. The decomposition
  oracle needs correction BEFORE lever credit (ops test #10).
- F11 open-history producer: verify history[0] {started_at, verdict BLOCKED,
  completed_at null} -> 687s false censored span on a healthy row. HONESTY
  CORRECTION to 0076.5 receipt-1: the "SPW attestation-fail path" mechanism claim
  is WRONG — do_complete writes completed_at BEFORE attestation forcing
  (state-phase-write.py:1232, :1290-1294; write_state precedes the exit-1 return
  :2422-2425). True producer = complete skipped before re-spawn; root-cause in
  Stage A0.
- F11's 910s implement->SC window contains a full FIRST round of
  BUILD_GATE/CLEANUP/VERIFY (hist:1 each) — quick anatomy ignored history[];
  attribution.py unions history and was never wrong (F11 official interphase
  204s).
- K2b (F23): fix-loop re-entry past the arm cap; watchdog TERM at 3600s
  (run-ceiling-arm.sh:140, :645) but the child survived to 4203s and OPENED NEW
  PHASE SPANS post-TERM (implement 09:17:26, verify 09:19:25, death 09:19:39) —
  benchmark kill-escalation leak, distinct from product wall-awareness.
- Session-tail: HONESTY CORRECTION to 0076.5 receipt-3: -21d F7 tail_ms = 25,021
  (final_report completed 03:20:00.500, cap 03:20:25) — "hung streaming until the
  wall cap" was an overclaim; the hour was consumed by phases. -21e tails 24-93s.
- Quality bar semantics (nodeg-verdict.json): rule = "A never below frozen B on
  any axis"; blind axis decisions currently B_win 45 / A_win 9 (54 decided). A
  "quality 0/7 stays" guard is sign-inverted; corrected guard below.
- Cross-cohort no-lever wall noise band: 10.888 -> 12.1 -> 11.324.

## Mechanisms (frozen)

- **H0 — corrected-oracle admission gate (zero lever credit)**: anatomy corrected
  to union current + history[] spans; phase entry bound to actual dispatch
  evidence where state stamps are post-hoc; ambiguous rows marked ineligible.
  Back-applied to -21e BEFORE lever build: requires >=5/7 unambiguous rows,
  conservation +/-1s per eligible row, published relocation ledger
  (adjusted_bucket := raw_bucket + declared_relocation; unledgered relocation =
  credit invalid). Includes root-causing the F11 open-history producer and fixing
  the SPW writer so re-spawn over an open span cannot produce {started, verdict,
  completed_at:null}. Also folds the arm kill-escalation fix (TERM->KILL so no
  child outlives the cap writing new phase spans) — zero-credit benchmark
  hygiene, measurement-protective (R1 Q1 unanimous).
- **W-B — deterministic PHASE-0 bootstrap** (bucket: startup): one script does
  the mechanical majority of SKILL.md:73-106 — flag validation, engine/config
  preflight, state init, untracked baseline, deterministic preclassification,
  announce receipt — and opens PLAN at PLAN-dispatch time (atomic entry). Model
  keeps: goal/spec reading, criteria synthesis, risk/complexity override.
- **W-T0 — atomic transition verb, machine data only** (bucket: interphase): SPW
  verb completing the current phase + opening a caller-specified, mechanically
  legal next phase in one transaction, returning paths/digests/state data ONLY.
  No prompt rendering, no agent spawn/selection, no auto-advance. Structurally
  prevents open-history re-entry and post-hoc starts.
- **CUT**: W-W tail watchdog (unanimous; class evidence dissolved by the -21d
  correction). **K2b**: record-only (Thermometer Integrity / Outcome-Preserving
  Deadline Authority); indirect relief via W-B/W-T0 is a secondary observation,
  never a primary claim.

Decisive criteria (named, adopted): Decision-Ownership Boundary (P1);
Thermometer Integrity + Outcome-Preserving Deadline Authority (P2); Product-Path
Causality (P3); Same-Oracle Comparability via adjusted-bucket + relocation
ledger (P4); Minimum Independent Decision Set (P5); Matched-Oracle Net Reduction
(P6).

## Stage plan

- **Stage A0 (H0)** — Codex sol build, benchmark-only: anatomy correction +
  -21e back-application + relocation ledger + F11-producer root-cause + SPW
  writer discipline + kill-escalation fix + self-tests from the real -21e
  receipts (F11 open-history, F12/F26 probe_derive pair, F11/F23 plan stamps).
  Gates: P-0077-H passes; deterministic absolute numbers for the P-B/P-T
  denominators published before lever build.
- **Stage A1 (levers)** — Codex sol build: W-B bootstrap script + W-T0 SPW verb
  + SKILL PHASE-0/transition contract edits (net-subtractive on prose: the
  script absorbs enumerated mechanical steps). Gates: SPW self-tests green; lint
  + token gauge + config<->.claude sync; one live micro-probe row under the arm
  recipe (sonnet arms / terra executor — test-tiering directive 2026-07-21) with
  FS-0077-B checks.
- **Stage B** — one 7-row cohort: CSV "F7,F25,F26,F11,F12,F23,FS1" F7-first,
  fresh post-Stage-A SHA, run-owned pins both engines (claude 2.1.215 copy +
  codex VENDOR Mach-O 0.144.5, sha-receipted), node v20.19.0, frozen best_B
  baseline unchanged, NEW-COHORT identity. Mechanical report: per-bucket
  adjusted deltas + partition {K1, K2a, K2b, other} + wall bar.

## Frozen predictions (post-lever cohort vs H0-corrected -21e baseline)

- **P-0077-H (admission)**: H0 reconstructs >=5/7 -21e rows unambiguously,
  conservation +/-1s, relocation ledger published — else Stage B BLOCKED.
- **P-0077-B (mechanism)**: adjusted startup median <= 60% of corrected baseline.
- **P-0077-T (mechanism)**: adjusted interphase median <= 75% of corrected
  baseline. (Grok stretch observation 0.55 recorded, not the bar.)
- **P-0077-W (roadmap, fail-open)**: wall-ratio median <= 10.19x (>=10% vs
  11.324x). Wall is a roadmap read, not a revert trigger (R1 Q2 unanimous):
  conserved bucket wins + flat wall implies growth elsewhere (executor variance;
  no-lever noise band above); a miss is reported as an explicit wall-direction
  miss and the residual target re-derived.
- **P-guards (senior)**: complete-verify >=5/7; zero K1; objective >=6/7; blind
  quality B_win axis decisions <= 45 (any quality-bar row passing = improvement,
  never a violation); zero new CRITICAL/HIGH harness-path findings.

## Falsifiers

- **FS-0077-A**: H0 admission fails (<5 unambiguous rows, conservation break, or
  unledgered relocation) -> lever build BLOCKED, redesign.
- **FS-0077-B**: Stage A1 live micro-probe shows W-B/W-T0 changes judgment
  content, agent selection, phase semantics, halt behavior, or autonomy ->
  redesign before cohort.
- **FS-0077-C**: a lever misses its own adjusted-bucket bar -> revert THAT lever
  independently; the other may ship.
- **FS-0077-D**: any senior guard fails -> revert levers; no-degradation is
  senior to wall.
- **FS-0077-E**: decomposition conservation breaks on any Stage B row -> block
  ship.

**Out of scope (frozen)**: C1 wiring (next registration); M1.5 runner; corpus
changes; wall-aware fix-loop; session-tail mechanisms; F26 halt-class
enforcement; L-format-valid-false-N/A.

**Build**: Codex sol (workspace-write, detached, one silent-hang retry;
orchestrator commits builds). Test arms: claude->sonnet, codex->terra.

## STAGE A0 RESULTS (2026-07-21 night, raw before interpretation)

Build: Codex sol (workspace-write, detached, 2352s, zero silent hangs; report
/tmp/threeway-0077-r0/stageA0-build-report.md). Orchestrator closeout: .agents
SPW mirror copy (sandbox read-only there), three-way mirror diff clean, lint
rerun with writable npm cache. All gates orchestrator-re-run on disk:

- **P-0077-H: PASS.** corrected-anatomy.py back-application on -21e:
  eligible 5/7 (F23 out — phase activity after the 3600s cap; F11 out —
  verify history[0] verdict-bearing open span), conservation raw AND
  adjusted residue 0ms on ALL SEVEN rows, relocation ledgers published
  per row/bucket (`adjusted_bucket = raw_bucket + declared_relocation`,
  equation_passed everywhere).
- **Published denominators (frozen)**: P-0077-B adjusted startup median
  225,768ms → 60% target **135,460.8ms**; P-0077-T adjusted interphase
  median 397,906ms → 75% target **298,429.5ms**; population F7, F25,
  F26, F12, FS1.
- Dispatch-binding receipts: F12 interphase 811,208→498,070ms (probe_derive
  bound to its real dispatch); F7 interphase 660,858→397,906ms (build_gate
  history[0] post-hoc stamp bound to its 05:07:51 Agent dispatch, adjusted
  span 263,045ms); F11 startup 308,482→230,683ms and F23 381,061→297,802ms
  (plan stamps bound).
- **F11 producer ROOT-CAUSED**: VERIFY merge wrote BLOCKED onto the open
  span, the caller skipped SPW complete before fix-loop re-entry, and old
  `do_spawn` archived the open span into history[] unconditionally. Fix:
  do_spawn now rejects any {started_at set, completed_at null} span before
  history mutation (fail-closed, SystemExit names the repair path);
  clear_verify_round_artifacts moved AFTER successful spawn (a rejected
  spawn no longer destroys verify artifacts). Self-test replays the literal
  F11 receipt: rejection leaves state byte-identical, no history entry.
- Arm kill-escalation: watchdog now enumerates descendants, TERM → 5s
  grace → KILL; timeout_flag/censoring semantics intact;
  test-ceiling-harness gains a detached TERM-ignoring-child regression.
- Gates green (orchestrator re-run): corrected-anatomy self-test, SPW
  self-test (incl. new F11 test), attribution 25 assertions,
  test-nodeg-cell, test-ceiling-harness, three-way SPW mirror diff,
  lint-skills ALL PASS (npm-pack EPERM on first run was root-owned
  ~/.npm/_cacache — environment, passed with writable cache).
- Build-seat fresh VERIFY pass: one MEDIUM found and fixed pre-handoff
  (F26 self-test now locks the exact honest 409,045ms receipt); final
  zero CRITICAL/HIGH/MEDIUM.

Stage A0 CLOSED → Stage A1 (W-B + W-T0 lever build) unblocked.

## STAGE A1 RESULTS (2026-07-21 night, raw before interpretation)

Build: Codex sol retry (first launch died in a codex models-manager silent
hang at ~7min, zero files written, worktree clean — killed-build recipe
applied, clean relaunch; retry 2958s, complete). Report:
/tmp/threeway-0077-r0/stageA1-build-report.md. Orchestrator closeout:
four .agents mirrors synced (incl. new resolve-bootstrap.py), three-way
cmp clean, all gates re-run on disk:

- **W-B shipped**: config/skills/_shared/resolve-bootstrap.py — one
  invocation absorbs PHASE-0 mechanical steps (flags incl. 18
  BLOCKED:invalid-flags combos, engine/config preflight, schema-v3.0
  state init byte-exact, untracked baseline, goal-file rules +
  goal.raw.txt + sha256, spec staging --check/--check-expected,
  deterministic complexity + risk preclassification, announce), emits
  one machine JSON; model keeps goal/spec reading, criteria synthesis,
  reasoned overrides. Self-test: 8 families PASS.
- **W-T0 shipped**: SPW `transition` verb — completes current + opens
  caller-specified next phase in ONE atomic state write (deep-copy
  candidate, single replace); legal-edge table validates the edge but
  never selects it; machine-only JSON out. Self-tests: atomicity under
  forced midpoint failure, attestation mismatch, illegal edge, open-span
  guard — all leave state byte-identical; happy path commits both.
- **SKILL net-subtractive (hard requirement met)**: cold-start 330→317
  lines, 43,962→38,781 chars, tok≈c/4 10,990→9,695 (−11.8%); resolve
  subtotal 30,196→29,045. PHASE 0 prose = bootstrap call + judgment
  steps + spawn-at-dispatch; transition_protocol block added; the
  --engine/pair sentence relocated to <engine_routing> (contract
  preserved). Recorded observation (no action): --max-rounds/--bypass
  value semantics now live in the self-tested bootstrap, not SKILL
  prose; fix-loop budget semantics remain in PHASE 3/5.
- **FS-0077-B self-audit + orchestrator diff review**: no judgment
  content moved, no agent/phase/engine selection in scripts, no prompt
  rendering, no new halt class, PHASE 1.5/2.5 + M-RE/M0/M2v2 + fix-loop
  + VERIFY/pair + autonomy lines untouched. Frozen oracle files
  (corrected-anatomy.py, attribution.py) untouched (git diff clean).
- Gates green (orchestrator re-run): bootstrap self-test, SPW self-test
  (6 transition + F11 + all M-CP), spec-verify self-test, nodeg-cell,
  lint-skills ALL PASS after mirror closeout.

Stage A1 build CLOSED → live micro-probe (FS-0077-B live check,
sonnet arms / terra executor) next; Stage B cohort after probe PASS.

## LIVE MICRO-PROBE (F12 ×2, 2026-07-21→22, raw before interpretation)

Recipe: run-nodeg-cell.sh --tasks "F12", worktree ae9f9ae
(exam-0077-probe), pins claude 2.1.215 (90608b5c…, run-owned copy) +
codex VENDOR 0.144.5, node v20.19.0, health ping before each launch.
probe-b first launch refused on the documented worktree-dirty gotcha
(probe-a results untracked) — archived to main-repo results/, relaunched.

- **probe-a (iter0077-probe-a): FAILED-INCOMPLETE, K2a shape.** invoke_exit
  0, elapsed 1568s, build_gate open. Mechanism (claude-debug.log): the
  sonnet orchestrator dispatched the BUILD_GATE Agent as a BACKGROUND task
  and ended its turn ("Waiting for the BUILD_GATE agent's completion
  notification"); headless print wind-down aborted the 141s-old agent
  (`tool_dispatch_end tool=Agent outcome=aborted`; "print wind-down: no
  longer waiting on background local_agent task"). Pre-existing K2a class
  (FS1 -21e, F25 -20260720e: invoke_exit 0 + phase open). C2 classified
  FAILED-INCOMPLETE correctly. Objective: resolved 1/1 (terra implement
  was correct before the death). Lever receipts on the same row:
  bootstrap state init exact (risk keywords + documented probe-demote
  reason recorded), plan→implement gap 0ms, implement→build_gate 1ms,
  turns 149 (-21e) → 32.
- **probe-b (iter0077-probe-b): FULL COMPLETION.** elapsed 3240s < cap,
  timed_out false, objective 1/1. Full chain incl. fix-loop: plan →
  implement r1 → build_gate PASS (probe-a's death point, foreground) →
  cleanup → verify r1 NEEDS_WORK → implement r2 (fix) → verify r2
  NEEDS_WORK → final_report terminal NEEDS_WORK → archived. The F11-class
  re-entry path (verify→fix→re-verify) ran clean under the new open-span
  guard. Transition gaps: plan→implement 1ms, build_gate→cleanup 0ms.
- **FS-0077-B ADJUDICATION: NOT FIRED.** probe-b completing the identical
  row end-to-end refutes stack-induced systematic death; probe-a is
  sonnet draw variance of the out-of-scope K2a class (C1 wiring packet
  receipt). Mechanisms behaved contractually in BOTH probes.
- **Environment contamination caveat (user-reported, binding on Stage B)**:
  during both probes the machine ran multiple concurrent sessions across
  projects and the network moved between mobile hotspot and home wifi.
  Absolute wall numbers from the probes are therefore NOT lever evidence
  (behavioral gates only — that is all the probes were for). Stage B
  launches ONLY in a quiet window: no other heavy sessions on the
  machine, stable home network, API health-gated (2-ping recipe).

## Principles check

- **0**: closes the frozen wall failure (11.324x median; user-visible wall-time)
  and unlocks the skeleton-absorption go/no-go for the loop's next architecture
  decision. Predictions frozen before any build.
- **7**: Mission 1 ceiling addendum — single-task efficiency instrument + lever;
  no parallel-fleet surface touched.
- **1**: two credited levers + one zero-credit admission gate; W-W cut,
  prompt-skeleton emission cut, K2b record-only; SKILL edits net-subtractive on
  prose (script absorbs enumerated steps).
- **2**: falsifiable per-bucket bars + fail-open roadmap wall bar + senior
  guards, all frozen above before Stage A0.
- **3**: why-chain landed on two violated invariants: (wall) mechanical,
  contract-determined steps must not execute at LLM-turn latency (asymmetric
  harness: determinism in the skeleton); (oracle) phase records must reflect
  actual spans or every wall conclusion is unfalsifiable (ops test #10).
- **4/5**: Stage A self-tests from real receipts; standard primitives (SPW verb
  family, existing attribution union); no new defensive layers.
- **6**: no new pair surface; micro-probe is minutes-tier; cohort is the
  existing periodic exam (measurement-tiering rule 7).

## STAGE B RESULTS (cohort nodeg-20260722a, 2026-07-22, raw before interpretation)

Launch: quiet window (user-cleared) + API health gate 2/2 (09:29/09:49) +
worktree ae9f9ae clean + pins sha-verified. Full completion 09:49→15:21,
zero draws. Artifacts: benchmark/ceiling/results/nodeg-20260722a/
(nodeg-verdict.json + corrected-baseline.json; committed with this record).

- **P-0077-B (startup ≤135,460.8ms): MISS** — adjusted startup median
  250,220ms = 110.8% of the corrected -21e baseline (target 60%).
  Per-row: F7 111,738 / F11 142,737 / F12 223,775 / F26 250,220 /
  FS1 287,534 / F25 316,790 / F23 457,952.
- **P-0077-T (interphase ≤298,429.5ms): PASS** — adjusted interphase
  median 47,698ms = 12.0% of baseline (bar 75%; Grok stretch 0.55
  obliterated). Per-row: F11 0 / F12 5,159 / F26 26,160 / F7 47,698 /
  F25 115,327 / FS1 121,302 / F23 279,838.
- **P-0077-W (wall ≤10.19×, fail-open): MISS at 10.659×** — below the
  ENTIRE no-lever noise band (10.888/12.1/11.324; best cohort median
  ever measured — descriptive only, not improvement evidence beyond the
  band). Ratios: F25 9.54 / F23 9.95 / F12 10.46 / F11 10.66 /
  F26 10.75 / FS1 10.90 / F7 35.46 (composition outlier: startup only
  111.7s, phase_union 2,191.7s carries it; included per
  no-post-hoc-outlier-surgery — excluding it the median is still a miss).
- **Senior guards ALL PASS (FS-0077-D clear)**: complete-verify 6/7
  (best ever; sole incomplete F11 = K2a, invoke_exit 0, censored open
  489,547ms — pre-hook baseline datum for 0078, never a P-0078-C read);
  **zero K1** — sole SC event cohort-wide is FS1 surface_close
  skipped_reason=surface_close_rolled_back_adjudication_malformed +
  continued_after_block=true then completed VERIFY: **0076 M0
  skip-carrier FIRST CLEAN LIVE COHORT FIRING** (mechanism receipt);
  objective 6/7 (F12 hidden-oracle behavioral, apply_exit 0,
  unconfounded); blind axes A_win 19 / B_win 36 / tie 1 (guard ≤45
  PASS; A_win 9→19 direction improvement, not a quality-bar claim);
  zero harness-path CRITICAL/HIGH (snapshot severity hits are VERIFY
  findings on fixture task code). Conservation adjusted residue 0ms on
  ALL 7 rows (FS-0077-E clear); eligible 7/7.
- Partition: {K1: 0, K2a: 1 (F11), K2b: 0, other: 0}.

## STAGE B ADJUDICATION (three-way R-final 2026-07-22, packets /tmp/threeway-0077-stageB/)

Seat verdicts: Q1 W-T0 SHIP unanimous. Q4 shape-unchanged unanimous
(no post-hoc outlier surgery; F7 stays). Q3 fail-open miss accepted by
both; Codex broadened the residual with a fresh measurement the
orchestrator VERIFIED on both corrected-baseline artifacts: matched
frozen-five phase_union median 1,664,239→2,191,700ms (+31.7%), all
five frozen-population rows increased (F12 +12.9% / F26 +15.0% /
F25 +22.9% / F7 +83.4% / FS1 +248.3%), FS1 increase > F7. Honesty
caveats recorded: over all SEVEN matched rows F23 (−15.6%) and F11
(−10.7%) DECREASED; FS1/F11 deltas carry a completion-mix caveat
(-21e FS1 died mid-flight, so its phase mass was truncated).
**Q2 split**: Grok Option B (claim/carrier separation, hard
anti-laundering bounds, strip = separate registration); Codex OBJECT →
gated Option C (Claim-to-Byte Earned-Keep: 0078 measured only
state-init + session stamp — the remaining absorption machinery is
unearned; strip now, re-run gates). Both seats named the SAME strongest
counter (post-hoc claim substitution / file-colocation laundering).

**Orchestrator synthesis (named criterion: No Unregistered Survival)**:
falsified machinery may outlive its falsification ONLY under a
registered, gated, deadlined removal obligation. Adopted: **P-0077-B
MISS recorded, zero startup-lever credit, W-B loses lever status
(FS-0077-C executed at claim level tonight — no third unmeasured byte
shape created inside this closeout)** + **the strip is REGISTERED
IMMEDIATELY as iter-0078 Stage A2** (bootstrap slims to
state-init + session-stamp — the 0078-measured surface; absorbed
PHASE-0 steps return to SKILL prose; gates = bootstrap/state byte
contract re-run + P-0078-K/O/I re-run + one live resolve micro-probe
row sonnet/terra; deadline = BEFORE the first hook-bearing cohort so
no further measurement rides the unearned carrier). Grok's hard bounds
adopted verbatim: retention arguments may cite only 0078's measured
claim; "bootstrap almost earned P-B" is banned; future startup credit
requires a NEW registered bar; the laundering counter is recorded here,
not waved away.

**Record corrections (Codex Q4, orchestrator-verified)**: (a) the
treatment corrected-baseline.json `denominators.*_absolute_target_ms`
fields are SELF-REFERENTIAL (0.6/0.75 × this cohort's own medians —
150,132 / 35,773.5); they must never replace the frozen -21e targets
(135,460.8 / 298,429.5) in any adjudication (instrument-labeling
record-only note; corrected-anatomy.py is a frozen oracle, no edit).
(b) Cohort artifacts were local-until-committed during the R-final
(consistent with R-final-before-commit); committed with this record.

**Wall residual re-derivation (fail-open obligation)**: next targets =
(1) STARTUP — oracle-corrected, unmoved at 110.8%, requires a NEW
lever registration with a fresh mechanism hypothesis (the mechanical-
absorption hypothesis is falsified: the model re-derives PHASE-0
context at LLM latency regardless of the script); (2) PHASE-UNION
growth/variance (different lever class — executor/model work, not
skeleton; F7/FS1 exemplars with the completion-mix caveat). The 12%
interphase win was largely absorbed by phase growth on this cohort.

Iter-0077 verdict: **PARTIAL SHIP** — W-T0 shipped (12% of baseline,
conservation-clean), H0 corrected oracle shipped (Stage A0), W-B
claim-revoked with registered removal obligation, wall direction
missed fail-open with the residual re-named. CLOSED.
