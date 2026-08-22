---
id: "0108-band-rederivation-pilot"
title: "Repo-scale difficulty re-derivation — three-engine anchor pilot"
kind: instrument
status: REGISTERED-FROZEN 2026-08-22 (trio: sol FREEZE-0108-REG-SOL + grok FREEZE-0108-REG-GROK + fable adjudication)
complexity: medium
depends_on: ["0105-repo-scale-discovery-corpus", "0107-frontier-anchor-pilot"]
---

# iter-0108 — repo-scale difficulty re-derivation pilot

## Why this iter exists (pre-flight 0)

The frozen EQ4P repo-scale difficulty is EVIDENCED above-band for all
three anchor engines: 0105 sonnet REJECT (mean above upper bound,
interior < 3, one prototype at q=1; `0105-*.md:606-609`) and 0107
opus-5 + opus-4-8 REJECT (both engines mean above upper bound +
interior below minimum + shared-task both-ceiling; `0107-*.md:352-358`;
repo log entries DECISIONS 0105.1 / 0107.1). Both closures name the
same evidenced next step: **difficulty re-derivation under a NEW
registration**, user-gated — gate opened 2026-08-22 (user directive:
trio collaboration through verification). The question this iter
answers: does a registered EASIER repo-scale geometry land ALL THREE
anchor engines in the registered interior band, licensing the corpus
successor in one measurement instead of a repeat of the 0105→0107
two-step?

## Decisive criterion

The registration is FREEZE-worthy iff a fresh session could execute it
mechanically — every apparatus file derivable from the enumerated
delta classes alone, every self-test reachable — and its
PROCEED/REJECT answers exactly one question: "is the re-derived
geometry usable as the difficulty basis for a sonnet-calibrated
opus-5 vs opus-4-8 repo-scale corpus?" — with no unscored ambiguity,
no leakage of sealed 0105/0107 per-task outcomes into design, and no
scope beyond the band decision.

## Principles check

- **Pre-flight 0** (FIRST) ✅ Passes — this iter exists because both
  prior closures left "re-derive easier" as the evidenced, user-gated
  next step, and the re-derived geometry is unmeasured until piloted.
- **#7 Mission-bound** (SECOND) ✅ Passes — serves Mission 1's
  ceiling-instrument track: the repo-scale coverage module cannot
  advance to corpus/calibration/matrix without a band-passing
  difficulty basis.
- **#1 No workaround** ✅ Passes — fail-closed gates carried (launch
  gate digest pins, ordinal locks, three-route verdict domain with a
  registered mechanical router); difficulty is eased by REGISTERED
  tree re-geometry enforced by fail-closed validator laws, never by
  relaxing a law while keeping the hard trees (law relaxation ≠ tree
  easing — the exact-distance law and inverted dominance law force
  the geometry).
- **#2 No overengineering** ✅ Passes — band decision only; no corpus
  stage, no new flags, no adaptive control flow; three engines in one
  fixed launch replaces two sequential registrations; the L-R3 delta
  is a single-comparator inversion, the smaller of the candidate
  shapes.
- **#3 No guesswork** ✅ Passes — the geometry knobs return toward
  the 0102-measured in-band regime (distance floor 2 law,
  `validate-discovery-task.py:301-303`; no decoy-dominance law in the
  0102 parent) while preserving non-locality; what the pilot measures
  is stated precisely: repo mass + exact-distance-3 + decoy
  non-dominance geometry — NOT "mass alone". Sealed per-task outcomes
  are NOT design inputs; only the abstract three-gate diagnoses are
  used.
- **#4 Worldclass** ✅ Passes — 0105/0107 freeze discipline carried in
  kind (digest pins, reversal proofs, sealed boundary, trio audit
  before launch).
- **#5 Best practice** ✅ Passes — proven schedule shapes reused with
  formulas frozen literally (0105 lane-parity block; 0103/0107
  two-engine ABBA block); exact `Fraction` arithmetic;
  clause-isolated, per-engine-parameterized self-tests.
- **#6 Optimized** ✅ Passes — 24 fixed runs at peak concurrency 2
  close the three-engine question in one detached launch; the
  sonnet-first sequential-gate alternative saves at most 16 runs on a
  REJECT but adds a second launch window and a second freeze surface
  on the PROCEED path.
