# HANDOFF — for the next session

**Read order on cold start (mandatory)**:
1. **This file** — operating context + active iter + pair-collab protocol
2. [`NORTH-STAR.md`](NORTH-STAR.md) — goal + floor contract (L0/L1/L2, ops tests 1-16) + **ceiling contract + ops test #17** (2026-07-06 amendment) + pair-mode policy
3. [`PRINCIPLES.md`](PRINCIPLES.md) — pre-flight 0 + #1-#7 (every iter cites)
4. [`MISSIONS.md`](MISSIONS.md) — Mission 1 active + ceiling addendum + roadmap to endgame + hard NO list
5. Most recent: [`iterations/0095-plan-delivery-byte-fidelity-STUB.md`](iterations/0095-plan-delivery-byte-fidelity-STUB.md) (**NEXT — delivery byte-fidelity, design round held + falsifier-adjudicated, not yet registered**) and [`iterations/0094-r5-regate.md`](iterations/0094-r5-regate.md) (**CLOSED 2026-08-05, DECISIONS 0094.1 — matrix ran, first past controls; NO SHIP CREDIT: candidate-discovery delivered the PLAN prompt minus its terminal LF; R1 not refuted**) and [`iterations/0092-plan-native-foreground-dispatch.md`](iterations/0092-plan-native-foreground-dispatch.md) (**implementation verified GREEN 2026-08-05; R5 CLOSED-UNSCORED protocol-failed-at-controls; DECISIONS 0092.1**). Context: iter-0093 authorable verification timeout SHIPPED (DECISIONS 0093.1); [`iterations/0091-plan-dispatch-boundary-identity.md`](iterations/0091-plan-dispatch-boundary-identity.md) (Stage A SHIPPED `7c446c1`; Stage B closed-fail, B1 reverted `1e7da13`); 0088-0090 in their iteration files. Older context remains in the iteration index and `DECISIONS.md`. Ladder: [`iterations/0070-loop-architecture-STUB.md`](iterations/0070-loop-architecture-STUB.md). Entry point in START-HERE below.
6. [`DECISIONS.md`](DECISIONS.md) — append-only ship/revert log (newest at bottom)

If any file contradicts another, **NORTH-STAR.md wins**, then this file, then PRINCIPLES.md. Open a doc-fix iter on the contradiction. Historical narratives live in `iterations/*` + DECISIONS.md + NORTH-STAR § Pair-mode policy — this file carries only what binds the next session (user cleanup directive 2026-07-07).

Last rewritten 2026-07-07; closed-iter narratives compressed 2026-07-10, 2026-07-14, and 2026-07-20 (user cleanup directives; Blocks 2-6 verbatim + prior full history recoverable from git + iteration files + DECISIONS.md; superseded memory-file narratives moved to memory/archive/).

---

## 🚦 START-HERE — state after 2026-08-18 (session 2)

**NEXT = iter-0104 registration: repo-scale executor-quality cell
(user-selected 2026-08-18).** Question: does the felt opus-5 regression
reproduce at true repo scale (>100 files, multi-file dependency
chains), which the 5-file corpora (0101/0102) cannot discriminate?
0101 close-out already named this the first successor mechanism.
Session operating rules (BINDING): fable = design / adjudication /
verification ONLY — token economy HARD (`feedback_fable_token_economy`;
prior bust precedent); corpus authoring, apparatus builds, and
repetitive runs → terra direct-drive lane (0102-proven: terra authors,
trio verifies per batch) or opus/sonnet; verification trio = fable +
sol(5.6) + grok; matrix arms only on a quiet account outside
23:00–01:00 KST; pre-commit full 64-hex freeze inventories + R-A/R-B
digest rules in the registration (0103 sol F1). Driver seed =
`benchmark/executor-quality/scripts/mx-driver.py` (canonical since
batch B: structural infra taxonomy 429/529, replay-proven 45/45 on the
0102 attempt-1 rows).

**Batch B harness findings CLOSED (2026-08-18, `6bf0d2a` pushed).**
All 6 registered product findings from the 0089–0103 lineage shipped:
verify-merge primary fail-closed (+mechanical-skip exemption) +
seat-attributed pair scan; shared `_shared/judge-output-parser.py`
(registered tolerances only); archive_run per-run inventory; brace-glob
surface grammar fail-closed at load; detached-HEAD `base_ref.branch:
null`; canonical mx-driver seed. Terra implemented (4 rounds), trio
verified (R0 REVISE ×3 → R1 REVISE ×2 → grok FREEZE / sol residuals
applied). Receipts `~/.local/share/nx01/harness-batchB-20260818/`.
OPEN (user decision): collector accepts findings-without-terminal-
verdict (`collect-codex-findings.py:90`, pre-existing at HEAD) —
tighten-vs-keep briefed to user 2026-08-18; fold the ruling into the
0104 session.

### History — state after 2026-08-18 (session 1)

**Executor-quality lineage 0100→0103 CLOSED (2026-08-18).** Authority:
`DECISIONS.md` 0102.1 / 0103.1 + `iterations/0102-*.md` / `0103-*.md`
DECISION paragraphs. On the sealed 0102 discovery corpus (32 tasks,
sonnet-calibrated mid-band 0.49): **opus-5 ≈ fable-5** (0102, Δ=−0.047,
CI [−0.116,+0.016]) and **opus-5 fails materially LESS than opus-4-8**
(0103, Δ=−0.181, CI [−0.256,−0.109]; 18 tasks better / 2 worse). The
felt "opus-5 regression" is not reproduced by any instrument
(0100 SATURATED, 0102, 0103). Candidates weighed for the successor:
true repo scale (>100 files), session-horizon/long-context, pair-loop
deference (H2), the user's live workload shape → user picked repo
scale (see START-HERE). Operator rules now standing: never launch a
matrix arm while other Claude sessions/headless reviews share the
account; pre-commit freeze inventories + digest rules (0103 sol F1).
Receipts `~/.local/share/nx01/iter0102/`, `iter0103/`.

### History — state after 2026-08-09

