---
id: "0105-repo-scale-discovery-corpus"
title: "Repo-scale discovery corpus — checkup coverage module"
kind: instrument
status: DESIGN-FROZEN 2026-08-20 — R0+R1 folded, trio freeze complete (grok FREEZE, sol FREEZE, fable adjudication; final digest 77f3b10e…). User rulings 2026-08-20: L-R2 = import-graph derivation with pre-committed distance-only fallback; matrix pair = opus-5 vs opus-4-8; registration approved. Sequencing step 2 (authoring table + generator) FROZEN 2026-08-20 (trio; see Execution log)
complexity: high
depends_on: ["0102-executor-quality-discovery-corpus", "0103-opus-line-regression-cell", "0104-model-checkup-loop"]
---

# iter-0105 — repo-scale discovery corpus (checkup coverage module)

## Why this iter exists (pre-flight 0)

- 0102 scoped its claim to mid-scale fixtures and put **true repo
  scale (>100 files) explicitly OUTSIDE the shape**
  (`0102-*.md:42-47`). Its accepted strongest counter is the known
  residual: at 24-60 files with `Read,Grep,Glob,Edit,Write,Bash` and
  1800 s, sonnet CAN read the whole fixture, and no mechanical law at
  that scale prevents it (`0102-*.md:49-60`).
- The executor-quality lineage 0100→0103 CLOSED with the felt opus-5
  regression NOT reproduced at ≤60-file fixtures (`HANDOFF.md:56-69`).
  Of the weighed successors the user picked repo scale
  (`HANDOFF.md:19-22`).
- Deliverable is a **module, not a one-shot cell**: a sealed band that
  `playbooks/model-checkup.md` §5 (`model-checkup.md:149-227`) can
  select per model.

## Decisive criterion (two gates, carried in kind from 0102)

1. **Calibration is the SOLE difficulty measurement.** The frozen
   0102 calibrator gate is carried VERBATIM: exact-Fraction mean AND
   frozen even-n median ∈ [1/5, 3/5], interior ≥ 22/32, total-fail
   ≤ 2 (`score-calibration.py:169-177`; median indices `sorted_q[15]`
   / `sorted_q[16]` at `:169`; ledger row_count 64 at `:127-128`;
   `ENGINE = "claude-sonnet-5"` at `:15`). Task-set delta only. A
   valid MISS ⇔ **TERMINAL CALIBRATION_MISS**, valid negative, no
   retuning (`0102-*.md:354-361` in kind).
2. **ONE matrix evaluation**; the derived scorer's terminal token IS
   the decision. Bijection carried verbatim from
   `score-cohort.py:185-193` (threshold `Fraction(3,20)`):
   `H1_CONFIRMED` / `H1_MATERIAL_GAP_REFUTED` / `SATURATED` /
   `INCONCLUSIVE_AT_PILOT_N`.

**Module-success clause.** After this iter, reuse of this band for a
new model must require ONLY the §5 checkup deltas — engine tuple,
derived scorer, launch-gate constants (`model-checkup.md:168-185`).
Needing anything else means the module FAILED as a module.
Band-construction deltas — `FROZEN_TASKS`, fixture-ID re-targets,
corpus bindings — are one-time; per-model reuse is ONLY the §5 three.

## Registered treatment

The 0102 discovery mechanism carries wholesale — unstated, non-local,
two-fragment complementary, stateful restore (`0102-*.md:71-94`);
class semantics UA/MI/AF/BD unchanged (`0102-*.md:107-116`). The
repo-scale axis is added as **MECHANICAL laws only** — every law is a
fail-closed check in the derived validator, no prose laws.

- **L-R1 (scale)**: visible regular-file count ≥ 120 AND total visible
  source bytes ≥ **F**. `F` is a numeric constant RATIFIED AT
  DESIGN-FREEZE; this registration proposes **F = 2,000,000 bytes**.
  `F` is NEVER derived from pilot timing (grok F4 / sol F5 —
  pilot-derived = post-freeze tuning). Replaces the parent validator's
  24-60 topology window (`validate-discovery-task.py:265-266`).
- **L-R2 (dependency chain — USER RULED 2026-08-20: import-graph
  derivation)**: the corpus is **Python-only** (registered
  constraint). The derived validator builds an import graph over
  visible files with stdlib `ast` — imports, re-exports, literal file
  loads — extending the primitives already present at
  `validate-discovery-task.py:281-295` (import walk) and `:335-341`
  (`visible_local_module` resolution). Law: graph distance from the
  edit-site module set to EACH contract artifact ≥ 4 edges, AND
  registered edges must match derived edges, AND
  `directory_distance(edit_site, artifact.parent) ≥ 4` — the existing
  primitive (`:344-349`) raised from 2 (`:301-303`).
  **Pre-committed fallback (recorded here, adjudicated at FREEZE,
  never silent)**: if the graph deriver fails its freeze-round
  self-test bar, L-R2 narrows to the directory-distance-only law and
  the module claim narrows from "dependency chains" to "distance +
  distractor-mass discovery".
