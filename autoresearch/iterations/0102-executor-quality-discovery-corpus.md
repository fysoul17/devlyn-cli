---
id: "0102-executor-quality-discovery-corpus"
title: "Executor-quality discrimination cell, take 3 — non-local unstated-contract discovery corpus N=32, opus-5 vs fable-5 (iter-0101 CALIBRATION_MISS successor)"
kind: instrument
status: DRAFT — pre-R0; 3-seat design round (fable orchestrator + codex sol R0 + grok R1) required before DESIGN-FROZEN
complexity: high
depends_on: ["0100-main-ai-executor-quality", "0101-executor-quality-hard-corpus"]
---

# iter-0102 — executor-quality discovery corpus (non-local unstated contract)

## Why this iter exists (pre-flight 0)

iter-0101 CLOSED at TERMINAL=CALIBRATION_MISS (2026-08-12, launch
`cal1-20260811T150824Z`): the sonnet calibrator solved the sealed
N=32 two-axis compound-invariant corpus at mean fail **1/40**
(interior 5/32 vs bar ≥22). Two structural causes, both evidenced:

1. **The invariant was stated.** The 0101 task-shape law REQUIRED the
   visible contract excerpt to state both axes and their composition,
   and the goal named the change site. The task was therefore
   "implement a stated contract", not "discover an unstated one" —
   and implementation of stated contracts on small fixtures is
   saturated for every current engine (0100 SATURATED, 0101 q_cal=0
   on 27/32 tasks).
2. **Composition did not create difficulty.** The `interaction`
   manifestation — the designed hard part — failed exactly ONCE in 64
   runs (EQ2-AF1 r2). The only repeatable failure signal was
   state-restoration semantics: both RI-pair tasks failed BOTH reps
   (EQ2-UA5 axis1-b; EQ2-AF4 axis1-a), and 3 of 5 signal tasks had a
   rollback axis. BD class (dependent-component law, the most
   discovery-like 0101 class) still scored 0/8 — because the
   dependent contract was stated in the excerpt.

The live signal (user-observed opus-5 defects on real long-horizon
multi-invariant work) remains UNIDENTIFIED. The 0101 close-out
pre-named this successor: a REVISED registration whose difficulty
mechanism is qualitatively beyond compound invariants on small
stated-contract fixtures.

**Scope of claims**: this cell tests ONE difficulty mechanism —
non-local contract discovery under repo-scale-lite fixtures — under
oracle-closed scoring. Long-horizon session context, pair-loop
framing, and true repo scale (>100 files) remain OUTSIDE this shape.
A positive result confirms a discovery-load quality gap; a null
bounds only this shape. H2 deference stays demoted.

## Decisive criterion: ORACLE-IDENTIFIED SEPARATION AFTER AN EASY-REGIME SCREEN

Unchanged from 0101 (all 0100 oracle laws carry: mechanical oracle
only; ground truth independent of compared models; SATURATED remains
a valid negative). The sonnet calibration gate remains the sole
difficulty measurement and proved its value by construction in 0101
(it rejected before the 128-run spend that 0100 paid).

## Design

### Difficulty mechanism (the registered treatment)

Every task is a **symptom-level ticket against a mid-scale fixture
whose binding contract is unstated, non-local, and stateful**:

- **Unstated**: neither `task.json.goal` nor ANY file in the
  edit-site module states the contract. The goal reads like a real
  ticket: observed behavior, desired behavior, nothing more.
- **Non-local**: the contract is derivable ONLY by reading ≥2
  distant artifacts (a consuming module and a test or executable
  doc), each at directory distance ≥2 from the edit site.
- **Stateful restore** (the one 0101 ingredient with empirical
  signal): every contract involves restore-to-pre-state or
  exactly-once semantics across a failure path — the class of
  semantics both RI tasks failed on both reps.

The quality claim under test: discovering non-local contracts before
editing is the executor-quality behavior that separates engines,
where implementing stated contracts does not (0100+0101 evidence).

### Corpus — N = 32, 8 per class, IDs `EQ3-{UA,MI,AF,BD}{1..8}`

N=32 carried under the 0101 DECISION REACHABILITY adjudication
(planning sim: N=32 ≈ 83%/80% for confirming TRUE Δ=0.30 / refuting
TRUE Δ=0; N=12 was INCONCLUSIVE-modal). 2 reps × 32 tasks × 2
engines = 128 scored runs; δ_defect = 0.15; SATURATED = both engines
≥63/64 all-clean.

