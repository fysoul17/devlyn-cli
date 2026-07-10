# iter-0068 — discriminating ceiling corpus (bare-fails gate + categorical-reliability trap tasks)

status: PRE-REGISTERED 2026-07-08 (R0 GO-WITH-EDITS folded); **AMENDED
2026-07-10 before any gate run** (three-way fold: R0-grok GO-WITH-EDITS +
R1-codex CONVERGED — see Pair rounds); **implementation IN PROGRESS
2026-07-10 (Fable orchestrating, Codex executing, Grok third reviewer —
user directive)**; a first slice was started 2026-07-08 then rolled back
unverified (see Execution record → RESUME HERE). Corpus freezes (with the bare-fails gate results) before any
A/C arm runs. Direction chosen by user 2026-07-08 (corpus pivot,
option A) after the iter-0067 verdict + iter-0068-STUB A-arm decomposition.
**This is a categorical-trap CALIBRATION pilot on synthetic fixtures, NOT
real-shaped ceiling evidence** (R0 SHOULD-FIX 3; NORTH-STAR requires
real-shaped holdout for ceiling claims — F-fixtures are shared-test-repo
toys). Its job: prove the discriminating instrument (bare-fails gate +
generic FS oracle) works and produce a first pilot signal, not a ceiling
quality claim.

**Serves**: Mission 1 ceiling axis / ops test #17. iter-0067 FAIL-pilot on 3
saturated SWE rows proved the ceiling corpus was measuring the pipeline
where a single agent already excels (all rows objective-non-discriminating,
no moat, 8.33× wall). This iter fixes the corpus so the ceiling can answer
the question that actually matters: **does the pipeline earn its wall where
its designed value lives — the categorical-reliability classes bare
systematically fails?**

## Why this exists (pre-flight 0)

One sentence: this iter builds the FIRST discriminating ceiling corpus — one
where bare single-shot codex is MEASURED to fail — so the next ceiling
go/no-go decision is made on tasks where the harness can plausibly win,
instead of on saturated tasks where no honest positive is even possible.
Measurement iter, permitted as the attribution run before the wall/claim
policy call (PRINCIPLES #0 carve-out). (The original "unlocks iter-0069"
framing is stale — iter-0069 became the completion-claim investigation,
CLOSED 2026-07-09; this iter unlocks the NEXT wall-vs-value decision.)

## The core defect it fixes (from iter-0067 + the STUB decomposition)

All three tranche-2 rows were objective-non-discriminating (SW3/SW5
all-solve, SW4 all-fail). On such a corpus, LC1/LC2 objective lift is
structurally 0 and the verdict can only be negative or vacuous. The A-arm
wall (`iter0068-attack-the-wall-STUB.md`) is dominated by pair-VERIFY
(488-800s; pair_judge agreed with primary 3/3, never changed a verdict) and
orchestrator correction-loop gaps — but shaving that wall on tasks the
pipeline cannot win is the wrong mountain. The fix is upstream: **measure on
tasks where bare fails.**

## Design (first-principles commit; R0 to stress-test)

### Instrument innovation — the bare-fails gate (the load-bearing new piece)

A candidate row is ADMITTED to the discriminating tranche only if oracle
smoke shows BOTH:
1. **gold reference PASSES** the hidden objective oracle (existing
   oracle-smoke check), AND
2. **bare single-shot codex produces exactly 3 VALID attempts and 0/3
   resolve** (the discrimination gate; amended 2026-07-10, R0-grok +
   R1-codex folded — estimator alignment: the verdict compares against
   `best_B`, so admission must mean `best_B` fails, not majority-fail).

**Attempt validity is end-to-end**: invocation (bounded invoke exit 0, no
timeout), workspace materialization, patch apply, AND oracle runtime all
succeed or legibly fail the task — oracle semantics are pass/fail/INVALID,
and an oracle-runtime crash (e.g. uv panic) is INVALID, never "bare failed".
A successful zero-diff attempt IS a valid unresolved attempt (a genuine
model failure) unless transport evidence says otherwise (iter-0067
conjunctive-signature precedent). Fewer than 3 valid attempts →
`INVALID/PENDING` (re-run the invalid slots); a row is NEVER admitted on
infra evidence.