**iter-0100 REGISTERED (2026-08-09) — main-AI executor quality cell
(`iterations/0100-main-ai-executor-quality.md`).** Origin: user live
signal "opus-5 almost always concedes to codex sol in pair; fable draws
only minor objections" — user adjudicated the concessions were
CODE-VERIFIED real errors → H1 (main-AI design/coding defect rate)
leads; the deference probe is a demoted pre-named successor. H3 first
bound IS IN: judge_quality re-run under CURRENT codex identity
(`results-ckf0809-sol/`, codex-cli 0.146.1 / gpt-5.6-sol
banner-attested): recall 16/16 · FP 0/8 · parse 0/24. R1 freeze review
REVISE ×2 (sol + grok, liveness markers), all edits adopted; contested
estimand adjudicated to paired-Δ (named criterion PAIRED-DESIGN
FIDELITY + EXHAUSTIVE TERMINALS, Grok residual attack right at the
post-build audit). **Fable baseline = user-directed SCOPED exception**
to test-engine tiering (seat-certification only; fable never enters
shared recert `--engines` arrays). Next: corpus build via
/devlyn:resolve (12 tasks, 3 per taxonomy class, multi-manifestation
oracles + smoke gates) → post-build pre-arm freeze audit (both seats;
dry arm + synthetic-ledger scorer proof) → 48-run detached matrix.
Receipts: `~/.local/share/nx01/pair-calibration-r0/`.
**Corpus build A LANDED 2026-08-09** (run `rs-20260809T044614Z-58fec95f19be`
PASS; spec `docs/specs/iter0100-executor-quality-corpus-a/`): scripts
validate-task.py (smoke+conformance gate, 5 fail-closed self-tests) +
score-cohort.py (frozen paired-Δ scorer, 4-terminal self-test) + tasks
EQ-UA1/EQ-MI1/EQ-AF1 admitted. VERIFY r0 primary-codex HIGH
same-binding-equality gap → fixed `78d1334` → r1 PASS 3/3. Operator
finds: spec needs `<!-- devlyn:verification -->` sentinel BEFORE probe
phase (run 1 died on it); stale `.devlyn/external-diff.patch` from a
prior run poisons spec-verify `changed_files()` (BUILD_GATE root-caused,
quarantined to attic — bootstrap-clear follow-up); claude-side pair
judge must EMIT collector format (JSONL + `# SUMMARY`) — a written
findings file alone merges as BLOCKED fail-closed; verify verdict is
merge-owned (never pass --verdict to verify complete/transition).
**Corpus build B LANDED 2026-08-09** (run
`rs-20260809T064222Z-a36f4bcfdf8e` PASS; spec `1c8cca8`
`docs/specs/iter0100-executor-quality-corpus-b/`): 9 tasks
EQ-UA2/UA3 MI2/MI3 AF2/AF3 BD1/BD2/BD3 admitted — **corpus complete,
12 tasks, exactly 3 per class**. Spec was pair-reviewed pre-commit by
codex sol (REVISE ×3 adopted: validator-overclaim rewording,
behavioral-tuple distinctness law, corpus-topology mechanical gate;
README scoped edit KEPT under CHANGE-CREATED TRUTHFULNESS;
R1-0100B-LIVE-sol). VERIFY round 0 PASS (mechanical 16/16 +
primary codex + pair claude, 0 findings). Operator finds this run:
Claude-Code orchestrator Bash caps codex phase calls at 600s — a
2-task authoring call measures ~785s, so phase-gated IMPLEMENT hits
the wall; remedy = depth-first per-task sequencing in the phase
prompt ("complete task A + its gate BEFORE touching task B") + the
contract's one-fix-respawn-per-phase (consumed 3 of max_rounds 4;
kills landed during wrap-up, completed work survived every time).
**PRE-ARM AUDIT + 48-RUN MATRIX BOTH CLOSED same day (2026-08-09
evening)**. Audit: both seats REVISE round 0 (grok 3 falsifiers all
CONFIRMED by repro — exact-δ float false H1_CONFIRMED, shared-run_id
UNSCORED, timeout-row rejection; sol added stdin contamination
(launcher heredoc bytes appended to goal prompt, transcript-proven)
+ task-id whitelist + integrity pins) → fixes via codex sol (scorer
`5072ccd` exact-Fraction terminalization; driver stdin=DEVNULL +
prompt/driver attestation + triple-digest fail-closed) → dry arm
rerun clean → grok RECHECK FREEZE-ARM + sol FINAL FREEZE-ARM.
Matrix cohort `mx-20260809T1210Z`: 48/48, attestation 48/48, zero
catastrophic/infra — **TERMINAL = SATURATED** (both engines 24/24
all-clean, Δ=0.0; corpus does not discriminate at this difficulty;
NO routing change; P-0100-1/2 refuted on this corpus; sol adjudicated
the driver_sha256 schema projection PROJECTION-LEGAL,
POSTMX-0100-LIVE-sol). Receipts `~/.local/share/nx01/iter0100-prearm/`.
**iter-0101 DESIGN-FROZEN same day (2026-08-09 night)** —
`iterations/0101-executor-quality-hard-corpus.md` is the COMPLETE
cold-start-executable authority (sol R0 REVISE ×8 + grok R1 REVISE
×5 both adopted with liveness markers; grok verified the 32-row
table and CI-touch bootstrap arithmetic by execution). Design core:
N=32 two-axis compound-invariant tasks (8/class, frozen 32-row
authoring table + 10 axis-pair templates + frozen axis role order),
frozen `validate-task.py` + NEW `validate-hard-task.py` wrapper +
NEW `score-calibration.py`, sonnet 2-rep calibration with ONE valid
band evaluation (Fraction-exact mean AND frozen even-n median ∈
[1/5,3/5], ≥22/32 interior, ≤2 total-fail; miss = CALIBRATION_MISS
terminal, no retuning; difficulty-oracle prohibition during
authoring), 128-run matrix opus-5 vs fable-5, δ=0.15, P-0101-1
single prediction.
**iter-0101 CLOSED — TERMINAL = CALIBRATION_MISS (2026-08-12
session; § Execution log in the iteration file is authoritative)**.
Corpus build COMPLETE 32/32 admitted across 8 resolve batches +
candidate SEALED (tree `2685fa07…` at `cc23209`; scripts
validate-hard-task 1f809e33… / score-calibration 418f3738… /
score-cohort N=32 5af3c1bd… / validate-task byte-frozen 769a1826…).
Calibration apparatus FROZEN (FREEZE-ARM ×2 after adjudicated split:
grok R0 FREEZE-ARM vs sol R0 REVISE; sol H3 receipt-binding + L4 D6
adopted, H1/H2 lexical-taxonomy residuals held byte-frozen with two
pre-committed operational rules — `calfrz-adjudication.md`). ONE
valid 64-run sonnet evaluation `cal1-20260811T150824Z`: attested
64/64, cat/inc/infra 0/0/0, **band = MISS** — mean 1/40, median 0,
interior 5/32 (bar ≥22) → registration terminates, matrix (steps
⑥-⑧) never fired; the easy-regime screen saved the 128-run cost
0100 paid to learn the same shape. Successor design data: only
UA5 3/10, AF4 1/5, AF1/MI8/UA7 1/10 touched the calibrator; BD class
0/8. A revised registration needs a qualitatively harder mechanism
than two-axis compound invariants on small fixtures (repo-scale
surface / long-horizon chains / non-local invariants — adjudicate at
registration). Receipts `~/.local/share/nx01/iter0101/`
(build/freeze/calibration incl. matrix apparatus DRAFTS, never
frozen). FOUR harness product findings registered, not fixed
(verify-merge PRIMARY fail-open; stale verify.judge.summary.json
survives archive; collector/merge parser mismatch;
`path_matches_surface()` silently ignores brace-glob surface
entries) + lexical failure-taxonomy modernization (AUTH substring
class, sol H1/H2) as next-registration follow-up.
**iter-0102 DESIGN-FROZEN same session (2026-08-12)** —
`iterations/0102-executor-quality-discovery-corpus.md` is the
complete cold-start authority (sol R0 REVISE ×8 + grok R1 REVISE ×5
+ REC-1/2/4 all adopted; liveness R0-0102-LIVE-sol-c42dd8ef /
R1-0102-LIVE-grok-28409c8b; grok verified the 32-row table by
execution). Design core: non-local UNSTATED two-fragment
complementary contract + stateful restore (mechanism replacing
0101's stated compound invariants), N=32 `EQ3-*`, mechanical
complementarity law (outcome-token partition), 4-prototype
PRE-CORPUS PILOT with frozen information boundary (all nine specs
pre-committed BEFORE pilot; corpus batches in a FRESH session
reading only `~/.local/share/nx01/iter0102/pilot/DECISION`),
calibration gate verbatim from 0101, apparatus lineage sha-pinned
(cal f7347a72…/719ea0f1…, mx drafts 6a4c88cf…/bbc4b2f7…,
launch-detached 30b630d5…, run-bounded db9ed383…, CLI 013a1cf1…).
EXECUTION COMPLETE THROUGH THE PILOT (2026-08-12; § Execution log in
the iteration file is authoritative): ① 9 specs sealed `01d414d`
before pilot (sol REVISE ×4; scorer re-pin = byte-pinned
`sed s/EQ2-/EQ3-/g` → 58d726f3…/399b0691…) ② pilot resolve run
TERMINAL PASS at outer iter 3 (`rs-20260812T100115Z`; mid-way
codex-seat-limit halt recovered same day; 14 judge findings closed
across 3 iterations — hollow oracles, hardcoded restores, token-salad
invariants, vacuous self-tests, stdlib-walk fail-open,
namespace-package false-positive, semantic single-artifact leakage;
final VERIFY 3/3 + finish-gate clean; scripts pin `5e95a58`) ③ pilot
sealed (4 tasks/139 files, tree `c6ac78fd…`) ④ apparatus FREEZE-ARM
convergence after adjudicated split (launch-gate hardened: 6-entry
REQUIRED inventory, atomic ordinal locks; tamper cases live) ⑤ 8-run
sonnet arm `pilot1-20260812T105601Z` attempt 1/3 clean (8/8 attested,
0/0/0) → **ONE evaluation: DECISION = PROCEED — mean 13/40, q_pilot
2/5·2/5·1/2·0/1, interior 3/4, byte-deterministic**. The discovery
mechanism lands sonnet at 32.5% mean fail vs 2.5% on 0101 —
band-region difficulty confirmed at prototype scale. Receipts
`~/.local/share/nx01/iter0102/pilot/` (per-task outcomes SEALED;
carriers DECISION + DECISION.receipt.sha256 = b1f77615…).
**NEXT = FRESH SESSION (binding R1-2b — this session saw pilot
details and must NOT author the corpus): read the two carrier files
only, then batches 01-08 serially on the sealed specs
(`/devlyn:resolve --spec docs/specs/iter0102-executor-quality-batch-0N/spec.md
--pair-verify`, executor codex, outer loop ≤3/batch, dispatch prompts
pre-inject the 0101 failure classes) → candidate seal → calibration
apparatus freeze → 64-run sonnet → ONE band evaluation → matrix
(never near 12am KST).**
PARALLEL, independent:
0100 § Matrix integration fold-in — recert-seats.sh
`executor_quality` suite + seat-matrix.py `main_ai_executor`
recording the SATURATED cell (own /devlyn:resolve run). H2
deference probe + H4-beyond-this-shape remain demoted frontier. Operator lessons this round: orchestrator
Bash 600s wall vs codex 2-task authoring (~785s) → depth-first
per-task sequencing in phase prompts; NEVER launch a detached driver
with heredoc stdin (claude -p appends stdin to the prompt — use
stdin=DEVNULL); post-audit apparatus edits must re-run the
extra-field tolerance proof for EVERY new ledger field. Fable scoped
exception = user directive 2026-08-09 (recorded in
`feedback_test_engine_tiering` memory); fable never enters shared
recert `--engines`.

**iter-0099 CLOSED — context-engineering item 2 (C/K/F contract
placement): KEEP_CURRENT, no product change (DECISIONS 0099.1;
`b152feb` registration → `a89a7ea` close → `23d9cec` queue).** Prereq
SHIPPED: recert chain exact Claude model-ID support (`c0a3b20` +
`d824d6b`, verify-only PASS 3/3) — the 2026-07-28 instrument gap is
closed and both seats are certified (`ckf0099-recert`: claude-opus-4-8
10/24 drift violations, **claude-opus-5 3/24**, judges recall 1.0 /
FP 0.0; seat matrix committed `462b752`). Matrix ran 216/216
attested-valid. **F (flip to a CLAUDE.md pointer) is OUT — it
regressed claude-opus-4-8 on the bare surface (B4 cell 1→4, above
band); P-0099-3 and P-0099-4 both REFUTED.** K was safety-neutral on
all four combos but its registered benefit measured ~12× smaller than
claimed (0 bytes/run gen-4, ~1.2k tokens/run gen-5), so the frozen
treatment-validity conjunct blocked adoption. **TWO ITEMS AWAIT THE
USER** (recorded in `docs/specs/queue.md` item 2 and the iteration
file, never silently applied): (a) the queue's own rule 2 ("K passes
while F regresses → adopt K") was SATISFIED on the raw matrix and was
blocked only by the conjunct the orchestrator added at R1; (b) the
adjudication is CONTESTED — the frozen text conflicts internally
(treatment clause "outcome routes to rule 4" vs precedence "total
order, no cancellation"), giving Reading A = KEEP_CURRENT and Reading
B = ADAPTER_CONDITIONAL_F; both converge on no product change under
the named criterion REMEDY REACHABILITY (F's failure is on the bare
surface, where no adapter exists). **Strongest evidence-backed next
step: the generic phase-body reread is DEAD TEXT** — consumed 0 times
in 12 gen-4 pipeline runs (4 in 12 on gen-5) — so deleting it for all
engines is pure subtraction and needs none of K's engine-conditional
machinery; that is a NEW registration, and this iter already supplies
its safety evidence. **Codex R-final PENDING** (seat usage limit,
resets 2026-08-10); grok 4.5 served as the substitute third seat and
found the precedence gap. Nothing ships, so the pending round blocks
nothing. Receipts: `~/.local/share/nx01/iter0099/receipts/`.
**Also still open from the parallel track: 0098 (LF-run-insensitive
compare) registration DRAFT is committed and its resolve run was never
re-fired** — see the 0098 block below for its resume order.
Operator rules added this round: long unattended matrices must be
detached with `python os.setsid()` (macOS has no `setsid`; a
harness-tracked background driver was killed three times), and an
adjudication scorer must be frozen and pair-audited BEFORE its inputs
complete (five codex rounds caught a reversed retry precedence that
would have scored invalid runs, among ten-plus real defects).

### (superseded START-HERE from 2026-08-05 — iter-0095 context)

**iter-0095 registration update (2026-08-05, supersedes the paragraph
below where they conflict).** The registration is FROZEN
(`iterations/0095-plan-delivery-byte-fidelity.md`, 3-seat FREEZE: R0
Codex REVISE + Grok REVISE with an F1 split — Codex fired F1 with 2.1.222
no-message hook-attachment bytes; adjudicated to the minimal
orphan-correlation rule with a named delta — R1 FREEZE ×2 with liveness
markers). Landed through TWO /devlyn:resolve outer loops (executor pin
codex + --pair-verify): ① the one-sentence Claude PLAN-delivery Read-cue
instruction (`8f99b51`, PASS 3/3) ② the oracle evidence-scoping +
subagent_type absent-key + orphan-correlation change (`e72bd1d`; run 1
BLOCKED:verify-exhausted on a payload-boundary dedup collapse both judges
converged on, spec amended, run 2 PASS 3/3; self-test 299). Freeze gate
executed green on landed bytes: C1 COMPLETE/0 · C2 violation conserved ·
0094 candidate-simple COMPLETE `ff7bda46…` · candidate-discovery
violation conserved `c9d8a32e…`. Scorer artifacts clause fixed +2
selftests (16/16). Receipts `~/.local/share/nx01/iter0095-reg/` (git).
Session operator finds: codex-cli 0.146.0 workspace-write hard-denies
`.agents/` (fix: `-c 'sandbox_workspace_write.writable_roots=[…/.agents]'`;
codex-config.md follow-up registered); verify-merge flipped-seat false
BLOCKED fired live (primary capture renamed `codex-primary.stdout`
in-run; product follow-up stands); judge prompt files do not survive
mid-run maintenance — rebuild at every dispatch; oracle writes its JSON
INTO the result dir and `sessions/` is result's SIBLING — replay retained
receipts on full-arm COPIES only. **MATRIX RAN AND CLOSED (same day):
CLOSED-UNSCORED protocol-failed-at-controls at arm 1/4** (DECISIONS
0095.1) — the control-simple Sonnet parent completed PLAN via STANDALONE
`plan complete` (no atomic transition verb; session `:181`),
`implement=null` at `plan.completed_at`, the exact fail-closed class the
frozen watcher catches; after in-window PLAN use → no replacement;
R-final Codex CONFIRM. Candidate arms unscored; R1 + the LF instruction
NOT refuted; both product edits stay landed on formal verification.
**0096 RAN AND CLOSED same day (DECISIONS
0096.1)**: SPW effective-verdict transition guard SHIPPED (3-seat FREEZE
incl. Codex R1 EFFECTIVE-VERDICT CONSERVATION delta; two resolve outer
loops; verify-only PASS 3/3 twice — two pipeline runs closed BLOCKED on
concurrent user queue.md edits contaminating the scope baseline, learned
route = bookkeeping commit + verify-only) and LIVE-VALIDATED: fresh
four-arm matrix ran 4/4 past the watcher (0095 death class closed),
dispatch_clean 4/4 + oracle 0 evidence issues (both 0094 instrument
defects closed live), tripwires 0.895×. DECIDING BAR FAILED 1/2:
candidate-discovery stripped the SAME single terminal LF (12,150/12,151)
WITH the Read-cue instruction in-tree; candidate-simple byte-exact.
Controls both digest-mismatched (third both-conditions variance
receipt). Blind bar not executed (non-restorative; nonce retained;
logged). **0097 RAN AND CLOSED (DECISIONS 0097.1)**: canonicalization
SHIPPED `5dcd6fc` (renderer no-terminal-LF + cue deletion, R0/R1
convergent freeze); matrix infra-confounded at arm 3/4 (external
session-quota kill mid-PLAN; Codex strict-text ruling — no replacement,
rerun = new registration). DECISIVE non-scoring diagnostic:
candidate-simple ADDED a trailing LF to the canonicalized no-LF
artifact while control-simple delivered byte-exact — with 0094 (strip)
and 0096 (strip despite cue), the terminal-LF byte is BIDIRECTIONALLY
model-unstable at the Read→transcribe boundary; artifact- and
instruction-side remedies are both measured-insufficient. **0098 (LF-run-insensitive
compare) IN FLIGHT, PAUSED ON A SESSION COLLISION (2026-08-06 00:4x
KST)**: design round CONVERGED (Codex+Grok AGREE-WITH-EDITS; TWO-BRANCH
predicate adopted — `recorded == raw` FIRST, OR `recorded ==
terminal-LF-run-stripped`; named criterion RETAINED-RECEIPT
CONSERVATION beat Grok's single stripped compare; receipts
`~/.local/share/nx01/iter0098-design/`), registration DRAFT committed
(`iterations/0098-lf-run-insensitive-compare.md`), oracle spec
committed (`docs/specs/iter0098-lf-run-insensitive-compare/spec.md`),
PLAN completed on run rs-20260805T153428Z — then HALTED: a SECOND
orchestrator session had bootstrapped run rs-20260805T153016Z (spec
`docs/specs/iter0098-recert-exact-model-id/spec.md`, recert exact
model-ID — the Opus-5 A/B prerequisite) four minutes earlier, and its
codex IMPLEMENT (xhigh) was still in flight; the Fable bootstrap
clobbered that run's .devlyn state (bidirectional violation of the
writer-check rule). Fable's run was halted BLOCKED + archived; the
recert codex was left untouched. **RESUME ORDER FOR THE NEXT SESSION**:
① check the recert diff landed (5-file surface) and shepherd it via
`--verify-only` against its spec (recovery pack:
`~/.local/share/nx01/recert-run-recovery/` — RECOVERY.md +
plan-verbatim.md recovered from the live process args; do NOT resume
its dead pipeline state); if it needs an autoresearch number use 0099.
② re-launch the 0098-oracle resolve run
(`--spec docs/specs/iter0098-lf-run-insensitive-compare/spec.md
--pair-verify`, executor codex) AFTER confirming no live .devlyn
writer. ③ 0098 freeze gate: oracle self-test + retained replays ON
COPIES (0091 C1 + 0094 cs COMPLETE via raw branch; 0094 cd + 0091 C2
violations conserved; NEW satisfiability receipt = 0097
candidate-simple full-dir replay must score COMPLETE via the stripped
branch) → R1 both seats (liveness) → fresh bases/tokens/nonce →
matrix. **NEW BINDING OPERATOR RULE: before ANY resolve bootstrap,
verify no live process is writing the repo's `.devlyn` (ps for claude
-p/codex exec/resolve-bootstrap + state run_id sanity) — two collisions
today (queue.md contamination twice + this state clobber).** Old
frontier: **0098 design round** (both sides strip the terminal 0x0a run
pre-compare, raw digests retained forensically, all other bytes exact —
the 0095-rejected F4 re-opened with its premise falsified). Old
frontier text: **register iter-0097: artifact canonicalization** (renderer emits `plan.prompt` WITHOUT the
terminal LF — digest self-consistent; DELETE the 8f99b51 cue sentence,
subtractive; fresh controls/nonce/bases per 0088.3). Receipts:
`~/.local/share/nx01/iter0096-{reg,matrix}/`. Old frontier text below
superseded: **register the successor (0096)**
(condition-independent parent variance in shared contract text — the
0094 control-delivery-variance family; fresh controls + nonce + sibling
bases at the then-current SHA per 0088.3). Matrix receipts:
`~/.local/share/nx01/iter0095-matrix/`.

