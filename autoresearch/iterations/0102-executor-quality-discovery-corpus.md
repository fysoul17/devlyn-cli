---
id: "0102-executor-quality-discovery-corpus"
title: "Executor-quality discrimination cell, take 3 — non-local unstated-contract discovery corpus N=32, opus-5 vs fable-5 (iter-0101 CALIBRATION_MISS successor)"
kind: instrument
status: DRAFT+R0-ADOPTED — sol R0 REVISE ×8 REQUIRED + 2 RECOMMENDED all adopted in-text (R0-0102-LIVE-sol-c42dd8ef, 2026-08-12); grok R1 pending before DESIGN-FROZEN
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
   manifestation failed exactly ONCE in 64 runs (EQ2-AF1 r2). The
   only repeatable failure signal was state-restoration semantics:
   both RI-pair tasks failed BOTH reps (EQ2-UA5, EQ2-AF4), and 3 of
   5 signal tasks had a rollback axis. This is two tasks, not causal
   identification — state restoration is adopted as the **strongest
   registered hypothesis** for residual difficulty, not an
   identified mechanism (R0 REC-1). BD class scored 0/8 because the
   dependent contract was stated in the excerpt.

The live signal (user-observed opus-5 defects on real long-horizon
multi-invariant work) remains UNIDENTIFIED. The 0101 close-out
pre-named this successor: a REVISED registration whose difficulty
mechanism is qualitatively beyond compound invariants on small
stated-contract fixtures.

**Scope of claims**: this cell tests ONE difficulty mechanism —
non-local contract discovery under mid-scale fixtures — under
oracle-closed scoring. Long-horizon session context, pair-loop
framing, and true repo scale (>100 files) remain OUTSIDE this shape.
A positive result confirms a discovery-load quality gap; a null
bounds only this shape. H2 deference stays demoted.

**Known residual (R0 strongest counter, accepted)**: with
`Read,Grep,Glob,Bash`, 1800 s, and 24-60 files, sonnet CAN read the
whole fixture; directory distance is not cognitive distance, and no
mechanical law at this scale can prevent whole-fixture reading. The
two-fragment complementarity law below ensures single-artifact
reading is insufficient; whether whole-fixture reading still
saturates the shape is exactly what the pilot and the ONE
calibration evaluation measure. A second CALIBRATION_MISS is a
priced-in possible outcome; the pilot bounds its cost to 1 resolve
run + 8 sonnet runs instead of 8 batches.

## Decisive criterion: ORACLE-IDENTIFIED SEPARATION AFTER AN EASY-REGIME SCREEN

Unchanged from 0101 (all 0100 oracle laws carry: mechanical oracle
only; ground truth independent of compared models; SATURATED remains
a valid negative). The sonnet calibration gate remains the sole
difficulty measurement for the corpus.

## Design

### Difficulty mechanism (the registered treatment)

Every task is a **symptom-level ticket against a mid-scale fixture
whose binding contract is unstated, non-local, split across two
complementary artifacts, and stateful**:

- **Unstated**: neither `task.json.goal` nor ANY file under
  `edit_site_dir` states the contract.
- **Non-local and two-fragment complementary (R0-1)**: the contract
  exists ONLY as **exactly two ordered contract artifacts**,
  `contract_artifacts[0]` ↔ `remote-a` and `contract_artifacts[1]` ↔
  `remote-b` (one-to-one, ordered). Each artifact carries a DISTINCT
  registered contract fragment with its own registered token set.
  **Neither artifact alone states or implies the composed
  restore/exactly-once outcome**; the `restore` manifestation
  exercises the COMPOSITION of both fragments.
- **Stateful restore**: every composed contract involves
  restore-to-pre-state or exactly-once semantics across a failure
  path (the strongest registered hypothesis from the 0101 signal).

The quality claim under test: discovering and composing non-local
contract fragments before editing is the executor-quality behavior
that separates engines, where implementing stated contracts does not
(0100+0101 evidence).

