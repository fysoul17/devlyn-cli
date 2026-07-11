# iter-0068 — discriminating ceiling corpus (bare-fails gate + categorical-reliability trap tasks)

status: RE-CLOSED 2026-07-12 — **VALID-NEGATIVE RESTORED on clean
isolation-v2 data** (§ Re-closure at the end of this file): fair admitted
set ∅; F21 EXCLUDED-UNFAIR by the pre-registered admitted-set audit;
6 DR + F12-supplement + FS1 saturated; zero fair-row evidence of
identity-leak materiality. History: REOPENED 2026-07-11 evening by
Amendment A1 (cohort-g Identity-Blindness failure — that validity ruling
STANDS; isolation v2 became permanent instrument hardening); originally
CLOSED 2026-07-11 VALID-NEGATIVE on cohort g (§ Closure, superseded). Originally PRE-REGISTERED
2026-07-08 (R0 GO-WITH-EDITS folded); AMENDED 2026-07-10 before any gate
run (three-way fold: R0-grok GO-WITH-EDITS + R1-codex CONVERGED — see Pair
rounds); a first slice was started 2026-07-08 then rolled back unverified
(see Execution record). Corpus froze (with the bare-fails gate results)
with no A/C arm runs. Direction chosen by user 2026-07-08 (corpus pivot,
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
The neutral blind judge's codex seat is ALSO pinned to terra
(`ceiling-judge.py call_codex` adds `-m gpt-5.6-terra`; it `--ignore-user-config`
so `-m` is the only lever) — done ahead of the A/C tranche so the whole
benchmark is sonnet + terra, sol nowhere in the measured path.

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

- **2026-07-11 afternoon — cohort f DISCARDED (harness stall found, no verdicts
  emitted); watchdog pipe-hold fixed; relaunched as `iter0068-gate-20260711g`.**
  Cohort f's F21 bare attempts finished in 202/278/240s but the gate blocked
  ~3600s per attempt: `corpus-gate.py run_command` reads the runner via
  `subprocess.PIPE`, and `run-ceiling-arm.sh`'s watchdog subshell (plus its
  orphaned `sleep $TIMEOUT`) inherited that pipe and held it open until the
  sleep expired (process-table evidence: defunct runner + 50-min orphan
  `sleep 3600`). Every prior live cohort paid the same silent
  max(attempt,timeout) wall-tax — cohort e's ~2.5-3h/row pace was this
  artifact, not model time. Fix: watchdog subshell stdio → `/dev/null`
  (1 line + comment, `bash -n` verified; orchestrator-implemented, surfaced
  for three-way reconciliation at R1-gate). Cohort f had emitted zero row
  verdicts → clean discard per single-cohort policy; g runs wholly on fixed
  code.