- **Production ready (#7 core)** ✅ Passes — three-route verdict
  domain with a MECHANICAL router (below); no silent fallback
  anywhere.

## Registered treatment

**Re-derivation principle (the evidence anchor).** 0105 stacked three
hardness axes at once relative to the 0102-measured in-band shape:
scale (≥120 files / ≥2,000,000 bytes), contract distance (≥4, raised
from the 0102 law floor of 2), and decoy dominance (≥10 decoys
strictly closer than every contract artifact with strictly more
distinct hits). The re-derivation KEEPS the scale axis — the module's
identity: 0102's accepted residual is that at 24-60 files
whole-fixture reading is an available shortcut no law prevents
(`0102-*.md:49-60`, glossed at `0105-*.md:107-110`), and mass is the
axis that closes that shortcut — and eases the other two axes to a
registered NON-LOCAL MINIMUM: contract distance pinned at EXACTLY 3
(the smallest value that keeps both contract artifacts outside the
edit site's top-level package at the frozen edit-site depth —
non-locality is mechanism identity), and decoy dominance INVERTED to
non-dominance. What PROCEED licenses is this exact geometry — repo
mass + exact-distance-3 + decoy non-dominance — not "mass alone".
Per-task outcomes of 0105/0107 stay sealed and are not inputs; the
re-geometry is uniform and non-discretionary across all four
prototypes (exact-3 for every contract artifact, same law set), so no
per-task differential easing exists to encode anything.

**Prototype bases.** The four frozen EQ4P trees (UA1 `453093a6…` ·
MI1 `40b6db84…` · AF1 `0d567197…` · BD1 `ad69e711…`) are the
re-geometry BASES — domains, class anchors, behavioral tuples,
fragments, edit-site paths (byte-carried, which freezes edit-site
depth and makes exact-3 well-defined), and the discovery mechanism
(unstated, non-local, two-fragment complementary, stateful restore)
carry unchanged. New IDs `EQ4R-{UA,MI,AF,BD}1` under
`TASKS_ROOT_PILOT = benchmark/executor-quality/tasks-0108-pilot`.
Per-tree deltas are enumerated and reversal-provable against the EQ4P
bases; the transformation rule is the same for all four trees:
relocate both contract artifacts to directory distance exactly 3,
update every import/reference to the new locations, and redistribute
contract-token occurrences so distinct decoy `(file, token)` hits ≤
distinct contract-artifact hits (arithmetic consequence, registered:
with ≥10 decoys at ≥1 hit each, contract artifacts must carry ≥10 of
the ≤12 possible `(artifact, token)` pairs — each artifact weaves in
most of both contract-token sets, which is natural for a test that
exercises the consumer). Decoy module positions and counts are
byte-carried.

### Law deltas (validator `validate-repo-task-0108.py`, derived from `f88474ca…`)

1. **L-R1 carried; wording corrected**: visible file count ≥ 120
   (`validate-repo-task.py:370-371`) AND visible regular-file bytes
   ≥ 2,000,000 (`:372-373` — the implementation sums every visible
   regular file regardless of suffix; the prior "source bytes" gloss
   is retired). No law change — repo-scale identity.
2. **L-R2″ (exact distance)**: the floor law `< 4 → reject`
   (`:383-384`) becomes the degenerate window
   `directory_distance(edit_site, artifact.parent) == 3` for EVERY
   contract artifact, fail-closed both sides (`!= 3 → reject`).
   Rationale: 3 is the NON-LOCAL MINIMUM at the frozen edit-site
   depth (2 under `visible/`) — distance 2 would force a contract
   artifact into the edit site's own top-level package or the
   `visible/` root, destroying the cross-subsystem character the
   mechanism requires; distance 4 is the falsified geometry. The
   degenerate pin is non-discretionary (no per-tree window freedom)
   and non-vacuous (every EQ4P base tree fails it until its artifacts
   actually move).
3. **L-R3″ (decoy non-dominance)**: the decoy-distance conjuncts
   (`:309-310` — each decoy within distance 2 AND strictly closer
   than every contract artifact) are BYTE-CARRIED; under exact-3
   artifacts and ≤2 decoys they are satisfied by construction, and
   the far-decoy tamper still exercises them. The dominance law
   (`:324` — distinct decoy hits must EXCEED distinct
   contract-artifact hits) is INVERTED: distinct decoy hits ≤
   distinct contract-artifact hits (non-dominance; equality
   permitted). ≥10 decoy modules with ≥1 distinct hit each and the
   NEUTRALIZATION proof (temporary-copy token neutralization ⇒
   oracle vectors identical — zero contract force) carry unchanged.
4. **L-R4 byte-carried**: two-fragment mechanical complementarity law
   unchanged.
5. **Schema unchanged**: the three frozen fields
   (`dependency_edges`, `contract_paths`, `decoy_artifacts`) with
   structural-shape validation, generator-inventory law, and the
   inventory self-digest exclusion all carry.
6. **ID re-target**: in `REGISTERED_IDS` (`:33-40`) the prototype
   block `EQ4P-*1` → `EQ4R-*1`; the `EQ4-{UA,MI,AF,BD}{1..8}` corpus
   block is byte-carried and INERT in this lane (no corpus tree
   exists; the successor registration owns its fate).
7. **Self-test corollary (enumerated, the 0105 parity-corollary
   class)**: the positive fixture `write_fixture` currently places
   artifacts at distance 4 (`:601-614`) and creates 10 decoy hits
   against 6 artifact hits (`:609-621`) — ILLEGAL under laws 2-3.
   Enumerated fixture deltas: both fixture artifacts relocate to
   distance exactly 3; artifact contents extended so distinct
   contract-artifact hits ≥ 10 (both token sets woven into both
   artifacts); decoy emission unchanged. Affected helpers enumerated:
   `move_artifact_near_edit` (`:841` region) retargets to the new
   fixture paths and becomes the near tamper (artifact at distance
   2); a NEW far tamper places an artifact at distance 4;
   `saturate_artifact_hits` (`:958` region) — which ADDS artifact
   hits and would PASS the inverted law — is REPLACED by a NEW
   excess-decoy tamper that adds decoy hits above the artifact count;
   neutralization/complementarity/inventory helpers (`:890`, `:921`
   regions) retarget paths only. Tamper expectation strings updated:
   `distance-near` ("must be exactly 3"), `distance-far` (same law),
   `decoy-excess` ("distinct decoy hits must not exceed
   contract-artifact hits"), `decoy-distance` carried. Self-test
   fixture IDs re-targeted EQ4P→EQ4R (`:670-671`).

Nothing else changes in the validator.

### Apparatus delta classes (frozen NOW; exact bytes reversal-proven at derivation)

Base files (the ONLY readable prior apparatus; digests verified
2026-08-22): 0107 `pilot-driver.py` `e531f1bf…` / `pilot-launcher.py`
`225889a0…` / launch gate `launch-detached.py` `cba26f9d…` /
`score-pilot-0107.py` `74077f40…` / `run-bounded.py` `db9ed383…` /
`pilot-manifest.json` `78d153da…` (manifest-shape base); 0105
`pilot-launcher.py` `e86d8b38…` (block-1 schedule base) /
`validate-repo-task.py` `f88474ca…` / `gen-repo-skeleton.py`
`213594c6…`; the four EQ4P trees (digests above).

- **driver** (from `e531f1bf…`): docstring/iter label;
  `ALLOWED_ENGINES` → the three exact IDs `("claude-sonnet-5",
  "claude-opus-5", "claude-opus-4-8")`; `TASKS_ROOT` → the 0108
  corpus root; manifest path/digest/tree constants → the 0108 sealed
  manifest. Taxonomy carried VERBATIM (combined stdout+stderr
  `INFRA_FAILURE`; zero-turn ⇒ infra except the registered rc=124
  censoring branch ⇒ terminal f=1). No engine-specific taxonomy
  edits in this lane. **PLUS one cause-contract delta (sol R1 +
  micro-pass)**: every ledger row gains `infra_cause` — `null` when
  `infra_invalid` is false; else exactly one token, stamped at EVERY
  `infra_invalid=True` assignment site of the base (enumeration
  verified exhaustive at the bytes): `"runner-integrity"`
  (`pilot-driver.py:175`), `"task-seal"` (`:177`),
  `"attestation-mismatch"` (`:135-136` — attested ≠ requested),
  `"attempt-setup"` (`:187`), `"runner-failure"` (`:223`),
  `"provider-signal"` (`api_error_status ∈ {429, 529}` or an
  `INFRA_FAILURE` match, `:138-140`), `"zero-turn"` (`:137`;
  assigned only when no provider signal — provider-signal precedence
  pinned). The TRANSIENT set is exactly {`provider-signal`,
  `zero-turn`}; the other five are non-transient apparatus/identity
  classes. The base records causes only in per-run stderr
  (`failed_row` `:102-113`), making them ledger-indistinguishable
  from retriable rows; the cause field closes that. Any cause token
  outside the seven routes non-transient (fail-closed).
- **launcher**: NEW `pilot-launcher-0108.py`, constructed from the two
  frozen schedule bases — neither base is byte-carried whole. Block 1
  (rows 1-8): sonnet single-engine, the 0105 lane-parity formula
  frozen literally — per lane ∈ {0,1}:
  `[(task, rep) for rep in (1, 2) for i, task in enumerate(TASKS) if
  i % 2 == lane]` (source `e86d8b38…` `lane_schedule`). Block 2
  (rows 9-24): matrix pair ABBA frozen literally as
  `ENGINES[(i + rep + group) % 2]` with the 2-lane task split (source
  `225889a0…`, precedent `iter0103/apparatus/mx-launcher.py:22-33`).
  **Cut rule (drain barrier)**: block 2 starts only after every
  block-1 row has terminated — mechanically observable, keeps peak
  concurrency 2, and keeps the only cross-engine gate inside the
  time-symmetric ABBA block. `TASKS` → the four EQ4R IDs. Row-id
  grammar and run-id confinement carried from the 0107 gate rules.
  Per-lane ledgers merged after, as both bases do.
- **launch gate** (from `cba26f9d…`): `engines` receipt field = the
  exact ordered three-ID list; expected row count 24; schedule digest
  over the full 24-row schedule; `FROZEN` map → derived driver /
  launcher / `validate-repo-task-0108.py` / `score-pilot-0108.py`
  digests + the four EQ4R tree digests + 0108 manifest;
  freeze-inventory filename `frozen-0108-apparatus.sha256`; ordinal
  locks, attempt cap 3, `start_new_session`, receipt-before-effect
  killpg carried.
- **scorer**: NEW frozen `score-pilot-0108.py` derived from
  `74077f40…` with enumerated deltas: `ENGINES` → the three exact IDs
  + `MATRIX_ENGINES = ("claude-opus-5", "claude-opus-4-8")` ordered
  sub-tuple; **gate 3 iterates `MATRIX_ENGINES`, not `ENGINES`**
  (`score-pilot-0107.py:185`); `PILOT_TASKS` → the four EQ4R IDs
  (`:17`, also reachable at `:95`, `:141`); `row_count == 24`
  (`:133`); complete-cell validation over 3 × 4 × 2 (`:149`);
  per-engine aggregation over three engines; the wrong-engine
  self-test literal `claude-sonnet-5` (`:351`) — now a VALID engine —
  replaced by a non-registered ID; the self-test scenario identity
  output (`:375`) re-targeted to the 0108 suite; **row schema
  REQUIRES `infra_cause`** (an `infra_invalid` row with a missing or
  unknown cause is a NON-TRANSIENT validation error, fail-closed);
  reasons emit `infra_invalid:<run_id>:<cause>`; **on UNSCORED the
  scorer emits `route`** — `"transient"` iff EVERY offending row
  error is `infra_invalid` with cause ∈ {`provider-signal`,
  `zero-turn`}, else `"non-transient"` (mixed ⇒ non-transient,
  fail-closed) — so the route is frozen and self-testable, not
  orchestrator judgment. q semantics carried
  verbatim: per rep `f = Fraction(failed, total)`, or `Fraction(1)`
  for catastrophic/incomplete; `q(e,t) = (f(e,t,1) + f(e,t,2))/2`;
  `mean(e) = Σ_t q(e,t)/4`; exact `Fraction` throughout.

**Non-deltas (byte-carried on purpose)**: `BOUND_SEC = 1800`
(OUTCOME-INDEPENDENT CENSORING CONTROL), `EFFORT = "high"`, `TOOLS`,
pinned CLI `~/.local/share/nx01/pins/claude-2.1.226-iter0100/claude`
(`013a1cf1…`), `run-bounded.py` (`db9ed383…`), prompt = task goal
only, scrubbed env, opaque workdir copytree, manifest/tree pins.

## Decision rule (frozen at registration; scorer implements verbatim)

Let q_e(t) be as defined above; engines e range over the three exact
IDs; MATRIX = (claude-opus-5, claude-opus-4-8).

**PROCEED** iff ALL of:
1. for EACH of the three engines e: mean(q_e) ∈ [1/10, 3/5];
2. for EACH of the three engines e: ≥ 3 of 4 prototypes interior
   (0 < q_e(t) < 1);
3. NO prototype has BOTH MATRIX engines at q == 1.

Gate 3 is MATRIX-PAIR-SCOPED (SUCCESSOR-CONTRAST SUFFICIENCY): the
successor's contrast is opus-5 vs opus-4-8; a shared MATRIX
both-ceiling is the zero-contrast configuration that defeats it, and
an all-three-engine conjunct would ADMIT that configuration whenever
sonnet stays interior. Sonnet is the calibration anchor; gate 2
already caps its non-interior slots at one. The floor asymmetry
carries frozen from 0107: joint impossibility is fatal; a single
both-floor prototype is tolerated as an apparatus-health control.

**Verdict domain (three routes) + MECHANICAL router.** Gate-level
apparatus/digest failures never reach scoring — the launch gate
already stops fail-closed (carried behavior). On a ledger, the FROZEN
scorer emits PROCEED/REJECT when valid and complete, else UNSCORED
with `reasons` AND a `route` field computed from the registered
`infra_cause` contract (driver delta above) — the route is scorer
bytes, self-testable, never orchestrator judgment:
- Valid complete ledger failing any gate → terminal
  `BAND_REDERIVATION_REJECTED`: the re-derived geometry is unusable;
  no in-lane retuning of trees, laws, or taxonomy; any successor is a
  NEW user-gated registration.
- UNSCORED with `route == "transient"` (EVERY offending row
  `infra_invalid` with cause ∈ {`provider-signal`, `zero-turn`};
  rc=124 exempt — registered censoring, scores f=1, never infra) →
  relaunch ONLY on byte-identical digests, max 3 attempts, quieter
  window; a third transient failure → terminal
  `BAND_REDERIVATION_UNSCORED`.
- UNSCORED with `route == "non-transient"` (any schema violation,
  missing/duplicate cell, wrong engine id, any of the five
  non-transient causes — `runner-integrity`, `task-seal`,
  `attestation-mismatch`, `attempt-setup`, `runner-failure` — or any
  `infra_invalid` row with a missing/unknown cause; mixed ledgers
  included, fail-closed) → STOP and surface to the user; no blind
  retry.

**What PROCEED licenses (STAGE-LICENSE PRECISION)**: exactly one
fact — the re-derived four-task, two-rep geometry (repo mass +
exact-distance-3 + decoy non-dominance) passes the registered
three-engine band gate — licensing a separately registered corpus
successor (batches from the frozen 0105 32-row authoring table
re-geometried to these laws, sealing, calibration, matrix). It does
NOT establish corpus-level validity; the nested-screen caveat carries
(pilot floor 1/10 is weaker than the calibration floor 1/5, so a
PROCEED at mean ∈ [1/10, 1/5) does not predict a 32-task calibration
PASS). Two reps support only this coarse floor/interior/ceiling gate;
no population-rate, stability, or engine-ordering inference is
claimed. The mx-driver taxonomy corners (success+empty-modelUsage
f=1; no rc=124 censoring branch) remain registered at the successor's
matrix derivation.

### Scorer self-tests (clause-isolating, reachable, synthetic 24-row; vectors pinned EXACTLY)

Notation: S = claude-sonnet-5, M1 = claude-opus-5,
M2 = claude-opus-4-8; I = `[2/5, 2/5, 2/5, 2/5]` (mean `2/5`,
interior 4); C = `[1, 2/5, 2/5, 2/5]` (mean `11/20`, interior 3);
U = `[4/5, 4/5, 4/5, 4/5]` (mean `4/5` > 3/5, interior 4);
L = `[0, 1/10, 1/10, 1/10]` (mean `3/40` < 1/10, interior 3);
N = `[1, 0, 2/5, 2/5]` (mean `9/20` in band, interior 2).

1. pair both-ceiling: M1=C, M2=C (ceiling on the SAME task), S=I —
   gates 1-2 pass for all three, ONLY gate 3 rejects. This is the
   gate-3 SCOPE isolator: an all-three-engine gate 3 would PROCEED
   here (S ≠ 1 on that task).
2. single matrix ceiling: M1=C, M2=I, S=I — PROCEED.
3. different-task dual ceiling: M1=`[1, 2/5, 2/5, 2/5]`,
   M2=`[2/5, 1, 2/5, 2/5]`, S=I — both means `11/20`, interiors 3,
   no shared ceiling task — PROCEED.
4. upper-band isolation ×3 (parameterized once per engine e ∈
   {S, M1, M2}): e=U, others=I — REJECT via gate 1 only.
5. lower-band isolation ×3: e=L, others=I — REJECT via gate 1 only
   (lower edge; gate 2 passes at interior 3).
6. interior isolation ×3: e=N, others=I — REJECT via gate 2 only
   (no matrix both-ceiling, so gate 3 untriggered).
7. sonnet-only ceiling tolerated: S=C, M1=I, M2=I — PROCEED (gate-2
   boundary).
8. both-floor tolerated: S=M1=M2=`[0, 2/5, 2/5, 2/5]` (mean `3/10`,
   interior 3) — PROCEED.
9. catastrophic carry: the 0107 one-rep pattern pinned on M1 task 1
   rep 1 (total=0 catastrophic ⇒ f=1; rep 2 `f=2/5` ⇒
   `q(M1,t1) = 7/10`), all other cells I-valued — PROCEED with the
   exact q asserted (no gate-3 fire: M2 interior on task 1).
10. complete-cell validation: missing cell ⇒ UNSCORED; duplicate cell
    ⇒ UNSCORED; wrong engine id (a NON-registered literal, not
    `claude-sonnet-5`) ⇒ UNSCORED.
11. determinism double-run byte-identical.
12. route-transient: an otherwise valid ledger with one
    `infra_invalid` row, cause `provider-signal`, and one with cause
    `zero-turn` ⇒ UNSCORED, `route == "transient"`.
13. route-non-transient: one `infra_invalid` row with cause
    `runner-integrity` ⇒ UNSCORED, `route == "non-transient"`.
14. route-mixed fail-closed: one `provider-signal` row PLUS one
    `task-seal` row ⇒ UNSCORED, `route == "non-transient"`.
15. route-missing-cause fail-closed, three isolated variants: one
    `infra_invalid` row with `infra_cause` (a) `null`, (b) the key
    ABSENT, (c) an unknown token (e.g. `"weather"`) ⇒ each UNSCORED,
    `route == "non-transient"`.

Additionally at derivation freeze: the driver taxonomy fixture set
runs once per exact ID (all three), unchanged case list from the 0107
freeze; the validator self-test suite (positive fixture + full tamper
set incl. `distance-near`, `distance-far`, `decoy-excess`) passes.

## Pre-registered prediction

- **P-0108-1**: the frozen scorer returns PROCEED. Falsifier: any
  valid scored REJECT. (Direction basis: the geometry knobs return
  toward the 0102-measured in-band regime while keeping repo mass;
  whether THIS composite geometry holds the band is the measurement.
  A REJECT in either direction — too hard or below-floor too easy —
  is a valid negative bounding the geometry claim.)

## Information boundary

Carried in kind from 0105/0107: this registration is FROZEN before any
0108 row content or score is read; per-task outcomes stay SEALED from
authoring; post-run exposure = one line (PROCEED/REJECT/UNSCORED) +
the decision-receipt digest. Sealed 0105/0107 per-task outcomes remain
sealed and are not inputs to design or apparatus. (The repo's
append-only `DECISIONS.md` entries are an authorized surface and are
distinct from lane receipt carriers.)

**Derivation is FILE-LEVEL** (SEALED CAUSAL ISOLATION, carried): lane
root `~/.local/share/nx01/iter0108/pilot/`. The ONLY readable prior
sources are the digest-pinned base files enumerated in § Apparatus
delta classes. Reading, listing, or copying the LANE-ROOT receipt
carriers of prior pilots — `~/.local/share/nx01/iter0105/pilot/
attempt-*`, `~/.local/share/nx01/iter0107/pilot/attempt-*`, their
`DECISION` / `DECISION.receipt.sha256` files, or any verdict/receipt
carrier — is PROHIBITED for every seat and writer in this lane.

## Sequencing

1. Registration R0 (done, folded) → R1 seat review → trio FREEZE →
   commit.
2. Tree re-geometry + apparatus derivation: terra single-writer,
   digest-pinned brief (the base files above ONLY), complete delta
   list + reversal proofs vs the EQ4P/0107/0105 bases;
   validator-green all four EQ4R trees; trio freeze audit
   (`FREEZE-0108-PILOTLAUNCH-{SOL,GROK}`; grok probe rounds
   STATIC-ONLY per the 0107 operational rule).
3. Launch: quiet account (operator rule, user-overridable), outside
   23:00-01:00 KST, same-day sequential exact-ID smokes for ALL THREE
   engines (pinned CLI, neutral dir), detached; 24 rows at 2 lanes ≈
   the 0105 pilot wall + the 0107 pilot wall (~2.5-3.5 h;
   informational, never a license to tighten `BOUND_SEC`).
4. Read ONLY `DECISION` + `DECISION.receipt.sha256`; trio verification
   (sol S-checks + grok G-checks, fresh adversarial seats); record
   verdict; successor registration is user-gated.

## Execution log

- **2026-08-22 — DRAFT + R0 folded.** Contested positions C1-C5
  staged; sol REVISE (8: 3 BLOCKER, 2 HIGH, 2 MED, 1 LOW) + grok
  GO-WITH-EDITS (12). Convergent syntheses ADOPTED C1-C5 in the
  draft's direction with named criteria: C1 FORCED
  MECHANISM-PRESERVING EASING / NON-VACUOUS-PIN (window + decoy
  non-dominance over distance-only, decoy-delete, and d=3-only-knob);
  C2 GATE-CONDITION INDEPENDENCE / ABSOLUTE-BAND BLOCK INDEPENDENCE
  (one-launch two-block; falsifier (c) unmet — time noise, not gate
  corruption); C3 SUCCESSOR-CONTRAST SUFFICIENCY / BILATERAL
  DIFFERENTIAL OBSERVABILITY (pair-scoped gate 3; all-three scope
  ADMITS the zero-contrast defeat case); C4 SEALED MATCHED-BASE
  ISOLATION / GEOMETRY-NOT-DOMAIN (EQ4P bases, uniform
  transformation); C5 FAIL-CLOSED TREATMENT IDENTIFIABILITY /
  NON-VACUOUS-PIN (ceiling required; floor-only fails falsifier (b) —
  every base tree would pass unmoved). Convergent folds applied:
  complete apparatus delta classes frozen at registration (sol 5 /
  grok 1 — the 0105 scorer-gap class); scorer deltas completed —
  `PILOT_TASKS`, gate-3 `MATRIX_ENGINES` iteration, wrong-engine
  literal, scenario identity (sol 2 / grok 2); validator positive-
  fixture + helper + tamper corollaries enumerated (sol 1 / grok 3,
  5); self-test vectors pinned exactly with per-engine parameterized
  isolators + lower-band vector + non-gate-3-firing cat case (sol 4 /
  grok 4); verdict-domain mechanical router registered (sol 3);
  L-R1 "regular-file bytes" rename (sol 6); evidence gloss rewritten —
  license = mass + exact-3 + non-dominance, NOT "mass alone"; "0102
  saturates" mis-gloss and "strictly-closer unsatisfiable" overclaim
  dropped; "decoy parity" renamed non-dominance (sol 7 / grok 6, 7,
  8); block-1 formula + drain-barrier cut frozen literally (grok 10 /
  sol 5); `REGISTERED_IDS` corpus block registered inert (grok 5);
  CLI pin path exact (grok 11 / sol 5). **Fable adjudications, named
  criteria**: distance pin = EXACT 3 uniform (NON-LOCAL MINIMUM —
  resolves grok 9's degeneracy demand and sol C1's mechanism-identity
  concern: d=2 at the frozen edit-site depth forces same-package or
  root placement, destroying non-locality; supersedes the draft's
  2-3 window); strictly-closer conjunct BYTE-CARRIED not deleted
  (SUBTRACTIVE-DELTA MINIMALITY — auto-satisfied under the pinned
  geometry, still tamper-exercised; the draft's deletion rationale
  was refuted by grok 8); sol 8 DECLINED with clarification
  (AUTHORIZED-SURFACE DISTINCTION — repo `DECISIONS.md` entries are
  the append-only public log, not lane receipt carriers; the
  prohibition wording now scopes lane roots explicitly). R0 logs:
  `/tmp/r0-0108/{sol,grok}.log` → archive at
  `~/.local/share/nx01/iter0108/registration/`.
- **2026-08-22 — R1.** grok `FREEZE-0108-REG-GROK` (12/12 closed;
  fables a-c accepted with independent arithmetic — d=2 vs d=3
  placement classes, self-test means/interiors, block formulas
  matched to bases, ≥10-artifact-pair arithmetic). sol REVISE ×1:
  the R0-3 router remained unimplementable — the base scorer reduces
  infra to `infra_invalid:<run_id>` in `reasons`
  (`score-pilot-0107.py:153`, `:203`) and the base driver marks
  runner-integrity/task-seal failures `infra_invalid=True` with the
  cause written ONLY to per-run stderr (`pilot-driver.py:175`,
  `:177`, `failed_row:102-113`) — non-transient apparatus failures
  ledger-indistinguishable from retriable rows. **Fable adjudication:
  SOL ADOPTED over grok's router-clause FREEZE** (named delta: the
  `:175/:177` reachability demonstration, orchestrator-verified at
  the bytes; criterion MECHANICAL ROUTE DECIDABILITY, 0105-r2
  precedent for sol-over-grok-FREEZE on demonstrated reachability).
  Folds: driver `infra_cause` contract (four causes,
  provider-signal precedence); scorer requires `infra_cause`, emits
  `infra_invalid:<run_id>:<cause>` reasons and a frozen `route` on
  UNSCORED (missing/unknown cause and mixed ledgers fail-closed
  non-transient); verdict-domain routes re-keyed to `route`;
  self-tests 12-15 added. All other R0 findings confirmed closed by
  both seats; sol accepted the sol-8 decline. R1 logs archived at
  `~/.local/share/nx01/iter0108/registration/`.
- **2026-08-22 — micro-pass round 1.** sol REVISE ×2, both adopted
  with orchestrator byte-verification: (1) the four-cause partition
  was NOT exhaustive — `infra_invalid=True` is also reachable at
  attestation-mismatch (`pilot-driver.py:135-136`), attempt-setup
  (`:187`), and runner-failure (`:223`) → cause contract extended to
  SEVEN tokens with the transient set pinned to exactly
  {`provider-signal`, `zero-turn`} and fail-closed default; (2)
  test 15 split into null / absent / unknown-token variants. grok's
  parallel micro-1 REVISE independently converged on the identical
  three unmapped sites (`:135-136`, `:187`, `:223`) — folded by the
  same amendment.
- **2026-08-22 — micro-pass round 2 → REGISTRATION TRIO-FROZEN.**
  sol `FREEZE-0108-REG-SOL` (seven-token partition verified
  exhaustive + disjoint at the bytes; transient set correct; no fold
  contradiction; both micro-1 residuals closed). grok
  `FREEZE-0108-REG-GROK` (independent site walk incl. rc=124 and
  oracle-cat non-infra confirmations; micro-1 finding closed).
  Registration frozen with fable adjudication. All round logs
  archived at `~/.local/share/nx01/iter0108/registration/`
  (r0/r1/micro1/micro2, packets + seat logs). NEXT = Sequencing
  step 2: terra single-writer apparatus derivation + tree
  re-geometry, trio freeze audit.
- **2026-08-22 — apparatus derived + fix round 1 + LAUNCH APPARATUS
  TRIO-FROZEN.** Terra single-writer derivation in four continuations
  (two lawful STOPs honored: lane-root sandbox permission →
  orchestrator-created root + writable-root grant; A3-before-B
  ordering defect in the orchestrator brief → B-first order
  authorized; A3 taxonomy fixture source → authorized inline from
  `0107-*.md:162-167`). All base digests verified; reversal proofs
  driver/validator/scorer PASS; four EQ4R trees validator-green with
  oracle parity FFFFF/FFFFF/TTFFF/TTTTT vs the EQ4P bases. Freeze
  audit r1: sol REVISE ×8 (BLOCKER freeze-digest mismatch;
  receipt-after-effect; launch.log symlink-alias mutable-freeze-root
  — probe-demonstrated; banner; reason grammar; two self-test
  isolation defects; manifest `tree_sha256` deletion; UA1 formatting
  deltas) / grok REVISE ×2 (banner — CONVERGENT with sol; test-12
  vector shape). Terra fix round F1-F8: banner → per-artifact natural
  prose weave (hits 12 ≥ 12 ≥ 10 re-measured by the validator);
  receipt fsync BEFORE Popen; per-run logs O_CREAT|O_EXCL|O_NOFOLLOW;
  digest chain rebuilt bottom-up; exact reason grammar; test 12 =
  one combined-transient ledger + membership-isolated wrong-engine;
  manifest `tree_sha256` restored; UA1 base formatting restored.
  Re-freeze: sol `FREEZE-0108-PILOTLAUNCH-SOL` (symlink probe re-run
  in temp, 584-file compile sweep) + grok `FREEZE-0108-PILOTLAUNCH-GROK`
  (static full walk). Final pins: validator `343ae7d0…` · scorer
  `1037bba3…` (repo pin `docs/specs/iter0108-pilot/scripts.sha256`) ·
  driver/launcher/gate + 14-row inventory `18a772e1…` in-lane · trees
  UA1 `ad9c364c…` MI1 `366470ef…` AF1 `e6e8415a…` BD1 `f453b957…` ·
  manifest `7f70b17a…` (tree_sha256 `a4424e80…`) · schedule
  `d02c08c0…`. Audit receipts:
  `~/.local/share/nx01/iter0108/pilot/audit/`. **LAUNCH HELD** at
  peer request: the pyx-memory-v1 session's X24 benchmark (~2.5-3h,
  shared account) — same protocol as 0107's X23 hold; its all-clear
  doubles as our quiet-account window.