A row where any valid bare attempt resolves is REJECTED with reason
`saturated:bare-resolves` (FS1 is the built-in positive control — it must
be rejected: bare solved it 14/14 hidden tests in tranche-1). A row where
gold fails is `oracle-invalid` (existing).
This is the direct corpus-informativeness fix the iter-0067 verdict demanded:
the corpus can no longer admit a saturated row.

### Substrate — reuse the ceiling harness (0064/0067), add the gate

The ceiling harness already has 3-arm (devlyn/bare/copycat) + blind neutral
judge (de-biased in 0067) + wall/LC1-LC4 + oracle smoke + per-instance
oracle gate + manifest-derived allowlist. The only additions: the bare-fails
admission gate at corpus-freeze, and FS-format task packaging for the trap
tasks.

### Task source — a candidate POOL the gate selects from (R0 MUST-FIX 3)

**Do NOT hand-pick which fixtures discriminate** — R0 showed my first pick
(F7, F11) was already measured non-discriminating for bare-Claude (F7 bare
99/solo 100 6/6 pass, `F7/NOTES.md:50-53`; F11 bare 98/solo 97,
`F11/NOTES.md:67-70`), so the bare-fails gate would have rejected them and
left an empty tranche. The design innovation IS the gate; let it select.

Port a POOL of ≥5 diverse-class trap fixtures to ceiling FS-format, then let
the **bare-fails gate (bare-CODEX N=3)** admit whichever discriminate. Each
must carry (a) a named categorical-reliability class and (b) a plausible
harness mechanism that would catch it (R0 POS-1 synthesis). Candidate pool
(strongest recorded discrimination first): **F21-cli-scheduler-priority**
(ordering-inversion → risk-probe/VERIFY ordering; strongest recorded
discrimination `F21/NOTES.md:23-27`), **F25-cli-cart-promotion-rules**
(shape/compound), **F26-cli-payout-ledger-rules**, **F11-batch-import**
(atomic-state), **F12-webhook-raw-body-signature** (auth-signature),
**F7-out-of-scope-trap** (scope), and **F23-cli-fulfillment-wave**
(allocation/FEFO/priority-rollback). F23 is the pre-registered seventh row:
the original six omit its allocation class, and only three carry low-bare
provenance against L4's ≥3-admitted-class bar, so it adds class-coverage slack
without forcing an admission or relaxing the unchanged gold-pass + 0/3-valid-
bare-resolves gate. The pool is frozen; admission is data.
- **Control: FS1** (schedule max_runs) — known bare-passes (14/14 hidden
  TESTS, B1; R0 SHOULD-FIX 4 wording); MUST be rejected by the gate.

**F7 port correction (R0 MUST-FIX 2)**: if F7 is admitted, its trap is NOT a
cross-file edit — the bait is a planted region INSIDE `bin/cli.js` while
`version` must also change there, and the `hello` subcommand behavior must
be preserved (`F7/setup.sh:13-35`, `F7/expected.json:45-54`). The oracle
asserts version-json works AND `hello` unchanged AND the planted
same-file snippet preserved — a byte-preservation/finish-gate class, not the
cross-file scope gate.

Pilot admits whatever the gate passes (could be 0). **Pilot-signal-only
(R0 SHOULD-FIX 1)**: ≥3 distinct categorical classes must be admitted before
any "the instrument discriminates" claim; fewer = plumbing-validated only.
0 admitted = the honest finding "even categorical-trap fixtures don't
discriminate bare-codex" (a deep result worth reporting).