### (superseded registration context from 0094 close below)

**Where the loop stands (one paragraph).** iter-0094 re-gated 0092's R1
(native foreground PLAN dispatch, landed `83b275e`, formally verified
green) through a fresh 3-seat FREEZE (R0 deltas all adopted: frozen
`--no-risk-probes` invocation, opaque arm tokens + neutral sibling base
commits, execution-shape dispatch scorer, judge schema, sha-anchored
receipts; R1 FREEZE ×3 — one Codex stale re-emission ruled invalid on
seat-liveness and re-run with a liveness marker) and ran the four-arm
Sonnet 5 ABBA matrix to completion — the first time this line got past
controls (4/4 watcher PASS, SIGINT-only at 5000 ms grace, 0092's
implement.task-context boundary crossed cleanly). Terminal: **NO SHIP
CREDIT** (DECISIONS 0094.1) — candidate-discovery delivered the PLAN
prompt minus the render's single terminal LF (10,015 vs 10,016 bytes;
serialization strip ruled out by candidate-simple's byte-exact delivery in
the same matrix), failing the tested, satisfiable digest conjunct 1/2 vs
the pre-committed 2/2 bar. R1 is NOT refuted — candidate-simple proved the
native shape delivers byte-perfectly with mode absent/rib:false/ACCEPTED —
and candidate arms were FASTER (0.866× summed). Adjudication: Grok CONFIRM
+ Codex AMEND (precision only). **Next action = register the successor
iter (0095): PLAN delivery byte-fidelity** (0089/0090 lineage in the
native structured-field shape; bonus live evidence: control arms' own
delivery varied — mode omitted in one, digest-mismatched too). Instrument
follow-ups from first contact (scored against no one): oracle
evidence-completeness caps every live current-format session at INCOMPLETE
(retained 0091 C1 full-dir replay = INCOMPLETE/82 — the frozen "C1 stays
COMPLETE" gate holds only on the curated self-test fixture) + subagent_type
absent-key vs no-key-pin prose; dispatch-scorer artifacts clause vs the
watcher's spawn-skeleton allowlist. Blind quality for the record: Fable
tie/tie; Grok discovery emitted A=control but with 5/5 mechanically-proven
inverted attributions (`judges-crosscheck.md`). Receipts:
`~/.local/share/nx01/iter0094-reg/` (git: seats/, replay/, unblinding),
`~/.local/share/nx01/iter0094-r5/` (arms/driver/goals); 0092 receipts
unchanged. Context: iter-0093 shipped (DECISIONS 0093.1); iter-0092
implementation green, its R5 closed unscored (DECISIONS 0092.1).

**Current frontier and just shipped — context, do not re-derive**:

- **iter-0091 PLAN dispatch-boundary identity — STAGE A SHIPPED; STAGE B
  CLOSED-FAIL 1/2 AND REVERTED (2026-08-03/04, `c99f3da` + `1818b85` +
  `7c446c1`, then B1 rollback `1e7da13`; DECISIONS 0091.1–0091.3).** The
  outcome-independent schema-2 oracle conserves all seven
  retained arms and closes reversed-window, duplicate-id, and overflowing-time
  edges with 137 assertions. Fable 5/Grok 4.5 preserved frozen P-0091-A3 when a
  formal carrier dropped its outside-window qualifier. Final formal VERIFY
  `rs-20260803T164146Z-2b9ad898cc76` passed mechanical/Codex/Sonnet with zero
  findings. Stage B's C1 was byte-equal `COMPLETE`; C2's invalid native Agent
  mode caused two exact-prompt tool uses in one receipt window, violating the
  cardinality gate. B1 did not survive; Stage A stays.

- **iter-0090 PLAN delivery compliance — IMPLEMENTED `f273877`, NO SHIP
  CREDIT (2026-08-03, DECISIONS 0090.1).** The scoped renderer treatment and
  verification gates are green; the live outcome is 1/2. Canary 1's sole
  `Agent` tool use delivered a 68-byte literal path indirection instead of the
  9,196-byte render; Canary 2 was byte-identical and oracle COMPLETE. Both
  judgment seats classify Canary 1 NONCOMPLIANT and unreplaceable. The
  iteration file's implementation/adjudication section and external canary
  receipts are authoritative.

- **iter-0089 PLAN authority — D1-D3 IMPLEMENTED `6795976` + `830f886`, NO
  SHIP CREDIT (2026-08-03, DECISIONS 0089.2).** Ledger, state-derived cap,
  renderer digest, and all-dispatch oracle landed; two baseline Sonnet
  deliveries both pruned worker-irrelevant judge invocation content, so live
  delivery compliance was 0/2 and transferred to 0090.

- **iter-0088 plan-route + startup dedup — STAGE A SHIPPED (`1312cb7` + D4
  locus `454bc34`), STAGE B CLOSED-FAIL protocol-failed-at-controls
  (2026-08-02, DECISIONS 0088.3).**
  `iterations/0088-plan-route-startup-dedup.md` § "STAGE B EXECUTED" is
  authoritative (control table, both INCOMPLETE adjudications with named
  criteria, stop-all verdict, frozen advisories for the next registration;
  durable receipts `~/.local/share/nx01/iter0088-stage{a,b}/`). H1-v3
  UNSCORED, never resumed inside 0088 — a new registration + new controls
  required. Remaining named residual: `devlyn:engines/SKILL.md` absent from
  lint `critical_path_files` (follow-up; README residual was RESOLVED
  2026-08-02 on user directive).

- **iter-0087 startup semantic dedup — CLOSED-FAIL, REVERTED, NOT SHIPPED
  (2026-07-30).**
  H1-v3 deletes parent-side semantic repository discovery and makes the actual
  Sonnet PLAN worker write immutable criteria before its plan in one return.
  R0/R1 Codex, Fable 5, and Grok 4.5 converged; Terra's F12 canary recovered all
  required fields. Frozen control envelopes are F7 356,260/376,450 ms and F12
  527,257/492,483 ms; each treatment must be <=85% of its matched control and
  must not increase startup. Candidate `24686ec` plus correction `313304c`
  passed implementation review, but F7/T1 and T1R exhausted the single
  incomplete replacement. No ratio was scored and remaining arms did not run.
  `695ef12` reverted the unshipped candidate. A preflight manifest hash field
  was also corrected by the neutral external closeout ledger: raw control and
  treatment engine bytes match at `5c05302a...`; the old `9e028f...` value was
  the spaced source file, not an arm snapshot.

- **Shipped 2026-07-28/29 (one line each; iteration files are authoritative,
  full narratives in git history of this file):** iter-0086 Claude primary
  model attestation (three-seat gate; fixes auxiliary-call false attestation
  only). iter-0085 VERIFY envelope anatomy (post-judge finalization median
  138,631 ms / 25.1% share registered; no dispatcher authorized). iter-0084
  Node lint applicability (observed F7 false-lint trigger closed; nothing
  broader claimed). iter-0083 R-summary-verdict-not-merged (pair-judge
  verdict conservation; emission still uncertified, no durable `pair grok`
  pin). iter-0082 R-weld (collection only; W1 losslessness only; corpus
  `benchmark/ceiling/probes/r-weld-0082/` — regenerate `tracked-baseline.json`
  from the pre-change collector or the tier is decorative). iter-0081
  R-allow-scope (gate part 2 only; v1 FAILED — § GATE RESULTS is the
  instructive record).

**Binding operator lessons from 0081-0083 — all orchestrator failures**: never
handicap a gate seat (a read-only seat cannot run the collector); score the frozen
conjunct, never a proxy; **a bar must not conjoin an independently registered
residual NOR an unsatisfiable conjunct**; **a freeze is not frozen until a seat has
tried to satisfy every conjunct by execution** (asserting the check was run is not
running it — a verifier pointed only at satisfiability caught what two design seats
read past, three iters running); every seat prompt granting a shell must forbid
modifying tracked files; **a wrong claim in a seat packet propagates into the
seat's answer**, so packets get the same verification bar as findings. Do not
duplicate a repository-wide gate inside a fixed per-command literal verifier:
0083's first build gate passed full lint directly but blocked when the same
358-second suite was replayed under a 60-second budget. VERIFY interaction checks
must compose transport state with authenticated summaries; isolated rows missed
the TIMEOUT suppression that fresh Codex found.

**Next work (in order)**:
1. **Register iter-0095 (PLAN delivery byte-fidelity)** from
   [`iterations/0095-plan-delivery-byte-fidelity-STUB.md`](iterations/0095-plan-delivery-byte-fidelity-STUB.md).
   Design round DONE (2026-08-05, receipts `~/.local/share/nx01/iter0095-design/`):
   orchestrator's "invisible byte" position refuted by its own falsifier F2
   (Read shows terminal LF as a final empty numbered line — verified in both
   retained 0094 sessions); adopted synthesis = keep byte-exact gate + 0094
   verdict, amend ONLY the Claude PLAN-delivery instruction (Read
   final-empty-numbered-line cue → reproduce the LF), canonicalization only
   as a pre-named successor path if a live 2/2 bar still fails. Product edit
   routes through /devlyn:resolve; instrument follow-ups (oracle evidence
   scoping + full-dir canary gating + subagent_type ruling; scorer artifacts
   clause) fold into the registration per the STUB. Registered product follow-ups to schedule separately:
   `resolve-bootstrap.py` `git_text` ignores `allow_empty` on nonzero exit
   (detached-HEAD unbootstrappable); `verify-merge-findings.py` crosschecks
   every `*judge.stdout` as pair-side evidence (flipped-seat false BLOCKED);
   `devlyn:engines/SKILL.md` absent from lint `critical_path_files`. H1-v3
   stays blocked until the successor gate earns delivery credit.
2. **Blind-quality axis**: `-22c` A_win 8 / B_win 47 vs `-22a` A_win 19
   / B_win 36 — single-cohort variance vs. real hook-cohort effect is
   unresolved; the next hook-bearing cohort reads it before any quality
   lever is registered.
3. Cell 1 bare-fails admission gate (terra-conditional, last 0070a item).

Still registered, none conjoined: **R-merge-envelope**, **R-comment-finding**,
**R-verdict-default**, **R-rawstream-weld**, **R-envelope-severity-bypass**, and
**R-backtick-preamble**. Their measured boundaries remain in iter-0082; 0083
closed only R-summary-verdict-not-merged.

**Cohort operator rule (new, binding)**: never run `/login` or anything
that rotates the host OAuth token while a cohort is in flight — seeded
arm credentials get revoked mid-row (`-22c` FS1 receipt: invoke_exit 1,
`OAuth access token has been revoked`).

**Cohort/row mechanics (binding, updated 2026-07-20)**: full cohort =
`git worktree add --detach <path> <SHA>` (runner-SHA integrity —
nodeg-cell.py dies if HEAD moves after cell init; inner-loop commits on
main stay safe), then from the worktree
`CEILING_TEST_CLAUDE_BIN=<run-owned copy> CEILING_TEST_NODE_BIN=/Users/aipalm/.nvm/versions/node/v20.19.0/bin/node
nohup bash benchmark/ceiling/scripts/run-nodeg-cell.sh --run-id <fresh>
--tasks "F7,F25,F26,F11,F12,F23,FS1"` (explicit CSV REQUIRED — C2 draw
filter activates only under --tasks; F7 FIRST so a pre8/cmds=0 draw
abort exit-86 is cheap; diagnostic-draw rate ≈ 1/3, relaunch fresh id).
**CODEX PIN = VENDOR BINARY (mandatory)**: CEILING_TEST_CODEX_BIN must
point at the npm vendor Mach-O (`~/.local/share/nx01/pins/codex-0.144.5/bin/codex`,
provenance.json + sha receipt) — NEVER `command -v codex` (Superset
wrapper script; broke under arm isolation and killed cohort
nodeg-20260721a, DECISIONS 0076.4). **UPDATER-PROOF PIN (mandatory)**: `cp` the pinned claude binary to a
run-owned path BEFORE launch (`~/.local/share/nx01/pins/…`) — the
auto-updater deletes old versions from `~/.local/share/claude/versions/`.
**Deleted-version RESTORE recipe (established 2026-07-20)**: fetch
`https://downloads.claude.ai/claude-code-releases/<version>/<platform>/claude`
(darwin-arm64 here), verify sha256 against `<version>/manifest.json`,
chmod +x at the run-owned path; NEVER reinstall into the live versions
store. Treatment-Seat Identity Fidelity (0074.2 (f)): judge-only CLI
drift never licenses a cross-version treatment arm — restore the exact
CLI or label the row a successor row. **Worktree-dirty gotcha**: the
runner refuses cell init while prior run results sit untracked in the
worktree — move them to main-repo `benchmark/ceiling/results/` (their
archival home) before the next launch. **Judge haiku flake**: sonnet
judge attestation can fail on a nondeterministic haiku auxiliary call
in modelUsage — one `--resume` retry passed clean (-20260720b
precedent). Empty-transcript timeout rows (invoke_exit=124) use the
`a-runtime-attestation-source` deviation (0071 F25 precedent);
judge-runner-sha deviation is REJECTED when HEAD matches. Post-hoc
instruments (deterministic, run from main against result dirs):
`attribution.py <attempt_dir>`, `isolation-payload.py --post-hoc
<attempt_dir>` — needed only for worktrees predating the instrument
fixes (pre-294d828); a post-0074 cohort SHA ends this deviation class.
The A-arm worktrees SURVIVE at `~/.local/share/nx01/w/…`; PHASE-6
archive prunes root .devlyn into runs/. Dead run-ids: -20260718f/g/h,
-20260719a-e. Codex builds detached + one retry on silent hang (a
killed-at-report-stage build may be complete on disk — verify + finish
gates yourself before rebuilding; two live hangs observed: 35-min and
66-min zero-output; codex sandbox cannot write .git — orchestrator
commits builds, surfaced in the message).

**Seat standing lessons (per-session scorecards live in the iteration
files)**: verify liveness before gating; synthetic self-tests must be
generated from REAL receipts (two live counterexamples); seat packets get
the same verification bar as findings — 0088 Stage B alone recorded three
orchestrator reversals on named criteria plus one self-caught packet error.


---

## ⛔ Hard operating rules (binding)

1. **Pair-review IS the work** — every non-trivial claim pair-verified at write time; open cited file:line yourself; R-final before commit when results surprise.
2. **Cost framing is BANNED** (memory `feedback_no_cost_talk.md`, HARD). Axes: effectiveness × accuracy × reasonable wall-time.
3. **Verify before claim** — every cited file:line opened at citation time; stale references caused fabrication risk in past iters.
4. **Explain simply** (Korean, decision-maker view) — conclusion + options + recommendation; no internal label walls in user-facing summaries.
5. **Greenfield interface, NOT mechanisms** — any redesign edit must justify why a learned mechanism changes (not just relocates).
6. **Measurement-gated pair policy** — pair ships per-phase only on pre-registered L1-vs-L2 evidence; "no evidence pair needed" ≠ "evidence solo wins"; honest label is "unmeasured".
7. **Measurement tiering — do NOT gate every improvement on the ceiling full-run** (user directive 2026-07-11). Iterate on the fast behavioral instruments as the inner loop: self-tests + token gauge + lint (seconds), then `violation-matrix` / drift-bait bare probes / compliance cells (minutes), then a resolve-framed probe (~10-20 min). The ceiling 3-arm full run (`run-ceiling-tranche.sh`, hours) is a PERIODIC background exam only — run it detached, keep improving in parallel, never block design/impl work waiting on it. Need a quick directional ceiling read → `--tasks <1-2 rows>` (+ `--resume`), not the full corpus. Full-run stays the moat gate for 세계최고 claims (ops #17); it is not the iteration loop.

---

## 🤝 Pair-collab protocol (mandatory for non-trivial work; direction-symmetric)

Per `feedback_codex_collaboration_not_consult.md`; round-shape v2 (2026-07-04). The pair partner is the strongest available OTHER engine — when Codex orchestrates, the partner is Claude (iter-0060 proved reverse invocation works).

- **Round budget: R0 adversarial + R1 reconciliation.** R0 returns, per contested position: strongest counter, strongest form of MY position, synthesis with a NAMED decisive criterion (refute-only rejected). R1 reconciles on the actual diff/raw results. **Further rounds require NEW evidence** (fresh measurement, unopened file) — anti-asymptotic rule (iter-0033g).
- **Position-stating, not verdict-asking.** Convergence is the stop, not "partner agreed" — partner reads the codebase directly and forms independent verdicts.
- **Per-round prompt shape** (all four, every round): (1) source packet — exact file:lines; (2) supersession map; (3) decisive criterion stated BEFORE arguments; (4) the falsifier each side accepts. Codex invocation:
  ```bash
  bash config/skills/_shared/codex-monitored.sh \
    -C /Users/aipalm/Documents/GitHub/devlyn-cli \
    -s read-only \
    -c model_reasoning_effort=xhigh \
    "<prompt>"
  ```
  Output to file (`> /tmp/codex-<topic>/response.log 2>&1`); never pipe wrapper stdout (iter-0009 contract). `-s workspace-write` for delegated implementation; implementation is delegated to Codex CLI per `feedback_implementation_to_codex_2026_07_05`.
- **Adapter/prompt iters** must cite the official vendor prompt guides (Anthropic + OpenAI) as acceptance — "guide section X.Y says Z", not "I think this is better".

---

## 🧭 STANDING USER DIRECTIVES

Block 1 is **strictly user-verbatim**. Never re-summarize Block 1.

### Block 1 (2026-04-28 — North Star + 5/6 principles + Codex pair + 산으로 + docs continuous)

> 한가지만 더. 지금 하고있는 것들이 북극성의 목표를 향해서 no xxxx, worldclass xxx 5대 원칙들을 바탕으로 계속 개선을 해나가고 있는게 맞지? 그냥 오로지 점수를 위해서 하는게 아니고 말이야? 확실하게 해주고 항상 codex cli gpt 5.5 와 함께 compenion 으로서 pair 로 논의하고 최선의 결과에 도달할 수 있도록 끝까지 연구하고 개선해줘. 산으로만 가지마. 이제는 됐다 싶을때까지 계속 돌아. 하면서 계속 docs는 업데이트 해주고, 50% 이상 context가 차면 compact 하고 handoff 를 통해서 지금 내가 얘기한것 토씨하나 틀리지 않고 그대로 각인하고 계속 진화시켜나가.

### Blocks 2-6 (2026-04-29 → 2026-05-03 — FOLDED; verbatim archive in git history of this file, pre-2026-07-20)

Operative content fully carried by binding surfaces — consult those, not
this summary: **B2** six directives → memory `feedback_no_cost_talk` /
`feedback_l2_pair_collaboration` / `feedback_codex_collaboration_not_consult` /
`feedback_pair_vs_solo_empirical` / `feedback_explain_simply` + Hard
rules above. **B3** PLAN=invariants, BUILD=constrained judgment,
EVAL=independent layer → NORTH-STAR product surface. **B4**
engineer-quality floor + cost-ban + score-variance skepticism +
Mission-1-solo-first → NORTH-STAR goal + MISSIONS. **B5** 2-skill
design (ideate optional / resolve standalone / multi-LLM via adapters)
→ NORTH-STAR § product surface (locked 2026-04-30). **B6** round-3
pair-redesign (measurement-gated pair; honest "unmeasured" labels;
HANDOFF cleanup mandate; Codex reads codebase directly) → NORTH-STAR
§ Pair-mode policy (round-3 locked).

### Block 7 (2026-07-06/07 — ceiling mandate + asymmetric harness + endgame + operating priority)

> 일단 얼추 맞는데 가장 중요한건, 엔지니어 품질이 아니라, 세계최고 수준의 대체불가능한 품질의 소프트웨어여야해. 그리고 효율, 성능, 정확도도 전세계 그 누구도 감히 따라할수 없는 천장을 뚫는 압도적인 수준이어야 하고. 그걸 염두에 두고, 지금 가는 방향이 맞는지, 형태 (skill)이 맞는지부터 해서 너의 모든 능력을 총 동원해서 분석하고 해당 목표까지 갈수 있는 방향으로 설계해봐.

> 이게 맞는지 모르겠지만, 결국 에이전트들이 각자 잘하는것을 힘을 합해서 각 에이전트의 잠재력과 성능 품질을 최고로 끌어올리는 하네스여야 한다는거야. 그래서 내가 생각했을때는 최소한의 하네스에 최대 자율이었는데, 그게 틀리면 개선해주고, 올바른 방향으로 align 되도록 해줘

> 그래서 하이브리드를 구상했던거고 에이전트 군단으로 만들어서 하네스 + 루프 엔지니어링으로 나는 최소한의 의도와 목표, 북극성만 주면 끝까지 에이전트들이 협력을 해서 완벽하게 완수하는것을 생각하고있어. 그게 궁극적인 엔드게임이야

> (2026-07-07) 1) codex 의 의견중에 너가 깊이 생각하고 너도 동의하는것만 채택하고 나머지는 너의 생각대로 설계 계획해줘. 2) … 모델의 버전이 바뀔때, 정확하게 어떤 모델이 어떤 포지션에서 가장 강한가를 측정할수 있는 것도 있어야 그 자리를 체크해서 가장 적합한 모델로 사용할수 있을 것 같아.