### Corpus — N = 32, 8 per class, IDs `EQ3-{UA,MI,AF,BD}{1..8}`

**Power carry-over (R0-7 replacement text)**: N=32 is retained as
the minimum previously adjudicated corpus size (0101 DECISION
REACHABILITY). The 0101 planning figures (≈83%/80% at TRUE Δ=0.30 /
Δ=0) remain conditional on the 0101 paired-task SD ≤0.30 assumption;
they are NOT empirical power estimates for the discovery corpus.
2 reps × 32 tasks × 2 engines = 128 scored runs; δ_defect = 0.15;
SATURATED = both engines ≥63/64 all-clean. The frozen decision rule
does not change with SD sensitivity.

Class semantics carry from 0100/0101 and classify the LOCAL premise
the registered comparator patch embodies (per-row anchors in the
table):

- **UA**: a NAMED local assumption contradicted by a consumer.
- **MI**: a NAMED invariant absent from the edit site, enforced only
  remotely.
- **AF**: a NAMED failure-path transition the local repair omits.
- **BD**: a NAMED output/state change that violates a dependent
  component's contract.

### Task shape (frozen mechanical laws; R0-2 definitions)

- **Visible fixture: 24-60 regular files across ≥4 top-level
  modules** (Python 3 stdlib, odd index; Node ≥20 no-deps, even
  index). *Top-level module* = a non-symlink immediate child
  directory of `visible/` containing ≥1 registered regular file.
- **Edit-site byte share ≤30%** — raw bytes of all registered
  regular files under `edit_site_dir` ÷ raw bytes of ALL registered
  visible files (denominator must be nonzero). This is layout
  telemetry constraining fixture shape, NOT difficulty evidence.
- **`task.json` exact schema (R0-8)**: `id`, `class`, `goal`,
  `invariant` (the composed contract sentence — hidden-side binding
  only), `visible_files`, `edit_site_dir`, `contract_artifacts`
  (ordered array, length exactly 2), `contract_tokens_a`,
  `contract_tokens_b` (each ≥3 unique non-generic tokens; stored in
  `task.json`, checked against the frozen per-task table in the
  validator). No `contract_excerpt` field exists in this shape.
- **Distance law**: for each contract artifact, directory distance =
  edge count between `edit_site_dir` and `parent(artifact)` through
  their lowest common ancestor, after normalized safe resolution
  under `visible/`; must be ≥2.
- **Token laws**: matching is over UTF-8 text, Unicode-casefolded,
  whole lexical tokens. `contract_tokens_a` must appear in
  `contract_artifacts[0]` and `contract_tokens_b` in
  `contract_artifacts[1]`; BOTH sets must appear in ZERO of:
  `task.json.goal`, any file under `edit_site_dir`, any relative
  path or filename under `edit_site_dir`. Goal text must not
  contain any `contract_artifacts` path, and artifact paths and
  filenames are scanned for leakage alongside contents.
- **Five manifestations, roles `local-a`, `local-b`, `remote-a`,
  `remote-b`, `restore`**. The single-binding law is replaced by the
  **ordered two-binding set**: every manifestation carries BOTH
  contract bindings — for each of the two artifacts: path, SHA-256,
  and exact quote (the fragment) — byte-identical across all five
  manifestations. `remote-a` checks fragment A's consumer,
  `remote-b` fragment B's, `restore` their composition.
- **Patch vectors (frozen)**: `gold.patch` → `TTTTT`. The
  **registered local comparator patch** `symptom.patch` → exactly
  `TTFFF` (passes both `local-*`, fails `remote-a`, `remote-b`,
  `restore`), and must modify ONLY paths under `edit_site_dir`
  (mechanical locality law). Pristine (no patch) and `noop.patch`
  must each fail BOTH `local-*` roles (remaining roles recorded but
  unconstrained). f=3/5 for the comparator sits at the inclusive
  upper band edge; this does NOT imply an engine producing a
  different patch lands there — the band is measured, not assumed.

### Validator — NEW frozen `validate-discovery-task.py` (standalone; R0-4 law list)

