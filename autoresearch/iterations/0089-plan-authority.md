---
id: "0089-plan-authority"
title: "PLAN authority — dispatch ledger, cap enforcement, prompt-delivery attestation, round-aware oracle"
kind: reliability
status: D1-D3 IMPLEMENTED 2026-08-03 (6795976 + hermeticity fix 830f886) — NO SHIP CREDIT (R-final NOT-SHIP); conjuncts 2/3/4 satisfied by execution; conjunct 1 machinery green, live delivery compliance 0/2 → OPEN, owned by the next registration
complexity: medium
depends_on: ["0088-plan-route-startup-dedup"]
---

# iter-0089 — PLAN authority (registered)

## Why this iteration exists (pre-flight 0)

This iter unlocks the go/no-go for re-registering H1-v3: iter-0088 Stage B
died at the control stage because the pre-H1 product's PLAN-region
orchestration is stochastic at fixed bytes — 2/5 controls out-of-instrument,
both F12, two distinct classes (`0088` § STAGE B EXECUTED): (i) F12/C2 —
parent composed the PLAN worker prompt with the canonical body under an H2
heading, killing the frozen H1-literal finder; (ii) F12/C3 — three PLAN
dispatches ("CORRECTING ROUND 0", "narrow sync fix") past the prose cap of
one re-spawn, plus divergent RISK_PROBES activation and a receipt-source
startup disagreement (registered precisely in P-0089-5 below). Until
PLAN-region evidence is scoreable, no startup/wall lever can run controls
that survive.

**Mission-bound**: Mission 1 (single-task excellence) — this repairs the
measurement substrate the wall lever's go/no-go depends on; M1.5 surfaces
(dispatcher, deterministic runner) stay out.

## Seat map (named delta from stub)

User directive 2026-08-02: **3-seat = Fable 5 (orchestrator, position stated
first) / Codex gpt-5.6-sol (xhigh, read-only) / Grok 4.5 (headless,
read-only allowlist)** — the stub's registration line named Opus 5 as the
Claude-vendor R0 seat; the user override supersedes it (delta recorded
here). Fable is never a test arm; token-heavy execution arms use
terra/sonnet (`feedback_test_engine_tiering_2026_07_04`).

## Design provenance

Three-way converged 2026-08-02 (receipts
`~/.local/share/nx01/iter0088-stageb/seats/r3-{codex,grok}-determinism.log`):
"identical every time" is the wrong target. Grok criterion
**Invariant-Bookkeeping Asymmetry** (skeleton owns invariant bookkeeping,
intelligence keeps judgment); Codex criterion **narrow PLAN authority**
(mandate the mechanical ledger, reject prompt-delivery forcing — PLAN
workers are native-Agent dispatches with no mechanical interception seam,
contrast SURFACE_CLOSE's `prompt_sha256` machinery,
`references/state-schema.md:61`, `state-phase-write.py:149-201`). Named
orchestrator delta: from "mechanical prompt concatenation" to "render +
digest + fail-closed delivery ATTESTATION".

## Deliverables (the ONLY three)