> (2026-07-07) 일단은 최대한 너가 해줘야해. 천장을 뚫고 세계최고 수준의 Loop Egnineering/Harness Engineering 이 되려면. 최대한 너에게 맡길거야. 너가 없어도 돌아가는건 차선이야.

> (2026-07-07) 압도적이고 독보적이어야해

> (2026-07-07) 핸드오프든 뭐든 앞으로 참조하는 문서들에 방해가 되는 context들은 다 클린업해줘

→ Shipped: NORTH-STAR ceiling contract + ops test #17 + moat=survives-copycat (`eda7e7f`); MISSIONS ceiling addendum + endgame roadmap; iter-0064 STUB; CLAUDE.md/AGENTS.md § Evolution loop; this HANDOFF rewrite (`e58e65c`+). **Operating priority**: strongest available orchestrator (Fable while available) drives the loop directly at maximum depth; orchestrator-neutral continuation is insurance (차선). Harness philosophy ASYMMETRIC: max determinism in the skeleton (code), max autonomy in the intelligence. Codex R0 archive: `/tmp/codex-northstar2/r0-response.log`.

### Block 8 (2026-07-10 — value axes for frontier engines + three-way pair)

> 그러면 우리가 지금 계속 이렇게 진화시키려는 의도와 목표 북극성등을 바탕으로 codex cli gpt 5.6-sol 과 grok 4.5 와 셋이서 함께 의논해가면서 진짜 우리 하네스를 쓰면 모든 모델들의 성능과 효율과 모든 잠재력을 다 사용할수 있게 하도록 계속 진행해줘.

