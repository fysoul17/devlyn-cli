# iter-0109 — repo-scale proximity-parity pilot

**Status: REGISTERED-FROZEN (trio: R0-R1 + micro ×6, double FREEZE 2026-08-23)**

## Why this iter exists (pre-flight 0)

0105 stacked three non-identity hardness axes onto the 0102-measured
in-band discovery shape: contract distance ≥4, decoy HIT dominance,
and decoy PROXIMITY dominance (12 registered decoy modules per tree
— law floor ≥10 — every one within parent-distance 2 of the edit
site and strictly closer than every contract artifact). 0107
falsified the engine-swap explanation; 0108 eased distance (exact-3)
and inverted hit dominance — and REJECTED with all three anchors
above the 3/5 upper bound (sonnet 4/5 · opus-5 7/10 · opus-4-8 7/8;
DECISIONS 0108.1). The proximity axis was BYTE-CARRIED through 0108
(`0108-*.md:146-156`; `validate-repo-task-0108.py:309-310` — every
registered decoy sits at parent-distance exactly 2, structurally
strictly closer than the exact-3 artifacts; measured live by R0).

This iter eases the PROXIMITY axis to parity and measures that ONE
contrast: repo mass (identity — closes the whole-fixture shortcut,
`0102-*.md:49-60`) + exact-distance-3 (NON-LOCAL MINIMUM, 0108 R0)
+ hit non-dominance (0108) + decoy PROXIMITY PARITY (new). What a
verdict licenses is THIS registered point only: PROCEED calibrates
the module at this exact geometry and unlocks the corpus successor;
a valid scored REJECT bounds this point — with count reduction
(12→floor or a re-litigated floor) and distance-2 (requires a new
edit-site-depth answer) remaining as unmeasured same-mechanism
knobs, and the 0103-alternative pivot as the preferred
research-efficiency successor reading (user-gated either way).
(R0 fold: sol 6 + grok 11, criterion CLAIM–MEASUREMENT MATCH /
ONE-AXIS CONTRAST — the prior draft's "minimal hardness / entire
easing space" claims are deleted as overclaims.)

**Adjudicated direction (user-delegated 2026-08-23).** Named
criteria: LAST-AXIS COMPLETION (proximity is the last axis of the
0105 stack with no measurement on the eased side; pivoting first
leaves "was the decoy axis ever eased?" unanswered); IDENTITY
PRESERVATION (mass-bisection rejected — re-opens the 0102 shortcut;
distance-2 rejected — 0108 R0 NON-LOCAL MINIMUM); APPARATUS REUSE
ECONOMY (enumerated deltas on trio-frozen 0108 machinery).

## Decisive criterion

Carried from 0108 (`0108-*.md:28-37`) with the dropped conjuncts
restored (R0 grok 9): FREEZE-worthy iff a fresh session could
execute it mechanically — every apparatus file derivable from the
enumerated bases + deltas alone, every self-test vector reachable
and pinned at registration, every gate mechanical, the registration
answering exactly one question, and every verdict routed without
orchestrator judgment.

## Registered treatment

**Prototype bases.** The four frozen EQ4R trees (UA1 `ad9c364c…` ·
MI1 `366470ef…` · AF1 `e6e8415a…` · BD1 `f453b957…`): domains, class
anchors, behavioral tuples, fragments, edit-site paths,
contract-artifact placements (exact-3), token weave, oracle,
patches, and root-level `generator-inventory.json`
(`validate-repo-task-0108.py:329-330`; R1 sol 7) carry
BYTE-UNCHANGED.
New IDs `EQ4S-{UA,MI,AF,BD}1` under
`TASKS_ROOT_PILOT = benchmark/executor-quality/tasks-0109-pilot`.

**The single re-geometry rule (canonical, non-discretionary; R0
fold of sol 2 + grok 2, criteria UNIQUE GEOMETRY-ONLY
IDENTIFIABILITY / SHELL-PARITY-WITHOUT-NEIGHBORHOOD-TRANSFER):**
per tree, let `<fn>` be the existing decoy directory name
(`field_notes` or `field_records`) under the edit-site top-level
package. Move EXACTLY the registered decoy modules (the
`decoy_artifacts.modules` list — 12 per tree) from
`visible/<editpkg>/<fn>/` to the NEW two-part parent
`visible/<fn>/`, byte-identical content (no rewrites — F1 bound).
Resulting decoy parent-distance from the edit site: up 2 + down 1 =
exactly 3 — the artifacts' shell, but NOT an artifact parent
directory and NOT under the edit-site package. Fail-closed
preconditions (terra lawful-STOP on violation): `visible/<fn>/`
must not pre-exist; the destination name must differ from every
contract-artifact parent directory name in that tree. Non-decoy
residents of the source directory stay in place (BD1
`accommodation_register.py` — `EQ4R-BD1/task.json:15` vs
`:202-214`); a source directory emptied by the move is deleted;
BD1's source directory survives with its non-decoy resident.
Registered metadata rewrites (closed list): `task.json`
`visible_files` + `decoy_artifacts.modules` path entries and
`hidden/generator-params.json` decoy path entries — byte-preserving
edits outside the changed path strings (F8); tree IDs EQ4R→EQ4S in
both files. The decoy Python import graph is EMPTY on all four
trees (R0-verified: no visible import targets a decoy) — the
derivation VERIFIES this no-op rather than editing imports.

### Law deltas (validator `validate-repo-task-0109.py`, derived from `343ae7d0…`)

1. **L-R1, L-R2″, L-R4, schema, generator-inventory law:
   byte-carried** (mass ≥120 visible files / ≥2,000,000 visible
   regular-file bytes; every contract artifact `.parent` at exactly
   3; two-fragment complementarity; three frozen fields).
2. **L-R3‴ (decoy proximity parity)**: the carried decoy-distance
   conjuncts (within parent-distance 2 AND strictly closer,
   `validate-repo-task-0108.py:309-310`) are REPLACED by
   `directory_distance(edit_site, decoy_module.parent) == 3` for
   EVERY registered decoy module — the SAME `.parent` primitive as
   L-R2″ (R0 grok BLOCKER 1 adopted, criterion PARENT-DISTANCE
   PRIMITIVE IDENTITY: a file-path-distance formula is vacuously
   satisfied by the unmoved bases). Fail-closed both sides; frozen
   reason string literally `decoy parent directory distance must be
   exactly 3`. Non-vacuous: every EQ4R base tree fails it (decoy
   parents at 2) until the move lands. Hit non-dominance (distinct
   decoy hits ≤ distinct contract-artifact hits) and the
   NEUTRALIZATION proof carry unchanged.
3. **Self-test corollary — COMPLETE closed list (R0 sol 3 + grok 3,
   5; R1 sol 3 + grok 1; every path pinned NOW, none deferred).**
   The fixture edit site is the two-part `visible/edit`
   (`validate-repo-task-0108.py:637`), so the TREE destination shape
   (two-part parent) is geometrically wrong for the fixture — the
   LAW is one (`.parent` distance == 3); the pinned destinations
   differ because edit-site depths differ. Positive fixture:
   `write_fixture` decoy emission (`:619` region) relocates fixture
   decoys from `visible/decoys/<mod>.py` to the LITERAL three-part
   parent `visible/decoys/shell/<mod>.py` (parent-distance from
   `visible/edit`: up 1 + down 2 = exactly 3), contents/hit counts
   unchanged. Helper retargets (path-only): `decoy-hit` (`:718`),
   `inventory-decoy` (`:729`), `collapse_module` (`:889-893`),
   `neutralization_collision_fixture` (`:907`),
   `add_decoy_excess` (`:971-973`), `make_decoy_semantic`
   (`:976-980`). Tampers with LITERAL frozen paths: NEW `decoy-near`
   (relocate fixture decoy `shell/decoy00.py` → `visible/decoys/`,
   parent-distance 2 → expect the frozen L-R3‴ reason string); NEW
   `decoy-far` (relocate it → `visible/decoys/shell/deep/`,
   parent-distance 4 → same string); the 0108 `decoy-distance`
   scenario is SUPERSEDED by this pair — validator scenario count =
   0108's count PLUS ONE (R1 sol 4 + grok 4; the prior "count
   unchanged" clause is deleted); `decoy-excess` carried with paths
   re-targeted. Fixture IDs EQ4R→EQ4S (`:670-671`). Every other
   0108 vector carried unchanged.
4. **ID re-target**: `REGISTERED_IDS` prototype block `EQ4R-*1` →
   `EQ4S-*1`; corpus block byte-carried and INERT.

Nothing else changes in the validator.

### Apparatus delta classes (frozen NOW; exact bytes reversal-proven at derivation)

Base files (the ONLY readable prior apparatus): 0108 driver
`0353fc2d…` / launcher `381c6d4c…` / launch gate `cdaddaf7…` /
scorer `1037bba3…` / validator `343ae7d0…` / `run-bounded.py`
`db9ed383…` / manifest `7f70b17a…` (shape base) + the four EQ4R
trees. 0105/0107/0108 lane-root RECEIPT carriers (attempt dirs,
DECISION*, ledgers, verdicts) are PROHIBITED — bases are apparatus
bytes and registration/audit docs only.

**Closed identity-delta list (R0 sol 5 + grok 4 — the 0105
scorer-gap class, enumerated exhaustively):**

- **driver** `pilot-driver.py`: docstring iter label; `TASKS_ROOT`
  → `tasks-0109-pilot`; manifest path + manifest digest +
  `MANIFEST_TREE_SHA256` constants → the sealed 0109 values.
  `ALLOWED_ENGINES`, taxonomy, and the seven-token `infra_cause`
  contract (transient = {`provider-signal`, `zero-turn`},
  fail-closed default) byte-carried.
- **launcher** `pilot-launcher-0109.py`: filename; docstring;
  `TASKS` → the four EQ4S IDs. Block formulas, drain barrier,
  2-lane split, `RUN_ID_RE` byte-carried.
- **validator/scorer repo copies**: filenames
  `validate-repo-task-0109.py` / `score-pilot-0109.py` in
  `benchmark/executor-quality/scripts/`, byte-identical to the
  apparatus copies.
- **scorer** `score-pilot-0109.py` from `1037bba3…`: `PILOT_TASKS`
  → EQ4S IDs; self-test scenario-identity string → the 0109 suite;
  self-test fixture IDs EQ4S. Bands, gates, q semantics, routes,
  `decision` emission strings (`PROCEED`/`REJECT`/`UNSCORED`), and
  the 15-scenario structure (test 12 stays ONE combined-transient
  ledger — F6) byte-carried.
- **NEW finalizer** `finalize-decision-0109.py` — apparatus-only,
  NO repo copy (R0 sol BLOCKER 1 adopted, criterion DECISION
  AUTHORSHIP MECHANIZATION; contract completed per R1 sol 1-2 +
  grok 2). FULL frozen contract:
  - placement: `apparatus/finalize-decision-0109.py`; in-script
    `HERE = its own parent (apparatus/)`, `LANE = HERE.parent` —
    the launcher's own convention (`pilot-launcher-0108.py:119`;
    micro1 grok 1). argv exactly `--attempt-dir <path>`; the path
    must resolve strictly inside `LANE` and match
    `attempt-<run_id>` with `run_id` matching the carried
    `RUN_ID_RE`; `attempt` is read from
    `<attempt-dir>/launch-receipt.json` key `"attempt"` (int 1..3);
    receipt `"run_id"` must equal the parsed run_id.
  - self- and input-attestation (micro1 sol 2): hashes ITS OWN
    on-disk bytes and requires equality with the launch receipt's
    `apparatus_sha256["apparatus/finalize-decision-0109.py"]`;
    computes the ledger sha256 BEFORE the first scorer run and
    again AFTER the second, requires equality (no mid-double-run
    mutation), requires the parsed verdict's own `ledger_sha256`
    field to equal that computed value (micro2 sol 1 — verdict and
    receipt must attest the same ledger bytes), and that value is
    the receipt's `ledger_sha256`.
  - verifies the on-disk `HERE/score-pilot-0109.py` digest against
    its own frozen constant, then runs
    `[sys.executable, HERE/score-pilot-0109.py, "--ledger",
    <attempt-dir>/pilot-ledger.jsonl]` TWICE; requires
    byte-identical stdout, equal exit codes, exit ∈ {0, 2, 3} with
    the frozen bijection 0=PROCEED / 2=REJECT / 3=UNSCORED; parses
    stdout as JSON and requires `verdict["decision"]` to match the
    bijection; on UNSCORED requires `verdict["route"]` ∈
    {"transient", "non-transient"}.
  - outputs, closed list of SIX names (micro1 sol 3 + grok 2):
    attempt-local `pilot-decision-verdict.json`,
    `pilot-decision-verdict.second.json`, `decision-receipt.json`,
    and (transient-nonfinal branch only) `RETRY_ALLOWED`; lane-root
    `DECISION`, `DECISION.receipt.sha256`. Transaction per file:
    write to `<name>.tmp` (O_CREAT|O_EXCL|O_NOFOLLOW), fsync, then
    publish via `os.link(tmp, target)` + `os.unlink(tmp)` — link is
    atomic no-replace (EEXIST on a pre-existing target), closing
    the check-then-rename race. Write ordering: ALL THREE
    attempt-local files first; then, terminal branch only,
    lane-root `DECISION.receipt.sha256` BEFORE `DECISION`
    (receipt-before-effect — a `DECISION` can never exist without
    its digest; the transient-nonfinal branch publishes
    `RETRY_ALLOWED` instead and never touches lane root). Any
    pre-existing target or tmp → fail-closed exit with nothing
    further written; a crash-truncated partial publication is
    surfaced, never auto-repaired.
  - `decision-receipt.json` = canonical sorted-key JSON + single
    trailing newline with EXACTLY these keys: `attempt`,
    `decision`, `double_run` (literal "byte-identical"),
    `exit_code`, `ledger_sha256`, `route` (null unless UNSCORED),
    `run_id`, `scorer_sha256`, `verdict_sha256` — the retry bit is
    digest-bound (R1 sol 1).
  - `DECISION` byte grammar: exactly
    `{"decision": "<PROCEED|REJECT>"}` + newline, or
    `{"decision": "UNSCORED", "route": "<transient|non-transient>"}`
    + newline (canonical sorted keys).
    `DECISION.receipt.sha256` = 64-hex sha256 of the receipt bytes
    + newline.
  - attempt-ladder mechanization (R1 sol 1): lane-root
    `DECISION` + digest are written iff the outcome is TERMINAL —
    decision ∈ {PROCEED, REJECT}, OR route == "non-transient", OR
    attempt == 3. For UNSCORED-transient with attempt < 3 the
    finalizer instead writes attempt-local `RETRY_ALLOWED` (same
    transaction rules); the relaunch path stays governed by the
    launch-gate rules (byte-identical digests, ordinal locks,
    attempt cap 3).
  - stdout channel PINNED (micro2 grok 1 — the orchestrator's only
    permitted read): exactly one line, the literal `TERMINAL`
    (terminal branch) or the literal `RETRY_ALLOWED`
    (transient-nonfinal branch); every diagnostic goes to stderr;
    scorer stdout is captured internally and never re-emitted.
  - deterministic, no network, no engine calls.