Standalone (does NOT invoke `validate-task.py`, whose 15-file cap
and stated-excerpt laws are incompatible). It must implement ALL of:

1. Exact required fixture files: `task.json`, `hidden/oracle.py`,
   `hidden/manifests.json`, `patches/{gold,noop,symptom}.patch`.
2. Exact `task.json` schema above; nonempty strings; class enum; id
   == directory name; id→class/table registration.
3. Safe POSIX-relative paths under `visible/`; no absolute paths,
   `..`, escapes, symlinks, or non-regular files anywhere in the
   task tree.
4. Unique, exhaustive `visible_files` matching every regular visible
   file.
5. Exact ordered two-binding schema (path + lowercase SHA-256 +
   exact quote per artifact); hash match against the file bytes;
   UTF-8; nonempty quote present in the artifact.
6. Exact manifest root/entry schema; exactly five unique roles as
   registered.
7. Every manifestation matches the task invariant, class, and the
   SAME ordered two-binding set.
8. Leakage scanning of manifestation ids, hidden filename stems, and
   long assertion/comparison literals against relative visible
   paths, visible UTF-8 contents, and goal text.
9. Oracle exit 0 within a fixed timeout; exactly one JSON object;
   exact root/result fields; boolean `passed`; count, ids, and
   invariants exactly matching manifests, no duplicates.
10. Patch utility availability; fail-closed application on a
    pristine copy via `patch -p1 --forward --batch`.
11. Independent pristine cases: no-patch, noop, gold, symptom.
12. Registered pass-vectors: gold `TTTTT`, symptom `TTFFF`,
    no-patch/noop fail both `local-*`.
13. Discovery topology: file count 24-60, ≥4 modules, parity/
    language, distance ≥2 per artifact, token presence/absence laws
    (incl. path/filename scan), goal-path law, byte-share ≤30%,
    artifact↔remote-role one-to-one order, symptom-patch locality.
14. **NEW 0102 law (not inherited — R0-4 correction: no such guard
    exists in the 0101 validators)**: filesystem snapshot
    before/after EVERY oracle invocation; any created, deleted, or
    modified path (incl. `__pycache__`) fails validation.
15. Fail-closed self-tests for every law above plus one valid
    end-to-end Python task and one valid Node task.

### Authoring table (frozen at DESIGN-FREEZE; fixture internals IMPLEMENT-creative)

Language: odd index Python, even Node. Distinctness tuple =
(edit-site component, failure trigger, restore outcome) — all 32
distinct after entity renaming, and vs 0100 (12), 0101 (32), and the
4 prototypes. Column key: **local premise** is the class anchor (UA
assumption / MI missed invariant / AF absent failure transition / BD
breaking change); **fragment A** lives in `contract_artifacts[0]`
(consumer module), **fragment B** in `contract_artifacts[1]` (test
or executable doc); neither alone implies the composed outcome.