- **2026-07-11 — gate cohorts c/d/e ALL DISCARDED-contaminated: the bare arms
  were never bare (user-reported, transcript-proven). Isolation fix shipped
  three-way; relaunch as cohort f.** codex v0.144.1 auto-loads GLOBAL skills
  (`~/.agents/skills/`; in cohort c also `~/.codex/skills/`) regardless of
  `--ignore-user-config --ignore-rules --ephemeral` and a redirected
  CODEX_HOME — no skills-disable feature flag exists (`codex features list`
  verified; `--ignore-rules` covers execpolicy `.rules` only). Cohort-e F21
  B1: the "bare" agent announced "I'm using the repository's hands-free
  implementation workflow", read `~/.agents/skills/devlyn:resolve/SKILL.md`,
  and ran the devlyn pipeline
  (`results/iter0068-gate-20260710e/DR-ordering-f21-scheduler/B1/transcript.txt:2,30`).
  Contamination breadth (Grok-verified, Fable-spot-checked): e 16/16, c 4/4,
  d 1/1 bare transcripts. Second vector: engine workspaces lived at
  `benchmark/ceiling/external/workspaces/` INSIDE the repo tree (ancestors
  carry AGENTS.md/CLAUDE.md/.devlyn). Record corrections (Codex R0,
  Fable-verified): cohorts c AND d both ran `gpt-5.6-sol` bare arms (c
  predates `36cf373`); cohort e stopped after F12 B1 runner completed (exit
  0, 486s, timing.json present, objective absent), process gone by 12:50
  KST. **Impact = gate inversion**: contaminated bare resolved trap rows →
  `saturated:bare-resolves` (F7/F25/F26/F11 in cohort e) is untrustworthy
  specifically in the row-REJECTING direction; F21 was
  `admitted:ordering-inversion` (0/3) even with harness context — still
  re-gated clean. Quarantine: c/d/e are non-evidence for
  admission/freeze/DR-scoring/wall-time; read-only incident artifacts only
  (contamination signatures, seat-pin verification, F3 regression fixtures).
  **Fix (three-way: Grok R0 GO-WITH-EDITS + Codex R0 GO-WITH-EDITS; Fable
  adjudication with named criteria; Codex implemented; Grok R1 on the actual
  diff)**: (E1) `EXTERNAL_ROOT` → `$HOME/devlyn-ceiling-external` in
  run-ceiling-arm.sh / ceiling-eval.sh / corpus-gate.py / ceiling-judge.py
  (4th site Grok-found — judge scratch was also in-repo); (E2) per-attempt
  fresh `HOME` (`bare-homes/<run>/<task>/<armN>`) and `CODEX_HOME`
  (`codex-homes/…`) for codex arms — criterion: attempt-independence must be
  structural (Codex correction: codex-home-terra was never fully recreated,
  only config.toml overwritten); (E3) corpus-gate bare-attempt validity
  gains fail-closed provenance checks (transcript exists; model header
  required AND = terra — `runtime-model-missing` tightening added by
  orchestrator, surfaced in R1; timing worktree outside repo root) +
  contamination markers → INVALID `bare-context-contaminated:<marker>`,
  provenance-only families (`global-skills-path`, `devlyn-skill-identity`,
  `devlyn-runtime`); REJECTED markers with named deltas: bare `devlyn`
  (fixture package.json legitimately says "devlyn-cli auto-resolve
  benchmarks" — Grok FP find), `Subtractive-first`/`Goal-locked`
  (content-word echo — Codex counter); criterion: Artifact-Provenance
  Specificity; (E4) selftest 30→37 assertions (clean-no-FP, skill-load,
  skill-read, missing/empty transcript, in-repo worktree, model
  mismatch/missing). Verified: selftest 37 PASS, `bash -n`, `py_compile`.
  **Post-fix canary CLEAN** (new layout, exact B-arm flags): zero markers,
  `model: gpt-5.6-terra`, no instruction content, codex built-ins only —
  transcript persisted at
  `~/devlyn-ceiling-external/canary/canary-postfix-20260711.transcript.txt`.
  **Open risks (recorded, no code this pass; blocking prerequisites for the
  NEXT measured A/C tranche, not the bare gate)**: (a) A-arm environment
  purity — canary RUN 2026-07-11 (staged workspace + exact A-arm flags,
  sonnet): staged devlyn context present AND user-global `~/.claude/CLAUDE.md`
  LEAKED (the Next.js server-component instruction quoted verbatim; not in
  any staged file — grep-verified; skills list all staged/built-in, no skill
  leak; pyx-memory block NOT reported — partial-load mechanism unknown).
  `--setting-sources project,local` does not exclude user CLAUDE.md memory.
  Transcript: `~/devlyn-ceiling-external/canary/canary-a-arm-20260711.transcript.txt`.
  Fix to be designed three-way BEFORE the next A/C tranche; same
  prerequisite for both neutral judges. (b) Fixture identity leak: seed
  package.json tells the agent it is a devlyn-cli benchmark fixture —
  bench-aware-behavior risk, corpus-hygiene follow-up.
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

### RESUME HERE — superseded by § Closure below (2026-07-11)

## Closure (2026-07-11) — VALID-NEGATIVE

**Frozen result** (cohort `iter0068-gate-20260711g`, manifest
`tranche3.discriminating`): admitted 0/7, rejected 8/8
`saturated:bare-resolves` (per-row bare resolves: F21 1/3 · F7 3/3 · F25 3/3
· F26 3/3 · F11 3/3 · F12 2/3 · F23 3/3 · FS1 control 3/3). 24/24 attempts
valid, zero invalid reasons, zero contamination flags, terra-only cohort
identity, drift false. FS1 positive control behaved exactly as
pre-registered. Wall ≈ 15 min/row post watchdog fix.

**Three-way R1-gate (Codex sol + Grok 4.5, both independently audited the
manifest; Codex verified 24/24 patch hashes + external worktrees + fix
commits predating the cohort)**: GATE **VALID** unanimous. Converged honest
finding (claim-population identity / claim-contract locality):

> On clean bare Codex CLI 0.144.1 running `gpt-5.6-terra`
> (`iter0068-gate-20260711g`, N=3 valid attempts per row, FS1 control
> correctly saturated), the frozen seven-row synthetic categorical-trap pool
> admitted 0/7 under the pre-registered gold-pass ∧ 0/3-valid-resolve rule —
> these traps do not discriminate bare-codex-terra; the bare-fails gate +
> generic FS oracle are **plumbing-validated only**, and no categorical-trap
> generality, real-shaped ceiling, amplification, or moat claim follows.

**The one divergence + orchestrator adjudication (named criterion)**: Grok
= skip A/C, close now ("No contaminated A measurement" — the proven A-arm
user-CLAUDE.md leak makes any A run manufactured-contaminated data); Codex
= keep 0068 open through a bounded A-only no-degradation tranche on the 8
saturated controls after purity is fixed ("Orthogonal Estimand Value" —
Block-8 no-suppression is pre-registered and the controls exist for it).
Both agree purity-first; the disagreement is ledger bookkeeping only.
Adjudicated: **close now** (criterion: iteration stop-condition integrity —
the pre-registered stop was the freeze; A/C was conditional on admitted
rows, which are empty; holding an iter open behind an unsized prerequisite
repeats the iter-0033g anti-pattern and blocks the user-mandated 0070
ladder). Codex's estimand survives as a first-class pre-registered deferred
cell, below.

**Survives into future corpus/ceiling work (validated instrument)**: FS
task packaging + generic `hidden/oracle.sh` contract; bare-fails admission
gate + 0/3-valid semantics; fail-closed hash freeze + frozen-rerun refusal;
provenance + contamination INVALID markers; isolated `EXTERNAL_ROOT` +
per-attempt HOME/CODEX_HOME; FS1 positive-control design;
`admitted_amplification_rows` / `saturated_no_degradation_controls` split.
**Retired**: the 7 DR F-fixtures as discriminating-candidate rows for terra
(kept frozen as archived calibration/control fixtures only; pre-registered
anti-fixture-tuning rule — do NOT re-tune them to force admissions).

**Pre-registered deferred cell (NOT run; blocked)**:
`no-degradation control cell` — A1 (full devlyn resolve) vs frozen `best_B`
on the 8 saturated controls; objective preservation 8/8 + blind quality +
wall cap; reuses cohort-g B data. **BLOCKED on the A-arm + neutral-judge
purity fix** (user-CLAUDE.md leak, Execution record 2026-07-11). Suggestive
observation only, N too small: contaminated-e F21 0/3 vs clean-g F21 1/3
(direction consistent with harness-context suppression).

**Follow-ups recorded (non-blocking)**: (a) watchdog cancellation should
also reap its sleep child (resource lifecycle; fe252ee accepted by both
seats); (b) manifest should freeze the runner commit hash (auditability,
Codex); (c) `requested_alias: "default"` provenance label vs `-m` pin
(cosmetic, Grok); (d) fixture identity leak in seed package.json
(bench-aware-behavior risk); (e) `test-ceiling-harness.sh` stale fixture
enumeration (pre-existing, Execution record 2026-07-10).

**Next**: enter the 0070 ladder (`0070-loop-architecture-STUB.md`; design
frozen, user-mandated) + `0070a-noncoding-instruments.md` pre-registration
(held for this closure).

## Amendment A1 (2026-07-11 evening) — closure verdict superseded: IDENTITY-CONFOUNDED / INCONCLUSIVE

**Trigger**: user report (same evening) — terra's trap-avoidance suspected to
be caused by running in a harness-identity-bearing environment; mandate:
fully isolated (new-folder) runs. Orchestrator verified at file level, then
three-way R0 (Grok 4.5 independent + Codex sol; archives
`/tmp/iter0068-reopen/{packet,addendum-r0}.md` + `{grok,codex}-r0.log`,
ephemeral; this section is the durable record). Verdicts: **P2 amendment GO
(Codex) / GO-WITH-EDITS (Grok); isolation-v2 + staged re-gate GO-WITH-EDITS
(both).**

**Named delta vs § Closure** (what changed): the closure's follow-up (d)
"fixture identity leak in seed package.json (bench-aware-behavior risk)" was
recorded as non-blocking; the new evidence upgrades it from *risk* to
*observed exposure at scale*, and widens it far beyond package.json:

- **Observed ingestion**: 19/24 cohort-g transcripts contain the literal seed
  string "for devlyn-cli auto-resolve benchmarks. Every fixture starts from a
  fresh copy of this directory" (20/24 attempts read package.json; 6/24 read
  the seed README announcing "benchmark fixture... arm (variant or bare)").