- **launch gate** `launch-detached.py`: `FROZEN` map re-keyed —
  closed list: `apparatus/pilot-driver.py`,
  `apparatus/pilot-launcher-0109.py`, `apparatus/run-bounded.py`
  (`db9ed383…` byte-carried), `apparatus/pilot-manifest.json`,
  `apparatus/validate-repo-task-0109.py`,
  `apparatus/score-pilot-0109.py`,
  `apparatus/finalize-decision-0109.py`,
  `repo/validate-repo-task-0109.py`, `repo/score-pilot-0109.py`,
  `pin/claude-2.1.226-iter0100` (`013a1cf1…`), four `tree/EQ4S-*`
  digests; `MANIFEST_TREE_SHA256`; PLUS the registered retry-ladder
  preconditions (micro1 sol 1; grammar micro2 sol 2 + grok 2;
  dead-end closure re-derived at micro3 — sol 1 + grok 1 proved
  ABSENCE-based routing unsound in both directions, so the gate now
  writes a POSITIVE witness, criterion POSITIVE-WITNESS ROUTING):
  (i) the gate REFUSES `--run-id ABORTED` at argv validation (micro4
  grok 1 — the literal matches `RUN_ID_RE`, so this exclusion is
  what makes the two lock payloads a true partition); (ii) refuse to
  launch when lane-root `DECISION` exists; (iii) ordinal lock N must
  be absent, and for `--attempt N > 1` lock N-1 must exist and route
  by content — content `<run_id>\n` (dispatched): that run's attempt
  dir must contain `RETRY_ALLOWED`, else refuse; content `ABORTED\n`
  (the gate's own no-child attestation): allowed; EMPTY or any other
  content (in-flight launch, hard crash, post-dispatch write
  failure, or unknown) → fail-closed refuse, surfaced, never
  auto-repaired. Lock byte grammar (the base lock is zero-byte):
  created empty O_CREAT|O_EXCL|O_WRONLY as carried; the gate's
  failure handler LATCHES DISPATCH (micro4 sol 1 + grok 2
  convergent): before `Popen` returns successfully, ANY failure —
  including a `Popen` raise, which means no child — writes exactly
  `ABORTED\n` + fsync into the still-empty lock before exiting
  nonzero; the instant `Popen` returns, the latch is set and
  `ABORTED` can never be written — a post-dispatch failure exits
  nonzero WITHOUT further lock writes (micro5 sol 1: the lock then
  holds either the complete `<run_id>\n`, which routes the
  dispatched branch — truthful, a child exists — or empty/partial
  bytes, which fail the full-match and refuse+surface). After
  successful `Popen` the gate writes exactly `<run_id>\n`
  (RUN_ID_RE payload, single trailing newline, no other bytes) +
  fsync. The N>1 parse reads the whole file and classifies
  ABORTED-FIRST (micro5 grok 1: `ABORTED` full-matches the carried
  `RUN_ID_RE`, so a run_id-first if-elif would classify the abort
  witness as a dispatched run and dead-end the allow-branch): test
  the literal `ABORTED\n` first — sound because the argv exclusion
  guarantees no real run carries that id — then a full-match of
  `<run_id>\n`; anything else refuses. REGISTERED CONSERVATISM (micro4 sol 2 observed;
  mechanism change declined, criterion ORDINAL-RECEIPT
  IMMUTABILITY): ABORTED launches consume ordinals — the cap is 3
  gate ordinals, not 3 dispatched runs; a lane that exhausts
  ordinals without a terminal `DECISION` (e.g. an ordinal-3 abort)
  ends BLOCKED-surfaced with no verdict, user-adjudicated. Aborts
  are apparatus failures, not measurement noise; reusing ordinals
  would weaken the immutable-lock receipt chain. Inventory filename
  `frozen-0109-apparatus.sha256` — FIFTEEN ordered rows =
  `set(FROZEN)` (14 keys: the 0108-equivalent 13 + the apparatus
  finalizer) ∪ {`launch-detached.py`}, the 0108 row order
  byte-carried with the single new
  `apparatus/finalize-decision-0109.py` row inserted immediately
  after the `apparatus/score-pilot-0109.py` row (R1 sol 5 + grok 3
  arithmetic); engines receipt field, 24-row schedule
  digest, ordinal locks, attempt cap 3, `start_new_session`,
  receipt-fsync-before-`Popen` (F2), `O_CREAT|O_EXCL|O_NOFOLLOW`
  logs (F3) all carried.
- **manifest**: same shape; per-file map over the four EQ4S trees;
  canonical task-map digest; top-level `tree_sha256` REQUIRED (F7).
- **repo pin file** `docs/specs/iter0109-pilot/scripts.sha256`:
  TWO rows — validator, scorer (the finalizer is apparatus-only,
  like the driver and launcher; R1 sol 5 + grok 3).
- **Non-deltas byte-carried**: CLI pin
  `~/.local/share/nx01/pins/claude-2.1.226-iter0100/claude`
  (`013a1cf1…`), `BOUND_SEC = 1800`, `EFFORT = "high"`, `TOOLS`,
  prompt = task goal only, scrubbed env, opaque workdir
  (OUTCOME-INDEPENDENT CENSORING CONTROL).

**Derivation conservation proofs (R0 sol 7 + grok 10, C5 syntheses
SEMANTIC CONSERVATION UNDER REVERSAL / REVERSAL-UNIQUE PLACEMENT —
the brief pins all of):** per-tree old→new path map (12 moves) +
emptied-dir deletions + BD1 remainder; decoy import-graph
emptiness VERIFIED (no invented import edits); decoy contents
byte-identical (F1 — no token rewrites); `task.json` /
`generator-params.json` edits byte-preserving outside the
enumerated strings (F8); L-R1 no-shrink (visible file count and
byte sum unchanged by moves; ≥120 / ≥2,000,000 re-measured); hit
counts re-measured 12 = 12 per tree; oracle parity
FFFFF/FFFFF/TTFFF/TTTTT; per-tree digests; manifest per-file map +
canonical digest + `tree_sha256`; bottom-up digest-chain recipe
covering apparatus AND repo copies AND the gate self-entry AND the
15-row inventory (F4).

## Decision rule (frozen; scorer implements verbatim — byte-carried from 0108)

Engines = (claude-sonnet-5, claude-opus-5, claude-opus-4-8); MATRIX
= (claude-opus-5, claude-opus-4-8). PROCEED iff: (1) every engine
mean(q) ∈ [1/10, 3/5]; (2) every engine ≥3 of 4 prototypes
interior; (3) no prototype with both MATRIX engines at q == 1.
Valid complete ledger failing any gate → terminal
`PROXIMITY_PARITY_REJECTED`: this registered point is unusable; no
in-lane retuning; any successor is a NEW user-gated registration.
The UNSCORED transient/non-transient router carries unchanged (max
3 attempts on byte-identical digests for all-transient).

## Pre-registered prediction

- **P-0109-1**: the frozen scorer returns PROCEED. Falsifier: any
  valid scored REJECT. (Direction basis: the proximity axis is the
  last 0105-stack axis with no eased-side measurement; the 0102
  parent geometry measured in-band with no proximity dominance. A
  REJECT is a valid negative bounding THIS point — exact-3 + parity
  + 12 decoys + identity mass — with count reduction and
  distance-2 remaining unmeasured same-mechanism knobs and the
  0103-alternative pivot the preferred research-efficiency
  successor reading.)

## Information boundary

Carried from 0108 with the widenings NAMED (R0 sol 8 + grok 12; R1
sol 6): registration FROZEN before any row content; per-task
outcomes SEALED; post-run orchestrator exposure = the finalizer's
pinned one-line stdout (literal `TERMINAL` or `RETRY_ALLOWED` —
micro2 grok 1) + the `DECISION` line (decision token, plus `route`
iff UNSCORED — route exposure is part of the registered surface) +
the `DECISION.receipt.sha256` digest; the abstract per-engine
diagnosis (mean value + side,
interior count, both-ceiling present/absent) is delivered by the
TRIO-VERIFICATION seat returns in sequencing step 4 — the channel
0108 established — never by reading ledgers or verdicts directly.
Lane root
`~/.local/share/nx01/iter0109/pilot/`. Reading lane-root receipt
carriers of ANY prior pilot (iter0105/0107/0108) is PROHIBITED for
every seat and writer.

## Sequencing

1. Registration R0 (done, folded) → R1 seat review → trio FREEZE →
   commit.
2. Terra single-writer apparatus derivation + tree re-geometry
   (digest-pinned brief, bases above ONLY), complete delta list +
   reversal + conservation proofs; validator-green all four EQ4S
   trees; trio freeze audit
   (`FREEZE-0109-PILOTLAUNCH-{SOL,GROK}`; grok STATIC-ONLY).
3. Launch: quiet account (user-overridable), outside 23:00-01:00
   KST, same-day sequential exact-ID smokes for ALL THREE engines
   (pinned CLI, neutral dir), detached; 24 rows at 2 lanes.
4. Run the frozen finalizer. If it prints `RETRY_ALLOWED`
   (UNSCORED-transient, attempt < 3): relaunch per the carried gate
   rules on byte-identical digests, quieter window. On a terminal
   outcome: read ONLY `DECISION` + `DECISION.receipt.sha256`; trio
   verification (fresh adversarial seats); record verdict;
   successor is user-gated.

## Execution log

- **2026-08-23 — R0 folded.** sol REVISE ×9 (3 BLOCKER, 3 HIGH,
  2 MED, 1 LOW) + grok REVISE ×12 (3 BLOCKER, 3 HIGH, 5 MED,
  1 LOW). Convergent adoptions: canonical destination function +
  closed metadata-rewrite list (sol 2 / grok 2); complete self-test
  site enumeration pinned at registration (sol 3 / grok 3, 5);
  closed identity-delta + FROZEN-map lists (sol 5 / grok 4);
  F-class conservation pins — F4 chain recipe, F7 `tree_sha256`,
  F8 byte-preserving edits, F1 no-rewrite bound (sol 4 / grok 6,
  12); overclaim deletions + retitle to proximity-parity + terminal
  rename `PROXIMITY_PARITY_REJECTED` (sol 6 / grok 11); info-
  boundary widening named (sol 8 / grok 12); decisive-criterion
  conjuncts restored (grok 9); citation fixes 146-156, live count
  12, proximity phrasing (sol 9 / grok 7, 8). Fable adjudications,
  named criteria: grok BLOCKER 1 ADOPTED — L-R3‴ re-pinned to the
  `.parent` primitive (PARENT-DISTANCE PRIMITIVE IDENTITY; the
  draft file-path formula was vacuous on the unmoved bases, the
  0108 C5 NON-VACUOUS-PIN class); sol BLOCKER 1 ADOPTED — frozen
  finalizer joins the apparatus (DECISION AUTHORSHIP MECHANIZATION;
  the 0108 hand-authored DECISION was an unfrozen gap); C1 resolved
  by the convergent syntheses (destination = new two-part parent
  `visible/<fn>/`, neither edit-site package nor artifact parents);
  C2 carry 12 (SINGLE-AXIS ATTRIBUTION); C3 single point, ladder
  only on UNSCORED (TERMINAL-INFORMATIVENESS); C4 pivot stated as
  preferred reading, never auto-action (EVIDENCE-PROPORTIONAL
  SUCCESSOR / SEALED SUCCESSOR-LICENSE); C5 conservation-proof list
  frozen (SEMANTIC CONSERVATION UNDER REVERSAL). R0 logs:
  `~/.local/share/nx01/iter0109/registration/`.
- **2026-08-23 — R1 folded.** sol REVISE ×7 (3 BLOCKER, 3 HIGH,
  1 MED; R0 findings 1/3/5/8 still OPEN) + grok REVISE ×4
  (3 BLOCKER, 1 MED; grok R0 all closed except 3). Convergent
  adoptions, all folded: (1) fixture analogue was geometrically
  impossible — the two-part fixture edit site `visible/edit` makes
  every two-part destination parent-distance 2; fixture decoys now
  pin LITERALLY to `visible/decoys/shell/` with literal `decoy-near`
  / `decoy-far` tamper paths, `add_decoy_excess` added to the
  helper list, and scenario count corrected to 0108+1 (sol 3, 4 /
  grok 1, 4 — criterion DEPTH-RELATIVE DESTINATION: one law, two
  pinned destinations because edit-site depths differ). (2)
  Finalizer contract completed to unique derivability: argv/HERE
  confinement/RUN_ID_RE parse, receipt-attempt cross-check, scorer
  `--ledger` argv + exit bijection {0,2,3} + decision/route schema
  validation, closed output list with exact-key canonical receipt
  (route digest-bound), DECISION byte grammar, tmp+fsync+rename
  transaction with ordering semantics, and the attempt-ladder
  (terminal-only lane-root publish; UNSCORED-transient non-final →
  `RETRY_ALLOWED`) (sol 1, 2 / grok 2). (3) Inventory arithmetic
  fixed: finalizer apparatus-only, FROZEN 14 keys, inventory 15 =
  set(FROZEN) ∪ {gate}, 0108 row order with pinned insert position,
  repo pin file back to TWO rows (sol 5 / grok 3). (4) Info
  boundary made executable: route exposure registered; abstract
  diagnosis channel = trio-verification returns only (sol 6). (5)
  `generator-inventory.json` path corrected to root-level (sol 7).
  Logs archived at `~/.local/share/nx01/iter0109/registration/`.
- **2026-08-23 — micro-pass 1 folded.** sol REVISE ×3 (all BLOCKER;
  R1 findings 1-2 OPEN) + grok REVISE ×2 (1 BLOCKER, 1 HIGH; grok
  R1 all closed). Convergent adoptions: (1) finalizer placement
  contradiction fixed — `HERE = apparatus/`, `LANE = HERE.parent`,
  attempt-dir confined to LANE, scorer at `HERE/` (grok 1, the
  launcher's own convention); (2) retry ladder ENFORCED at the
  gate — two registered preconditions: no launch when lane-root
  `DECISION` exists; attempt N>1 requires ordinal lock N-1 whose
  recorded run_id resolves to an attempt dir containing
  `RETRY_ALLOWED`, ordinal N absent; ordinal-lock format gains the
  run_id line (sol 1); (3) receipt-chain integrity completed —
  finalizer self-attests against the launch receipt's apparatus
  map; ledger sha256 computed before run 1 and after run 2 with
  required equality (sol 2); (4) transaction made coherent — closed
  list of SIX names incl. conditional `RETRY_ALLOWED`, all-three
  attempt-local before lane-root, `DECISION.receipt.sha256` before
  `DECISION` (receipt-before-effect), publication via
  `os.link`+`unlink` atomic no-replace, partial publication
  surfaced never auto-repaired (sol 3 / grok 2); (5) sequencing
  step 4 gains the RETRY_ALLOWED branch (grok 2). Logs at
  `~/.local/share/nx01/iter0109/registration/`.
- **2026-08-23 — micro-pass 2 folded.** sol REVISE ×3 (all BLOCKER;
  micro1 finding 2 OPEN) + grok REVISE ×2 (1 BLOCKER, 1 HIGH; grok
  micro1 both closed). Adoptions: (1) finalizer requires the parsed
  verdict's `ledger_sha256` to equal the independently computed
  before/after digest — verdict and receipt attest the same ledger
  bytes (sol 1); (2) ordinal-lock byte grammar pinned — created
  empty as carried, `<run_id>\n` written + fsync only AFTER
  successful Popen, whole-file full-match parse (sol 2 / grok 2
  convergent); (3) ladder dead-end closed — N>1 routes by lock
  content: non-empty ⇒ RETRY_ALLOWED required; EMPTY ⇒ allowed iff
  no launch-receipt records attempt N-1 (receipt-before-Popen
  proves no child), all other states fail-closed surfaced (sol 3);
  (4) finalizer stdout pinned to the literals
  TERMINAL/RETRY_ALLOWED, diagnostics to stderr, scorer stdout
  never re-emitted, and the info-boundary permitted surface now
  names that channel (grok 1). Logs at
  `~/.local/share/nx01/iter0109/registration/`.
- **2026-08-23 — micro-pass 3 folded.** sol REVISE ×1 (BLOCKER) +
  grok REVISE ×1 (BLOCKER) — the two seats refuted the empty-lock
  branch from OPPOSITE directions: sol showed EMPTY + no-receipt is
  also the live in-flight setup state (concurrent relaunch race);
  grok showed EMPTY + receipt spans both a Popen raise (no child)
  and the live post-Popen pre-write window, so absence-based
  routing is unsound both ways. Fable adjudication: replace
  absence-based routing with a POSITIVE witness (criterion
  POSITIVE-WITNESS ROUTING) — every gate step after lock creation
  runs under a failure handler that writes `ABORTED\n` into the
  still-empty lock before exiting nonzero (a Popen raise means no
  child, so ABORTED is truthful there); lock content routes N>1:
  `<run_id>\n` ⇒ RETRY_ALLOWED required, `ABORTED\n` ⇒ allowed,
  EMPTY/other ⇒ fail-closed surfaced (in-flight or hard crash — the
  only residual ambiguity, and it correctly refuses). The
  receipt-scan clause is deleted. Logs at
  `~/.local/share/nx01/iter0109/registration/`.
- **2026-08-23 — micro-pass 4 folded.** sol REVISE ×2 + grok REVISE
  ×2 (both BLOCKER); micro3 findings both CLOSED. Adoptions:
  (1) DISPATCH-LATCH TRUTHFULNESS (sol 1 + grok 2 convergent) — the
  abort handler latches the instant Popen returns; post-dispatch
  failures (including the run_id write/fsync) leave the lock EMPTY,
  which refuses and surfaces, so ABORTED can never falsely attest
  no-child; (2) PAYLOAD PARTITION (grok 1) — the literal ABORTED
  full-matches RUN_ID_RE, so the gate now refuses `--run-id
  ABORTED` at argv validation, making the two payloads disjoint
  without parse-order ambiguity. DECLINED with registered rationale
  (sol 2, criterion ORDINAL-RECEIPT IMMUTABILITY): ABORTED launches
  consume ordinals by design — the cap is 3 gate ordinals; an
  ordinal-exhausted lane without a terminal DECISION ends
  BLOCKED-surfaced, user-adjudicated; ordinal reuse or a separate
  dispatch counter would weaken the immutable-lock receipt chain
  for a rare² apparatus-failure scenario (fail-closed conservatism
  is the registered semantic, now explicit in the gate clause).
  Logs at `~/.local/share/nx01/iter0109/registration/`.
- **2026-08-23 — micro-pass 5 folded.** sol REVISE ×1 + grok REVISE
  ×1; all micro4 findings otherwise CLOSED (the sol-2 registered
  decline accepted). Adoptions: (1) the post-dispatch-failure
  clause corrected — the gate exits without further lock writes,
  and the lock then holds either the complete `<run_id>\n` (routes
  the dispatched branch, truthful) or empty/partial bytes (fails
  the full-match, refuses and surfaces) — the prior "leaves the
  lock EMPTY" wording was factually wrong for a landed write with
  failed fsync (sol 1); (2) N>1 classifier pinned ABORTED-FIRST —
  `ABORTED` full-matches the carried RUN_ID_RE, so run_id-first
  ordering would dead-end the allow-branch; ABORTED-first is sound
  because the argv exclusion guarantees no real run carries that id
  (grok 1). Logs at `~/.local/share/nx01/iter0109/registration/`.
- **2026-08-23 — micro-pass 6 → REGISTRATION TRIO-FROZEN.** sol
  `FREEZE-0109-REG-SOL` (micro5 finding CLOSED) + grok
  `FREEZE-0109-REG-GROK` (micro5 finding CLOSED, no new defects).
  Registration frozen after R0 + R1 + six micro-passes (finding
  counts 9→7→5→2+2→1+1→0; every fold group seat-verified at the
  bytes). All round logs archived at
  `~/.local/share/nx01/iter0109/registration/`. NEXT = Sequencing
  step 2: terra single-writer apparatus derivation + tree
  re-geometry, trio freeze audit.
- **2026-08-23 — apparatus derived + fix round 1 + LAUNCH APPARATUS
  TRIO-FROZEN.** Terra single-writer derivation in ONE continuation
  (31 min; the 0108 STOP classes pre-empted by orchestrator-created
  lane root + writable-root grant): all base digests verified;
  reversal proofs for every derived script byte-match the 0108
  bases; four EQ4S trees re-geometried by the canonical rule (12
  decoys per tree → `visible/<fn>/`; BD1 non-decoy remainder in
  place) and validator-green with conservation proofs (12=12 hits,
  L-R1 no-shrink, decoy bytes identical, import-graph no-op, oracle
  parity FFFFF/FFFFF/TTFFF/TTTTT); NEW `finalize-decision-0109.py`
  implements the full frozen contract. Freeze audit r1: sol REVISE
  ×4 (HIGH finalizer argv grammar — `=` form + duplicate options
  accepted, probe-demonstrated; 3 LOW stale docstring identities) /
  grok FREEZE (static full walk; checklist 7/7). Terra fix round
  F1-F4 + bottom-up chain re-pin; re-audit double FREEZE:
  `FREEZE-0109-PILOTLAUNCH-SOL` (argv rejection re-exercised in
  temp) + `FREEZE-0109-PILOTLAUNCH-GROK`. Final pins: validator
  `4be94c41…` · scorer `3d84d3c8…` (repo pin
  `docs/specs/iter0109-pilot/scripts.sha256`) · finalizer
  `94494e51…` · driver `50140a3a…` · launcher `27daee35…` · gate
  `cd04c405…` · 15-row inventory `ce6c3b6e…` · manifest `f46bdd2f…`
  (tree_sha256 `8ff48c3a…`) · trees UA1 `99adbf6b…` MI1 `b6ba7a36…`
  AF1 `904c771d…` BD1 `e89dfb25…`. Audit receipts:
  `~/.local/share/nx01/iter0109/pilot/audit/`. NEXT = launch
  (quiet account, outside 23:00-01:00 KST, three-engine smokes).
- **2026-08-25 — LAUNCH + pilot complete + TERMINAL (session 8).**
  Launch deferred 2026-08-23 by the user (usage-limit economy);
  resumed on user go-ahead. Cross-session coordination per
  START-HERE: 4 peer sessions live at resume; pyx-memory-v1 X27
  window ACTIVE → user pre-adjudicated wait-for-all-clear over
  immediate fire → HOLD ~40 min until the X27 close packet commit
  + all-clear message; pyx-www resolve pipeline held between
  phases on request (resumed after matrix completion); final
  headless scan clean; git clean; 01:47 KST (outside the
  23:00-01:00 window). Smokes 3/3 exact-ID (pinned CLI, neutral
  dir, `modelUsage` keys exact). Fired `pilot1-20260824T164713Z`
  attempt 1 detached; gate self-audit passed — launch receipt
  apparatus map byte-matches all 15 frozen pins. 24/24 valid rows
  in ~24 min (infra 0, rc=124 0, attestation 24/24 exact-ID;
  fast wall verified authentic = fast failure, 0108 precedent).
  Frozen finalizer: argv exactly two tokens, stdout literal
  `TERMINAL`; lane-root `DECISION` = `{"decision": "REJECT"}`,
  receipt `ecf2b587…`; decision-receipt: scorer double-run
  byte-identical exit 2, ledger `e5c408eb…`, verdict `904d5a10…`,
  attempt 1, route null. Trio verification:
  `VERIFY-0109-PILOTRUN-SOL: PASS` (S1-S8; scratch scorer replay
  ×2 byte-identical to BOTH verdict files, independent
  exact-Fraction recomputation licenses REJECT, at-bound mean
  in-band under rule text AND scorer, row authenticity vs fast
  wall confirmed at 2-lane concurrency) +
  `VERIFY-0109-PILOTRUN-GROK: PASS` (G1-G5 static; digest strings
  fully consistent, independent fraction arithmetic, per-row wall
  65-188s sums consistent, 24/24 real CLI payloads with unique
  session ids). Convergent abstract diagnosis: sonnet mean 37/40
  ABOVE 3/5 + interior 1/4; **opus-5 mean exactly 3/5 = IN-BAND
  (inclusive bound) + interior 3/4 — the first in-band anchor in
  the 0105 lineage — failing ONLY the matrix both-ceiling
  conjunct**; opus-4-8 mean 7/8 ABOVE + interior 2/4; matrix
  both-ceiling PRESENT; catastrophic rows 5 (count only). One
  seat relaunch (sol first attempt died on the known non-git-cwd
  codex trust refusal; scratch `git init` + relaunch). EXPOSURE
  DEVIATION (disclosed): while locating the DECISION artifacts
  the orchestrator read `decision-receipt.json` and
  `pilot-decision-verdict.json`, and the completion watcher's log
  tail surfaced 4 ledger rows — exceeding the registered post-run
  exposure (finalizer stdout + DECISION + digest). Per-task
  mappings are excluded from every narrative surface; any
  successor registration must weigh this orchestrator exposure at
  derivation isolation (0105-seal precedent).
- **DECISION (terminal): `PROXIMITY_PARITY_REJECTED`.** P-0109-1
  falsified by a valid scored REJECT — the registered point
  (exact-3 + proximity parity + 12 decoys + identity mass) is
  unusable; no in-lane retuning. Fourth consecutive too-hard-side
  bound in the lineage (0105 sonnet / 0107 frontier pair / 0108
  all three at eased knobs / 0109 proximity parity). NEW
  information vs 0108: the proximity easing moved opus-5 IN-BAND
  for the first time (at-bound mean + interior 3/4, blocked only
  by one shared both-ceiling prototype) while sonnet's mean moved
  FURTHER above (37/40 vs 0108's 4/5) — reading (interpretation,
  not measurement): the axis is live for the frontier anchor but
  not monotone across anchors; trees differ between registrations
  so cross-lane deltas are directional only. Successor is a NEW
  user-gated registration — registered preferred
  research-efficiency reading is the 0103-alternative pivot;
  count reduction and distance-2 remain the unmeasured
  same-mechanism knobs.