| id | domain / edit site | local premise (class anchor) | fragment A (consumer) | fragment B (test/doc) | trigger → composed restore outcome |
|---|---|---|---|---|---|
| EQ3-UA1 | library lending / loan desk intake | renewal = a fresh loan | overdue escalator treats renewals as fee-clock continuations | hold-expiry test: renewal never re-enters hold queue | renewal during pending hold → failed renewal restores due date AND hold position; fee assessed exactly once |
| EQ3-UA2 | hotel housekeeping / room-state updater | cleaned → immediately bookable | night-audit reconciler requires inspection sign-off ordering | linen ledger test: cleaning debits linen exactly once | failed inspection re-clean → room returns to dirty without second linen debit |
| EQ3-UA3 | freight customs / declaration parser | line items are independent | duty assessor aggregates per HS-code across lines | bonded-release test: release is all-or-nothing per declaration | one line fails classification → partial assessment fully unwound; resubmit assesses exactly once |
| EQ3-UA4 | payroll ledger / timesheet importer | late entries may append | pay-run splitter closes periods immutably at cutoff | retro-adjustment test: late entry = reversal+repost pair | late timesheet after close → failed import leaves closed period byte-identical |
| EQ3-UA5 | clinical enrollment / consent recorder | re-consent overwrites prior | cohort randomizer keys on first-consent version | withdrawal test: withdrawal releases randomization slot | withdrawal then re-enrol → slot released exactly once; re-enrol draws a fresh slot |
| EQ3-UA6 | telecom porting / port-in intake | resubmission replaces request | carrier notifier dedups notifications by port-request id | rollback-window test: cancel restores original binding | resubmit inside rollback window → binding restored, zero duplicate notifications |
| EQ3-UA7 | insurance triage / severity tagger | severity never decreases | reserve calculator releases reserve deltas on downgrade | reopen test: reopen restores prior reserve exactly | downgrade then reopen → reserve restored to pre-close value exactly once |
| EQ3-UA8 | container yard / stack planner | restack is a free move | crane sequencer debits a crane slot per lift | re-stack journal test: failed placement journals a compensating move | placement failure mid-restack → layout restored via journal; crane slots debited exactly once |
| EQ3-MI1 | court docket / filing clerk | amendment slots in anywhere | hearing scheduler enforces min notice from LAST amended filing | continuance test: continuance rollback restores hearing chain | amendment inside notice window → rejected amendment restores docket sequence |
| EQ3-MI2 | food dispatch / courier assigner | assignments stay editable | batch optimizer locks assignments at batch lock | refused-order test: refusal re-pools order at original priority | refusal after batch lock → order re-pooled exactly once; batch integrity kept |
| EQ3-MI3 | water metering / reading ingester | corrections overwrite readings | billing tierer requires monotonic cumulative series | misread test: correction = compensating delta entry | correction below prior reading → tiers recomputed from compensated series exactly once |
| EQ3-MI4 | school bus routing / stop editor | stop edits apply immediately | route balancer requires per-segment capacity on the ACTIVE plan | snow-day test: emergency swap restores regular plan byte-identical | stop edit during snow-day plan → edit queued; regular plan restored intact |
| EQ3-MI5 | pharmacy refill / refill intake | each fill is independent | interaction checker gates on active list INCLUDING pending fills | partial-fill test: partial fill debits authorization exactly once | second partial while first pends → failed fill releases authorization units |
| EQ3-MI6 | election supplies / precinct allocator | any precinct may donate stock | shortfall redistributor draws only from surplus precincts | recount-hold test: hold freezes precinct inventory | transfer touching held precinct → aborted transfer restores both precinct counts |
| EQ3-MI7 | ski lift passes / pass issuer | refund = simple reversal | gate scanner ledger marks passes single-use per window | weather-refund test: refund restores day-credit exactly once | refund after partial usage → prorated credit from scan ledger; pass invalidated exactly once |
| EQ3-MI8 | harbor pilots / assignment desk | pilot and berth book separately | tide-window planner co-reserves pilot+berth atomically | abort-return test: abort returns pilot AND releases berth | abort at tide-window close → both resources released; next assignment starts fresh |
| EQ3-AF1 | blood bank / donation intake | reserved units stay valid | crossmatch reserver holds units against orders | expiry-release test: expiry releases the order back to matching | unit expires while reserved → order re-queued; unit quarantined exactly once |
| EQ3-AF2 | fleet fueling / fuel-log writer | entries are append-only facts | consumption auditor flags variance vs odometer series | misfuel test: misfuel reversed by compensating record | misfuel then service → audit series stays consistent; reversal exactly once |
| EQ3-AF3 | museum loans / loan-out desk | approved loans always ship | conservation gate blocks items in treatment | recall test: recall restores exhibit slot allocation | recall during transit → loan closed, slot restored, insurance rider released once |
| EQ3-AF4 | orchard harvest / picking recorder | picked = graded eventually | grader ledger reconciles lot weights to bin weights | rejected-lot test: rejection returns bins to field inventory | rejection after partial grading → bins restored; grade entries voided exactly once |
| EQ3-AF5 | apartment maintenance / work-order intake | reschedule resets the order | contractor dispatcher books tenant-calendar access windows | no-access test: failed access preserves the SLA clock | second no-access visit → SLA clock continues; visit fee waived exactly once |
| EQ3-AF6 | bakery production / batch planner | failed batch just re-queues | oven scheduler enforces thermal changeover between families | failed-proof test: failure returns committed stock waste-adjusted | proof failure after slot lock → slot released; stock adjusted exactly once |
| EQ3-AF7 | animal shelter / adoption intake | available = adoptable | foster sync holds fostered-out animals unavailable | returned-animal test: return reinstates medical hold from history | adopting a returned animal with lapsed vaccination → hold reinstated; fee refunded once |
| EQ3-AF8 | greenhouse climate / setpoint editor | setpoints are zone-local | zone interlock forbids conflicts in shared-air zones | sensor-fault test: fault reverts zone to last-good profile | edit during active fault → last-good restored; edit journaled for exactly-once retry |
| EQ3-BD1 | ferry manifest / vehicle check-in | weight class is check-in detail | deck load balancer recomputes from check-in weight classes | bumped-vehicle test: bump preserves queue position for next sailing | overweight bump at gate close → position preserved; fare charged exactly once |
| EQ3-BD2 | conference review / reviewer assigner | load counts are internal | conflict detector consumes assigner load counts | withdrawn-paper test: withdrawal returns reviewer capacity | withdrawal after partial reviews → capacities restored; completed reviews archived once |
| EQ3-BD3 | gym classes / booking desk | cancel = seat decrement | instructor payroll feeds on locked per-head rosters | late-cancel test: inside cutoff issues credit, not refund | cancel inside cutoff → count decremented, credit exactly once, locked payroll unchanged |
| EQ3-BD4 | recycling pickup / route editor | stops are freely removable | depot intake forecaster consumes route stop material categories | missed-pickup test: missed stop auto-queues category-preserving makeup | removing a stop with pending makeup → makeup reassigned; forecast rebalanced once |
| EQ3-BD5 | theater props / checkout desk | checkout is a flat ledger | scene-change scheduler consumes checkout chains | damaged-prop test: damage swaps understudy prop, restores chain | damage mid-run → chain restored; damage logged exactly once |
| EQ3-BD6 | festival permits / permit issuer | revocation just deletes | pitch-map allocator consumes issuance for placement | revocation test: revocation refunds pro-rata exactly once | revocation after setup day → pitch released to waitlist in order |
| EQ3-BD7 | mine safety / finding recorder | findings clear independently | closure escalator consumes linked-finding severity | reinspection test: status restores only when ALL linked findings clear | partial clearance of multi-finding closure → status restored at last clearance; escalation stops once |
| EQ3-BD8 | seed inventory / lot receiver | received lots ship freely | germination sampler consumes per-class sampling quotas | failed-lot test: failure quarantines lot, releases quota | failure after partial distribution → distributed portions recalled; quota released once |