**D1 — Mechanical dispatch ledger + cap enforcement** in
`state-phase-write.py`. Today `append_phase_history`
(`state-phase-write.py:1256`, invoked from `do_spawn:1306`) records only
`started_at`/`verdict`/`completed_at`/`duration_ms` per superseded round;
`round` is written verbatim from the caller (`:1310`).
**Cap semantics — STATE-DERIVED TOTAL-DISPATCH AUTHORITY (R0 synthesis,
both seats)**: the stored ledger (history length + open/completed current
entry), never the caller-supplied `--round` integer or narrated reason, is
the dispatch count authority. Initial PLAN = count 0; registered cap value
N=1 re-spawn (current product contract, `devlyn:resolve/SKILL.md:112`).
A plan spawn whose ledger already holds an exhausted count fails
explicitly `BLOCKED:plan-respawn-exhausted` — rejected BEFORE
`append_phase_history` (`:1306`), regardless of the round label passed,
with byte-identical state (hash-verified). Round numbering is required
monotonic (next legal round only). Rationale: F12/C3 evaded the
reason-scoped prose cap by narrating "correction" rounds; F7/C1 shows a
live COMPLETE arm at `round=1, history=[], triggered_by=null` — the caller
already controls the integer today. SPW cannot physically prevent an
off-ledger native dispatch — D3 owns those (gate 2 is scoped to "third SPW
AUTHORIZATION rejected").
**D1 receipt field schema (explicit, per R0)** — spawn-known (required,
fail-closed): `round`, `started_at`, `triggered_by`, `engine`,
`model_requested`, `prompt_sha256`. Completion-enriched: `completed_at`,
`duration_ms`, `verdict`, `model_effective` (nullable; enrichment only via
`--engine-session-log` when a wrapper log exists — existing SPW behavior
`:1407-1417`, live plan shape is null, self-test `:2492`). The
worker-session-path field from the stub is CUT (native Agent dispatch
yields no product-visible session path; Codex "name it or cut it"). A
pre-D1 history shape (four timestamp/verdict keys) is
schema-distinguishable from a D1 receipt.

**D2 — Canonical prompt render + delivery attestation (no forcing)**. A
thin shared renderer (own script, e.g. `_shared/phase-prompt-render.py` —
NOT inside SPW) concatenates adapter bytes + canonical body bytes
(`references/phases/plan.md`, H1 at line 1) + task-context artifact, writes
`.devlyn/plan.prompt` + sha256; SPW records the digest in the round
receipt; plan spawn without a digest fails closed.
**Attestation split — PRODUCT ATTESTS INTENT, INSTRUMENT ATTESTS DELIVERY
(R0 synthesis)**: product-side authority = render + digest recording +
prose verbatim-use contract (probabilistic — violation-matrix precedent);
instrument-side authority = byte comparison of the worker-received prompt
(retained session JSONL) against the recorded digest, fail-closed on
mismatch; missing retained delivery evidence classifies the arm
INCOMPLETE. No product-path transcript parser; no forcing. Delivery
FORCING stays deferred unless a binding seam passes a no-degradation test
(M1.5 boundary).

**D3 — Round-aware all-dispatch oracle** (instrument, deterministic,
post-hoc against result dirs like `attribution.py`): attest every actual
PLAN dispatch including failed/pre-write ones.
**Dispatch identity — TOTAL-DISPATCH IDENTIFIABILITY (R0 synthesis)**: the
parent-session `Agent` tool_use is the dispatch authority; executable
predicate = tool name `Agent` AND delivered prompt contains a
start-of-line Markdown heading (ANY depth) whose text BEGINS WITH the stem
`PHASE 1 — PLAN (canonical body)` (stem match, not exact-line equality —
C3's legal re-plans append `— ROUND 1, CORRECTING ROUND 0` /
`— ROUND 2, narrow sync fix`). `subagent_type` is NOT keyed (measured:
C2 `claude`, C3 `general-purpose`). `plan.md`-writer evidence is optional
corroboration only — requiring it recreates the ALL-DISPATCH DOMINANCE
undercoverage on pre-write dispatches (`0088:361-363`).
**Region + decomposition**: PLAN region = first dispatch start → final
legal completion, decomposed per-round + parent inter-round (including the
SPW-spawn-record → actual-Agent-dispatch composition gap; C3 round 0
measured +42,978 ms). **Round continuity**: round=N with absent prior-round
receipts is flagged (F7/C1 live instance), never silently COMPLETE.
**Startup conjunct — SINGLE CLOCK (R0 blocker resolution, § P-0089-5)**:
the authoritative startup clock is the FIRST LEDGER SPAN start
(`startup_recomputed = first_ledger_started_at − invoke_start`), matching
`attribution.py:288` (`invoke_start → activity_union[0][0]`); conjunct
`startup_recomputed == attribution.startup_ms` ±1,000 ms. The legacy
current-round-only recompute (final `plan.started_at − invoke_start`) is
a NAMED wrong-procedure diagnostic when history is non-empty — detected
and reported, never used, never silent.
**Classification**: three-state — valid COMPLETE / **complete-evidence
CONTRACT-VIOLATION** (e.g. a third dispatch: receipts retained, no valid
comparator, no ship credit) / INCOMPLETE. Evidence completeness and
product eligibility stay orthogonal axes (0088 D1 lineage). Self-tests
generated from REAL retained receipts (standing lesson, two live
counterexamples); the pre-write-dispatch fixture is synthesized by
truncating a real retained dispatch record.

## Explicitly OUT (carried from stub; Codex bounding, both seats concurred)

- No general dispatcher / deterministic runner (M1.5 stays deferred).
- No attempt to make plan CONTENT identical; task-context authorship, plan
  conclusions, and the judgment to request a legal replan stay autonomous
  (no-suppression directive, Block 8). Parent composition determinism is
  addressed as D2-render + D3-detection, NOT prevention-by-forcing.
- No cap-VALUE change inside 0089. N=1 stays the shipping default. A later
  candidate iter may run matched N=1 vs N=2 (≥4 reps/arm, 0058 precedent)
  scored on TERMINAL outcomes, never on plan-PASS (C3 counterexample: plan
  PASS after 3 rounds, terminal still NEEDS_WORK).
- No second "determinism infrastructure" iteration; 0089 must not grow into
  a determinism project.
- No H1-v3 work inside 0089 (new registration + new controls required after
  0089 lands; 0087/0088 budgets/controls/ratios are dead — never reuse).

## Frozen predictions (BEFORE implementation; falsifiers named)

- **P-0089-1 (cap red)**: with D1 landed, a state whose plan ledger already
  holds count 2 (initial + one re-spawn) rejects a further plan spawn for
  EVERY supplied round label (`--round 0`, `1`, and `2`), each exiting
  nonzero with exact verdict `BLOCKED:plan-respawn-exhausted` and a
  byte-identical state file (hash compared). *Falsifier*: any label
  spawns, mutates state, or emits a different verdict.
- **P-0089-2 (ledger green)**: a legal round-0 spawn + complete writes a
  receipt carrying every spawn-known field (fail-closed if absent) and the
  completion-enriched fields per the D1 schema; the pre-D1 four-key
  history shape is schema-distinguishable. *Falsifier*: a spawn-known
  field absent on the green path, a digest-less plan spawn succeeding, or
  pre/post shapes indistinguishable.
- **P-0089-3 (oracle identity)**: D3 on the retained F12/C2 parent session
  identifies EXACTLY ONE PLAN dispatch (line 127; H2 canonical-body
  heading) with zero false positives on the same session's three non-PLAN
  Agent dispatches (BUILD_GATE + 2× VERIFY pair-judge); on a fixture whose
  prompt merely QUOTES the canonical title mid-line (not a start-of-line
  heading), no match; on the synthetic pre-write fixture (truncated real
  record), the dispatch is still counted. *Falsifier*: any false negative
  or false positive across these fixtures.
- **P-0089-4 (oracle over-cap)**: D3 against the retained F12/C3 receipts
  counts exactly three PLAN dispatches (parent JSONL lines 129/153/188,
  ROUND-suffixed stems match) and classifies **CONTRACT-VIOLATION** (not
  INCOMPLETE, not COMPLETE). *Falsifier*: any other count or class.
- **P-0089-5 (startup conjunct — single clock; supersedes the draft's
  mis-paired version, R0 blocker both seats)**: under the registered
  first-ledger-span clock, C3 replay yields `startup_recomputed` =
  181,191 ms ≡ `attribution.startup_ms` 181,191 (delta 0) → conjunct
  **PASS**; the three COMPLETE 0088 controls likewise PASS (measured
  deltas all 0: F7/C1 213,270; F7/C2 154,197; F12/C1 156,297). On C3 the
  oracle additionally reports the NAMED wrong-procedure diagnostic: the
  current-round-only recompute (697,569 ms, i.e. +516,378) is flagged as
  the legacy truncation class — 0088's receipt-source disagreement —
  never silent, never scored as startup. *Falsifier*: a nonzero conjunct
  delta on any of the four arms, the diagnostic absent on C3, or the
  legacy value used as startup anywhere.
- **P-0089-6 (delivery attestation — bound into exit conjunct 1)**: for a
  rendered `.devlyn/plan.prompt`, SPW spawn records the digest; instrument
  comparison of a 1-byte-flipped delivered prompt against the digest fails
  closed; an arm with no retained delivery evidence classifies
  INCOMPLETE. *Falsifier*: mismatch passes, a digest-less spawn succeeds,
  or missing evidence classifies COMPLETE.

## Exit gate (all four, by execution)

**Local independence restatement (0087:107 class, stated in-registration
per 0088 advisory): all four exit conjuncts are independent; no average,
aggregate, or adaptive rescue may hide one failure. Stop-all applies: if a
conjunct is unsatisfiable at the frozen baseline, the iter halts and
re-registers — no in-flight substitution.**

1. Every legal PLAN dispatch is accounted in the ledger with a
   schema-complete receipt INCLUDING the prompt digest, and delivery
   attestation holds end-to-end (green path P-0089-2 + P-0089-6; missing
   delivery evidence → INCOMPLETE, mismatch → fail).
2. A third SPW authorization is mechanically rejected with the canonical
   BLOCKED verdict for every supplied round label, state byte-identical
   (red-tested, P-0089-1). Off-ledger dispatches are D3's to flag, not
   SPW's to prevent.
3. Decorative heading variation cannot kill the oracle, and the identity
   predicate produces no false positives (F12/C2 replay + negative
   fixtures, P-0089-3; C3 ROUND-suffix stems counted, P-0089-4).
4. Startup attribution agrees across receipt sources on the registered
   single clock, and the legacy truncation class is detected as a named
   diagnostic, not silence (P-0089-5, all four retained arms).

Then IMMEDIATELY re-register H1-v3 with fresh controls.

## Satisfiability-by-execution record (probes run 2026-08-02, pre-freeze)

Binding lesson (0088 D4 = fourth receipt of the class): a freeze is not
frozen until a seat has tried to satisfy every conjunct by execution.
Scope note (Codex D synthesis): the implementation does not exist yet, so
what is exercised pre-freeze is (a) every replay INPUT's existence
byte-for-byte, (b) every registered PROCEDURE's arithmetic on the retained
receipts, and (c) every product locus. Gate execution with the shipped
code happens at implementation time against these same fixtures. Raw
results at tree `4b7e441` + retained receipts:

- **Conjunct 1/2 loci**: `append_phase_history` (`:1256`) four-key gap
  confirmed; `do_spawn` (`:1271`, round verbatim `:1310`) is the
  rejection hook, BEFORE `:1306`; SURFACE_CLOSE digest machinery
  (`:149-201`, `:1274-1329`) proves per-entry digest recording is
  SPW-native; `model_effective` enrichment `:1407-1417`, live plan null
  (`:2492`). Red fixture: C3 state `plan.round=2`, 2×NEEDS_WORK history;
  live caller-controlled numbering: F7/C1 `round=1, history=[]`.
- **Conjunct 3 fixtures**: C2 parent session (`c6aff32d….jsonl`) — 4
  Agent dispatches; #1 (line 127) desc `PLAN phase for webhook feature`,
  prompt 7,737 bytes, `## PHASE 1 — PLAN (canonical body)` at H2,
  `subagent_type=claude`; 3 non-PLAN negatives in the same file. C3
  parent session (`58d35d61….jsonl`) — exactly 3 PLAN dispatches, lines
  129/153/188, ids `toolu_018uNqsJQ5…/toolu_01V6ZMhiFh…/toolu_01XsaLyz…`,
  prompts 6,800/3,571/1,106 bytes, stems `# PHASE 1 — PLAN (canonical
  body)` + ROUND-suffixed variants, `subagent_type=general-purpose`.
  Canonical H1 verified at `references/phases/plan.md:1`.
- **Conjunct 4 arithmetic EXECUTED on all four arms** (invoke_start from
  `timing.json`, first ledger span from `pipeline.state.json`,
  attribution from `attribution.json`): F12/C3 first−invoke = 181,191 ≡
  attribution (delta 0); F7/C1 213,270; F7/C2 154,197; F12/C1 156,297 —
  all delta 0. C3 legacy current-round-only recompute = 697,569
  (+516,378 divergence, the 0088 disagreement); C3 actual Agent tool-use
  clock = 224,169 (+42,978 parent-composition gap, registered as a D3
  decomposition output, NOT a conjunct clock).

## Rejection rules

All of 0088's carry forward (worker resume; product-path transcript
parser; deterministic runner; BUILD_GATE transport dependency; halt
migration into LLM judgment), plus:

- D2 forcing (any mechanism that intercepts or rewrites the native Agent
  dispatch) → reject; detection + honest halt is the house pattern (C2
  terminal-claim precedent).
- An oracle that keys PLAN identity on Markdown heading level,
  `subagent_type`, or REQUIRED writer evidence → reject (C2 failure class;
  measured subagent divergence; ALL-DISPATCH DOMINANCE).
- A cap keyed on the parent's narrated reason OR the caller-supplied
  round label → reject (C3 + F7/C1 evasion surfaces).
- No failure in this iter authorizes M1.5 work.

## Claim boundary

PASS proves only: PLAN dispatches are mechanically ledgered and capped at
the SPW authorization layer, the rendered prompt is digest-attestable
end-to-end on the instrument side, and the oracle scores 1-or-2-dispatch
shapes with heading-robust identity plus a single-clock startup conjunct.
It does NOT prove wall or startup improvement, does NOT stabilize parent
composition (detection, not prevention), does NOT authorize a dispatcher,
and does NOT re-register H1-v3 — that requires its own registration with
fresh controls.

## Registration record — R0 + R1 (2026-08-02)

Durable receipts: `~/.local/share/nx01/iter0089-reg/seats/`
(`r0-packet.md`, `r0-codex.log`, `r0-grok.log`,
`r1-orchestrator-data.md`).