- **Trap-axis broadcast**: 24/24 workdir lines expose
  `devlyn-ceiling-external/.../iter0068-gate-.../DR-<trap-descriptive-name>/`
  — the directory name announces the discriminating axis (e.g.
  `DR-byte-preservation-f7-out-of-scope-trap`).
- **Host-shell leak, mechanism named**: ambient `ZDOTDIR=/Users/aipalm` in
  the runner session env defeats `export HOME=$BARE_HOME`
  (run-ceiling-arm.sh:286) — real `~/.zshenv` executed in 24/24 attempts (203
  occurrences), its error lines re-injecting descriptive bare-home paths.
  Reproduced independently by orchestrator and Grok.
- **Additional identity channels (Codex/Grok R0)**: git remote
  (`repos/fs/DR-*`), reflog with real host paths, commit authors
  (`benchmark@devlyn.local`), seed comments in `bin/cli.js` /
  `playwright.config.js` / `server/index.js` / `web/index.html`, lockfile
  name, `.gitignore` `.devlyn` entry, 18 inherited harness env vars
  (`CLAUDECODE=1`, `CLAUDE_CODE_SESSION_ID`, ... — present, NOT observed:
  0/24 transcripts inspect env), and the `codex` command resolving to the
  Superset wrapper (trusted-project config + notify hooks), so cohort g was
  not a stock-CLI launch.