Fresh judges at VERIFY review semantic distinctness of fixtures
against 0100, 0101, and the prototypes; the validator checks
id/class/parity/bindings/topology mechanically.

### PRE-CORPUS MECHANISM PILOT (R0-3 frozen information boundary)

Purpose: bound the blind-spend risk (0101 spent 8 batches before its
screen fired) to 1 resolve run + 8 sonnet runs. This is a
pre-registered mechanism screen, NOT corpus tuning.

- **Prototype rows (frozen)** — IDs, domains, class anchors, and
  behavioral tuples pre-registered here; same shape laws as corpus
  tasks; `TASKS_ROOT_PILOT = benchmark/executor-quality/
  tasks-0102-pilot`; domains and tuples BANNED from the corpus:

| id | domain / edit site | local premise | fragment A | fragment B | trigger → composed outcome |
|---|---|---|---|---|---|
| EQ3P-UA1 | campground bookings / site assigner | site swap is free | seasonal pricing engine bills site-class deltas | cancel test: cancellation restores availability + deposit once | swap across price class then cancel → deposit and availability restored exactly once |
| EQ3P-MI1 | car rental / return intake | return closes immediately | damage biller requires photos-before-close ordering | early-return test: early return releases the reservation block | early return with pending damage review → block released once; final bill after review |
| EQ3P-AF1 | cinema concessions / combo editor | combos deplete independently | inventory decrementer maps combos to components | spoilage test: expiry voids combos, restores substitutable stock | component expiry mid-shift → combo availability recomputed; spoilage recorded once |
| EQ3P-BD1 | community garden / plot assigner | abandonment frees a plot | water-share scheduler consumes plot assignments | abandonment test: return to lottery preserves waitlist order | abandonment mid-season → water shares rebalanced; waitlist order preserved |

