---
title: "Session-horizon interference cell — opus-5 vs opus-4-8 under accumulated-context horizon"
status: REGISTERED-FROZEN 2026-08-25 (double FREEZE on r4 — sol 9f3c7a1d + grok b8e4c1a3) + AMENDMENT 1 double ADOPT + APPARATUS TRIO-FROZEN 2026-08-26 (final double FREEZE a7b8eab7 sol+grok on identical bytes; launch USER-GATED) + AMENDMENT 2 2026-08-26 (launch preflight) + AMENDMENT 3 2026-08-26 (threshold re-derived 64,000 after the A5 gate FAIL_FAST; double FREEZE sol+grok bc85bde2; relaunch USER-GATED → scheduled after 01:00 KST 08-27) + AMENDMENT 4 2026-08-26 (exact-reproduction launch rule falsified at first use → monotone prefix attestation; T unchanged; double FREEZE sol+grok 025149c6) + AMENDMENT 5 2026-08-27 (second FAIL_FAST — engine-dependent footprints; T 48,000; double FREEZE sol+grok 981c4c83; relaunch = fresh session, root m3-*)
depends_on: ["0109-decoy-parity-pilot", "0103-opus-line-regression-cell", "0102-executor-quality-discovery-corpus"]
---

# iter-0110 — session-horizon interference cell

## Direction decision (2026-08-25 — user-delegated "best practice", fable+sol R0 convergent)

**DECIDED: PIVOT away from the repo-scale discovery mechanism**
(0105/0107/0108/0109 four terminal too-hard-side bounds). First
successor registration = **session-horizon/long-context instrument**,
H1-shaped, **pair assistance held out** so the first measurement
isolates H1 (main-AI design/coding quality — user delta 2026-08-09:
H1 leads, pair-deference later) from H2.

- **Decisive criterion (sol, ADOPTED over fable's knob-response
  evidence with a named delta): PROSPECTIVE GATE-CROSSING
  SUFFICIENCY** — "the mechanism responds somewhere" (knob liveness)
  is weaker than "this intervention is credibly large enough to make
  the registered decision reachable across every anchor and gate."
  Required movements were sonnet −13/40 and opus-4-8 −11/40 of mean
  PLUS interior and shared both-ceiling repairs; no mechanism-
  preserving basis exists for that magnitude.
- **Evidence corrections adopted**: the lineage contains TWO easings,
  not three (0107 was a re-anchor with byte-identical trees —
  0107:28, 0107:74); decoy COUNT was never varied (0108:124
  byte-carried counts; 0109:71 all 12 decoys relocated, none
  removed) — count is a distinct cardinality knob, so B's steelman
  stands as a real unmeasured intervention.
- **B (fifth same-mechanism easing) REJECTED with a registered
  resurrection falsifier**: B moves first iff a pre-registration
  derives an evidence-backed decoy-count effect large enough to move
  BOTH failing anchors through mean + interior + shared-ceiling gates
  while preserving repo-scale (L-R1) and discovery-mechanism
  identity. 12→10 (~17%) has no such basis; a deeper cut relitigates
  the ≥10 distractor-mass law; distance-2 relitigates 0108's
  non-local-minimum finding (0108:138). Absent that falsifier firing,
  the repo-scale module stays BOUNDED (four terminals), not retried.
- **C (matrix-pair-scoped band) REJECTED (convergent)**: the module
  contract makes the sonnet calibrator the SOLE difficulty
  measurement (0105:28-37); opus-4-8 sits near ceiling (7/8,
  interior 2/4, shared both-ceiling), so even a pair-scoped band is
  uninformative at this point; post-hoc band widening risks blessing
  saturation.
- **D (actual-workload factorial: horizon × solo/pair) recorded as a
  later candidate** — its smallest identifiable first slice collapses
  to this registration.
- R0 artifacts: `~/.local/share/nx01/iter0110-direction/`
  (packet.md, r0-sol.log; sol final line `R0-DIRECTION-SOL: A`).

## Registration (R0 three-way 2026-08-25: fable + sol + grok — adjudication § R0 record below)

### Claim under test + scope of claims

This cell measures **position-in-session degradation of 0102
discovery manifestation-fail under real-work-induced
accumulated-context interference** — the engine's own prior scored
work as model-visible history — **without cross-task obligation
carryover**. It does NOT measure accumulated-obligation retention,
architecture coherence at horizon, or the full live signal
(0102:36-40); those require a later registration (staged-invariant
family, or judge routes under `playbooks/model-checkup.md` seat
certification). A null bounds only this shape. H1-shaped; **pair
held out** (direction freeze). A mechanical terminal here must never
be narrated as closing "H1 design quality at long horizon" in full.

### (a) Horizon operationalization

- **Induction = real serialized work, no synthetic filler**: k tasks
  from the sealed corpus worked in ONE session; later tasks carry all
  earlier work as accumulated context. Filler rejected — it measures
  distraction/needle retrieval, not horizon.
- **PRIMARY process shape: driver-fed same-session resume.** One
  scored `claude -p` per task — the 0102 attempt envelope carries
  (opaque workdir mx-driver.py:145-183, hidden oracle after the
  attempt :248-257, exact-ID `modelUsage` attestation per
  invocation :118-135) —
  each subsequent task launched `--resume <previous reported id>`
  under the resume-chain custody rule below (id stability NOT
  assumed). Sequential reveal: each invocation's prompt carries only
  its own goal, never the queue.
- **REGISTERED ALTERNATE** (promoted only if the resume smoke fails):
  same-process realtime `stream-json` driver feeding tasks
  sequentially. This is a NEW stream-json driver + boundary protocol
  (new apparatus; `--print` + `stream-json` requires `--verbose`,
  0074:148) and therefore loses the primary slot under the round's
  decisive criterion.