- **NOT found (E1 stands)**: zero devlyn-pipeline application markers in all
  24 transcripts; the c/d/e skill-contamination mechanism did not recur.

**What is superseded**: only the certification claim "these traps do not
discriminate CLEAN bare-codex-terra" — cohort g fails the
**Identity-Blindness** criterion (Grok R0: identity bits in arm-visible
context invalidate certification in either direction, regardless of
behavioral effect). **What stands**: 24/24 artifact validity, 0/7 under the
implemented rule as a mechanical result, FS1 control, c/d/e contamination
finding (fdd574a), watchdog fix (fe252ee), gate/oracle plumbing validation.
The 7-DR-row "retired as discriminating candidates" status is SUSPENDED
pending the clean re-gate (not silently reversed).

**Materiality is a separate estimand** (Codex R0 criterion: **Counterfactual
Identity Invariance**) — decided ONLY by the isolation-v2 re-gate. Strongest
counter (both engines, honest prior for H-saturated): task texts already
state the discipline constraints; outcome heterogeneity (F21 1/3, F12 2/3 vs
rest 3/3) fits difficulty, not uniform evaluation-aware gaming; no transcript
shows explicit bench-aware meta-reasoning as action driver.

**Pre-registered re-gate (cohort h, frozen BEFORE implementation ran)**:
isolation v2 per `/tmp/iter0068-reopen/r1-implementation-contract.md`
(durable copy: § Amendment A1 contract summary below) — D1 opaque
identity-free arm-visible paths + opaque task ids + post-exit opaque-map;
D2 shared deterministic workspace-clone neutralizer (frozen corpus bundles
byte-untouched; solver patch diffed against the neutral baseline); D3/D6
`env -i` frozen-allowlist launch of the DIRECT codex binary (kills ZDOTDIR
inheritance + env advertisement + Superset wrapper), auth copied 0600;
D4 structured fail-closed marker families (host-shell-startup-leak +
benchmark-identity; bare `devlyn` marker REJECTED — F7's oracle-required
`TODO(devlyn)` bait, hidden/preservation.js:9) + per-attempt isolation.json
attestation; D5 staged minimal attempts (per DR row: 1 valid attempt; valid
resolve → saturated, stop; valid fail → complete to exactly 3 valid; FS1
exactly 1 valid attempt; fixed row order; invalid attempts replaced).
**Decision rule**: ≥1/7 DR rows admitted (3 valid bare-fails) → H-leak —
a discriminating row exists, closure finding superseded, corpus roadmap
updates; 0/7 → H-saturated — VALID-NEGATIVE restored on genuinely clean
data. No mid-cohort retuning of D1-D4 from peeks.

**Carrier attribution (user hypotheses tested, 2026-07-11)**: (1)
"ran in a devlyn-file/CLAUDE.md folder" — TRUE for c/d/e (discarded), NOT
the cohort-g carrier (no AGENTS.md/CLAUDE.md in workspace ancestry; zero
pipeline markers). (2) "global pyx-memory read" — structurally impossible
for bare codex arms (per-attempt config.toml has no MCP servers) and
empirically zero pyx/mcp traces in 24/24 transcripts. Actual carrier = the
seed fixture itself (`benchmark/auto-resolve/fixtures/test-repo/package.json:5`
description copied into every workspace) + path names. Also confirmed: the
Superset wrapper injected `trust_level = "trusted"` with the full
descriptive workspace path into per-attempt config.toml.