- **L-R3 (distractor mass — grok C4 law set merged with sol's
  neutralization check)**: ≥ 10 decoy modules, none a contract
  artifact nor on any registered L-R2 path, each with
  `directory_distance(edit_site, decoy) ≤ 2` AND strictly less than
  every contract artifact's distance. **Hit unit (frozen)**: a hit is
  a DISTINCT case-folded whole-word `(file, token)` pair over
  `contract_tokens_a ∪ contract_tokens_b` via `has_token`
  (`validate-discovery-task.py:141-142`, `TOKEN_RE` `:50`; law site
  `:304-314`); the law reads distinct decoy hits > distinct
  contract-artifact hits, AND ≥ 10 distinct decoy modules with ≥ 1 hit
  each. **NEUTRALIZATION**: in a temporary copy, neutralize every
  registered decoy-token occurrence → the no_patch / noop / symptom /
  gold oracle vectors must be IDENTICAL — a mechanical proof of zero
  contract force, reusing the smoke-case machinery.
- **L-R4 (two-fragment carry)**: the MECHANICAL complementarity law
  `0102-*.md:138-148` (grok precision fix — NOT the prose at
  `0102-*.md:79-89`).

**Frozen schema extension.** The parent validator enforces an EXACT
task-field set (`validate-discovery-task.py:41-45`; enforced at
`:174`); the derived one adds EXACTLY THREE frozen fields, no others:
`dependency_edges` (the edge list L-R2 matches against the derived
import graph), `contract_paths` (the L-R2 path node sets, one per
contract artifact), `decoy_artifacts` (the decoy module list +
registered decoy token set). Absence or any extra field fails closed.

**Quality claim under test**: at repo scale, selective navigation plus
contract discovery is the separating executor behavior; whole-fixture
reading is no longer a saturating shortcut. This closes the residual
at `0102-*.md:49-60` by scale.

## Corpus

N = 32, 8 per class, IDs `EQ4-{UA,MI,AF,BD}{1..8}`, reps = 2 → 128
scored matrix runs; 64-run sonnet calibration. `SATURATED` = both
engines ≥ 63/64 clean (`score-cohort.py:187`, `run_count = len(tasks)
* 2` at `:228`); δ_defect = 0.15.

**C1 adjudication (three-seat convergent) — TASK-CLUSTERED DECISION
REACHABILITY.** The frozen scorer averages reps into a per-task `q`
and bootstraps **task** differences, so reps never become statistical
N (`score-cohort.py:214-227`, `bootstrap_ci` at `:174-182`).
Replicating the registered percentile-bootstrap shape at paired-task
SD ≤ 0.30 and true alternatives Δ = 0 / Δ = 0.30: task-n 8 ≈ 29-37 %,
n 16 ≈ 52-55 %, n 32 ≈ 78-81 % — against the 0101-adjudicated ≈ 80 %
DECISION REACHABILITY bar (`0101-*.md:46-55`). 32 × 2 is additionally
the only shape that byte-preserves `REPS = {1, 2}`
(`score-cohort.py:18`), the `SATURATED` formula, and the calibration
median indices.

## Authoring

terra direct-drive lane (0102-proven, `HANDOFF.md:31-33`), 8 batches
× 4 tasks, trio verification per batch, hygiene fuzz auditor carried.
The 0102 (a)-(l) distinctness bar is carried as a **judge-gated
authoring self-check** — self-check bars reduce but do not replace the
judge gate (`0102-*.md:776-778`).

**Skeleton generator `gen-repo-skeleton.py` (new)**: frozen + digested
BEFORE any generation; per-task parameterized (grok C3); emits ONLY
non-treatment files, everything else hand-authored (sol C3
TREATMENT-BEARING AUTHORSHIP SEPARATION). Mechanically enforced, not
asserted (sol F6 residual 3): the generator MUST emit
`generator-inventory.json` (relative path + sha256 per emitted file),
and a NEW derived-validator law rejects the task if any inventory path
lies under `edit_site_dir`, is a contract artifact, appears in
`decoy_artifacts`, or is a node of any `contract_paths` entry. The
inventory is sealed with the corpus.

### Authoring table (frozen 2026-08-20; fixture internals IMPLEMENT-creative)

Language: **Python-only** (registered; Apparatus deltas item 2 deletes the
0102 language-parity law and retires its odd/even convention). Distinctness
tuple = (edit-site component, failure trigger, restore outcome) — all 32
distinct after entity renaming, and vs 0100 (12), 0101 (32), 0102 (32 + 4
prototypes), and the 4 EQ4P prototypes below. Column key: **local premise**
is the class anchor (UA assumption / MI missed invariant / AF absent failure
transition / BD breaking change); **fragment A** lives in
`contract_artifacts[0]` (consumer module), **fragment B** in
`contract_artifacts[1]` (test or executable doc); neither alone implies the
composed outcome.

Repo-scale fitness: every domain is plausible as a ≥120-file Python codebase
(L-R1; the skeleton generator supplies non-treatment mass). Every named
fragment A/B is a subsystem-crossing contract artifact planned at import-graph
distance ≥ 4 edges from the edit site (L-R2), rather than a same-package
neighbor.