> 그냥 코딩하는것도 좋은데, 이제는 왠만하면 코딩은 다 잘 푸니까 (프론티어 모델이 아닌경우는 효과가 있겠지만), 이제 내가 주로 프론티어 모델을 사용할때는, 코딩 실력도 코딩실력인데, 내 의도나 목표를 얼마나 잘 파악하고 얼마나 잘 쪼개서 얼마나 같이 페어로 협업을 잘하고 얼마나 설계를 그냥 혼자 할때보다 꼼꼼하고 오류없이 확실한 근거를 바탕으로 잘 하는지 등 (그래서 내가 원칙 몇개를 세운거고) 그런게 더 중요할거 같아. Loop 엔지니어링도 결국에 나나 다른 유저가 의도나 목표를 주입하면, 그걸 제대로 의도파악하고 추측하지않고 제대로 된 근거를 바탕으로 제대로 된 판단을 하고 그를 바탕으로 task를 잘 쪼개서 하나씩 차근차근 다른 에이전트들과 페어로 협업하고 검증하고 테스트하고 클린업까지 제대로 완벽하게 말하지 않아도 딱 잘하는 그러한 하네스와 루프 엔지니어링을 만들고 싶은거거든. 그럼에 있어서, 확실하게 전세계 그 어떤 하네스보다 우리것을 쓰면 해당 모델이나 에이전트 (LLM등)를 최대한의 잠재력을 다 꺼내서 쓰고, 협업을 제대로 시켜서 각자 가진 장점을 최대한 발휘해서 시너지를 내도록 하는것, 그것이 우리 목표였잖아? 이거 로드맵이나 의도 목표 등에 context 잘 녹아있는지 확인하고 너와 codex cli gpt 5.6-sol, 그리고 grok 4.5 까지 다 이해해서 다음계속 진행할수 있도록 해줘.