- **R0 verdicts**: Grok `BLOCKED:exit-gate-4-startup-conjunct-mis-specified`;
  Codex `BLOCKED:startup-clock-contradiction` — convergent core blocker.
  The draft paired 516,378 ms (final−first multi-round span) with
  181,191 ms (attribution startup) as if both were startup recomputes; the
  two differences coincidentally both equal 516,378, masking the
  procedure error. Orchestrator reversal with named delta = receipt
  arithmetic, execution-verified 4/4 arms delta 0 (the pre-accepted
  falsifier "conjunct mis-specified from actual receipt bytes" fired).
- **Adopted seat syntheses** (all execution-verified before adoption):
  Grok/Codex LEDGER-COUNT / STATE-DERIVED CAP (caller round label
  untrusted; F7/C1 live instance); Codex END-TO-END ATTESTATION CLOSURE
  (P-0089-6 bound into conjunct 1; field schema split spawn-known vs
  completion-enriched; session-path field cut); Grok stem-match rule +
  Codex executable identity predicate (subagent_type divergence measured
  claude vs general-purpose; writer evidence demoted to corroboration);
  Codex SINGLE CLOCK (first ledger span chosen — house attribution
  standard; 42,978 ms Agent-dispatch gap registered as decomposition
  output; 516,378/697,569 as named legacy diagnostic).