| id | domain / edit site | local premise (class anchor) | fragment A (consumer) | fragment B (test/doc) | trigger → composed restore outcome |
|---|---|---|---|---|---|
| EQ4-UA1 | biobank logistics / aliquot-relocation confirmer | UA assumption: a relabelled aliquot replaces its source custody leg | `chain_of_custody/reconcile/ledger_consumer.py` — reconciler consumes relocation legs as append-only custody segments | `quality/system/test_duplicate_barcode.py` — system test asserts duplicate-barcode rejection restores the source rack without another custody event | duplicate barcode during relocation → source rack AND custody sequence restored; one custody event remains |
| EQ4-UA2 | satellite operations / maneuver-window editor | UA assumption: a late maneuver simply supersedes the booked burn window | `propellant/reservations/window_ledger.py` — reservation ledger retains the booked burn window until its replacement is accepted | `mission/acceptance/test_protected_pass.py` — acceptance test asserts a protected-pass collision releases the provisional propellant allocation | collision with protected pass → prior maneuver plan restored; provisional propellant allocation released once |
| EQ4-UA3 | municipal bond trustee / coupon-correction intake | UA assumption: a coupon correction overwrites the prior accrual | `tax/yield/accrual_consumer.py` — accrual consumer reads the confirmed coupon schedule as the authoritative yield basis | `servicing/settlement/test_invalid_cusip.py` — settlement test asserts an invalid CUSIP records one exposure memorandum | invalid CUSIP after accrual staging → original coupon schedule restored; exposure memorandum recorded once |
| EQ4-UA4 | semiconductor fabrication / recipe-revision issuer | UA assumption: a revised recipe is production-ready when staged | `genealogy/wafer/revision_consumer.py` — wafer genealogy exposes a recipe to production only after qualification accepts it | `qualification/system/test_rejected_recipe.py` — qualification test asserts rejection removes the staged wafer links | qualification rejection after staging → active recipe restored; staged wafer links removed once |
| EQ4-UA5 | land-title registry / easement-amendment clerk | UA assumption: an amendment may replace the title abstract | `lien_priority/graph/index_consumer.py` — priority index consumes only the confirmed title abstract when deriving lien order | `adjudication/appeals/test_counterclaim.py` — appeals test asserts a counterclaim keeps the filing fee in escrow | counterclaim against amendment → prior priority graph restored; escrowed filing fee retained once |
| EQ4-UA6 | polar field logistics / cargo-manifest reprioritizer | UA assumption: an itinerary substitution overwrites the existing manifest | `survival_cache/allocation/load_consumer.py` — load consumer assigns survival-cache reservations from the accepted itinerary | `airlift/safety/test_weight_rejection.py` — safety test asserts a weight rejection rolls the cache reservation back | aircraft weight rejection → original manifest restored; cache reservation rolled back once |
| EQ4-UA7 | wind-farm curtailment / dispatch-override intake | UA assumption: a new override clears the prior curtailment window | `certificates/accrual/window_consumer.py` — certificate consumer accrues against the settled curtailment window | `grid/interconnect/test_conflicting_limit.py` — interconnect test asserts a conflicting limit preserves accrued certificates | conflicting grid limit → prior curtailment restored; certificate accrual preserved once |
| EQ4-UA8 | archaeological collections / provenance-merge controller | UA assumption: a merged record discards source ordering | `exhibit_loans/provenance/chain_consumer.py` — provenance consumer retains source-catalogue order for an active loan chain | `repatriation/review/test_contested_origin.py` — review test asserts a contested origin keeps the active loan lock | contested origin during merge → source catalogues restored; active loan lock retained once |
| EQ4-MI1 | meteorological reanalysis / observation-backfill merger | MI missed invariant: post-publication backfill must retain the external revision identity | `forecast/baselines/revision_consumer.py` — baseline consumer keys reanalysis by the external revision identity | `publication/system/test_station_correction.py` — publication test asserts a duplicate correction leaves one superseding issue | duplicate station correction → revision lineage restored; one superseding issue remains |
| EQ4-MI2 | university endowment / valuation-roll-forward service | MI missed invariant: a valuation after lock date cannot change official unit history | `custody/units/official_ledger.py` — official ledger accepts valuation changes only before the lock date | `governance/close/test_rejected_valuation.py` — close test asserts rejection removes the provisional allocation | rejected valuation at close → official units restored; provisional allocation erased once |
| EQ4-MI3 | wildfire mutual aid / resource-reassignment broker | MI missed invariant: demobilization releases a resource before another incident can claim it | `availability/resources/status_consumer.py` — status consumer permits a new claim only after the prior demobilization is recorded | `incident/command/test_cancelled_dispatch.py` — command test asserts a cancelled dispatch emits one mutual-aid notice | cancellation after dispatch → prior resource status restored; mutual-aid notice emitted once |
| EQ4-MI4 | medicinal cold-chain / excursion-adjudication service | MI missed invariant: a batch-release lock survives a corrected temperature excursion | `batch_release/controls/hold_consumer.py` — hold consumer releases a batch only while its corrected excursion remains audit-free | `audit/system/test_external_flag.py` — audit test asserts an external flag keeps the downstream order blocked | external audit flag after correction → release hold reinstated; downstream order remains blocked once |
| EQ4-MI5 | digital preservation / retention-policy migrator | MI missed invariant: a legal hold precedes a new retention-compression profile | `worm_index/retention/hold_consumer.py` — retention consumer selects a compressed manifest only after the legal hold is satisfied | `records/compliance/test_overlapping_hold.py` — compliance test asserts an overlapping hold retains the storage reservation | overlapping hold during migration → prior archive manifest restored; storage reservation retained once |
| EQ4-MI6 | geotechnical monitoring / threshold-rule publisher | MI missed invariant: alert thresholds advance as a monotonic versioned sequence | `alerts/acknowledgement/version_consumer.py` — acknowledgement consumer accepts alerts only for the current threshold version | `calibration/system/test_failed_threshold.py` — calibration test asserts failure preserves the acknowledgement state | failed calibration → prior threshold rule remains active; acknowledgement state preserved once |
| EQ4-MI7 | maritime rescue coordination / incident-merge worker | MI missed invariant: command handoff order is retained in a merged incident timeline | `command_timeline/handoff/order_consumer.py` — timeline consumer preserves command-handoff order when resolving incident history | `operations/system/test_out_of_order_handoff.py` — operations test asserts an out-of-order handoff consumes one notification token | out-of-order handoff → original incidents restored; notification token consumed once |
| EQ4-MI8 | research compliance / protocol-amendment router | MI missed invariant: disbursement authority is bound to the approved protocol version | `funding/disbursement/version_consumer.py` — disbursement consumer authorizes funds only for the approved protocol version | `oversight/system/test_withdrawn_amendment.py` — oversight test asserts withdrawal keeps disbursement frozen | amendment withdrawal → prior protocol version restored; disbursement remains frozen once |
| EQ4-AF1 | additive manufacturing / powder-blend release | AF absent failure transition: contamination after staging has no quarantine transition | `material_control/quarantine/lot_consumer.py` — lot consumer blocks material release until the contamination state is cleared | `release/system/test_contaminant_flag.py` — release test asserts a contaminant flag restores the material reservation | contaminant flag mid-release → powder lots quarantined; material reservation restored once |
| EQ4-AF2 | fisheries quota exchange / transfer confirmer | AF absent failure transition: a disputed catch report has no transfer-reversal transition | `quota_ledger/settlement/balance_consumer.py` — balance consumer treats a quota transfer as provisional until its report is undisputed | `disputes/system/test_report_challenge.py` — disputes test asserts a challenged report closes the transfer record | catch report challenged after transfer → both quota balances restored; transfer record closed once |
| EQ4-AF3 | regional rail signalling / route-authorisation updater | AF absent failure transition: interlocking acknowledgement timeout has no route rollback | `interlocking/locks/route_consumer.py` — route consumer accepts authority only after interlocking acknowledgement | `control/system/test_ack_timeout.py` — control test asserts an acknowledgement timeout releases the track lock | acknowledgement timeout → prior route authority restored; track lock released once |
| EQ4-AF4 | public pension administration / survivor-benefit recalculator | AF absent failure transition: revoked beneficiary evidence has no staged-award withdrawal | `payments/instructions/award_consumer.py` — award consumer issues payment instructions only from final beneficiary evidence | `eligibility/system/test_document_revocation.py` — eligibility test asserts evidence revocation voids the payment instruction | evidence revoked after staging → prior award state restored; payment instruction voided once |
| EQ4-AF5 | film restoration archive / reel-handoff coordinator | AF absent failure transition: a corrupt source scan has no checkout reversal | `preservation/copies/reel_consumer.py` — reel consumer retains the booking slot until the source scan passes integrity checks | `vault/system/test_corrupt_source_scan.py` — vault test asserts a corrupt scan discards the preservation copy | corruption after checkout → booking slot restored; preservation copy discarded once |
| EQ4-AF6 | emergency shelter operations / family-reunification intake | AF absent failure transition: a failed guardian match has no provisional-placement unwind | `bed_management/assignments/family_consumer.py` — assignment consumer commits a bed only after the guardian match succeeds | `safeguarding/system/test_guardian_mismatch.py` — safeguarding test asserts a mismatch consumes one case token | guardian mismatch after placement → previous bed assignment restored; case token consumed once |
| EQ4-AF7 | high-voltage grid maintenance / transformer-outage scheduler | AF absent failure transition: emergency pre-emption has no reserved-outage restoration | `switching/crews/callout_consumer.py` — callout consumer retains the reserved outage until the emergency state clears | `reliability/system/test_weather_preemption.py` — reliability test asserts weather pre-emption cancels the crew callout | weather emergency pre-empts outage → prior switching plan restored; crew callout cancelled once |
| EQ4-AF8 | bridge inspection authority / disposition updater | AF absent failure transition: revoked sensor evidence has no closure-notice rescind path | `asset_status/closures/notice_consumer.py` — notice consumer derives a closure only from currently valid sensor evidence | `engineering/system/test_revoked_sensor_evidence.py` — engineering test asserts evidence revocation rescinds the closure notice | sensor evidence revoked after staging → prior inspection disposition restored; closure notice rescinded once |
| EQ4-BD1 | nuclear-waste logistics / container-label updater | BD breaking change: reclassifying a label changes the transport-eligibility consumer's state | `transport_eligibility/certificates/label_consumer.py` — eligibility consumer reads transport state from the currently classified label | `safeguards/system/test_manifest_reclassification.py` — safeguards test asserts reclassification retains the route certificate | reclassification after manifest draft → prior label restored; route certificate retained once |
| EQ4-BD2 | social-housing allocation / household-priority normalizer | BD breaking change: normalizing priority changes the subsidy calculator's quoted state | `rent_support/quotes/priority_consumer.py` — quote consumer derives subsidy only from the official waitlist priority | `appeals/system/test_withdrawn_household_appeal.py` — appeals test asserts withdrawal removes the subsidy quote | appeal withdrawn after quote → waitlist priority restored; subsidy quote withdrawn once |
| EQ4-BD3 | analytical laboratory / calibration-coefficient publisher | BD breaking change: publishing a coefficient changes the assay signer's accepted version | `assay_signing/certificates/coefficient_consumer.py` — signing consumer accepts certificates only for the registered calibration coefficient | `metrology/system/test_invalid_coefficient.py` — metrology test asserts an invalid coefficient leaves issuance singular | invalid coefficient after publication → prior calibration restored; certificate issuance remains singular |
| EQ4-BD4 | urban forestry permits / species-correction registrar | BD breaking change: correcting species changes the mitigation-credit ledger's category | `mitigation_credits/ledger/species_consumer.py` — credit ledger derives category from the approved species record | `survey/system/test_voided_species_record.py` — survey test asserts a voided record releases the reserved credits | survey void after partial approval → original species record restored; reserved credits released once |
| EQ4-BD5 | research-compute platform / budget-allocation modifier | BD breaking change: changing an allocation alters the grant-billing reporter's committed usage | `grant_billing/reports/allocation_consumer.py` — billing consumer reports only the committed budget allocation | `sponsorship/system/test_expired_grant.py` — sponsorship test asserts expiry does not advance the invoice checkpoint | grant expiry during allocation → prior budget state restored; invoice checkpoint does not advance |
| EQ4-BD6 | road-toll concession / exemption-rule importer | BD breaking change: an imported exemption changes the dependent invoice processor's toll class | `invoicing/charges/exemption_consumer.py` — invoice consumer maps toll class only from a valid exemption rule | `ordinance/system/test_malformed_exemption.py` — ordinance test asserts a malformed rule emits one correction notice | malformed ordinance → prior toll class restored; correction notice emitted once |
| EQ4-BD7 | refugee resettlement / placement-priority reassessor | BD breaking change: reassessment changes the case-allocation service's offer ordering | `case_allocation/offers/priority_consumer.py` — offer consumer orders placements by the active eligibility priority | `eligibility/system/test_reversed_status.py` — eligibility test asserts reversal reopens the housing offer | eligibility reversal after offer → previous placement priority restored; housing offer reopens once |
| EQ4-BD8 | national-park ecology / habitat-survey merger | BD breaking change: merging habitat status changes the permit-quota engine's available capacity | `permit_quotas/capacity/habitat_consumer.py` — capacity engine sums source observations from the active habitat revision | `field_review/system/test_erroneous_merge.py` — field-review test asserts an erroneous merge recomputes quota capacity | erroneous survey merge → source observations restored; quota capacity recomputed once |