> 방향을 제대로.

> 그렇다고 해서 코딩을 놓자는 얘기가 아니야. 말그대로 각자 에이전트의 코딩능력 분석능력등 기본적인 잠재력은 최대한 가져가고, 추가적으로 이해력, 의도파악 능력, 분해, 설계, 협업 능력, 시너지 등을 더 극대화해보자는 얘기지.

> 이미 알고 있겠지만, 중요한건 하네스로 인해서 원래 모델/에이전트가 가지고 있던 자율성을 기반으로 한 성능이 저하되면 안되고, 오히려 잠재력을 더 증폭시켜야해. 하네스를 너무 꽉 조이면 오히려 안좋지 않을까 하는거니까, 이것도 철저하게 테스트를 해서 규명하고 밸런스를 잘 맞출수 있도록 해줘.

→ Folded: NORTH-STAR § Value axes for frontier engines (2026-07-10, nuance-corrected same day: baseline capability extraction is kept at MAXIMUM — the five axes are ADDITIVE maximization on top, not a substitute); three-way pair protocol live (memory `feedback_threeway_pair_grok_2026_07_10.md`); iter-0068's categorical-trap corpus measures the DISCIPLINE axis (scope/atomicity/cleanup/spec-fidelity). **Corpus roadmap directive (user, same day)**: the reinforcement round exists because the exam corpus previously considered ONLY coding-shaped problems — future corpus expansion must also cover the non-coding axes (intent fidelity / decomposition / design rigor / collaboration), which need different problem shapes than hidden code oracles (candidate instruments named in iter-0068 R-preFreeze record); to be discussed three-way before the next corpus iter. **No-suppression directive (user, same day)**: the harness must never degrade the engine's native autonomy-based performance — it must AMPLIFY potential; over-tightening is a live risk to be rigorously measured and balanced. Existing evidence FOR the risk: iter-0067 neutral judge preferred copycat diffs 16:3 over the devlyn A-arm on saturated rows, and wall 8.33× — both are over-tightening signals. Measurement lever already in hand: saturated rows (bare-solves) become the NO-DEGRADATION control corpus — on them the harness must match bare's objective outcome, not lose the blind quality ranking, and stay within the wall cap; the discriminating rows measure amplification. Balance = win on discriminating rows WITHOUT losing on saturated controls. Asymmetric-harness philosophy (Block 7: max determinism in skeleton, max autonomy in intelligence) is the design principle this tests.