- **R1**: orchestrator data (F7/C1 round-continuity anomaly,
  model_effective null-forever live shape) folded into D1/D3; every seat
  byte-claim independently re-verified by execution (dispatch lines/ids/
  timestamps, subagent types, SPW loci `:1324`/`:1407-1417`/`:2492`,
  four-arm startup table). No contested position remains; further rounds
  would require new evidence (anti-asymptotic rule).

## IMPLEMENTED (2026-08-03)

Codex gpt-5.6-sol executor build (7,134 s, per
`feedback_implementation_to_codex` + executor pin), orchestrator-verified
gate by gate. Files: `state-phase-write.py` +215/−20 (D1 state-derived
ledger + cap: `dispatch_count = len(history) + open/completed current
entry`, rejection BEFORE `append_phase_history`, spawn-known fields +
digest fail-closed, nonmonotonic round explicit);
`_shared/phase-prompt-render.py` +80 (D2 renderer);
`devlyn:resolve/SKILL.md` ±3 lines (PLAN render→digest→spawn contract,
receipt schema line, round-1 sole legal corrective re-spawn);
`benchmark/ceiling/scripts/plan-dispatch-oracle.py` +1073 (D3).

**Executed gates (orchestrator re-ran everything)**: SPW self-test incl.
`PASS iter-0089 PLAN ledger: P-0089-1/2/6` (all round labels rejected on
full ledger, state hash unchanged); renderer self-test; oracle self-test
87 assertions; spec-verify self-test; full `lint-skills.sh` with three
mirrors synced. Five-arm retained replay: F12/C3 → CONTRACT-VIOLATION,
3 dispatches, startup PASS delta 0, legacy diagnostic
`697,569 / +516,378, scored:false` present, composition gap 42,978 ms;
F12/C2 → exactly 1 PLAN of 4 Agent dispatches at H2 (identity conjunct),
INCOMPLETE per missing delivery evidence; F7/C1 → both round-continuity
flags; all five arms startup conjunct PASS delta 0.