- **Sequencing**: the FULL corpus authoring table above is frozen
  BEFORE the pilot runs (this file at DESIGN-FROZEN). One
  `/devlyn:resolve --pair-verify` run (executor pin codex; spec
  `docs/specs/iter0102-pilot/spec.md`) authors the 4 prototypes AND
  lands `validate-discovery-task.py` + `score-pilot.py` (the only
  run whose authorized surface includes those scripts). Then 8
  sonnet attempts (4 tasks × 2 reps) on the frozen apparatus
  lineage; receipts sealed under `~/.local/share/nx01/iter0102/pilot/`.
- **Scoring (frozen; `score-pilot.py`, exact-Fraction)**: per-task
  `q_pilot` = two-rep mean of the scored estimator f; catastrophic
  or incomplete VALID attempts contribute f=1; any
  infrastructure-invalid row → launch UNSCORED, replaceable ONLY on
  byte-identical prototype+apparatus digests (max 3 launches, same
  as calibration). **Decision rule**: PROCEED iff mean(q_pilot) ≥
  1/10 AND mean(q_pilot) ≤ 3/5 AND ≥3 of 4 prototypes have
  0 < q_pilot < 1 AND no prototype has q_pilot = 1. Otherwise
  MECHANISM_REJECTED terminal — no corpus build, no second pilot,
  return to design under a new registration revision.
- **Information boundary (frozen)**: corpus authoring sees ONLY the
  mechanical PROCEED bit and the decision-receipt hash. Per-task
  pilot outcomes, transcripts, oracle results, patches, and role
  failures stay SEALED until the candidate corpus is sealed.
  Receipt schema: `{decision, mean, q_pilot per id, ledger_sha256,
  apparatus_sha256s, launched_at_utc, attempt}` — the receipt file
  itself is sealed; only its sha256 and `decision` are quoted.
- The 0101 difficulty-oracle prohibition carries verbatim for the
  corpus window (batch-01 start → candidate seal): no
  sonnet/opus/fable invocation on any EQ3 corpus workdir or partial
  fixture. The pilot happens strictly before that window on the
  disjoint prototype fixtures. One pilot, ever, under this
  registration.

### Difficulty calibration gate (carried verbatim from 0101)

Calibrator `claude-sonnet-5`, 2 reps × 32, frozen apparatus, after
candidate seal. Band: exact-Fraction mean AND frozen even-n median ∈
[1/5, 3/5], ≥22/32 interior, ≤2 total-fail. ONE valid evaluation; up
to three launches only to replace infrastructure-invalid launches on
byte-identical digests; valid miss → CALIBRATION_MISS terminal, no
retuning.

### Scorer + apparatus re-pins (R0-6 enumeration; nothing else changes)

**Scorers** (both re-pinned in corpus batch-01, the only corpus run
whose surface includes scripts): `score-calibration.py` and
`score-cohort.py` freeze `FROZEN_TASKS = {EQ3-{UA,MI,AF,BD}{1..8}}`;
every hardcoded substitution control moves `EQ2-UA1/99 →
EQ3-UA1/99`. Self-tests preserved and re-run in full: band
mean/median/interior/total-fail controls, catastrophic zero-total
f=1, infra-invalid UNSCORED, byte-determinism, unknown/substituted
task rejection, unexpected-field (`driver_sha256`) rejection, exact
3/20 boundary, duplicate run-id rejection, 63/64 SATURATED proof,
attestation and prompt-hash controls.