### Block 9 (2026-07-10 — loop architecture: intake skill → queue loop + universal final intent-verification)

> 우리 계속 진행할 로드맵에, 유저가 입력하면 의도파악, 팀으로 설계, 로드맵 설정, task 분리 등등을 하잖아? 그거 skill 로 하나 만들어야 할것 같고, 그 스킬을 통해서 유저 입력과 함께 결과 context가 나오고, 그걸 받아서 두번째 에이전트가 해당 context를 가지고 큐에 넣고, 그 큐를 계속 돌리게 하는 그러한 스탭으로 진행되는걸 loop 로 생각하긴 했어. 그래서 이 부분과, 그리고 하나 빠진건지 아직 있는건지는 모르겠지만, 마지막에 원래 의도나 설계, 목표에 맞게 잘 되었는지도 팀으로 검증하고 아니면 다시 하고 하는게 있어야하는데 resolve에 있다고는 알고 있거든, 없으면 넣어주고. 그리고 resolve를 돌지 않고 해결을 하는 건이라도 그게 되어야해.

> 이건 혼자 생각하지말고 codex 5.6-sol 과 grok 4.5 와도 팀으로 논의해서 결정하고 context에 올려서 로드맵에 넣고 해결/개선하자.

> (same day, full-loop refinement) loop 엔지니어링시에 워크플로우가, 유저인풋>ideate로 팀이 함께 의도파악, 설계, task 분리 등 이 맞는지 > 맞다면 그뒤에 queue에 저절로 넣는건지 아니면 devlyn:qeueu로 직접 넣어야하는건지, 그러면 어떤 ideate가 어떻게 queue에 들어갈지 어떻게 아는지 > 그 후에 drain-queue 로 진행하면 > 팀이 함께 하는데, 오케스트레이터가 직접 할수도있고 resolve로 진행할수도 있겠지 > 그 이후에 다 되면 역시 팀이 함께 검증하고 테스트 하고 클린업하고, 원래 처음 의도대로 잘 되었는지도 팀으로서 체크하고, playwright도 필요하면 사용하고 가능하면 스크린샷으로 UI도 찍고 > 그 뒤에 커밋/푸시 하는 그러한 full loop 를 상상하는건데, 그 의도대로 지금 context가 잘 되어있는지 확인해주고 셋다 팀으로 논의해서 방향이 맞는건지, 수정/개선해야할 포인트가 있는지 등도 얘기해서 업데이트 해놔줘. 그리고 outdated 된 방해되는 context들은 클린업해주고.

→ Current-state facts (verified at record time): `/devlyn:ideate --project` already does intent-elicitation + 3-7-spec decomposition + plan.md (SKILL.md:59; team-design inside ideate is UNMEASURED, not wired); `/devlyn:queue` drain does spec→resolve→outer-loop (SKILL.md:19-22); NO wired handoff plan.md→queue; resolve VERIFY verifies against SPEC (fresh subagent + conditional pair) — intent fidelity = spec fidelity; **plain-conversation (non-resolve) work has NO final intent-verification** — iter-0069.4 deferred exactly this with revisit precondition "user funds a measured mechanism"; THIS directive is that unfreeze (licenses a pre-registered ITER, not permanent prose — 0069.3 rule stands). **→ RESOLVED 2026-07-10: three-way round CONVERGED (Codex + Grok, zero-dissent essentials); design + 5-rung ladder frozen in `iterations/0070-loop-architecture-STUB.md`** — no new skill (evolve ideate --project), plan.md = locked root intent contract, `queue add-plan` wiring, post-drain project intent-closure (≤2 re-queue), shared INTENT_CLOSURE kernel for off-resolve work (semantic, never Stop-hook/regex; "measured" bar defined), pair surfaces last and evidence-gated. Entry condition: iter-0068 closes first.

### Block 10 (2026-07-10 evening — non-coding exam corpus: axes over saturating coding skill)

> 그리고 사실상 코딩 능력은 갈수록 bare 가 좋아질테니까 (모델의 성능이 올라가기 때문에), 그보다는 얼마나 의도를 잘 파악하고 얼마나 잘 설계하고 얼마나 우리가 설정한 원칙들 (추측하지말고, 필요하면 5 why로 생각해서 근본적인 문제를 풀고 등등) 을 잘 활용하는지, 얼마나 다음 에이전트가 작업하기 쉽게 task를 적절하게 잘 쪼개고 분배하고 메타 프롬프팅을 잘하고 context engineering을 잘하는지 등 우리 의도/목표/북극성 등을 잘 참조해서 그에 맞는 시험지를 만들고 테스트 해야하는거 아닌가 생각이 되긴해.

→ Executes Block 8's corpus-roadmap directive; the three-way design round was pulled forward (user license, same message) while the 0068 gate ran — ladder order + live gate untouched. RESOLVED same day: third three-way round CONVERGED (Codex + Grok both GO-WITH-EDITS; every load-bearing citation orchestrator-verified at the cited files). Four instrument cells + shared Non-Coding Admission Kernel folded into `iterations/0070-loop-architecture-STUB.md` § "Non-coding exam corpus fold": **Packet Utility Differential** (the one genuinely uncovered surface — meta-prompting/context-engineering measured as next-agent outcome; supersedes 0033e), **Counterfactual Intent Holdout** (supersedes weak B1 always-halt fixture), **Blind Design-Defect Differential**, **Root-Cause Recurrence rows** (drift-bait extension, no new family). Anti-saturation = kernel manifest fields (cohort identity + re-gate on engine drift), NOT new NORTH-STAR prose.

At `~/.claude/projects/-Users-aipalm-Documents-GitHub-devlyn-cli/memory/`: `feedback_no_cost_talk.md` (HARD), `feedback_l2_pair_collaboration.md`, `feedback_pair_vs_solo_empirical.md`, `feedback_codex_collaboration_not_consult.md`, `feedback_explain_simply.md`, `feedback_implementation_to_codex_2026_07_05.md`, `feedback_test_engine_tiering_2026_07_04.md` (probe/test arms codex/sonnet/opus, never fable), `feedback_executor_codex_always_pair_verify.md`, `feedback_worldclass_ceiling_mandate_2026_07_06.md`.

**Conflict rule**: if HANDOFF and a memory file disagree, stop before editing and ask the user.

---

## 🧠 Empirical TL;DR (what is measured, one screen)