**Accepted residual (user decision 2026-07-11, "Docker 없이는 감안")**:
without container-level isolation (fresh codex install in Docker), host
shared state remains — codex binary/installation, macOS host, same auth
account, node toolchain. These are identity-NEUTRAL (carry no
benchmark/trap bits), so the re-gate's claim is scoped honestly as
"identity-clean at the file/path/env layer per fail-closed attestation;
host-install residual accepted". Docker/VM full isolation = escalation lane
only if a clean 0/7 re-gate still leaves suspicion or a marker trips
unexplainably.

## Re-closure (2026-07-12) — VALID-NEGATIVE RESTORED on clean isolation-v2 data

**Verdict**: VALID-NEGATIVE restored. Fair admitted set = ∅ on the valid
pool. F7/F25/F26/F11/F23 saturated (cohort `iter0068-gate-20260711h`, 1
valid resolve each under the staged D5 rule); F12 saturated (properly-staged
supplement `iter0068-f12supp2-20260712`: resolved, opaque_paths.passed=true,
terra, zero identity/zshenv hits); FS1 control correct; **F21
EXCLUDED-UNFAIR** (retired-frozen-defective — not saturated, not an
admission).

**The F21 story (decisive experiment, prediction frozen before run)**:
cohort-h F21 was mechanically admitted (3 valid bare-fails; the only flip vs
cohort g) and provisionally certified H-leak (manifest commit b5cca93). The
pre-registered admitted-set UNFAIR audit (this file :315-319) then killed
it: visible task.txt says "Times are same-day HH:MM values" + invalid times
→ exit 2, while BOTH hidden checks feed ISO `submitted_at`
(hidden/error-order.js:18-20, hidden/priority-blocked.js:27-30) and expect
normal scheduling output; the reference validates submitted_at as any
non-empty string (hidden/reference.patch:101) — the oracle author's private
reading. All three cohort-h bare attempts validated HH:MM per the visible
text (B1 `parseTime`, B2 `timeToMinutes`, B3 `parseTime`). **Experiment**:
B1's transported patch on a fresh neutralized clone + hidden inputs with
ONLY submitted_at converted ISO→HH:MM → BOTH hidden checks PASS (Grok 4.5
independently reproduced). Bare failed for FOLLOWING the visible contract →
manufactured discrimination. The g→h F21 "flip" is void in both directions
(same defective oracle). **H-leak certification RETRACTED.**

**Root cause of the fixture defect**: the pre-freeze fairness repair folded
the HH:MM contract into task.txt (Fix rule, this file :330-335) but had no
step re-auditing hidden INPUTS against the repaired visible input contract.
Follow-up instrument (pre-registerable): mechanical hidden-input conformance
check against the visible input spec at fixture-freeze time.

**Three-way record**: Grok R2 CONCUR (reproduced the experiment;
retire-frozen). Codex R1 independently discovered the same F21 defect on the
pre-experiment packet (convergent finding) AND caught the first F12
supplement failing the gate's own opaque-path attestation
(isolation.json `opaque_paths.passed=false` — orchestrator ran it with an
in-repo result dir; corrected by the properly-staged rerun under the new
run-id per Codex's no-label-reuse rule). **Contested point + adjudication
(named delta)**: Codex proposed repair-F21-and-rerun before any verdict
("remains REOPENED — INSTRUMENT-INVALID"); adjudicated EXCLUDE-and-close —
criteria: (a) the admitted-set UNFAIR audit is pre-registered process, so
exclusion is not post-hoc reinterpretation; (b) anti-tuning — repairing
fixture bytes after peeking at outcomes re-enables the exact blocked
failure mode (Grok); (c) decision-relevance per wall-hour — the experiment
already shows the repaired row would saturate. Codex's F12 finding adopted
wholesale; F21 repair remains possible ONLY under fresh pre-registration.

**What stands**: cohort-g Identity-Blindness invalidity (Amendment A1) — a
validity ruling, unaffected. Isolation v2 (`1452393` + patch transport
`e899e98`) = permanently required instrument hardening. Watchdog fix +
c/d/e skill-contamination findings unchanged. **Materiality**: ZERO
fair-row evidence that the identity leak changed any outcome (every fair
row: bare resolves both leaked and clean).

**Corpus state**: 0 discriminating rows; 6 DR + FS1 (+F12) = saturated
no-degradation controls; F21 tombstoned. The honest 0067/0068 conclusion
deepens: synthetic categorical traps do not discriminate clean bare terra —
a discriminating corpus must come from real-shaped/harder tasks (deferred
lane) or the 0070a non-coding instruments.

**Next**: the 0070 ladder + 0070a are UNBLOCKED. A-arm/judge purity remains
the blocking prerequisite for any measured A/C tranche.