Class semantics carry from 0100/0101 (UA unsupported_assumption, MI
missed_repo_invariant, AF absent_failure_mode, BD broken_dependency)
and now classify WHICH discovery failure the symptom patch embodies:

- **UA**: the plausible local fix assumes a property the distant
  consumer contradicts.
- **MI**: the local fix misses an invariant enforced only by a
  distant test/doc artifact.
- **AF**: the local fix handles the happy path; the distant contract
  requires a failure-path behavior (restore/exactly-once) it lacks.
- **BD**: the local fix changes the edited component's outputs in a
  way that breaks the distant dependent component's contract.

### Task shape (NEW validator contract)

- **Visible fixture: 24-60 regular files across ≥4 top-level
  modules/packages** (Python 3 stdlib, odd index; Node ≥20 no-deps,
  even index). The edit-site module ≤30% of total visible bytes.
- `task.json` gains two REQUIRED fields: `edit_site_dir` (relative
  dir the ticket points at) and `contract_artifacts` (≥2 relative
  file paths carrying the contract). Frozen mechanical laws:
  (a) every `contract_artifacts` path is at directory distance ≥2
  from `edit_site_dir` (distance = edges in the directory tree walk);
  (b) a per-task registered `contract_tokens` set (≥3 tokens, each a
  distinctive contract word) appears in EVERY contract artifact and
  in ZERO of: `task.json.goal`, any file under `edit_site_dir`;
  (c) goal text contains no path under `contract_artifacts`.
- **Five manifestations, roles `local-a`, `local-b`, `remote-a`,
  `remote-b`, `restore`**, ONE contract sentence byte-copied into
  every manifestation (same-binding law carried). `local-*` check the
  ticket's asked behavior at the edit site; `remote-*` check the two
  distant consumers; `restore` checks the stateful
  restore/exactly-once path.
- **Patch vectors (frozen)**: `gold.patch` passes 5/5.
  `symptom.patch` = the best plausible LOCAL fix: passes `local-a` +
  `local-b`, fails `remote-a` + `remote-b` + `restore` exactly
  (f=3/5 — the upper band edge; a calibrator that lands
  symptom-equivalent scores inside the band). `noop.patch` fails
  both `local-*` at minimum.
- **Validator**: NEW frozen `validate-discovery-task.py`, standalone
  (does NOT invoke `validate-task.py`, whose 15-file cap and
  stated-excerpt laws are incompatible with this shape). It carries
  forward from the 0101 wrapper: same-binding law, leakage-token
  scanning, oracle workdir-mutation guard (oracle must not mutate the
  workdir; `__pycache__` class), exact patch pass-vectors,
  five-role topology, per-task registered laws vs the authoring
  table; and adds: file-count 24-60, ≥4 modules, edit-site byte
  share ≤30%, distance law, contract-token presence/absence law,
  goal-path law. Fresh authorship; behavioral-tuple distinctness
  binds vs 0100 (12) + 0101 (32) + the discarded 0102 prototypes.

### Authoring table (frozen at DESIGN-FREEZE; fixture internals IMPLEMENT-creative)

Language: odd index Python, even Node. Distinctness tuple =
(edit-site boundary, contract surface, restore semantics); all 32
distinct after entity renaming and vs 0100/0101/prototypes.

