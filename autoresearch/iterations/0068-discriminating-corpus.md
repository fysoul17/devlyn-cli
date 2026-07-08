# iter-0068 — discriminating ceiling corpus (bare-fails gate + categorical-reliability trap tasks)

status: PRE-REGISTERED 2026-07-08 (R0 GO-WITH-EDITS folded) — design frozen
before implementation; corpus freezes (with the bare-fails gate results)
before any A/C arm runs. Direction chosen by user 2026-07-08 (corpus pivot,
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
policy call (PRINCIPLES #0 carve-out); it directly unlocks iter-0069's
wall-vs-value decision.

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
2. **bare single-shot codex FAILS** the oracle on ≥ ⌈2/3⌉ of 3 attempts
   (NEW: the discrimination gate).

A row where bare passes is REJECTED with reason `saturated:bare-resolves`
(FS1 is the built-in positive control — it must be rejected: bare solved it
14/14 in tranche-1). A row where gold fails is `oracle-invalid` (existing).
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
**F7-out-of-scope-trap** (scope). The pool is frozen; admission is data.
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
converts the `expected.json` verifiers into ONE hidden pass/fail oracle
(`hidden/oracle.sh` or `.js`) that boots the app and asserts the same
state (F11: failed-batch-leaves-store-unchanged + all-valid-succeeds;
F7: version-json-works + out-of-scope-file-unchanged-from-base). Gold =
`hidden/reference.patch`. The visible `task.txt` is the de-leaked spec
(F7's "Only touch bin/cli.js…" scope line stays visible — it IS the trap;
F11's "all-or-nothing" phrasing is softened so bare is not handed the
answer). The ceiling FS eval already runs an arbitrary hidden oracle
against a cloned+patched repo (FS1 precedent), so no eval-engine change —
only the oracle must be self-contained and language-present in the repo
(node, already there).

### Arms / judge / LC — unchanged from 0067

3-arm (A devlyn = sonnet orch + codex executor + pair-verify; B bare codex;
C copycat codex), N = round(wall_A/wall_B) capped [1,3], neutral blind judge
(sonnet+codex), LC1-LC4, objective-first. Test arms codex/sonnet only.

## Predictions (frozen before implementation)

- **P1 (the gate discriminates)**: run the bare-fails gate over the frozen
  pool + FS1. FS1 is REJECTED (`saturated:bare-resolves`, bare ≥2/3 pass) —
  the gate's self-test. At least ONE pool fixture is ADMITTED (gold-pass AND
  bare-codex fails ≥2/3); the admitted set + every rejection reason is
  reported. If FS1 is admitted, the gate is mis-calibrated (L1). If ZERO
  pool fixtures admit, that is not a gate failure — it is the honest finding
  that categorical-trap fixtures do not discriminate bare-codex (report it,
  do not re-tune the gate to force admissions — that would be fixture
  tuning, R0's decisive-criterion dishonesty).
- **P2 (earns-its-keep signal — objective lift)**: on admitted rows, devlyn
  A resolves where bare B fails — A_resolved > best_B_resolved on ≥1 row.
  This is objective lift tranche-2 could not express. **But per NORTH-STAR
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
- **P4 (wall in context)**: LC3 wall ratio recorded — but now against a
  bare that FAILS, so "8× the wall of a wrong answer" reframes the
  efficiency question entirely (bare-best-of-N of a failing arm never
  resolves, so the economic baseline math changes). This is the reframe
  that makes the wall question honest.

## Loss conditions

- **L1**: gate admits FS1 (the saturated control) → gate mis-calibrated,
  revert/re-tune before any tranche. (Zero pool admissions is NOT L1 — it is
  a reported finding, never a trigger to loosen the gate.)
- **L2**: oracle-invalid on a ported trap (gold fails its own oracle) →
  the port is wrong, fix the oracle before admitting.
- **L3**: the ported trap task leaks the trap answer in the visible
  `task.txt` (bare would pass by reading the spec) → re-author the visible
  spec to hide the leading keywords (the pair-fixture discipline:
  "public spec must hide leading keywords or solo aces").

## Implementation deliverables (Codex CLI; verification by orchestrator)

1. **Generic FS oracle runner (R0 MUST-FIX 1, prerequisite)**: the FS
   evaluator is FS1-hardcoded — `run-ceiling-arm.sh:156-182,307-310` treats
   every non-SW task as FS1; `ceiling-eval.sh:254-266,323-324` copies
   `hidden/test_max_runs_oracle.py` + runs `test_schedule.py`. Generalize to
   run an arbitrary declared hidden oracle (`hidden/oracle.sh` exit-0=pass)
   against the cloned+patched repo, task-agnostic. FS1 keeps working via a
   thin oracle.sh wrapper (regression guard).
2. **Fixture pool port**: `benchmark/ceiling/corpus/DR-<class>-*/` for the
   candidate pool (F21/F25/F26/F11/F12/F7 → FS-format: local git repo at a
   base sha, de-leaked visible `task.txt` that STILL states the observable
   invariant (R0 SHOULD-FIX 2, just not the trigger words), `hidden/oracle.sh`
   converted from the fixture's verifiers, `hidden/reference.patch` gold).
   F7's oracle is same-file per MUST-FIX 2.
3. **Bare-fails admission gate**: a corpus-gate step that runs
   `run-ceiling-arm.sh --arm B` (bare CODEX) N=3 per candidate + the gold
   oracle smoke, and writes admit/reject + reason
   (`saturated:bare-resolves` / `oracle-invalid` / `admitted:<class>`) into
   the manifest freeze. Admission = gold-pass AND bare-fail ≥2/3.
4. Manifest `discriminating` section frozen with hashes + gate results.
   Report the admitted set + every rejection with its reason (no silent
   drops).

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
- R1 (pending): on the frozen corpus + gate results (admitted set + reasons)
  BEFORE any A/C arm run.

## Execution record

(pending)