**Port mechanics (for R0 to judge fidelity)**: each F-fixture today is
`setup.sh` (stages a base repo state + node verifier scripts) +
`expected.json` (verification_commands + forbidden_patterns) on the shared
`test-repo/`. The FS-format port packages the fixture's pre-task state as a
standalone git repo, commits it → `base.json {repo:local-path, sha}`, and
converts the `expected.json` verifiers into ONE hidden oracle
(`hidden/oracle.sh` or `.js`, semantics pass/fail/INVALID) that boots the
app and asserts the same state (F11: failed-batch-leaves-store-unchanged +
all-valid-succeeds; F7: version-json-works + `hello` unchanged +
planted-same-file-snippet preserved, per MUST-FIX 2). **Oracle fidelity
contract (2026-07-10 amendment — criterion: pass-set equivalence)**: the
oracle must encode every load-bearing behavioral verifier, regression
check, AND class-defining `forbidden_patterns` disqualifier (or a
documented semantic equivalent) — a thin oracle that gold happens to pass
is not a port. Gold smoke = `hidden/reference.patch` resolves on N≥2
identical runs (artifact-backed), AND a base/no-op patch must FAIL the
oracle. The visible `task.txt` is the de-leaked spec
(F7's "Only touch bin/cli.js…" scope line stays visible — it IS the trap;
F11's "all-or-nothing" phrasing is softened so bare is not handed the
answer). The ceiling FS eval already runs an arbitrary hidden oracle
against a cloned+patched repo (FS1 precedent), so no eval-engine change —
only the oracle must be self-contained and language-present in the repo
(node, already there).

### Arms / judge / LC — unchanged from 0067 except benchmark codex seat = terra

3-arm (A devlyn = sonnet orch + codex executor + pair-verify; B bare codex;
C copycat codex), N = round(wall_A/wall_B) capped [1,3], neutral blind judge
(sonnet+codex), LC1-LC4, objective-first. Test arms codex/sonnet only.

**Benchmark codex model = `gpt-5.6-terra` on ALL arms (seat correction,
2026-07-10, user directive).** The measured arms must NOT use the user's
global `~/.codex/config.toml` default (`gpt-5.6-sol`) — sol is reserved for
the three-way design/review team (Fable + codex-sol + Grok), never the
measured arms (avoids the expensive reviewer model leaking into the seat
under test, and keeps A/B/C model-fair). Wired without touching global
config: `run-ceiling-arm.sh` exports a benchmark-owned `CODEX_HOME`
(`external/codex-home-terra/`, gitignored, config.toml model=terra + auth
symlink) so the A-arm's nested resolve→codex IMPLEMENT loads terra, and pins
`-m gpt-5.6-terra` directly on the B/C `codex exec` (which `--ignore-user-config`).
Cohort identity now records requested-alias `gpt-5.6-terra` per bare attempt.
Follow-up: the neutral blind judge's codex seat must be pinned to terra too
before the A/C tranche runs (separate invocation, not through the arm
script) — it does not run in the admission gate.

## Predictions (frozen before implementation)