### Pilot prototype rows (frozen; domains and tuples banned from the corpus)

- **Prototype rows** — IDs, domains, class anchors, and behavioral
  tuples are pre-registered here; same shape laws as corpus tasks;
  `TASKS_ROOT_PILOT = benchmark/executor-quality/tasks-0105-pilot`:

| id | domain / edit site | local premise (class anchor) | fragment A (consumer) | fragment B (test/doc) | trigger → composed restore outcome |
|---|---|---|---|---|---|
| EQ4P-UA1 | space-launch range / payload-window allocator | UA assumption: a payload swap frees the prior trajectory slot | `range_safety/trajectory/reservation_consumer.py` — reservation consumer retains the trajectory slot until range safety accepts the swap | `launch/operations/test_weather_hold.py` — operations test asserts a weather hold retains the hazard notice | weather hold after payload swap → original launch allocation restored; hazard notice retained once |
| EQ4P-MI1 | currency circulation / note-fitness policy editor | MI missed invariant: destruction eligibility follows the signed fitness-policy version | `destruction_ledger/authorizations/policy_consumer.py` — authorization consumer permits destruction only for the signed fitness-policy version | `vault/system/test_unsigned_policy.py` — vault test asserts an unsigned replacement leaves authorization unused | unsigned policy replacement → prior fitness policy restored; destruction authorization remains unused |
| EQ4P-AF1 | heritage preservation / facade-permit change processor | AF absent failure transition: a withdrawn structural report has no permit-hold transition | `inspection_holds/permits/report_consumer.py` — permit consumer keeps a provisional facade approval contingent on the structural report | `conservation/system/test_withdrawn_report.py` — conservation test asserts withdrawal releases the inspection appointment | report withdrawn after provisional approval → permit state restored; inspection appointment released once |
| EQ4P-BD1 | remote examination services / accommodation allocator | BD breaking change: changing an accommodation alters the proctor-scheduling consumer's seat plan | `proctor_scheduling/seats/accommodation_consumer.py` — seat consumer assigns proctors from the currently approved accommodation | `accessibility/system/test_expired_accommodation.py` — accessibility test asserts expiry reopens the proctor seat | accommodation expiry after seat assignment → prior accommodation restored; proctor seat reopens once |