- **Resume smoke gate (apparatus-time, fail-closed)**: (i) attested
  resume-chain custody holds across ≥2 resumed invocations (id
  STABILITY is not required — the custody rule below is the
  continuity contract); (ii) per-boundary effective context grows by
  a registered margin; (iii) exact-ID attestation present per
  invocation; (iv) request-level usage records are harvestable for
  every boundary (else the primary attestor is unimplementable). Any
  leg fails → alternate promoted; a dishonest horizon is never
  scored.
- **Horizon attestor (primary): REQUEST-LEVEL, request-ID-
  deduplicated effective context** — the peak unique request's
  `input + cache-read + cache-creation` within the boundary's
  invocation, harvested from per-request records by the
  boundary-ledger collector (record source frozen at apparatus
  time). The terminal `modelUsage` aggregate is REJECTED as horizon
  evidence — it accumulates input-side tokens ACROSS requests
  (fable-verified SINGLE-invocation receipt: nodeg-hook-20260722c
  fefo `surface-close.worker-session.0.jsonl`, session `6018fb9a…`
  — across-request cumulative input-side sum 193,126 vs
  request-deduplicated peak 43,685 over 5 unique usage-bearing
  requests: a 4.4× overstatement if an aggregate were read as
  occupancy) — and stays exact-ID + diagnostic only.
  Aggregate-only evidence, or missing/malformed request-level
  records, INVALIDATE the row — fail-closed, no silent fallback.
  Transcript bytes and tool-call counts = diagnostics only
  (compaction makes disk bytes ≠ window).
- **Session continuity = attested resume-chain custody
  (rotation-aware; sol/grok R1 convergent)**: invocation N+1 is
  launched `--resume <id_N>`; the driver records every
  (resumed-id → reported-id) link. Custody holds while each scored
  invocation was launched from the previous link's reported id and
  the CLI accepted the resume — id ROTATION inside an accepted
  resume keeps custody (the recorded link is the proof; the
  0078:98-102 honest bound is folded, not contradicted). A resume
  rejection, a fresh-session start, or a reported id with no
  recorded link BREAKS the chain → that row and all later cells in
  the session are INVALID.
- **Compaction observability on the primary**: the JSON envelope has
  NO `compact_boundary` event (that token exists only in the
  stream-json schema, collect-codex-findings.py:411). On the
  primary, compaction is INFERRED from the boundary ledger
  (effective-context drop between consecutive boundaries and/or a
  recorded id-rotation link) and recorded as a marker; the stream
  `compact_boundary` event is the ALTERNATE-shape attestor.