**Orchestrator finding + edit (disclosed, small, evidence-grounded)**:
Codex's synthesized F7C1 fixture did not reproduce the real
engine-bearing pre-D1 current-entry key shape, so live replay mislabeled
4/5 retained arms `plan-receipt-schema-invalid` + delivery
`FAIL`(mismatch) where the truth is legacy-unattestable — a null recorded
digest is UNATTESTABLE, never a MISMATCH (honest-labeling bar; fixtures
must come from REAL receipts — standing lesson). Fix: legacy-current
predicate accepts both measured variants (C3 no-engine/null vs F7/C1
engine+model strings), raw fixtures made byte-faithful, raw F7C1 replay
assertions added (80→87). Classification outcomes were unchanged
(INCOMPLETE either way); labels now truthful.

**Codex named deviations accepted**: mirror sync + commit are
orchestrator-side (its sandbox cannot write `.agents/`); its final VERIFY
was solo-primary (claude CLI `Not logged in` inside the sandbox);
H1-v3 re-registration correctly NOT attempted (out of its scope).

**Exit-gate status**: conjunct 2 (cap red) and 3 (identity) and 4
(startup single clock + named legacy diagnostic) satisfied by execution
against retained receipts; conjunct 1 (ledger green + delivery
attestation end-to-end) green in self-tests — the live product canary
(render → digest → spawn → native dispatch → oracle COMPLETE on a fresh
run) is the remaining receipt before the gate is called.

## LIVE CANARIES + R-FINAL ADJUDICATION (2026-08-03) — no ship credit

**Canary 1** (headless sonnet resolve, goal = the named 0088 lint residual;
receipts `~/.local/share/nx01/iter0089-reg/canary1/`): D1 green path LIVE —
receipt round 0 with all spawn-known fields, recorded digest ≡
`.devlyn/plan.prompt` on disk; goal fix correctly committed (`b6dd37d`,
1 line, lint green incl. the new entry). **Delivery attestation caught a
real mismatch**: worker-received bytes pruned the adapter's 35-line
pair-JUDGE block (+3 trailing lines). BUILD_GATE never completed — a
leftover process from the detached Codex build was writing the same
`.devlyn` (collision), plus a stale pre-run `external-diff.patch` polluted
scope-check; the run halted honestly.

**R-final (Codex xhigh, read-only; `rfinal-codex.log`)**: **NOT-SHIP,
adopted.** Named criterion **Attestation-Result Fidelity**: the pre-canary
implementation record committed to "oracle COMPLETE on a fresh run" BEFORE
observation; re-reading a detected mismatch as gate satisfaction after
observing it is a retroactive criterion edit. Conjunct 1 requires a
compliant-delivery arm classified COMPLETE.