Fresh judges at VERIFY review semantic distinctness of fixtures against 0100,
0101, 0102, and the prototypes; the derived validator checks
id/class/bindings/topology mechanically.

## Apparatus deltas (COMPLETE list — sol F2 / grok F2-F3 closure; nothing else changes)

1. New corpus root + sealed `candidate-manifest.json` (0105) + tree
   digest — fill-at-freeze.
2. **Derived validator `validate-repo-task.py`** from
   `validate-discovery-task.py`: topology window → L-R1; distance
   threshold 2 → 4; + import-graph deriver (L-R2); + decoy laws and
   neutralization (L-R3); + the three schema fields and the
   generator-inventory law (both tamper-set covered); **language-parity
   law DELETED** — the index-keyed odd-Python / even-Node branch
   (`:273`; laws `:277-280` / `:296-299`) would fail an even-index EQ4
   task closed under the Python-only fork, retiring the 0102 odd/even
   convention (`0102-*.md:120-123`, `:239`, `:211-212`); the
   stdlib-only import walk nested in it (`:281-295`) is RETAINED as
   L-R2's primitive, with the self-test corollary: fixture generation
   goes uniform-Python (parent even-index Node fixture `:480-481`,
   `:488-494`) and the parity tamper scenarios + their required
   diagnostics (`:562-566`, `:590-594`, `:605-610`) are REMOVED with
   the law; **task-ID prefix EQ3 → EQ4** (`REGISTERED_IDS`
   EQ3/EQ3P shape, `:33-40`); **self-test fixtures re-targeted to EQ4**
   (parent `EQ3P-UA1` / `EQ3-UA2` at `:528-533`), EXTENDED with one
   tamper fixture per NEW law. Frozen + digested.