**Drivers/launchers** (0101-frozen lineage sources:
`~/.local/share/nx01/iter0101/calibration/apparatus/{cal-driver.py
(f7347a72…), cal-launcher.py (719ea0f1…)}` and the never-frozen 0101
`matrix/apparatus-draft/{mx-driver.py, mx-launcher.py}`). Enumerated
changes ONLY, per instrument:

- pilot driver: `TASKS_ROOT_PILOT`; task set = the exact 4 EQ3P IDs;
  `ALLOWED_ENGINES={claude-sonnet-5}`; manifest constants → the
  sealed PILOT manifest (same canonical JSON + compact-JSON
  tree-digest construction as 0101); docstring strings. Launcher: 8
  attempts (4×2), 2 lanes.
- calibration driver/launcher: `TASKS_ROOT =
  benchmark/executor-quality/tasks-0102`; exact EQ3 32-ID set;
  manifest constants → the 0102 CANDIDATE seal; docstrings. All
  else byte-preserved from f7347a72…/719ea0f1… (BOUND_SEC=1800,
  outer +60, stdin DEVNULL, prompt_sha256, exact-ID modelUsage
  attestation, failure taxonomy, scrubbed env, pinned CLI
  013a1cf1…, run-bounded db9ed383…, oracle timeout 60, no
  driver_sha256 row field, JSON-manifest + tree-digest double
  binding, opaque workdirs).
- matrix driver/launcher: same enumerated deltas on the mx drafts;
  `ALLOWED_ENGINES={claude-opus-5, claude-fable-5}`; 128 attempts,
  2-4 lanes (`--lanes` at launch discretion, recorded in the cohort
  receipt), ABBA interleave.
- launch tooling: `launch-detached.py` lineage — fail-closed digest
  gate against the per-instrument freeze file + launch-receipt.json
  binding apparatus shas, tree digest, engine, attempt ordinal
  (1..3), run id, UTC timestamp, pid.
- schedule proofs (mechanical, pre-launch): 8/64/128-cell exactness,
  lane balance, unknown/tampered/extra-file/symlink rejection,
  emitted-row field set == scorer REQUIRED∪OPTIONAL.

**Seat audits (R0-6)**: two-seat FREEZE-ARM (sol + grok, liveness,
residual attack rights) before EACH arm: pilot launch (scoped),
calibration launch, and matrix launch (the matrix audit additionally
re-runs the four 0100 repro classes as synthetic-ledger proofs
against the EQ3 scorer).

**Operational rules carried from 0101**: both-seat
infra-authenticity adjudication recorded before burning any
replacement launch; MISS + success-subtype/empty-attestation rows →
CONTESTED escalation to the user before recording. Lexical
failure-taxonomy modernization stays a REGISTERED follow-up, not
applied (byte-preserved lineage).

**Diagnostics (R0 REC-2)**: role-level (local/remote/restore)
failure detail remains available in per-attempt `oracle.json`
receipts for post-hoc reading; the scorer and ledger schema are
UNCHANGED — no new ledger fields, no second decision rule.

### Pre-registered prediction (single)

- **P-0102-1**: opus-5 manifestation-fail rate exceeds fable-5's by
  ≥ δ = 0.15 on the discovery corpus. Refuted with terminal
  H1_MATERIAL_GAP_REFUTED → a live-signal-sized discovery-load gap
  is excluded at this shape; remaining candidates (true repo scale,
  session-horizon effects) are NEW registrations.

## Freeze protocol

1. 3-seat design round: sol R0 (DONE — REVISE ×8 adopted) → grok R1
   → adopt → DESIGN-FROZEN (this file amended in place; liveness
   markers recorded in frontmatter).