| id | domain | edit-site component | distant contract surfaces |
|---|---|---|---|
| EQ3-UA1 | library lending | loan desk intake | overdue escalator + hold-expiry test |
| EQ3-UA2 | hotel housekeeping | room-state updater | night-audit reconciler + linen ledger test |
| EQ3-UA3 | freight customs | declaration parser | duty assessor + bonded-warehouse release test |
| EQ3-UA4 | payroll ledger | timesheet importer | pay-run splitter + retro-adjustment test |
| EQ3-UA5 | clinical enrollment | consent recorder | cohort randomizer + withdrawal-restore test |
| EQ3-UA6 | telecom number porting | port-in intake | carrier notifier + rollback-window test |
| EQ3-UA7 | insurance claim triage | severity tagger | reserve calculator + reopen-restore test |
| EQ3-UA8 | container yard | stack planner | crane sequencer + re-stack journal test |
| EQ3-MI1 | court docket | filing clerk | hearing scheduler + continuance-restore test |
| EQ3-MI2 | food delivery dispatch | courier assigner | batch optimizer + refused-order restore test |
| EQ3-MI3 | water utility metering | reading ingester | billing tierer + misread-correction test |
| EQ3-MI4 | school bus routing | stop editor | route balancer + snow-day restore test |
| EQ3-MI5 | pharmacy refill | refill intake | interaction checker + partial-fill restore test |
| EQ3-MI6 | election supplies | precinct allocator | shortfall redistributor + recount-hold test |
| EQ3-MI7 | ski lift passes | pass issuer | gate scanner ledger + weather-refund test |
| EQ3-MI8 | harbor pilot scheduling | assignment desk | tide-window planner + abort-return test |
| EQ3-AF1 | blood bank stock | donation intake | crossmatch reserver + expiry-release test |
| EQ3-AF2 | vehicle fleet fueling | fuel-log writer | consumption auditor + misfuel-reversal test |
| EQ3-AF3 | museum artifact loan | loan-out desk | conservation gate + recall-restore test |
| EQ3-AF4 | orchard harvest | picking recorder | grader ledger + rejected-lot restore test |
| EQ3-AF5 | apartment maintenance | work-order intake | contractor dispatcher + no-access reschedule test |
| EQ3-AF6 | bakery production | batch planner | oven scheduler + failed-proof restore test |
| EQ3-AF7 | animal shelter | adoption intake | foster network sync + returned-animal test |
| EQ3-AF8 | greenhouse climate | setpoint editor | zone interlock + sensor-fault fallback test |
| EQ3-BD1 | ferry manifest | vehicle check-in | deck load balancer + bumped-vehicle restore test |
| EQ3-BD2 | conference review | assignment desk | conflict detector + withdrawn-paper restore test |
| EQ3-BD3 | gym class capacity | booking desk | instructor payroll feed + cancellation-credit test |
| EQ3-BD4 | recycling pickup | route editor | depot intake forecaster + missed-pickup makeup test |
| EQ3-BD5 | theater props | checkout desk | scene-change scheduler + damaged-prop restore test |
| EQ3-BD6 | festival vendor permits | permit issuer | pitch-map allocator + revocation-restore test |
| EQ3-BD7 | mine safety inspection | finding recorder | closure escalator + reinspection-clear test |
| EQ3-BD8 | seed inventory | lot receiver | germination sampler + failed-lot quarantine test |

### PRE-CORPUS MECHANISM PILOT (new; closes the 0101 blind-spend risk)

0101 spent 8 resolve batches authoring a corpus that the calibrator
then rejected. Before corpus batch-01 starts, this registration
authorizes ONE bounded mechanism pilot:

- **4 prototype tasks** (one per class, same shape laws, domains NOT
  in the authoring table), authored via one `/devlyn:resolve` run,
  then run **once each, 2 reps, sonnet, frozen apparatus lineage**
  (8 attempts). Receipts sealed under
  `~/.local/share/nx01/iter0102/pilot/`.
- **Pre-registered decision rule**: prototype mean fail ≥ 1/10 →
  proceed to corpus authoring; < 1/10 → MECHANISM_REJECTED terminal,
  return to design (no corpus build, no second pilot under this
  registration).
- **Guards**: prototypes are DISCARDED — never corpus members; their
  domains and behavioral tuples are banned from the corpus;
  prototype receipts are sealed BEFORE corpus batch-01; the formal
  calibration gate is untouched and remains the ONLY difficulty
  measurement for the real corpus. The 0101 difficulty-oracle
  prohibition carries verbatim for the corpus window (batch-01 start
  → candidate seal): no sonnet/opus/fable invocation on any EQ3
  corpus workdir or partial fixture. The pilot happens strictly
  before that window on disjoint fixtures.

### Difficulty calibration gate (carried verbatim from 0101)

Calibrator `claude-sonnet-5`, 2 reps × 32, frozen apparatus, after
candidate seal. Band: exact-Fraction mean AND frozen even-n median ∈
[1/5, 3/5], ≥22/32 interior, ≤2 total-fail. ONE valid evaluation; up
to three launches only to replace infrastructure-invalid launches on
byte-identical digests; valid miss → CALIBRATION_MISS terminal, no
retuning. `score-calibration.py` re-pinned with `EQ3-*` task IDs
(new frozen commit; self-test scenarios re-derived, incl. the
extra-field/UNSCORED classes).