3. **Derived scorer `score-cohort-0105.py`** — enumerated
   transformations: `ENGINES` → `("claude-opus-5",
   "claude-opus-4-8")` (user ruled 2026-08-20; base `:19`);
   `FROZEN_TASKS` → the EQ4 32-set (`:20-24`); and the substitution
   self-test's hardcoded IDs `EQ3-UA1` / `EQ3-UA99` (`:395-396`) →
   their EQ4 analogs, a mechanical corollary of the task-set transform
   without which the required `--self-test` full pass is unreachable.
   `REPS`, thresholds, bootstrap, `SATURATED` formula byte-preserved;
   `--self-test` full pass recorded pre-arm.
4. **Derived calibration scorer `score-calibration-0105.py`**:
   task-set delta ONLY (`score-calibration.py:17-21`); every gate
   constant byte-preserved.
5. **Driver copy from the canonical seed `mx-driver.py`**
   (`HANDOFF.md:35-38`): `CORPUS_MANIFEST` → the 0105 freeze manifest
   path (`:28`), `CORPUS_MANIFEST_SHA256` → the 0105 manifest digest
   (`:29`), `TREE_SHA256` → the 0105 tree (`:30`), `TASKS_ROOT` → the
   0105 corpus root (`:22`), `ALLOWED_ENGINES` tuple replacement
   (`:31`). **`BOUND_SEC = 1800` byte-preserved — an explicit
   NON-delta** (`:32`; C2 adjudication OUTCOME-INDEPENDENT CENSORING
   CONTROL): 0102 measured walls topped out at 238 s in calibration
   (`0102-*.md:791-792`) and 193 s in the matrix (`0102-*.md:844`)
   under 1800 s, so there is no censoring evidence, and raising the
   bound would ease the whole-read shortcut this iter exists to close.
   A pilot ceiling hit is a terminal mechanism failure, not a knob.
6. **Derived matrix launcher `mx-launcher-0105.py`**: `TASKS` → EQ4
   32-set — the SOLE delta (base hardcodes EQ3 at
   `~/.local/share/nx01/iter0103/apparatus/mx-launcher.py:17-18`).
   `ENGINES` (base `:19`) ALREADY is the registered ordered pair —
   **byte-preserved NON-delta**, order-identical to the derived
   scorer's per §5 (`model-checkup.md:172-174`). Frozen + digested.
7. **Calibration-lane apparatus** derived from the 0102 calibration
   apparatus: launcher `TASKS` → EQ4 (base hardcodes EQ3 at
   `~/.local/share/nx01/iter0102/calibration/apparatus/cal-launcher.py:14-15`),
   `ENGINE` stays `claude-sonnet-5` (`:16`); driver corpus-binding
   constants → 0105 exactly as item 5 (`cal-driver.py:22`, `:28`,
   `:29`, `:30`), `ALLOWED_ENGINES` (`:31`) and `BOUND_SEC = 1800`
   (`:32`) byte-preserved; calibration launch gate re-bound as in
   item 8. Frozen + digested; unavailable base fails closed, no
   substitution.