2. Pilot resolve run (`docs/specs/iter0102-pilot/spec.md`): 4
   prototypes + `validate-discovery-task.py` + `score-pilot.py`
   land; pilot manifest sealed (canonical JSON, compact-JSON tree
   digest); scoped two-seat freeze audit; 8-run sonnet pilot
   detached; `score-pilot.py` decision. MECHANISM_REJECTED → stop.
   PROCEED → pilot per-task receipts sealed (only the bit + receipt
   hash exposed).
3. Corpus lands via **8 `/devlyn:resolve --pair-verify` runs**
   (executor pin codex; specs
   `docs/specs/iter0102-executor-quality-batch-01..08/spec.md`),
   batch i = `EQ3-UAi → MIi → AFi → BDi`, one task per exec phase,
   `validate-discovery-task.py` green per phase gate; batch-01
   additionally lands both scorer re-pins. Dispatch prompts
   pre-inject the 0101 failure classes: same-pair structural copies,
   oracle workdir mutation, tie-break gaps, strawman symptom
   branches, patch lone-space hygiene (cumulative `git diff
   --check`).
4. Candidate seal: canonical JSON manifest (`{file_count, git_head,
   sealed_at_utc, task_count, tasks, tree_sha256}`; tree =
   sha256(compact sort_keys JSON of `tasks`)) + script-pin file
   `freeze/scripts.sha256`.
5. Calibration apparatus freeze (enumerated deltas) → two-seat
   freeze audit → 64-run sonnet calibration detached → ONE band
   evaluation.
6. Band PASS → candidate manifest + tree digest promoted BYTE-
   IDENTICAL into the matrix apparatus constants → matrix launcher
   freeze → two-seat pre-arm audit (incl. 0100 repro classes) →
   128-run matrix detached (fresh cohort ID). Band MISS →
   CALIBRATION_MISS, stop.

## Budget/wall (informational)

Pilot: 1 resolve run + 8 sonnet runs (≲30 min arm wall). Corpus: 8
resolve runs, heavier fixtures than 0101 (24-60 files) — expect
multi-session. Calibration: 64 sonnet runs (0101 measured 25-151 s/run
on small fixtures; mid-scale may run 2-10 min → plan 2-6 h at 2
lanes). Matrix: 128 runs × 3-30 min at 2-4 lanes, multiple detached
overnight windows, never near 12am KST.

## Receipts layout

```
~/.local/share/nx01/iter0102/
  registration/   R0/R1 packets, liveness logs
  pilot/          prototype manifest+seal, apparatus, 8-run ledger,
                  decision receipt (sealed; hash quoted)
  build/batch-01..08/
  freeze/         candidate manifest, tree digest, scripts.sha256
  calibration/    apparatus, attempt-N receipts, band verdict
  audit/          per-arm freeze/pre-arm packets
  matrix/<cohort-id>/
```

## Design notes (R0 adoption record)

sol R0 (R0-0102-LIVE-sol-c42dd8ef, 2026-08-12) — REVISE; all 8
REQUIRED + 2 RECOMMENDED adopted wholesale: (1) two-fragment
complementarity with ordered artifact↔role mapping and two-binding
sets; (2) exact definitions for distance/module/byte-share/token
matching, no-patch/noop vectors, "registered local comparator
patch" rename, band-edge caveat; (3) pilot information boundary
(PROCEED-bit-only exposure, 4-conjunct decision rule, exact-Fraction
q_pilot, byte-identical replacement law, table-frozen-before-pilot);
(4) standalone validator 15-law enumeration incl. the corrected
provenance of the oracle-mutation guard (NEW law, not inherited);
(5) semantic table completion (per-row premise/fragments/trigger/
restore; `assignment desk` duplicate renamed; class anchors);
(6) full scorer/driver/launcher re-pin enumeration + per-arm
two-seat freeze audits; (7) power-carry-over wording replaced
verbatim; (8) cold-start naming (pilot IDs/domains, schemas, spec
paths, receipt schema, promotion rule). Strongest counter accepted
into § Scope (whole-fixture reading residual; second MISS is a
priced-in outcome the pilot bounds).