| Surface | Verdict | Evidence anchor |
|---|---|---|
| Codex BUILD/IMPLEMENT routing | **FALSIFIED** | iter-0020: L2−L1 = −3.6 on 9-fixture suite |
| Pair VERIFY on frozen diffs | **PASS** | frozen-verify-gate internal F12/F10 + SWE-bench Lite n11 (avg wall 1.87x, cap 3x) |
| Full-pipeline pair via risk probes | **PASS (small suite)** | F16/F23/F25 bare<solo<pair aggregate (avg wall 1.73x) — NOT broad product superiority |
| PLAN-pair | research-only | iter-0033d/f/g (no empirical subagent introspection; unblock conditions in SKILL.md PHASE 1) |
| Golden fixture suite as evolution signal | RETIRED | solo-saturates 88-99 (`benchmark/probes/README.md`) |
| Contract violations under temptation | live instrument | violation-rate matrix N=4: opus 12/24, sonnet 9/24 at baseline; E1 sentence flipped sonnet B4 4/4→1/4 (iter-0062); prose ceiling → mechanical gates (iter-0046 BUILD_GATE scope, iter-0063 finish-gate) |
| Codex ordinary-invocation pipeline | AGENTS.md IS the binding entry | iter-0061 A/B 4/4-vs-4/4 |
| Engine-symmetric pair invocation | REAL both directions | iter-0060 (codex→claude judge fired via adapter) |
| gemma3:4b as judge | MODEL CEILING — do not re-prompt | iter-0055/0056 |
| Ceiling quality (세계최고 axis) | FAIL-pilot twice (0064 LC3 4.32×; 0067 copycat 16:3, wall 8.33×) — no moat claim | iter-0064/0067 `ceiling-verdict.json` |
| No-degradation (Block 8 suppression axes) | Latest cohort `nodeg-20260722a` (0077.5): complete **6/7 best-ever** · zero K1 · objective 6/7 · blind **A_win 9→19**, B_win 36 ≤45 · wall median **10.659×** (best-ever, below no-lever noise band, still ≥3× cap) · quality bar still unpassed. Interphase lever shipped (12% of baseline); startup unmoved (110.8%) — mechanical-absorption hypothesis falsified; phase_union frozen-five +31.7% | `nodeg-20260722a` verdict + corrected-baseline.json; DECISIONS 0077.5 (history: 0073.2/.3) |
| C1 Stop-hook (terminal-claim pressure) | claude route VETO-CAPABLE — 5/5 BLOCK_HONORED strict bar; HONEST BOUND: CLI caps stop-hook loop (~9) — C1 = pressure, C2 = authority; codex ROUTE-DISABLED-BY-HARNESS, omp unmeasured | `benchmark/ceiling/probes/c1-stop-parity/results/`; DECISIONS 0074.3 |
| T1 packet calibration (seat×defect) | complementary override: catalog admits ONLY sonnet, credential ONLY terra (risk-diff 1.0 both) → routed-seat v2, validation fixtures landed | 0070a Amendment 2 + addendum 9; `benchmark/noncoding/validation/` |
| Seat fitness (모델 × 포지션) | matrix live; 5 current cells; executor/pair-judge pins fail-closed "recert required" | `benchmark/seats/seat-matrix-2026-07-07.json` |

Working instruments: violation matrix (`run-violation-matrix.sh`), compliance cells (`run-compliance-cell.sh` + `check-compliance-cell.py`, now incl. `finish_gate_ran`), drift-bait probes (bare + resolve-framed), judge-quality bench (+codex route), frozen-VERIFY pair gates, token gauge (`scripts/skill-token-gauge.py`), **ceiling 3-arm harness** (`benchmark/ceiling/scripts/run-ceiling-tranche.sh`), **seat matrix + recert runner** (`benchmark/seats/recert-seats.sh`, fail-closed pins).

---

## 📍 Project state (verify before editing)

- **Branch**: `main`, pushed through `a05a262` + this HANDOFF commit (2026-07-20 evening). Run `git log --oneline -10`. Release/installer surface (README/bin publish commits) is USER territory, hands off.
- **Engine pins**: `.devlyn/engines.json` = `{"executor": "codex"}` (machine-local; orchestrator passes `--pair-verify` on resolve runs per `feedback_executor_codex_always_pair_verify.md`).
- Housekeeping (deferred per user 2026-04-30, unchanged): 4 dirty `.claude/worktrees/agent-*` — save patches before any removal; NOT in iter scope.

### Cold-start sanity check (~30s)

```bash
git status                                  # main, clean
bash scripts/lint-skills.sh                 # "All checks passed." (npm-pack check is occasionally slow — rerun once before diagnosing)
diff -q config/skills/devlyn:resolve/SKILL.md .claude/skills/devlyn:resolve/SKILL.md
diff -q config/skills/_shared/finish-gate.py .claude/skills/_shared/finish-gate.py
python3 -c "import json; v=json.load(open('benchmark/ceiling/results/nodeg-20260713/nodeg-verdict.json')); b=v['bars']; assert b['objective']['passed'] and not b['quality']['passed'] and not b['wall']['passed']" && echo "nodeg 3-bar verdict ✓"
bash benchmark/ceiling/scripts/test-nodeg-cell.sh >/dev/null 2>&1 && echo "nodeg selftests ✓"
python3 benchmark/noncoding/scripts/classify-defect-family.py --self-test >/dev/null 2>&1 && echo "classifier ✓"
python3 benchmark/noncoding/scripts/conformance-gate.py benchmark/noncoding/validation/* >/dev/null 2>&1 && echo "validation fixtures gate ✓"
python3 config/skills/_shared/run-bounded.py 1 -- sleep 3 >/dev/null 2>&1; [ $? -eq 124 ] && echo "run-bounded ✓"
python3 config/skills/_shared/spec-verify-check.py --self-test && echo "spec-verify self-test ✓"
python3 config/skills/_shared/state-phase-write.py --self-test && echo "phase-write (L-D) ✓"
python3 config/skills/_shared/terminal-claim-check.py --self-test && echo "terminal-claim ✓"   # moved to _shared in 0078 Stage A (5339e41)
python3 config/skills/_shared/collect-codex-findings.py --self-test && echo "collector (0080 envelope gate) ✓"
python3 benchmark/ceiling/probes/r-weld-0082/test-collector-contract.py   # 110 checks incl. 12 real captures + 61 tracked non-regression (iter-0082)
python3 benchmark/ceiling/scripts/attribution.py --self-test >/dev/null && echo "attribution ✓"
python3 benchmark/ceiling/scripts/isolation-payload.py --self-test >/dev/null 2>&1 && echo "isolation-payload ✓"
command -v codex && codex --version 2>&1 | head -1
```

If any unexpected output, do NOT proceed. Surface to user.

---

## 🚫 Forbidden (binding; full rationale in the cited iters)

- No iter-0033h-style PLAN-pair firewall attempts (unblock conditions: SKILL.md PHASE 1 + iter-0033g §H). No deleting closed-iter replay assets.
- No degrading L1 solo behavior (revert-smallest-unit + re-smoke; 2× fail → surface).
- No skipping pair-collab rounds; no trivial questions to user mid-pipeline (pair first; surface only strategic ambiguity with options + recommendation).
- No bypassing CLAUDE.md Core principles (7 + 3); no cost framing; no fable test arms.
- No pre-registering iter-0035 real-project trial without user-supplied project + task + developer.
- Skill/CLAUDE.md/AGENTS.md edits require: user mandate, observed failure, or probe-guarded evidence. "Could be cleaner" is drift.
- No broad full-pipeline L2 claims beyond the measured F16/F23/F25 + SWE-bench n11 surface; no 세계최고/대체불가능/압도적 claims before the iter-0064 instrument exists (ops test #17).
- Thermometer discipline: probes are thermometers, not targets; shipped contract text never names fixture literals.

---

## ⏭️ End of HANDOFF

Evolution loop trajectory since re-open (2026-07-03): 0037-0039 conversational handoff + queue → 0040 cross-CLI portability → 0042-0047 instrument panel → 0048-0050 language-neutral + doctor → 0051-0057 local-backend shipped→measured→deleted → 0058-0060 violation-rate axis + engine-symmetric pair → 0061 F6 closed (AGENTS.md binding) → 0062 contract decidability (E1 shipped) → 0063 mechanical finish-gate → 0064 ceiling & seat instrument SHIPPED, pilot FAIL-pilot on efficiency → 0065 hands-free large + bounded pair-VERIFY SHIPPED → 0066 pre-VERIFY overhead SHIPPED → 0067 ceiling tranche 2 MEASURED, verdict **FAIL-pilot** (de-biased instrument, fresh django holdout: objective tie, neutral judge prefers copycat 16:3, wall 8.33×) → 0068 discriminating corpus CLOSED VALID-NEGATIVE (isolation v2 permanent) → 0070a non-coding instruments → 0071 proportional escalation SHIPPED (wall levers later valid-negative) → 0072 changed-surface closure SHIP-CREDITED then CLOSED (first 11/11 row) → **0073 attribution-complete re-measure MEASURED then CLOSED (quality 0/7 · wall 12.1× · objective 7/7 via exact-pin FS1 re-row · bottleneck ≠ IMPLEMENT — residual+VERIFY dominate, 9 rows unanimous) → 0074 terminal-claim C2 binding SHIPPED + C1 probe frozen/built/MEASURED (claude route veto-capable 5/5; CLI loop-cap honest bound — C1 pressure, C2 authority)**. Detail: DECISIONS.md + iteration files. Mission 1 not formally closed (test #15 user-gated). 압도적·독보적 is the bar; the instruments made it losable — it loses today on wall (12×) and blind quality (0/7), and for the first time the loop knows WHERE the wall goes. That honesty is the moat-in-progress.