8. **`run-bounded.py` + matrix launch gate**: inherited by full 64-hex
   digest per the §5 pattern, every base bound by source path AND
   digest, unavailable base fails closed, no substitution
   (`model-checkup.md:158-163`). The inherited gate binds the OLD
   corpus (`~/.local/share/nx01/iter0103/launch-detached.py`), so
   enumerate: candidate-manifest path + sha256 and derived-scorer path
   + sha256 in the `FROZEN` inventory (`:29-37`; manifest `:33`,
   scorer `:34`), `TREE_SHA256` (`:28`), the inventory/`required` key
   list (`:63-64`), the SECOND hardcoded manifest path at the tree
   recomputation (`:108`), `FREEZE_FILE` →
   `frozen-0105-apparatus.sha256` (`:38`; `model-checkup.md:183-185`).
9. `gen-repo-skeleton.py` (new, per § Authoring).

Nothing else.

## Sequencing (0102 control carried — sol F4 / grok F7 closure)

1. Registration commit → **R1 seat review + trio FREEZE**.
2. Authoring table (ALL 32 specs) frozen + generator frozen; digests
   committed.
3. **Pre-corpus mechanism pilot**, mirroring `0102-*.md:287-352` in
   kind at repo-scale parameters: pilot tasks built to the FULL law
   set, validator-green, sonnet runs. Exposure to authoring is ONE
   LINE — PROCEED/REJECT — plus the decision-receipt digest, per the
   frozen 0102 information boundary (`0102-*.md:329-346`). REJECT =
   terminal `MECHANISM_REJECTED`, no retuning.
4. Batches 01-08, trio verification per batch.
5. Corpus sealing: canonical JSON manifest + tree digest.
6. Calibration: 64 runs, gate verbatim; MISS = TERMINAL
   CALIBRATION_MISS.
7. Apparatus freeze inventory commit (full 64-hex, one line per
   apparatus file) with the pre-committed R-A / R-B rules
   (`model-checkup.md:194-207`).
8. Sandbox tamper probes fail-closed → **two-seat FREEZE-ARM ×2**
   (sol + grok, liveness, residual attack rights;
   `0102-*.md:417-421`) → launch gate → **ONE matrix evaluation** →
   DECISION recorded.
9. **§5 band binding is ATOMIC** (sol C5 ATOMIC AVAILABILITY + grok
   C5): the band row — `band ∈ {0102-discovery, 0105-repo-scale}`,
   inherit-by-digest FROM THIS BAND'S OWN FREEZE — is added ONLY in
   the closing change that records calibration PASS together with a
   valid matrix terminal. A miss ⇒ NO table row.

## Pre-registered predictions

- **P-0105-1 (calibration)**: the sonnet band PASSES the carried gate
  ⇔ the repo-scale discovery mechanism is valid. MISS ⇔ TERMINAL
  CALIBRATION_MISS — a valid negative bounding the mechanism claim.
- **P-0105-2 (matrix)**: token bijection verbatim.
  `H1_CONFIRMED` ⇔ opus-5 fails materially more than opus-4-8 at repo
  scale — the first instrument in the lineage to reproduce the felt
  gap. `H1_MATERIAL_GAP_REFUTED` ⇔ a material opus-5-worse gap is
  excluded at repo scale too — a coverage extension of 0103.
  `SATURATED` and `INCONCLUSIVE_AT_PILOT_N` carry verbatim and
  neither confirm nor refute.

## Information boundary

This registration is FROZEN before any cohort row content or score is
read; only opaque row counts are observable during runs; the pilot
exposes one line plus a digest (§ Sequencing 3).

## Budget/wall (informational)

128 matrix runs + 64 calibration runs. Reference walls at mid scale:
0102 calibration 64 runs in ~35 min, run walls 20-238 s / median 55 s
(`0102-*.md:791-792`); 0102 matrix 128 runs in 80 min at 2 lanes
(`0102-*.md:840`), walls 27/67/193 s (`0102-*.md:844`); 0103 matrix
93 min at 2 lanes (`0103-*.md:222-223`). Repo-scale walls are
unknown and expected to be a multiple of these. Detached launch via
`python os.setsid()` (`HANDOFF.md:88`), quiet account, outside
23:00-01:00 KST (`HANDOFF.md:34-35`).

## Receipts layout

`~/.local/share/nx01/iter0105/` laid out per `0102-*.md:491-503` in
kind; cohort id `mx<n>-<UTCSTAMP>Z`.

## Design notes (R0 adoption record)

- **sol R0 — VERDICT REVISE (2, 3, 4, 5, 6)**, plus F1 non-blocking:
  the playbook's 0105-reservation reference was stale
  (`model-checkup.md:427` cited `HANDOFF.md:32-35`; the reservation
  is at `HANDOFF.md:19-22`) — fixed in the same working session.
  Blocking findings 2-6 (apparatus-delta completeness, 16×4
  reachability, impossible sequencing + pilot leakage, unfreezeable
  L-R1 + unjustified 2700 s, validator-unclosed L-R2/L-R3/generator)
  all folded above.