### Arms, apparatus, metrics (inherited; enumerated changes only)

Identical to the 0101-frozen apparatus lineage (pinned CLI 013a1cf1…,
run-bounded db9ed383…, stdin DEVNULL, prompt_sha256 + modelUsage
exact-ID attestation, scrubbed env, opaque workdirs, JSON candidate
manifest + tree-digest double binding, no driver_sha256 row field,
BOUND_SEC=1800, detached launches never near 12am KST). The ONLY
allowed driver/launcher changes: `TASKS_ROOT =
benchmark/executor-quality/tasks-0102`; task set = the exact EQ3
32-ID set; manifest/digest constants → the 0102 candidate seal.
Calibration launcher = 0102 lineage of `cal-launcher.py`; matrix
launcher = 0102 lineage of the (never-frozen) 0101
`mx-launcher.py` draft (128 runs, 2-4 lanes, ABBA). Scorer:
`score-cohort.py` re-pinned to `EQ3-*` (estimator, seed 20260809,
strict 3/20 bounds, terminal precedence, δ=0.15 all unchanged).
Both-seat pre-arm audit (sol + grok, liveness, synthetic-ledger
proofs incl. the four 0100 repro classes) before the matrix.
The two 0101-frozen operational rules carry: both-seat
infra-authenticity adjudication before burning a replacement launch;
MISS + success-subtype/empty-attestation rows → CONTESTED escalation
before recording. Lexical failure-taxonomy modernization remains a
REGISTERED follow-up, NOT applied here (byte-preserved lineage).

### Pre-registered prediction (single)

- **P-0102-1**: opus-5 manifestation-fail rate exceeds fable-5's by
  ≥ δ = 0.15 on the discovery corpus. Refuted with terminal
  H1_MATERIAL_GAP_REFUTED → a live-signal-sized discovery-load gap
  is excluded at this shape; remaining candidates (true repo scale,
  session-horizon effects) are NEW registrations.

## Freeze protocol

1. 3-seat design round: sol R0 → adopt → grok R1 → adopt →
   DESIGN-FROZEN (this file amended in place; liveness markers).
2. Mechanism pilot (4 prototypes → 8 sonnet runs → decision rule).
   MECHANISM_REJECTED → stop; else seal pilot receipts.
3. Corpus lands via **8 `/devlyn:resolve --pair-verify` runs**
   (executor pin codex), batch i = `EQ3-UAi → MIi → AFi → BDi`, one
   task per exec phase, `validate-discovery-task.py` green per phase
   gate; batch-01 additionally lands the new validator + both scorer
   re-pins (only batch whose surface includes scripts). Dispatch
   prompts pre-inject the 0101 failure classes: same-pair structural
   copies, oracle workdir mutation, tie-break gaps, strawman symptom
   branches, patch lone-space hygiene (cumulative `git diff
   --check`).
4. Candidate seal (canonical JSON manifest + tree digest).
5. Calibration apparatus freeze (0101 lineage; enumerated changes) →
   64-run sonnet calibration → ONE band evaluation.
6. Band PASS → candidate promoted unchanged → matrix launcher freeze
   → both-seat pre-arm audit → 128-run matrix detached (fresh cohort
   ID). Band MISS → CALIBRATION_MISS, stop.

## Budget/wall (informational)

Pilot: 1 resolve run + 8 sonnet runs (~15 min arm wall). Corpus: 8
resolve runs, heavier fixtures than 0101 (24-60 files) — expect
multi-session. Calibration: 64 sonnet runs (0101 measured 25-151s/run
on small fixtures; mid-scale may run 2-10 min → plan 2-6 h at 2
lanes). Matrix: 128 runs × 3-30 min at 2-4 lanes, multiple detached
overnight windows, never near 12am KST.

## Receipts layout

```
~/.local/share/nx01/iter0102/
  registration/   R0/R1 packets, liveness logs
  pilot/          prototype specs, 8-run ledger, decision receipt
  build/batch-01..08/
  freeze/         candidate manifest, tree digest, script pins
  calibration/    apparatus, attempt-N receipts, band verdict
  audit/          pre-arm packets
  matrix/<cohort-id>/
```