- **Thresholds**: the registered horizon threshold is the sole absolute
  effective-context threshold (48,000 by AMENDMENT 5, re-derived from BOTH matrix engines' gate-session ledgers — per-task footprints are engine-dependent; tested on the boundary-4 PEAK at any prior boundary); the context-window-fraction leg is RETIRED by
  AMENDMENT 2 (encoded `context_window_fraction_threshold: 0.0` = retired,
  NOT 0 % occupancy); denominators are recorded measured `contextWindow`
  values (1,000,000 for all three engines), no longer gate inputs.
- **Compaction** is measured engine behavior — recorded, never a
  reset exemption: a late cell qualifies if its unbroken custody
  chain crossed the registered threshold at any prior boundary, even
  if the session later compacted (marker recorded).

### (b) Task family: sealed 0102 corpus, byte-identical reuse

- The 32-task sealed 0102 trees reused **byte-identical** (candidate
  manifest tree `294eeade…`); hidden mechanical oracles carry. Any
  carryover-layer mutation = NEW trees = new calibration — rejected
  for this slice.
- The 0102 instrument-reuse clause is satisfied, not stretched:
  session-horizon effects were pre-named as a NEW registration
  (0102 ~:441/~:855) — this is that registration; the reuse is of
  fixtures, not of the 0102 claim.
- **Baselines**: the sealed single-shot aggregates (0102 sonnet
  calibration mean 39/80, interior 30/32; 0103 R(opus-5)=0.294,
  R(opus-4-8)=0.475) serve as the no-history ablation reference via
  G1. Per-task sealed outcomes stay sealed.
- Registered known weakness (accepted): independent tickets give
  accumulated CONTEXT, not accumulated OBLIGATIONS — a real slice of
  long sessions (task-switch interference), not the whole felt
  object.

### (c) Anchors, schedule, gates, decision

- **Matrix pair = `claude-opus-5` vs `claude-opus-4-8`** (the live
  user question; 0102/0103 refuted the felt regression SINGLE-SHOT —
  horizon is the unmeasured axis where it could live). Engine order
  discipline (ABBA) carries from 0103.
- **Calibrator sonnet's role = serialization/transport validator**,
  NOT difficulty-band membership — a REGISTERED departure from the
  0105 module contract (0105:28-37): a horizon instrument must allow
  the calibrator to degrade at late positions; the difficulty axis IS
  the horizon. The 0105 module-success clause does not bind this
  cell.
- **Schedule: counterbalanced task-order crossover in COMPLETE
  REPLICATES** — the schedule is organized into R complete crossover
  replicates; within each replicate every task appears exactly once
  in the EARLY and once in the LATE position class per engine
  (position must not alias with task); order balanced across
  engines. Exact schedule + k (tasks/session) + R derived at
  apparatus time under G0.
- **Gates (all fail-closed)**:
  - **G0 schedule reachability**: (i) a mechanical check that the
    frozen schedule satisfies the crossover law (every task in both
    position classes per engine, per replicate); (ii) a pre-freeze
    synthetic correlated-ledger power proof that R replicates can
    cross the registered decision threshold AND emit BOTH decisive
    terminals — evaluated across a REGISTERED CORRELATION ENVELOPE
    (independence → a registered worst-case within-session
    correlation; marginals anchored to the sealed 0102/0103 rates,
    which carry NO within-session correlation information — the
    envelope is the registered assumption surface, and reachability
    must hold at its worst-case member). Envelope parameters frozen
    with the apparatus.
  - **G1 early transport equivalence**: task-balanced EARLY-position
    means equivalent to the sealed single-shot rates within a
    pre-registered tolerance (sonnet vs 39/80; both opus engines vs
    the 0103 rates). G1 fail ⇒ the serialization wrapping, not
    horizon, is the treatment ⇒ no matrix scoring.
  - **G2 horizon attestation**: every deciding LATE cell sits on an
    unbroken attested resume-chain (custody rule under (a)) whose
    ledger crossed the registered threshold at a prior boundary.
    Compaction markers and rotation-with-recorded-link do NOT
    disqualify; broken custody does.
  - **G3 estimand support**: per-engine sufficient non-tied
    early/late pairs; early all-clean alone does not invalidate
    (late worsening is information).
- **Decision estimand**: per task t and replicate r,
  `d_{t,r} = (late−early)_opus5 − (late−early)_opus48`;
  `ΔH = mean over (t, r)`. **CI = bootstrap over COMPLETE REPLICATES
  (the resampling unit) — NOT per-task and NOT per-session
  resampling**: task-level resampling (score-cohort.py:173-181) is
  registered as insufficient under session clustering (serial tasks
  share session-level shocks); session-level resampling is
  ill-defined for this cross-session estimand (a resampled session
  set leaves early/late task pairs unmatched — R1 grok finding 3).
  Resampling replicates preserves task matching and carries
  session-level shocks inside the resampled unit.
- **Materiality threshold δH**: derived and frozen at apparatus
  freeze; the 0103 `3/20` carries only with explicit justification
  for this interaction estimand.
- **Terminal set** carries the 0103 family shape: CONFIRMED /
  MATERIAL_GAP_REFUTED / INCONCLUSIVE_AT_PILOT_N / a SATURATED-analog
  valid negative (both engines late-uniform ⇒ horizon saturation
  datum, not a 5-vs-4.8 decision). Exact token bijection frozen with
  the derived scorer.
- **Non-decisional diagnostics (mandatory report)**: per-engine
  absolute degradations D_5, D_48; late-position absolute contrast.
  **Headroom caveat registered**: opus-5's early base (0.294) has
  more degradation room than opus-4-8's (0.475) — the registered
  claim is the RELATIVE interaction only; a positive ΔH must never be
  narrated as "opus-5 degrades absolutely."

### (d) Oracle closure

Fully mechanical via the 0102 hidden oracles; **no judge anywhere in
0110**. Judge-gated design-quality axes = a later registration under
the 0104 checkup seat-certification discipline. Registered
fable-side falsifier: a prelaunch seeded-defect audit showing that
material long-horizon failure modes remain oracle-equivalent
(invisible to the oracles) often enough that the registered claim is
not mechanically identifiable.

### Registered falsifiers (accepted at R0)

- **(a)** resume smoke fails any leg → alternate promoted; engines
  effectively reset between tasks (fresh session / usage drop) → this
  operationalization is dead, redesign induction — never score a
  dishonest horizon.
- **(b)** G1-valid runs show late ≈ early ≈ single-shot with traces
  confirming zero prior-context dependence → interference null at
  this shape → staged-invariant family is the successor. G1 FAIL ⇒
  transport failure ⇒ NO matrix scoring (the body rule under (c));
  the serialization wrapping is redesigned and re-smoked — reuse
  without transport validity is dishonest.
- **(c)** the G0 correlated-ledger simulation shows undercoverage or
  unreachable terminals for any registered scorer shape → scorer
  revised BEFORE freeze; G3 fail (one engine degenerate) → re-derive
  the contrast (a late-only paired 0103 is NOT a horizon cell and
  must not be silently substituted).
- **(d)** the seeded-defect audit fires → the construct is not
  mechanically identifiable at this shape → judge-route successor
  under 0104 discipline.

### Predictions

Pre-registered at apparatus freeze (P-0110-1..n), not here. The G0
proof must show both decisive terminals reachable before any
prediction is frozen.

### Information boundary

This registration is frozen before any new run data exists. Sealed
per-task 0102/0103 outcomes stay sealed (published aggregates only).
Quiet-account launch rules, detached runs, pre-frozen scorers, and
single-writer + digest-pin delegation discipline carry (HANDOFF
operating rules).

### Sequencing

1. R1 trio reconciliation (DONE 2026-08-25 — REVISE ×2, all findings
   folded into r2) → micro-round on the r2 text → REGISTERED-FROZEN
   (sol + grok freeze tokens recorded here).
2. Apparatus (terra direct-drive lane): resume smoke, schedule
   derivation + G0 power proof, boundary-ledger collector, derived
   scorer — trio-frozen, digest-pinned, before launch.
3. Launch = USER-GATED, quiet account, outside 23:00–01:00 KST.

## R0 adjudication record (2026-08-25, fable)

- Seats: sol (`r0-sol.log`, final `R0-0110-SOL: a=AMEND b=AMEND
  c=REVISE d=ADOPT`), grok (`r0-grok.log`, final `R0-0110-GROK:
  a=AMEND b=AMEND c=AMEND d=ADOPT`); packet + logs
  `~/.local/share/nx01/iter0110-reg/`.
- **Fable flip on (a)** (single-invocation-primary → resume-primary).
  NAMED DELTA: the per-process attestation contract verified at the
  bytes (mx-driver.py:118-135 — one terminal `modelUsage` per
  process; no mid-process boundary attestation or oracle handshake)
  + the 0078 resume/compaction id-rotation honest bound + both-seat
  convergent refutation. Sol's same-process stream-json becomes the
  registered ALTERNATE — it requires a new stream-json driver (new
  apparatus) and so loses the primary slot under the round's
  decisive criterion
  (DECISION-REACHABILITY PER UNIT NEW APPARATUS); its promotion path
  is the registered resume-smoke falsifier, which grok's seat also
  accepts.
- **Adopted from sol over grok**: block-cluster bootstrap
  (score-cohort.py task-level shape verified insufficient under
  clustering), G0 power proof, δH derivation obligation, G3
  estimand-support formulation (over grok's hard early-headroom gate
  — early all-clean is still informative for worsening; headroom
  carried as registered caveat + mandatory diagnostics instead).
- **Adopted from grok over fable's draft**: crossover requirement
  named as a gate-level law (position must not alias with task),
  fail-closed G2 wording, the SATURATED-analog valid-negative
  terminal, and the "never score a dishonest horizon" clause.
- Convergent without dissent: 0102 corpus reuse + claim narrowing
  (interference-under-clutter, not obligation carryover), no judge,
  scope-of-claims sentence, pair held out.

## R1 record (2026-08-25, fable fold → r2)

- **sol REVISE** (`r1-sol.log`): S1 aggregate-vs-occupancy attestor
  blocker — the terminal `modelUsage` aggregates input-side tokens
  across requests → request-level attestor + aggregate rejection
  registered. The micro round then caught the r2 receipt comparison
  MIXING two invocations — CONVERGENT sol (`micro-sol.log`) + grok
  (`micro-grok.log`, independent recompute: worker 193,126 / peak
  43,685 / 5 unique) — rebound to ONE invocation at the bytes
  (worker session `6018fb9a…`: cumulative 193,126 vs peak 43,685);
  grok micro MINOR (residual "SAME session id" wording in the
  primary bullet vs the custody rule) also folded. S2 no
  rotation-aware lineage rule → attested resume-chain custody rule
  (replaces "stable session id" in smoke + G2). S3 unregistered
  session-correlation model in G0 → registered correlation envelope
  with worst-case-member reachability.
- **grok REVISE** (`r1-grok.log`): B1 falsifier-(b) remedy
  mispointer → direct no-matrix-scoring remedy inline. B2
  `compact_boundary` unimplementable on the JSON-envelope primary
  (stream-json-only token, collect-codex-findings.py:411) +
  stable-id demand vs compaction honest bound → inferred-compaction
  marker on the primary + custody rule (converges with sol S2). B3
  session-bootstrap vs cross-session estimand mismatch → COMPLETE
  REPLICATES as the resampling unit. M4 mx-driver citation ranges
  corrected (:145-183 workdir, :248-257 oracle); M5 0108:138; M6
  stream-json analog corrected to 0074:148 (not 0106); M7 crossover
  law promoted into G0 as a mechanical check.
- Both seats re-accepted all R0 named deltas; no settled position
  relitigated.

## FREEZE record (2026-08-25)

Double FREEZE on the r4 text: sol `FREEZE-0110-SOL: 9f3c7a1d`
(`freeze-sol.log`, zero residual findings) + grok `FREEZE-0110-GROK:
b8e4c1a3` (`freeze-grok.log`, independent byte recompute of the
attestor receipt: session `6018fb9a…` only, 5 unique usage-bearing
requests, peak 43,685, unique-request sum 193,126 — matching the
sibling `surface-close.output.json` `modelUsage` aggregate). This
registration text is FROZEN; any change requires a new registration.
Receipts: `~/.local/share/nx01/iter0110-reg/` (r0-packet, r0/r1/micro/
freeze logs ×2 each).

## AMENDMENT 1 (2026-08-25, apparatus freeze round — double seat-ADOPT)

Raised as sol freeze-round finding S2 (the T-r1 block-scoped schedule
narrowed the frozen replicate clause's "every task"); adjudicated in a
focused micro round, CONVERGENT `MICRO-0110-AMEND-SOL: ADOPT` +
`MICRO-0110-AMEND-GROK: ADOPT`
(`~/.local/share/nx01/iter0110-apparatus/micro-sol.log` / `micro-grok.log`):

> "every task" in the replicate clause is scoped to the replicate's task
> block: each sweep partitions the 32 sealed tasks into 32/k blocks; one
> COMPLETE REPLICATE = one block's forward + swapped-halves crossover
> session pair per engine. The resampling unit for the registered bootstrap
> is this block-crossover replicate. The estimand, schedule, and per-task
> d values are unchanged by this scoping.

Named synthesis criterion (sol): **REGISTERED-DEPENDENCE CLOSURE** — the
unit must be the finest one containing every dependence the registered
correlation envelope models (within-session shocks only; g0-power's
simulator draws one shock per session) plus the complete matched early/late
contrast; any coarser unit was shown empirically to lose decision
reachability without protecting a registered dependence (sol regrouped the
identical S=4 simulated values into full-corpus units: minimum coverage
0.7935/0.7820/0.7985 across ρ={0,0.25,0.5}, all below the 0.90 gate; grok:
within-sweep block-mean dependence is a finite-population partition —
zero/negative covariance, overcovers). Grok's condition folded: the change
is an EXPLICIT amendment (0105 registration-gap precedent), not a claim the
frozen sentence already licensed it. Interacting lane rule, convergent
`MICRO-0110-LANES-*: BLOCK-SERIAL-OK` ×2: the launcher preserves strict
schedule order WITHIN each block's session group (the ABBA-checked unit);
distinct blocks may run on parallel lanes; sonnet fills lanes freely —
full-schedule serial would reimpose the engine-time confound that 0107's
TIME-SYMMETRY adjudication rejected.

## Apparatus phase record (2026-08-25/26, fable-orchestrated terra lane)

Full adjudication log + every seat/terra receipt:
`~/.local/share/nx01/iter0110-apparatus/` (ADJUDICATIONS.md is the
narrative authority). Apparatus files: `benchmark/executor-quality/scripts/
{sh-driver,boundary-ledger,smoke-gate,derive-schedule,g0-power,score,
launch}-0110.py`, `tasks-0110-smoke/`, `docs/specs/iter0110/{schedule.json,
registered-params.json,scripts.sha256,README.md}`.

- **Resume smoke (registration §(a) gate)**: attempt 1 FAILED the
  registered peak-to-peak growth formula (2,238 < 4,096) while custody /
  attestation / harvest passed; diagnosis at the bytes showed carry PROVEN
  (first-of-boundary-2 45,008 ≥ last-of-boundary-1 44,788) and the formula
  measuring task-2's own footprint — NAMED DELTA, formula revised to
  first-to-first + a mechanical discriminability precondition
  (footprint ≥ 2×margin else INVALID), margin 4,096 unchanged, fixture
  enlarged. Attempt 2 GATE PASS (footprint 17,662; 61,013 ≥ 43,025+4,096;
  same-id resume; exact-ID sonnet). **PRIMARY (driver-fed resume chain)
  CONFIRMED; stream-json alternate unpromoted.**
- **Seeded-defect audit (§(d) falsifier)**: cross-task damage and
  wrong-dir work both oracle-visible; in-scope failure modes are
  mechanically identifiable → falsifier (d) does not fire.
- **Registered numbers**: k=8; **S=5 sweeps → 20 block-crossover
  replicates, 120 sessions / 960 attempts (320 per engine)** — the
  smallest S passing all four G0 criteria at EVERY envelope member
  (worst member ρ=0: P(C|S-large)=.517, P(R|S-null)=.5385, coverage
  .928, false-C 0); δH=0.15; G1 tolerances .115/.100/.110; horizon
  thresholds 48,000 abs (AMENDMENT 5; 90,000 and 64,000 each fired FAIL_FAST at the gate; fraction leg retired by AMENDMENT 2; measured window
  1,000,000 ×3 recorded) (operator window attestation required at launch); G2
  crossing strictly at a PRIOR boundary; G3 ≥47 non-tied
  pairs/engine (S=5 grid, conservative p2.5); launcher = serial A5 gate
  phase (sweep 1's first block alone; a clean matrix session below
  threshold → immediate sticky `FAIL_FAST_THRESHOLD_UNREACHED`; gate
  block complete with an unrecorded engine → `A5_SUBJECT_UNAVAILABLE`)
  then block-serial lanes; every terminal derived from the persisted
  manifest before any session start (`derive_terminal`).
- **Trio verification**: round 1 sol REVISE 11 (headline S1: G0 evaluated
  only at ρ=0.5 while ρ=0 is the reachability worst case — S=4 was NOT
  G0-passing; S2 replicate-clause narrowing → micro round → AMENDMENT 1
  double ADOPT) / grok FREEZE + 2 minors; all folded by terra T-r3 (+T-r3F
  G3 re-derivation); six launcher re-freeze rounds (sol 5+2+3+2+2
  findings, all adopted; grok converged with sol at round 3; round 5
  ruled a SUBTRACTIVE redesign → serial A5 gate phase +
  persisted-state `derive_terminal`) → double FREEZE 73654c88 →
  **fable-caught packaging defect at commit time** (both smoke-tree
  pins computed with gitignored `__pycache__/*.pyc` present — one
  inside `visible/`, which the driver copies into the engine
  workspace; plus a gitignored `*.log` fixture — missed by all seven
  seat rounds) → artifacts deleted, pins recomputed on clean trees,
  `*.log` fixture force-tracked, zero code change → **FINAL double
  FREEZE on identical bytes: sol `FREEZE-0110-APP8-SOL: a7b8eab7` +
  grok `FREEZE-0110-APP8-GROK: a7b8eab7`** (pin file
  `docs/specs/iter0110/scripts.sha256`). Superseded by AMENDMENT 2 re-freeze:
  double FREEZE on identical bytes, sol `FREEZE-0110-AMEND2-SOL: 7e67c1cd` +
  grok `FREEZE-0110-AMEND2-GROK: 7e67c1cd` (pin file sha256
  `7e67c1cdcecb368ce54201eb8214d17e502374fc4905dddd561d8b59df7b73b8`).
- **Pre-registered predictions** (before freeze): P-0110-1 G1 passes all
  engines; P-0110-2 (restated by AMENDMENT 5; the 90,000 and 64,000 forms were FALSIFIED at the gate 2026-08-26) every custody-unbroken matrix session crosses 48,000 at a boundary ≤ 4 — A5 never fires and G2 threshold-unreached exclusions = 0; P-0110-3 the pilot does NOT emit
  CONFIRMED (0102/0103 lineage).
- **Deviation disclosed**: terra T-r3 attempt 1 routed the fold through a
  nested worker that cannot initialize under the wrapper sandbox → honest
  BLOCKED, no apparatus bytes changed, relaunched with direct
  implementation.
- **Launch = USER-GATED** (quiet account, outside 23:00–01:00 KST; other
  Claude sessions idle). Recipe: `launch-0110.py --sweep N --lanes 3 --out
  <root> --run-id <id> --window-attestation <operator json>` per sweep
  (5 sweeps, each 24 sessions / 192 attempts, independently stageable),
  then `score-0110.py --results-root <root> --schedule … --params …`.

## AMENDMENT 2 (2026-08-26, launch preflight — sol+grok micro round, fable adjudication)

The registered `context_window_denominator_tokens = 200,000` was false at the bytes: all four smoke receipts at `~/.local/share/nx01/iter0110-apparatus/smoke*/claude-sonnet-5.smoke.r1/t*/cli.stdout`, fresh `~/.local/share/nx01/iter0110/launch/ctxprobe/probe-*.json` probes with and without `CLAUDE_CODE_MAX_CONTEXT_TOKENS=200000`, and the pin's model table report `context:{window:1e6}` for all three registered engines.
With the truthful 1,000,000 denominator, `max(90,000, 0.45×D)` would be 450,000 and is unreachable at k=8 (registered LATE-1 projection: 92,177); the fraction leg was tautological (`0.45×200,000 = 90,000`) and never entered the absolute derivation `43,025 + 4×12,288`.
The trio-convergent criterion is TRUTHFUL-DENOMINATOR CLAIM PRESERVATION: launch only under a denominator true at the bytes, preserving the claim and every gate with the smallest delta.
Rejected options: A launches to a pre-derivable FAIL_FAST; C reverse-engineers 0.09; D forces 200k despite inert env behavior on first-party IDs, driver env scrubbing, and a treatment-changing compaction change.
Fable registered B′ as a FOLLOW-UP (not a launch gate): after retirement the denominator binds no gate, so a per-request `contextWindow` guard is recurrence detection; operator attestation `source` cites the receipts, satisfying MEASURED-GATE PROVENANCE.
Byte list: record the retirement and measured windows in this registration, params, and README; update launcher self-test literals, scorer params pin, and exactly three inventory digests. Fable fills the re-freeze token and writes the operator attestation.

## Launch record (2026-08-26 session 11) — serial A5 gate fired `FAIL_FAST_THRESHOLD_UNREACHED`; AMENDMENT 3 USER-GATED

Fired 17:53 KST on the user's go-ahead (`launch-detached-0110.py --sweep 1 --run-id s1-20260826T085326Z`, pin `7e67c1cd…`, attestation 1,000,000 ×3; account quiet: no headless workers for 3 h, peer sessions idle). Gate session `claude-opus-5.s01-b01-claude-opus-5-fwd.r1` completed CLEAN in ~14.5 min (8/8 rows `infra_invalid:false`, custody unbroken, no compaction) with boundary peaks 43,173 / 55,682 / 65,514 / **77,972** / 95,015 / 109,162 / 122,062 / 135,394 (first request 31,527). The registered 90,000 was crossed at boundary 5 — one boundary after the prior-boundary predicate (`launch-0110.py:264-296`) — so `a5.claude-opus-5.a5_crossed=false` → sticky `FAIL_FAST_THRESHOLD_UNREACHED`, one session spent, receipt `~/.local/share/nx01/iter0110/matrix/s1-20260826T085326Z/launch-abort-0110.json`. **P-0110-2 (riskiest, "A5 never fires") is FALSIFIED at the registered gate before any matrix session.** Per-task outcomes of the gate session were NOT opened by any seat (sealed).

**Root cause (trio-verified: grok CONFIRM, sol REVISE→two-factor adopted; receipts `~/.local/share/nx01/iter0110/launch/{packet-gate-failfast.md,.pins.txt,gate-sol.log,gate-grok.log}`)** — the margin (92,177 − 90,000 = 2,177) could not survive either of two independent derivation errors:
1. **Engine-dependent baseline.** The 43,025 first-request baseline came from the SONNET smoke (`iter0110-apparatus/ADJUDICATIONS.md:82-85`); pinned-CLI system+tool overhead measured on a 2-token prompt is sonnet-5 41,203 / opus-5 29,993 / opus-4-8 29,022 (`launch/ctxprobe/probe-*.json`, `cacheCreationInputTokens`) — Δ 11,210, 5× the margin. The opus-5 gate session opened at 31,527 ≈ 29,993 + prompt. These receipts existed from 09:00 KST and were read by all three seats in the AMENDMENT 2 round; nobody (fable included) connected them to the baseline.
2. **Footprint overestimate.** Measured four-task accumulation 77,972 − 31,527 = 46,445 (mean 11,611/task; range 9,832–12,509 over positions 2–4) vs registered 4 × 12,288 = 49,152 — a 2,707 deficit that alone exhausts the margin (sonnet-transplant projection 43,025 + 46,445 = 89,470 < 90,000; grok's strongest counter, sol's second cause). Fable's packet claim "footprint held" is withdrawn (named delta: ledger mean 11,611 < 12,288).
Docs precision (grok D5): the derivation projected the LATE-1 *first request*; the launcher scores the boundary-4 *peak* (Δ 1,074 here, immaterial). Provenance (sol D5): ctxprobe receipts carry no argv/executable digest/env — the pinned-CLI claim rests on `window-attestation.json` prose.

**Successor — AMENDMENT 3 (user-gated; relaunch needs a fresh run root + run id, ~11 h quiet account).** Trio ranking under SUCCESSOR MINIMALITY: **A first ×2** — re-derive the absolute threshold from per-engine measured geometry, everything else unchanged (k=8, schedule, G0, S=5, G2 prior-boundary attestation; byte list = AMENDMENT 2's shape: params, this registration, README, launcher self-test literals, scorer PARAMS pin, three inventory digests). Registered falsifier for A: OUTCOME-RETUNING — any consultation of per-task outcomes while deriving T invalidates it. B (keep 90k, LATE = 6–8) and C (keep 90k, k=16) re-derive G0/S/schedule/position classes; D (filler preamble) contradicts §(a). Fable's candidate derivation for A, to be trio-frozen at registration: T = min-engine baseline (opus-4-8 29,022 + ~1.5k prompt) + 4 × min observed per-task footprint (9,832) − 4,096 margin ≈ 65,800 → **64,000** (rounded DOWN); 72,000 is unsafe under task-mix variance (four ~9.8k tasks ⇒ boundary-4 ≈ 70.9k) and G2 excludes every session below T, not only the gate session. The claim's substance is carried by the recorded ledgers (LATE positions measured at 78k→135k); T is the floor attestation. AMENDMENT 3 must also (i) say "boundary-4 peak" and (ii) attest probe provenance or derive the baseline from driver-attested ledgers only.

Operator contract corrected at the bytes: sweeps 2–5 are fired into the SAME `--out`/`--run-id` as sweep 1 (`load_manifest` run-id equality; `a5-gate-requires-sweep-one`; scorer reads one manifest for all 120 sessions) — HANDOFF "sweeps 2–5 likewise" was under-specified. Deviation disclosed: the first grok verification invocation was misprompted as the SOL seat (zsh `${var/pat/rep}` glob-group parsing), killed at 19 s, relaunched with the GROK prompt (`gate-grok.misprompted.log` kept).

## AMENDMENT 3 (2026-08-26, after the A5 gate FAIL_FAST — sol AMEND + grok ADOPT, fable adjudication; user ruled option A)

Cause: § Launch record (two-factor: sonnet-smoke baseline applied to opus subjects + footprint overestimate, against a 2,177 margin).
Rule (context geometry only): T = floor₁₀₀₀((opus-5 gate first request 31,527 − opus-4-8 overhead delta 971) + 4 × min first-to-first footprint 9,724 − boundary-4 tail 1,074 − margin 4,096) = floor₁₀₀₀(64,282) = **64,000**; "first request" = the boundary's first `usage_entries` value (the ledger's `.requests` list is sorted by request id, `boundary-ledger-0110.py:180-183`). The worst matrix engine with four minimum-footprint tasks projects a boundary-4 PEAK of 68,378 ≥ 64,000. The gate (`launch-0110.py:264-296`) and G2 (`score-0110.py:388-396`) test the boundary-4 PEAK at any prior boundary; EARLY/LATE remain position classes (`sh-driver-0110.py:139-144`).
Rejected 72,000 (cleaner p4-first 66,390 < T < p5-first 79,046 separation): cosmetic — no registered claim conditions EARLY on context — and unsafe under task-mix variance (8/32 footprints known) → decisive criterion G2 EXCLUSION SAFETY (trio AGREE ×2).
Reproducibility receipts (sol A4): superseded by AMENDMENT 4 — the exact-reproduction rule was falsified at first use (see below).
Falsifiers: OUTCOME-RETUNING (no per-task outcome field of the gate session was opened by fable or either seat; any evidence otherwise voids this amendment); P-0110-2 restated above — a second FAIL_FAST or any G2 threshold-unreached exclusion falsifies the re-derivation.
Byte list applied (terra T-r11): registered-params.json (threshold, descriptors, derivation), scorer PARAMS pin, two inventory digests, README, this registration. Launcher, driver, ledger collector, schedule, window attestation values untouched (attestation prose updated by the operator). Relaunch: fresh run root + run id, quiet account, outside 23:00–01:00 KST, after the pyx-memory-v1 X31 all-clear; sweeps 2–5 same `--out`/`--run-id`.
Re-freeze on the final bytes (2026-08-26 20:0x KST, both seats F1 exact byte list / F2 confirmed / F3 NONE): `FREEZE-0110-AMEND3-SOL: bc85bde2` · `FREEZE-0110-AMEND3-GROK: bc85bde2` (pin file sha256 `bc85bde2c19774ecdc0d3d4a69708e41a34a0d4481ba2d325da273d4703cfa99`; receipts `~/.local/share/nx01/iter0110/launch/refreeze-amend3-{sol,grok}.log`).

## AMENDMENT 4 (2026-08-26 20:27 KST — reproducibility rule falsified at first use; sol AMEND + grok AMEND folded, fable adjudication)

Facts: after the X31 all-clear, fable ran the AMENDMENT 3 receipts in the driver's exact shape (`sh-driver-0110.py:316-347`, `scrubbed_env()`, exe sha256 `013a1cf1…`): opus-5 cacheCreation 34,486 · opus-4-8 33,513 (Δ 973) versus the 09:08 KST receipt values 29,993 / 29,022 → +4,493 / +4,491 (`launch/ctxprobe/repro-*.json` + `.meta.json`). Control with cwd `/private/tmp/nx0110-repro-cwdtest/ws`: 15,864 + 17,589 cacheRead = 33,453 (cwd is not the cause). The 09:08 receipts carry no argv/env/executable metadata, so "identical inputs" is NOT byte-attested; the 17:53 gate first request 31,527 (= 29,993 + 1,534 workspace/cwd context + prompt; `prompt.txt` ≈ 70 tokens) corroborates intervening growth but used a different prompt/cwd. Cause not pinned: `~/.claude/plugins/{installed_plugins,known_marketplaces}.json` + `plugins/cache` rewritten 19:28 KST (installed set unchanged), `~/.claude/sessions/*.json` rewritten; settings/CLAUDE.md/skills unchanged. The pinned CLI's system prompt is a function of HOME state the driver does not isolate.
Named delta: the AMENDMENT 3 rule assumed the bare prefix is a fixed function of (exe, model, argv, env) — falsified. Exact equality cannot separate a baseline error from benign drift, and the drift direction is safety-positive (T subtracts the baseline).
A4-1 T unchanged 64,000 (ADOPT ×2): re-deriving from the 20:27 inputs gives floor₁₀₀₀(68,773) = 68,000; the lower floor from the smaller attested prefix stays under G2 EXCLUSION SAFETY (gate boundary-3 65,514 / boundary-4 77,972 already cross).
A4-2 Launch rule (ADOPT ×2, sol shape): immediately before firing the fresh run root, one fixed `Reply OK` probe per matrix engine with the pinned executable, driver flags, `scrubbed_env()`, cwd pattern `/private/tmp/nx0110-<12hex>/ws`; record argv, cwd, env keys + TERM, executable sha256, JSON. prefix_e = cacheCreation + cacheRead. **Launch iff opus-5 prefix ≥ 29,993 AND opus-4-8 prefix ≥ 29,022**; either smaller value BLOCKS → new amendment from the attested numbers, never silent substitution; no tolerance. Today's 34,486 / 33,513 PASS.
A4-3 Drift receipts (recording only): at launch and after the last sweep, content-hash manifests of `~/.claude/plugins/{installed_plugins.json,known_marketplaces.json,cache/**}`, `~/.claude/sessions/*.json`, `~/.claude/{settings.json,CLAUDE.md,skills/**}` and the pinned executable; all diffs disclosed in the scored record. Registered FOLLOW-UP (not a gate): isolate the driver's HOME/system-prompt inputs (0068 isolation-v2 shape) before any successor cell — within-session ABBA makes prefix drift a nuisance, not a bias, for the 0110 estimand.
A4-4 P-0110-2 unchanged; falsifier: any matrix-engine gate session with boundary-4 peak < 64,000, or any G2 threshold-unreached exclusion.
Byte list applied (terra T-r12): registered-params.json (source clause, `amendment4_attestation`, derivation), scorer PARAMS pin, two inventory digests, README, this registration; HANDOFF.md by fable.
Re-freeze on the final bytes (2026-08-26 21:5x KST, both seats F1 exact byte list / F2 confirmed; sol F3 = expected HANDOFF change in the tree, grok F3 NONE): `FREEZE-0110-AMEND4-SOL: 025149c6` · `FREEZE-0110-AMEND4-GROK: 025149c6` (pin file sha256 `025149c68598d12c376b30d0cb5514e880df0509b3b959904be5829980ea1e27`; receipts `~/.local/share/nx01/iter0110/launch/refreeze-amend4-{sol,grok}.log`).

## AMENDMENT 5 (2026-08-27 — A4-4 falsifier fired: second gate FAIL_FAST; sol AMEND + grok AMEND folded, fable adjudication; user ruled the recommendation)

Facts: m2 `m2-20260826T140616Z` (fresh root, pin 025149c6, prefix attestation PASS 34,425/33,424, fired 23:06 KST on user override): opus-5 gate session A5 PASS (peaks 42,973/57,803/67,618/79,440 — crossed 64,000 at boundary 3); opus-4-8 gate session CLEAN (custody unbroken, 8/8 rows valid) but boundary-4 peak 57,871 < 64,000 (crossed at boundary 5, 67,084) → sticky FAIL_FAST, 2 sessions spent. Same b01 tasks: opus-4-8 footprints 9,849/6,761/5,767/5,545 vs opus-5 12,422/12,717/9,724/12,656 — **per-task accumulated-context footprints are ENGINE-dependent (~59%)**; AMENDMENT 3's minimum came from the opus-5 session only. grok's freeze-round warning (8/32 footprints known) is the confirmed mechanism; A4-4 licensed this amendment.
Rule: T = floor₁₀₀₀(opus-4-8 gate first request 30,525 + 4 × min footprint 5,545 − boundary-4 tail 576 − margin 4,096) = **48,000**. Checks: opus-4-8 crosses at boundary 3 (52,298), m2 opus-5 at boundary 2 (57,803), sonnet prefix 41,203 trivially. AMENDMENT 4 prefix-attestation baselines 29,993/29,022 unchanged.
Exposure (recorded, not gated; sol wording): a non-gate session with boundary-4 peak < 48,000 excludes position 5 AND every later LATE cell until a prior boundary crosses (G2 `threshold-unreached`, G3 erosion), never an abort; an observed LATE-position footprint of 5,292 (< 5,545) marks the exposure class. **A THIRD gate FAIL_FAST falsifies the fixed-absolute-threshold design itself — the successor redesigns the gate semantics (growth-based or per-engine), it does not re-derive the constant.**
Claim wording (sol): 48,000 is a total-effective-context floor; the prefix is HOME-state-dependent, so no fixed ≥18k real-work decomposition is guaranteed. The scored record reports, from the pinned boundary ledgers, the per-engine distribution of each LATE cell's qualifying prior-boundary peak (descriptive; frozen decision inputs unchanged — fable split ruling FROZEN-DECISION-SURFACE MINIMALITY over sol's in-scorer implementation).
P-0110-2 restated: every custody-unbroken matrix session crosses 48,000 at a boundary ≤ 4; A5 never fires; G2 threshold-unreached exclusions = 0.
Byte list applied (terra T-r13): registered-params.json (threshold, amendment5_inputs, A4 supersede note, derivation), scorer PARAMS pin, two inventory digests, README, this registration; HANDOFF by fable.
Re-freeze on the final bytes (2026-08-27 00:5x KST, both seats F1 exact byte list / F2 confirmed / F3 NONE): `FREEZE-0110-AMEND5-SOL: 981c4c83` · `FREEZE-0110-AMEND5-GROK: 981c4c83` (pin file sha256 `981c4c834ca907bce2a7347b1980c7cf798d5c8a32092635904b9726449791f3`; receipts `~/.local/share/nx01/iter0110/launch/refreeze-amend5-{sol,grok}.log`).