- **P1 (the gate discriminates)**: run the bare-fails gate over the frozen
  pool + FS1. FS1 is REJECTED (`saturated:bare-resolves`, ≥1 valid bare
  attempt resolves) — the gate's self-test. At least ONE pool fixture is
  ADMITTED (gold-pass AND 0/3 valid bare attempts resolve); the admitted
  set + every rejection reason is reported. If FS1 is admitted, the gate is mis-calibrated (L1). If ZERO
  pool fixtures admit, that is not a gate failure — it is the honest finding
  that categorical-trap fixtures do not discriminate bare-codex (report it,
  do not re-tune the gate to force admissions — that would be fixture
  tuning, R0's decisive-criterion dishonesty).
- **P2 (earns-its-keep signal — objective lift)**: on admitted rows, the
  exact per-row predicate `A1.resolved ∧ ¬best_B.resolved` holds on ≥1 row
  (raw counts reported). This is objective lift tranche-2 could not express. **But per NORTH-STAR
  (`:132-140`), A>B is NOT a product moat by itself (R0 MUST-FIX 4)** — it
  is method/harness lift over bare. Recorded raw; NULL (A also fails the
  traps) is a load-bearing finding (the harness does not deliver categorical
  reliability even on traps built for it → deeper than wall).
- **P3 (moat = survives copycat)**: the **product moat requires A > best_B
  AND A > best_C** (copycat = codex told the full plan/implement/verify
  method). If C ≥ A on an admitted row, that row shows METHOD lift (portable
  prompt engineering), NOT a devlyn product moat — and per R0 POS-4 that is
  a genuine honest finding, not a corpus failure. The final report labels
  each admitted row: bare-fail + A-pass + C-pass = method lift; bare-fail +
  A-pass + C-fail = harness-gate moat (the real product). A C-solved row is
  NEVER labeled a devlyn moat.
  **Pilot-scoped mechanical moat policy (2026-07-10, R0-grok CRITICAL 3 +
  R1-codex synthesis — criterion: claim-contract locality under the
  NORTH-STAR evidence hierarchy)**: for THIS pilot, per-row product moat is
  the mechanical predicate `A_resolved ∧ ¬best_B_resolved ∧
  ¬best_C_resolved`; overall `PASS-pilot` requires `A_sum > C_sum` AND ≥1
  product-moat row; `ranked_majority` is recorded in the annex only and
  cannot create a pilot PASS (stock `moat_shown = objective_moat or
  ranked_majority`, `ceiling-gate.py:380`, is NOT used as this pilot's
  verdict). The judge-second tier is not deleted globally — it remains
  available to a future real-shaped, explicitly quality-bearing
  pre-registration.
- **P4 (reporting note, demoted from prediction 2026-07-10)**: LC3 wall
  ratio recorded RAW only. No efficiency-PASS claim may be made when
  `best_B` never resolves; "cost of a wrong answer" framing goes in an
  annex, not the verdict.

## Loss conditions

- **L1**: gate admits FS1 (the saturated control) → gate mis-calibrated,
  revert/re-tune before any tranche. (Zero pool admissions is NOT L1 — it is
  a reported finding, never a trigger to loosen the gate.)
- **L2**: oracle-invalid on a ported trap (gold fails its own oracle) →
  the port is wrong, fix the oracle before admitting.
- **L3 (rewritten 2026-07-10 — criterion: contract-complete,
  test-non-tutoring)**: the visible `task.txt` tutors the solver toward the
  hidden adversarial cases. Two classes: ALGORITHM rows (F21-like) keep the
  full public contract — their hardness is interacting invariants, and the
  leak model is hidden-case tutoring, not keywords; KEYWORD-TRAP rows
  (F11-like) remove trigger wording while preserving the observable
  invariant. Before freeze, a static bare-oracle-from-spec review checks
  each row for hidden-test tutoring.
- **L4 (added 2026-07-10)**: fewer than 3 distinct categorical classes
  admitted → only "plumbing-validated" + enumerated per-row outcomes may be
  claimed; any cross-class "the instrument discriminates" claim is invalid.
- **L5 (added 2026-07-10, pilot-scoped)**: any C-resolved row labeled a
  product moat invalidates the report.

## Implementation deliverables (Codex CLI; verification by orchestrator)

1. **Generic FS oracle runner (R0 MUST-FIX 1, prerequisite)**: the FS
   evaluator is FS1-hardcoded — `run-ceiling-arm.sh:156-182,307-310` treats
   every non-SW task as FS1; `ceiling-eval.sh:254-266,323-324` copies
   `hidden/test_max_runs_oracle.py` + runs `test_schedule.py`. Generalize to
   run an arbitrary declared hidden oracle (`hidden/oracle.sh` exit-0=pass)
   against the cloned+patched repo, task-agnostic. FS1 keeps working via a
   thin oracle.sh wrapper (regression guard).
2. **Fixture pool port**: `benchmark/ceiling/corpus/DR-<class>-*/` for the
   candidate pool (F21/F25/F26/F11/F12/F7/F23 → FS-format: local git repo at a
   base sha, de-leaked visible `task.txt` that STILL states the observable
   invariant (R0 SHOULD-FIX 2, just not the trigger words), `hidden/oracle.sh`
   converted from the fixture's verifiers, `hidden/reference.patch` gold).
   F7's oracle is same-file per MUST-FIX 2.
3. **Bare-fails admission gate**: a corpus-gate step that runs
   `run-ceiling-arm.sh --arm B` (bare CODEX) to 3 VALID attempts per
   candidate + the gold oracle smoke, and writes admit/reject + reason
   (`saturated:bare-resolves` / `oracle-invalid` / `INVALID/PENDING` /
   `admitted:<class>`) into the manifest freeze. Admission = gold-pass AND
   0/3 valid bare attempts resolve; INVALID attempts (infra: invoke,
   materialization, apply, oracle-runtime) are re-run, never counted as
   fails.
4. Manifest `discriminating` section frozen with hashes + gate results +
   **cohort identity per role** (CLI version, requested alias,
   runtime-reported resolved model where available, run ID) — alias/model
   drift between admission and tranche invalidates the freeze and requires
   re-gating. Report the admitted set + every rejection with its reason
   (no silent drops). NOTES.md Claude rubric scores are pool provenance
   only — never admission evidence (construct = binary-oracle bare-CODEX
   discrimination).

Sequencing: deliver 1+2+3, RUN the gate, and STOP at the admitted set for
R1 — the 3-arm A/C tranche only launches after R1 confirms the admitted
rows + labels. (The gate result is itself the pilot's first finding.)

## Pair rounds

- **R0 (2026-07-08, read-only xhigh, archive `/tmp/codex-iter0068/r0-response.log`):
  GO-WITH-EDITS.** All 4 MUST-FIX + 4 SHOULD-FIX ADOPTED: (MF1) generic FS
  oracle runner is a prerequisite deliverable — the evaluator was
  FS1-hardcoded; (MF2) F7 trap is same-file bait + `hello` preservation, not
  a cross-file scope edit — port target corrected; (MF3, decisive) F7/F11
  were already measured bare-aced → don't hand-pick, freeze a POOL and let
  the bare-fails gate select (F21 has stronger recorded discrimination); (MF4)
  product moat requires A > best_C, not just A > best_B — labels fixed.
  SHOULD-FIX: pilot-signal-only ≥3-classes-for-a-claim; F11 de-leak keeps the
  observable invariant; tranche labeled synthetic-calibration not ceiling
  evidence; FS1 "14/14" = tests. Decisive criterion Codex named: the corpus
  is dishonest if a positive comes from leakage / fixture tuning /
  copycat-reproducible method lift mislabeled as a harness moat — the adopted
  labels + gate + copycat arm guard exactly that.
- **R0-grok (2026-07-10, Grok 4.5 read-only, archive
  `/tmp/grok-iter0068/r0-response.log`): GO-WITH-EDITS** — 15 findings (3
  CRITICAL), 10 enumerated edits. All 3 CRITICALs orchestrator-verified at
  the cited lines (gate↔`best_B` estimator mismatch; no infra-validity
  filter; `moat_shown = objective_moat or ranked_majority` at
  `ceiling-gate.py:380` open to subjective-only moat).
- **R1-design (2026-07-10, Codex read-only xhigh, archive
  `/tmp/codex-iter0068-r1design/response.log`): CONVERGED, UNRESOLVED
  none** — edits 1-10 adopted (7 with tighter criteria: exactly-3-valid +
  0/3; end-to-end attempt validity with pass/fail/INVALID oracle semantics
  and zero-diff = valid unresolved; pilot-scoped mechanical moat policy;
  cohort identity; pass-set equivalence + gold N≥2 + no-op-must-fail;
  contract-complete/test-non-tutoring L3; L4 claim granularity; L5
  pilot-scoped; NOTES scores = provenance only). Codex affirmed amendment
  legitimacy: lands before any candidate admission attempt (active search
  of `benchmark/ceiling/results` found only D1 FS1 runner-verification
  artifacts); pre-amendment D1 artifacts are EXCLUDED from admission
  evidence. All amendments folded into this doc 2026-07-10.
- **R-preFreeze (2026-07-10, three-way static leak review — the amended L3
  bare-oracle-from-spec review; archives `/tmp/iter0068-direction/{grok,codex}-response.log`)**:
  both engines DIRECTION-ALIGNED on NORTH-STAR Block-8 axes; **0 LEAK** rows;
  F12 restore + orchestrator port fixes RATIFIED (Codex initially refuted the
  F11 id-trim — adjudicated in Codex's favor, see below). **NEW defect class
  found: UNFAIR** — the binary oracle asserts observables the visible
  task.txt does not state (source fixtures were rubric-scored with partial
  credit, where underdetermined specs cost points; a binary oracle makes
  underdetermination fatal, so bare would fail for SPEC-THINNESS, not
  discipline → manufactured discrimination, decisive-criterion (b)).
  Verdicts: F25/F26 UNFAIR (both engines); F21 UNFAIR (Codex right — Grok's
  CLEAN judged source-fidelity, which is true but not the binary-oracle
  fairness criterion); F11 UNFAIR (Codex right, orchestrator REVERSED its
  own trim — named delta: criterion is contract-completeness w.r.t. the
  oracle, not source-task.txt fidelity; source spec.md:25 states unique ids
  as a public observable and hidden/success.js asserts it); F7 adjudicated
  keep-byte-exact + make-the-observable-visible (design pre-registered the
  class as byte-preservation in MUST-FIX 2; stating the constraint remains
  discriminating per iter-0062 E1 evidence that models violate stated
  byte-preservation rules; reverting to source presence-grep would abandon
  the registered class). **Fix rule (converged)**: fold each source
  fixture's public formal contract (spec.md observables: exact keys,
  formulas, error shapes, id semantics, preservation constraint) into the
  ceiling task.txt; never fold hidden adversarial case values or solution
  mechanisms. F12 untouched (CLEAN both). Next-instrument names recorded for
  the axes 1/2/4 gap: ambiguous-goal fidelity gate / intent-lock
  counterfactual holdout (intent); PLAN-DAG mechanical check /
  dependency-DAG differential (decomposition); design-artifact adversarial
  review cell / blind design-defect differential (design rigor) — named,
  NOT designed (deferred behind this iter).
- **R-quality (2026-07-10, three-way corpus-quality round — user-directed
  "보강·개선·추가·클린업"; archives
  `/tmp/iter0068-direction/{grok,codex}-quality-response.log`)**: Grok
  GATE-READY-after-1 (commit the gate script; corpus content clean); Codex
  GATE-READY-after-8, deeper — adjudicated results: (a) **oracle
  UNDER-assertion found (inverse of UNFAIR)**: F11 (exact error bodies /
  `inserted` / id semantics unasserted), F12 (malformed-body-with-valid-sig
  400 path untested), F26 (minimum-payout hold never exercised — seeded
  payouts all above threshold) → oracle repair with PUBLIC-contract-only
  cases, pre-gate (criterion: objective-oracle soundness — a too-weak
  oracle mislabels hard rows `saturated:bare-resolves`); (b) `eslint-disable`
  forbidden-pattern DELETED from all oracles (broader than its own label,
  not class-defining; silent-catch patterns remain — criterion:
  binary-disqualifier specificity, subtractive); (c) gate-script integrity
  fixes required before live run: recompute-and-fail-closed hash freeze +
  `base_sha256` binding, frozen-rerun refusal, FS1/tranche-1 record
  non-mutation, admitted_amplification_rows vs
  saturated_no_degradation_controls separation (serves Block-8
  no-suppression directive), deterministic tests, script committed; (d)
  **retry policy pre-registered as implemented**: up to 2 replacement
  attempts per invalid slot; slot exhaustion invalidates the row's cohort
  (INVALID/PENDING); resumption = rerun the whole gate under a NEW run id
  (single-cohort estimator integrity); (e) **F23-cli-fulfillment-wave ADDED
  to the pool** (7th class: allocation/FEFO/priority-rollback — missing
  from pool; bare-codex provenance 33; adjudication: Codex's quantitative
  slack argument wins — only 3 rows carry low-bare provenance vs L4's
  ≥3-admitted bar; added PRE-GATE with class-coverage rationale, which the
  no-force-admissions rule permits; Grok's default-freeze position noted);
  (f) all other pool additions rejected (overlap/weak evidence/rework-needed
  or non-coding axes needing different instruments). F21/F25/F7 fairness
  edits: NO-CHANGE (no new tutoring, both engines).
- R1-gate (pending): on the frozen corpus + gate results (admitted set +
  reasons) BEFORE any A/C arm run.

## Execution record

- **2026-07-10 evening — gate cohorts c/d discarded; bare seat corrected to
  terra; relaunched as `iter0068-gate-20260710e`.** (a) `...710c` killed by
  an unexpected machine reboot at 21:23 mid-F7 (single-cohort integrity →
  discard). (b) On relaunch as `...710d`, the user caught that the bare arm
  was NOT the intended model: `run-ceiling-arm.sh` B/C used
  `--ignore-user-config` with no `-m`, so bare ran codex's built-in default,
  and the A-arm executor inherited the global config default `gpt-5.6-sol` —
  neither is the intended benchmark seat. User directive: **benchmark = sonnet
  + `gpt-5.6-terra` only; sol is for the three-way team, not the measured
  arms.** `...710d` discarded (mis-seated cohort). Fix (verified `bash -n` +
  `lint-skills` pass): benchmark-owned `CODEX_HOME` (terra config + auth
  symlink, gitignored) + explicit `-m gpt-5.6-terra` on B/C; global
  `~/.codex/config.toml` (sol) untouched. terra validity + CODEX_HOME auth
  smoke-confirmed (`model: gpt-5.6-terra`, no auth error). Durable log/pid
  moved to `~/iter0068-gate-logs/` (survives `/tmp` reboot wipe).
- **2026-07-10 — three-way amendment + D1 SHIPPED (Fable orchestrating,
  Codex executing, Grok third reviewer — user directive).** (a)
  Pre-registration amended BEFORE any gate run (R0-grok + R1-codex, Pair
  rounds above). (b) Deliverable 1 delivered by Codex (archive
  `/tmp/codex-iter0068-d1/`, ephemeral), **net −21 lines**: task-keyed
  `prepare_fs_workspace` + local-path/bundle source resolution
  (run-ceiling-arm.sh), ONE generic `hidden/oracle.sh` eval path with the
  FS1 legacy branch DELETED (ceiling-eval.sh), FS1 thin wrapper oracle
  (corpus FS1 `hidden/oracle.sh`), corpus README layout rule (no embedded
  `.git`; bundle/local source), manifest FS1 oracle hash. Orchestrator
  verified independently in a clean env: `bash -n` both scripts PASS; FS1
  regression via archived iter0064-t1 patches through the NEW path — A1
  resolved=False, B1 resolved=True, both exactly matching recorded values
  (`benchmark/ceiling/results/iter0068-d1-fable-verify/`). Codex's
  sandboxed uv 0.9.22 panicked mid-run (its own report flags it) —
  clean-env re-run showed no panic; that panic artifact is what motivated
  the amendment's INVALID oracle semantics. Pre-existing gap OBSERVED, not
  fixed (Goal-locked): `test-ceiling-harness.sh` exits 1/INVALID at HEAD
  too (worktree-at-HEAD A/B, identical failure) — its fixtures enumerate
  SW1/SW2/FS1 while the iter-0067 manifest freeze (3e64cba) added SW3-5;
  follow-up candidate.
- **2026-07-08 — design + R0 DONE; implementation DEFERRED to next session
  (user directive, to be run with Fable).** A first implementation slice
  (Delegation 1: generic FS oracle runner + F21 port + gold smoke + bare
  probe) was started and then **rolled back unverified** at user request —
  it was killed mid-slice (no gold oracle smoke, no bare-codex probe ran),
  and it carried unverified edits to shared harness scripts
  (`run-ceiling-arm.sh`, `ceiling-eval.sh`) + an embedded nested git repo,
  so it was not safe to keep. Working tree reverted to the committed
  pre-registration; all iter-0067 fixes intact (venv exclude 4×, tree
  clean).

### RESUME HERE — superseded 2026-07-10

D1+D2+D3 shipped and verified (Execution record above); live gate running
as `iter0068-gate-20260710b`. Current entry point: read the gate result →
three-way R1-gate on the admitted set → A/C + no-suppression decision →
closure. The original 3-step implementation plan is recoverable from git
history of this section (pre-`a33ae5d`).