- **grok R0 — VERDICT REVISE (1-7)**: task-clustered reachability,
  band-construction deltas that would UNSCORE the corpus,
  unenumerated calibration apparatus, pilot-as-tuner, source-underived
  L-R2, unrankable L-R3, and the 0102 R1-2 information-boundary
  regression. All folded above.
- **fable adjudications, named criteria**: C1 → 32 × 2 (TASK-CLUSTERED
  DECISION REACHABILITY, three-seat convergent); C2 → `BOUND_SEC`
  1800 byte-carry (OUTCOME-INDEPENDENT CENSORING CONTROL — grok's
  2700 s rejected on grok's own timing citations, no censoring
  evidence, delta deleted); C3 → generator gated by TREATMENT-BEARING
  AUTHORSHIP SEPARATION + per-task parameterization; C4 → EXECUTABLE
  PREDICATE CLOSURE (grok's validator-primitive law set merged with
  sol's neutralization check); C5 → ATOMIC AVAILABILITY.
- **USER RULINGS 2026-08-20**: L-R2 = import-graph derivation with a
  pre-committed distance-only fallback; matrix pair = opus-5 vs
  opus-4-8; registration approved.

## Execution log

- **2026-08-20 — REGISTERED.** R0 folded (sol + grok); R1 seat review
  and trio FREEZE pending.
- **2026-08-20 — R1**: grok FREEZE (7/7 closed, no new findings); sol
  REVISE F2/F6 residuals → this amendment (fable adjudication: sol
  residuals adopted, batch-B precedent); sol residual re-confirmation
  FREEZE (F2/F6 all closed); author-flagged #2 (parity-law delta), #3
  (playbook live-example deletion), #4 (one-time vs per-model) adopted.
- **2026-08-20 — final freeze round → trio FREEZE.** grok FREEZE on
  digest `6681994b…` (full citation walk; consistency: parity-vs-L-R2,
  "Nothing else.", module-clause-vs-item-3). sol REVISE — the parity
  deletion's self-test corollary was unenumerated (parent even-index
  Node fixture `:480-494`; parity scenarios + diagnostics `:562-566`,
  `:590-594`, `:605-610`) → folded into item 2 (+4 lines). Micro-pass
  on digest `77f3b10e…`: sol FREEZE ("fully closes E1 self-test
  transformation closure") + grok FREEZE (pre-insertion file
  hash-reconstructed; delta = exactly the insertion). Status →
  DESIGN-FROZEN.
- **2026-08-20 — Sequencing step 2 COMPLETE: authoring table + generator
  FROZEN (trio).** Terra (single writer, digest-pinned briefs) authored
  the 32-row EQ4 table + 4 EQ4P pilot rows (§ Authoring table) and
  `benchmark/executor-quality/scripts/gen-repo-skeleton.py`. Trio rounds:
  r0 — sol REVISE (5 fable findings upheld + new r0-6) / grok REVISE
  (all 6); F-T3 split resolved 2-of-3 (LABEL-CONTENT FIDELITY). r1 —
  terra fixes verified; sol NOT-RESOLVED residual on F-G1 (one-grep
  provenance markers = 95.0% of visible bytes) ADOPTED over grok's
  RESOLVED — named criterion EXACT-MARKER vs STATISTICAL-REGULARITY;
  new evidence rule satisfied. r2 — in-band provenance constants
  deleted (the sealed inventory is the sole provenance carrier),
  per-module docstring/prefix/symbol variation, NEW line-level
  shared-exact-marker self-test arm (proven to FAIL on the pre-fix
  content class); F-R1 stale header sentence replaced (3-0). Final
  micro-pass: sol FREEZE (`FREEZE-0105-STEP2-SOL`) + grok FREEZE
  (`FREEZE-0105-STEP2-GROK`, digests independently recomputed).
  Frozen digests: generator `213594c6…`; this file at freeze
  `addeb27a…` (diff vs `97c975e` = one +71/−0 hunk, registration
  bytes untouched). Distinctness: 36/36 vs the 80 prior tuples
  (0100/0101/0102 + prototypes), mechanical + manual sweep, fable
  re-swept. **sol r0-6 adjudication (binding on step 3)**: the
  § Authoring inventory clause "per emitted file" reads "per emitted
  payload file" — the inventory cannot contain its own digest and is
  the SOLE exclusion; mechanically enforced at `verify_inventory`;
  the derived validator MUST enforce the same exclusion.
  **Stopping rule (frozen)**: the generator self-similarity bar is
  the line-level arm; substring-level template regularity is conceded
  — post-freeze filler-realism findings require a self-advertising
  exact marker or pilot-observed pruning evidence. Receipts:
  `~/.local/share/nx01/iter0105/authoring/`. NEXT = Sequencing
  step 3: pre-author ALL NINE specs (pilot + batch 01-08) from the
  frozen table and commit BEFORE the pilot fires; pilot lane lands
  the 4 prototypes + derived `validate-repo-task.py`; 8 sonnet runs.