**Runaway-spawn defect (canary yield, root-fixed `830f886`)**: canary 1's
live `.devlyn/spec-verify.json` (verification command = lint) closed a
latent mutual recursion — pipeline replay exports `BENCH_WORKDIR=<repo>`;
`spec-verify-check.py --self-test` scenario children inherited it, and
default-mode resolution (`work = BENCH_WORKDIR or cwd`,
spec-verify-check.py:3933) made them replay the LIVE contract → lint →
lint-skills.sh:470 self-test → unbounded spawn storm (~18 procs/min
observed live). Deterministic marker repro pre-fix; fix = scrub
BENCH_WORKDIR at self-test entry (one deletion point, all 88 child calls
covered); red-tested both env shapes. Pre-existing latent (not introduced
by 0089), fixed in-scope because it blocked the canary path.

**Canary 2** (goal = the R-final-surfaced `rg` dependency at
lint-skills.sh:1029; receipts `canary2/`): PLAN receipt green (digest ≡
disk), goal fix landed clean (net 1 file / 1-line change over two fix
rounds, lint green). **Second delivery mismatch, same family**: the
orchestrator pruned the adapter's 61-line judge-invocation block and
added a 6-line principles condensation. The run was stopped from outside
the session mid-VERIFY (`terminal_reason: aborted_streaming`, 131 turns)
— no terminal verdict; PLAN receipts salvaged.

**Adjudication — final for this iter**:
- Conjuncts 2/3/4: SATISFIED by execution (retained-arm replays +
  red-tests; record above).
- Conjunct 1: machinery green at every layer (fail-closed spawn, digest
  recording live 2/2, mismatch DETECTED live 2/2, missing-evidence →
  INCOMPLETE); the pre-registered live receipt (oracle COMPLETE fresh
  run) is NOT met — **measured live delivery compliance 0/2**, both
  prunings the same class: the rendered artifact concatenates the FULL
  adapter, whose judge-invocation machinery two independent live
  orchestrators each judged irrelevant to a PLAN worker and pruned.
  No falsifier of P-0089-1..6 fired. Per the frozen no-forcing rejection
  rule, compliance cannot be forced inside 0089; per stop-all, the open
  conjunct transfers to a new registration, not in-flight iteration.
- **Named next-lever hypothesis (frozen advisory for the successor
  registration)**: worker-scope the render inputs — a PLAN-worker-scoped
  adapter view should remove the observed prune incentive WITHOUT
  forcing; score delivery compliance as the registered outcome. This is
  0088's "parent composition determinism … registered as its own scored
  gate" advisory, now with 2/2 same-class live receipts and a working
  measurement instrument.
- H1-v3 re-registration stays blocked until the delivery-compliance gate
  closes (its controls need scoreable PLAN regions AND compliant
  delivery).

## Principles check

0. Not score-chasing: unblocks the H1-v3 go/no-go and closes a receipted
   cohort-killer class (2/5 controls out-of-instrument). ✅
1. No overengineering: three deliverables, closed list; forcing rejected;
   no new runtime beyond one renderer script + SPW extension + one
   instrument; stub's session-path field cut when unobtainable. ✅
2. No guesswork: every prediction has a named falsifier; all registered
   procedures' arithmetic executed on retained receipts pre-freeze; the
   draft's own startup mis-pairing was caught by this discipline and
   corrected with a named delta. ✅
3. No workaround: cap lands in the mechanical skeleton (SPW state-derived
   authority), not another prose sentence; the prose cap's evasion is the
   documented root cause. ✅
4/5. Worldclass/best practice: fail-closed everywhere; digest via sha256
   file bytes (SURFACE_CLOSE precedent); no hand-rolled parsing in the
   product path. ✅
6. Layer-cost-justified: zero added model calls in the product path;
   renderer is one local script; oracle is post-hoc instrument. ✅
7. Mission-bound: Mission 1 measurement substrate; M1.5 explicitly out. ✅

## Registration protocol status

- [x] Cold start per HANDOFF read order (2026-08-02 session)
- [x] Stub citations verified at cited files
- [x] Satisfiability-by-execution probes (record above; all four
      conjuncts' inputs + procedures exercised on retained receipts)
- [x] 3-seat R0 (Fable position first / Codex xhigh / Grok headless) —
      both seats returned; convergent blocker adopted
- [x] R1 reconciliation — seat claims re-verified by execution; syntheses
      folded; no contested position open
- [x] FREEZE (this commit; status REGISTERED-FROZEN)
