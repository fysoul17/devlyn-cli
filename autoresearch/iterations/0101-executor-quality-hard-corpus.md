---
id: "0101-executor-quality-hard-corpus"
title: "Executor-quality discrimination-regime cell — multi-invariant interaction corpus N=32, opus-5 vs fable-5 (iter-0100 SATURATED successor)"
kind: instrument
status: DESIGN-FROZEN 2026-08-09 — sol R0 REVISE ×8 adopted (R0-0101-LIVE-sol) + grok R1 REVISE ×5 adopted (R1-0101-LIVE-grok; grok additionally VERIFIED the 32-row table counts and the CI-touch bootstrap arithmetic by direct execution); EXECUTION DEFERRED to a new session per user directive — resume recipe in HANDOFF § iter-0101
complexity: high
depends_on: ["0100-main-ai-executor-quality"]
---

# iter-0101 — executor-quality hard corpus (discrimination regime)

## Why this iter exists (pre-flight 0)

iter-0100 CLOSED at TERMINAL=SATURATED (2026-08-09, cohort
`mx-20260809T1210Z`): both `claude-opus-5` and `claude-fable-5` swept
the 12-task single-invariant corpus 24/24 all-manifestations-clean
(Δ=0.0); the sonnet dry arm had already swept it. The live signal
(user-observed, code-verified opus-5 defects caught by codex sol pair
on real long-horizon multi-invariant work) remains UNIDENTIFIED, and
the same session produced live counter-evidence that hard-regime
defects are not opus-specific (audit-confirmed defects in
codex-authored frozen scorer bytes and fable-authored apparatus).
The frozen 0100 rule pre-named this successor: harder corpus, new
registration.

**Scope of claims (R0-adopted limit)**: this cell tests ONE H4
candidate — multi-invariant interaction load — under oracle-closed
scoring. It cannot causally resolve the live signal: repository
scale, long-horizon session context, and pair-loop framing effects
remain OUTSIDE this corpus shape. A positive result confirms an
interaction-load gap; a null bounds only this shape. H2 deference
probe stays demoted.

## Decisive criterion: ORACLE-IDENTIFIED SEPARATION AFTER AN EASY-REGIME SCREEN

All 0100 oracle laws carry over (mechanical oracle only; ground truth
independent of compared models). Before freeze, a non-scored sonnet
arm must reject corpora that are obviously too easy or pathologically
concentrated. Passing this gate demonstrates difficulty relative to
sonnet only; it does not prove variance or separation between opus-5
and fable-5. SATURATED remains a valid negative result (read as "both
scored engines clear a band the calibrator does not").

## Design

### Corpus — N = 32 tasks, 8 per class (R0 power adjudication)

Planning simulation (registered percentile-bootstrap shape, paired SD
0.30, 600 synthetic cohorts/cell, δ=0.15): N=12 confirms a TRUE
Δ=0.30 only 44% and refutes a TRUE Δ=0 only 48% — INCONCLUSIVE modal;
N=32 gives ≈83%/80%. Adopted **N=32, IDs `EQ2-{UA,MI,AF,BD}{1..8}`,
2 reps × 32 tasks × 2 engines = 128 scored runs** under the named
criterion DECISION REACHABILITY. The planning alternative is Δ=0.30
with paired-task SD ≤0.30; δ_defect=0.15 remains the boundary.
SATURATED = both engines ≥63/64 all-clean runs.

### Task shape (frozen-validator-compatible, R0 B-adjudication)

Every task: **10-15 regular files under `visible/`** (frozen
validator cap is 15 — the draft's 10-25 was a collision, corrected),
exactly **five manifestations** with roles `axis1-a`, `axis1-b`,
`axis2-a`, `axis2-b`, `interaction`, and ONE compound invariant
sentence copied byte-for-byte into every manifestation (frozen
`validate-task.py` same-binding law). The single bound visible
excerpt must state both axes and their composition. `symptom.patch`
passes all four single-axis manifestations and fails `interaction`;
`gold.patch` passes all five; `noop` fails. Python 3 stdlib (odd
task index) or Node ≥20 no-deps (even index). Fresh authorship — no
reuse of 0100 fixtures, drift-bait, or ceiling corpus; 0100 corpus-B
**behavioral-tuple** distinctness binds by reference. **Family/axis
spread for 0101 is the registered pair table** (eight distinct pairs
per class); the 0100 "exactly one primary family per task" rule is
**superseded** here because every task is a two-axis compound
invariant — do not invent a primary-family label at VERIFY (R1
grok).

**Validator**: `validate-task.py` stays byte-frozen (sha256
769a1826…). A NEW frozen `validate-hard-task.py` first invokes it,
then enforces: five-role topology, exact symptom pass-vector
(4 pass + interaction fail), registered axis assignment per the
table below, 10-15 visible-file constraint, and the same leakage
token set additionally applied to `task.json.goal` (0100 validator
never scanned the goal text).

### Axis-pair templates (canonical trigger/outcome per pair)

Axes: O=ordering, R=rollback, I=idempotency, A=auth-order,
E=error-priority. Ten unordered pairs; each row fixes the canonical
trigger and required composed outcome that every task with that pair
must instantiate in its own domain.

**Axis role order (frozen; R1 grok)**: for pair code `XY`,
`axis1 = X` and `axis2 = Y` (first letter, then second letter of the
pair code as written below). Manifestation ids must be exactly
`axis1-a`, `axis1-b`, `axis2-a`, `axis2-b`, `interaction`.
`validate-hard-task.py` embeds the full frozen id→pair map from the
authoring table and checks each task's pair and role ids against
that map; no other axis order is legal under this registration.

| pair | canonical trigger | required composed outcome |
|---|---|---|
| OR | lower-priority entity arrives first; a middle entity partially applies then fails | higher-priority wins AND the failed entity's tentative state is fully released for a later entity |
| OI | duplicate submission of a queued entity around a priority reorder | priority order holds AND the duplicate is absorbed exactly-once regardless of arrival slot |
| OA | privileged and unprivileged requests interleave in priority order | authorization is decided BEFORE priority placement; denied entities never consume ordered slots |
| OE | malformed and valid entities interleave under priority | error-priority (reject reason ranking) composes with processing order; rejects never block valid placements |
| RI | replay of a batch whose first application partially failed and rolled back | rollback restores pre-state AND the replay applies exactly-once from clean state |
| RA | a batch mixing authorized and unauthorized operations | unauthorized op aborts the whole batch atomically; auth check ordering never leaks partial writes |
| RE | multiple failure causes in one batch (validation vs conflict) | the highest-priority error is reported AND the store is byte-identical to pre-batch |
| IA | repeated identical requests under rotating/expired credentials | idempotency key honored only for authorized calls; auth failure never records a dedup entry |
| IE | duplicate submissions that would each fail validation differently | first-seen error priority is stable across duplicates; no duplicate creates a second error record or side effect |
| AE | unauthorized request that is also malformed | auth-order beats validation in the error contract; the response/exit reflects auth failure and no validation side effect occurs |

### Authoring table (frozen; fixture internals remain IMPLEMENT-creative)

Language: odd index = Python stdlib, even = Node ≥20 no-deps. Domain
and component boundary are fixed per row; trigger/outcome = the
pair's template instantiated in that domain. Distinctness tuple =
(boundary, template trigger, template outcome) — all 32 must remain
distinct after entity renaming, and vs the 12 iter-0100 tasks.

| id | pair | domain | component boundary |
|---|---|---|---|
| EQ2-UA1 | OR | seat reservation | hold queue vs seat map |
| EQ2-UA2 | OI | print queue | spooler vs job dedup index |
| EQ2-UA3 | OA | expense approval | approval router vs role gate |
| EQ2-UA4 | OE | invoice batch intake | line parser vs posting order |
| EQ2-UA5 | RI | backup rotation | snapshot applier vs catalog |
| EQ2-UA6 | RA | bank transfer batch | ledger writer vs mandate check |
| EQ2-UA7 | RE | inventory transfer | stock mover vs discrepancy reporter |
| EQ2-UA8 | IE | poll voting | ballot intake vs rejection log |
| EQ2-MI1 | OR | auction bids | bid book vs settlement |
| EQ2-MI2 | OI | notification fanout | scheduler vs delivery dedup |
| EQ2-MI3 | OA | room booking | calendar placer vs access policy |
| EQ2-MI4 | RI | migration runner | step applier vs journal |
| EQ2-MI5 | RE | order returns | refund engine vs reason ranker |
| EQ2-MI6 | IA | coupon redemption | redemption store vs session auth |
| EQ2-MI7 | IE | waitlist promotion | promoter vs duplicate-entry log |
| EQ2-MI8 | AE | artifact registry | publish gate vs schema check |
| EQ2-AF1 | OR | parking assignment | slot allocator vs release pool |
| EQ2-AF2 | OA | ticket escalation | severity router vs on-call ACL |
| EQ2-AF3 | OE | gradebook import | row validator vs rank order |
| EQ2-AF4 | RI | cache invalidation | purge batch vs generation counter |
| EQ2-AF5 | RA | subscription proration | charge writer vs plan entitlement |
| EQ2-AF6 | IA | loyalty points | accrual store vs member token |
| EQ2-AF7 | IE | meeting scheduler | slot request vs conflict reporter |
| EQ2-AF8 | AE | certificate renewal | issuance gate vs CSR validation |
| EQ2-BD1 | OI | media transcode queue | encoder feed vs manifest dedup |
| EQ2-BD2 | OA | firmware rollout | wave sequencer vs device attestation |
| EQ2-BD3 | OE | DNS zone editor | record applier vs syntax ranking |
| EQ2-BD4 | RI | shipment manifest | leg applier vs tracking journal |
| EQ2-BD5 | RA | quota accounting | debit batch vs tenant scope check |
| EQ2-BD6 | RE | warehouse picking | pick executor vs shortage reporter |
| EQ2-BD7 | IA | feature flags | flag mutation vs actor token |
| EQ2-BD8 | AE | rate limiter config | limit writer vs admin gate |

(BD rows additionally carry the 0100 BD class law by reference: the
goal directs change in one component; the DEPENDENT component's
composed contract is the invariant; symptom repairs the visible
break while the interaction manifestation on the dependent path
fails.)

### Difficulty calibration gate (R0-replaced; NO adaptive tuning)

- Calibrator: `claude-sonnet-5`, **2 reps × 32 tasks**, frozen
  apparatus, run after all tasks are admitted, against the CANDIDATE
  corpus manifest (see freeze order). Per-run `f` defined exactly as
  the scored estimator; `q_cal[t]` = two-rep mean; any
  infrastructure-invalid row makes the launch UNSCORED; catastrophic
  or incomplete rows contribute f=1.
- **The gate passes iff**: `1/5 ≤ mean_t(q_cal[t]) ≤ 3/5` AND
  `1/5 ≤ median_t(q_cal[t]) ≤ 3/5` AND ≥22 of 32 tasks satisfy
  `0 < q_cal[t] < 1` AND ≤2 tasks satisfy `q_cal[t] = 1`.
  All comparisons use exact `fractions.Fraction` (no float).
  **Even-n median (n=32, mandatory)**: sort `q_cal` ascending;
  `median = (q_sorted[15] + q_sorted[16]) / 2` (0-based indices —
  average of the 16th and 17th order statistics). No lower-/upper-
  median alternative. (R1 grok: with fifths × 2-rep means, q_cal ∈
  multiples of 1/10; band edges are reachable and decidable under
  exact Fractions.)
- **There is ONE valid calibration evaluation.** Up to three
  launches exist only to replace infrastructure-invalid launches on
  byte-identical task+apparatus digests. A valid band miss
  terminates the registration `CALIBRATION_MISS`; no task may be
  hardened, softened, replaced, or re-run under this registration —
  any changed corpus requires a REVISED registration before another
  attempt. (R0 named delta: the draft's "difficulty-only edits, 3
  rounds" was unenforceable semantic tuning; adopted sol's
  one-evaluation rule wholesale.)
- **No difficulty oracle before the one valid calibration
  evaluation** (R1 grok — closes the authoring-time tuning
  loophole): from the start of batch-01 through candidate seal, no
  invocation of `claude-sonnet-5`, `claude-opus-5`, or
  `claude-fable-5` may be used to estimate manifestation-fail rates,
  band position, or "is this hard enough?" on any EQ2 workdir or
  partial fixture. Resolve executor/pair may implement and run
  mechanical validators/oracles only. A candidate sealed after such
  a probe is void; the registration does not authorize a second
  formal calibration on a retuned corpus. (Formal calibration
  remains the sole difficulty measurement; no pilot arm is
  authorized.)
- Scoring the calibration ledger requires a NEW frozen
  `score-calibration.py` (single-engine ledger; `score-cohort.py`
  mechanically requires the two-engine paired matrix; exact-Fraction
  band math as above) with `--self-test` covering at least: (a) band
  PASS control; (b) mean below 1/5; (c) mean above 3/5; (d) median
  below 1/5 with mean in-band; (e) median above 3/5 with mean
  in-band; (f) interior count <22; (g) total-fail count >2; (h)
  UNSCORED on any infra-invalid row; (i) byte-determinism of the
  band verdict.

### Arms (inherited from 0100 + enumerated amendments)

Identical to 0100 § Arms (exact IDs `claude-opus-5`/`claude-fable-5`;
prompt bytes = task.json.goal only; tools
`Read,Grep,Glob,Edit,Write,Bash`; effort pin `high`;
`--strict-mcp-config`; `--output-format json` modelUsage exact-ID
attestation; opaque workdirs; scrubbed env; stdin=DEVNULL;
prompt_sha256 attestation; pinned updater-proof CLI; ABBA-interleaved
2-lane detached launch; never near 12am KST). **The ONLY allowed
driver/launcher changes (pre-registered)**:
`TASKS_ROOT = benchmark/executor-quality/tasks-0101`; task list = the
exact 32-ID set; `BOUND_SEC = 1800` (outer subprocess bound stays
+60; docstring 900→1800); DELETE the per-row `driver_sha256` field
(0100 lesson: every ledger field must pass the scorer schema-gate
proof); `CORPUS_MANIFEST` + digest constants point at the iter-0101
candidate seal; launcher count 48→128 and lane schedule generalized
to 32 tasks. Everything else byte-preserved (stdin DEVNULL, prompt
digest, attestation, failure taxonomy, scrubbed env, pinned CLI,
run-bounded sha db9ed383…).

### Metrics + decision rule (inherited; enumerated scorer amendment)

Estimator frozen (exact-Fraction f/q/R/d/Δ; paired-task bootstrap
seed 20260809 × 100000; catastrophic-or-incomplete f=1; strict 3/20
bounds; exactly-one-terminal). Pre-registered scorer commit changes
ONLY: `FROZEN_TASKS = {f"EQ2-{p}{i}" for p in (UA,MI,AF,BD) for i in
1..8}`; `--expected-tasks` default 32; self-test controls re-derived
for N=32 — INCONCLUSIVE control (16 zeros + 16 × 2/5), CI-touch
control (7 × 2/5 + 25 zeros → upper bound exactly 3/20), substitution
control (`EQ2-UA1 → EQ2-UA99`), SATURATED proof resolving to 63/64,
plus the four 0100 repro classes re-run against the new set. Terminal
precedence and δ unchanged; only H1_CONFIRMED changes routing.
`H1_MATERIAL_GAP_REFUTED` bounds a ≥15pp gap at this regime; an
observed point estimate below 0.15 or a refuted directional
prediction does NOT establish that bound when the terminal is
INCONCLUSIVE.

### Pre-registered prediction (single; R0 deleted P-2/P-3)

- **P-0101-1**: opus-5 manifestation-fail rate exceeds fable-5's by
  ≥ δ = 0.15 (the live signal under H1 at a screened difficulty).
- P-0101-1 refuted with terminal H1_MATERIAL_GAP_REFUTED → a
  live-signal-sized interaction-load gap is excluded at this shape;
  remaining live-signal candidates (repo scale, long-horizon
  context, session effects) are NEW registrations. (R0 subtraction:
  P-2 was a weak catastrophic proxy that contributed nothing in
  0100; P-3 required an interaction diagnostic the frozen scorer
  cannot see.)

## Freeze protocol (R0-corrected order)

1. Corpus lands via **8 `/devlyn:resolve --pair-verify` runs**
   (executor pin codex): batch `i` authors `EQ2-UAi → EQ2-MIi →
   EQ2-AFi → EQ2-BDi`, one task per execution phase, both validators
   green per phase gate. Specs at
   `docs/specs/iter0101-executor-quality-batch-01..08/spec.md`,
   each carrying the `<!-- devlyn:verification -->` sentinel,
   frozen-scripts sha pins, corpus-topology gate for its cumulative
   ID set, and non-regression sweep of all previously admitted EQ2
   tasks. `validate-hard-task.py` + `score-calibration.py` + the
   scorer amendment land in batch-01's spec (the only run whose
   authorized surface includes scripts).
2. Candidate corpus tree hash + flat manifest created.
3. Calibration driver/runner frozen against the CANDIDATE manifest.
   **Calibration apparatus (pre-registered; separate from the matrix
   change list; R1 grok)**: same 0100 driver/launcher lineage;
   engine set = `{claude-sonnet-5}` only; attempt count = 64 (2 reps
   × 32); ledger is single-engine and is scored ONLY by
   `score-calibration.py` (never `score-cohort.py`); `TASKS_ROOT` /
   candidate manifest / digests / `BOUND_SEC=1800` / stdin DEVNULL /
   prompt_sha256 / attestation / scrubbed env / pinned CLI match the
   matrix rules; no `driver_sha256` field. Matrix apparatus follows
   the "ONLY allowed changes" list above and is frozen only after
   band PASS + candidate promotion.
4. Calibration arm runs (2 reps × 32, sonnet).
5. Band PASS → candidate digest promoted UNCHANGED to final; band
   miss → `CALIBRATION_MISS`, stop.
6. Matrix launcher + final apparatus hashes frozen.
7. Both-seat pre-arm audit (sol + grok, liveness markers; residual
   attack rights preserved; synthetic-ledger proofs incl. the four
   0100 repro classes).
8. 128-run scored matrix, detached, fresh cohort ID; schema-exact
   ledger by construction (no projection).

## Matrix integration

Same clause as 0100: `executor_quality` folds into
`benchmark/seats/recert-seats.sh` as a manual suite recording both
cells (0100 SATURATED + this terminal) in `seat-matrix.py`
`main_ai_executor`; `claude-fable-5` never enters shared recert
`--engines` (scoped user exception). The 0100 fold-in may land
before or with this cell; neither gates the other.

## Budget/wall (informational; R0-corrected)

Corpus authoring: 8 resolve runs across multiple sessions (one task
per exec phase — no wall-kill sequencing; a timeout is a failed run,
not a primitive). Calibration: 64 sonnet runs. Matrix: 128 runs ×
3-30 min at 2 lanes ≈ 3.2-32 h of lane wall — plan MULTIPLE detached
overnight windows or raise to 4 lanes at launch discretion (recorded
in the cohort receipt), never near 12am KST.

## Receipts layout (frozen)

```
~/.local/share/nx01/iter0101/
  registration/        R0/R1 packets and liveness logs
  build/batch-01..08/  spec hash, resolve run id, validator logs
  calibration/attempt-N/  candidate tree/manifest hashes, ledger,
                       per-attempt prompt/oracle receipts, band verdict
  freeze/              final tree hash, flat manifest, scorer and
                       apparatus SHA-256 files, synthetic proofs
  audit/               packet, sol log, grok log, falsifier repros
  matrix/<cohort-id>/  lane receipts, schema-exact ledger, verdict
```

Every calibration receipt binds task bytes, apparatus bytes, exact
sonnet identity, rep, and attempt number.

## Design notes (R0 adoption record)

sol R0 REVISE ×8 adopted in full (R0-0101-LIVE-sol,
`~/.local/share/nx01/iter0100-prearm/sol-0101-r0.log`): calibration
claim weakened to easy-regime screen; adaptive tuning replaced by
one-evaluation CALIBRATION_MISS rule; N=12→32 under DECISION
REACHABILITY (power table 44%→83%); frozen-validator collision
(10-25 files vs 15-cap) corrected + `validate-hard-task.py` wrapper;
scorer amendment enumerated; P-0101-2/3 deleted (subtractive);
"wall-kill as designed recovery" deleted (No-workaround) — replaced
by one-task-per-phase; freeze order corrected
(candidate-manifest-before-calibration); receipts layout + wall
estimate frozen. sol's strongest counter is recorded as the § Scope
of claims limit.

grok R1 REVISE ×5 adopted in full (R1-0101-LIVE-grok,
`~/.local/share/nx01/iter0100-prearm/grok-0101-r1.log`): even-n
median frozen (avg of 16th/17th order stats, Fraction-exact —
undefined median could flip PASS/MISS on the same ledger); axis role
order frozen to pair-code letter order + validator id→pair map;
authoring-time difficulty-oracle prohibition (probe-then-seal voids
the candidate); 0100 single-primary-family rule superseded by the
pair table; calibration apparatus deltas enumerated. grok VERIFIED
by execution: 32-row table counts (8 distinct pairs per class, all
domains/boundaries unique, all pairs ∈ templates), CI-touch control
arithmetic TRUE under the frozen bootstrap (7×2/5 + 25 zeros → upper
bound exactly 3/20), EQ2 prefix parses in the existing class parser.
Known residuals (accepted, non-blocking): batch-01 surface is
heavier than other batches (2 new scripts + scorer amendment + 4
tasks — mitigated by one-task-per-phase); a soft-but-passing corpus
remains possible under the weakened screen claim; EQ2-MI8 "artifact
registry" is the softest domain-noun neighbor to 0100 EQ-UA2
"artifact catalog" (different pair/boundary; behavioral-tuple law
governs).

## Execution log (2026-08-09 → 2026-08-10 session)

Freeze-protocol step 1 progress — 16/32 candidate tasks admitted:

| batch | run | terminal | fix rounds (all primary-codex HIGH findings) |
|---|---|---|---|
| 01 (scripts + EQ2-*1) | rs-20260809T125952Z | PASS | 1 — MI1 re-authored (renamed structural copy of UA1) |
| 02 (EQ2-*2, Node) | rs-20260809T144652Z | PASS | 1 — UA2 (copy of BD1) + BD2 (copy of AF2) re-authored |
| 03 (EQ2-*3) | rs-20260809T155123Z | PASS | 1 — UA3/AF3 oracle `__pycache__` workdir-mutation guard; AF3/BD3 same-reason tie-break coverage |
| 04 (EQ2-*4, Node) | iter1 rs-20260809T164937Z BLOCKED:verify-exhausted; iter2 rs-20260809T175755Z | **CLOSED PASS (2026-08-11 close-out)** | iter1 r0 ×4 (MI4/BD4 symptom rollback-incorrectness, UA4 copy of AF3, MI4/AF4/BD4 shared RI oracle template) → fix; r1 re-fired UA4 topology + strawman symptom → iter2 re-authored UA4 (1e40f67); BUILD_GATE + MECHANICAL + pair claude green in-run; primary codex judge re-run 2026-08-11 after seat recovery (diff dc53576...1e40f67, 204s, 0 findings, PASS) → merge PASS 3/3, evidence-valid; run archive + receipts completed |

Batch-01 spec pair-reviewed pre-commit (sol REVISE ×4, R1-0101B01-LIVE-sol,
incl. CI-touch corrected to exact [3/80, 3/20] by execution ×2). Batch-02
spec pair-reviewed as the 03-08 template (sol REVISE ×7,
R1-0101B02-LIVE-sol); batches 03-08 specs generated by row substitution and
mechanically verified against the frozen authoring table (`76657bd`).
Scripts landed: `validate-hard-task.py` (1f809e33…), `score-calibration.py`
(418f3738…), `score-cohort.py` N=32 amendment (5af3c1bd…);
`validate-task.py` byte-frozen (769a1826…) throughout.

**Harness product findings from this session (registered, not fixed here)**:
(1) `verify-merge-findings.py` fail-opens the PRIMARY judge — a missing
`verify.findings.jsonl` merges as `judge: PASS` (`source_verdicts`
initializes PASS; only pair_judge is spawn-evidence-gated) — the iter-2
batch-04 state's `verify: PASS` is EVIDENCE-INVALID for exactly this
reason; (2) `verify.judge.summary.json` is not in `archive_run.py`
PER_RUN_PATTERNS, so a stale copy survives into the next run's `.devlyn`
root (quarantined evidence: `~/.local/share/nx01/iter0101/build/batch-04/`);
(3) collector vs merge parser tolerance mismatch (strict JSONL vs
preamble-tolerant `*judge.stdout` crosscheck) — batch-02 receipt has the
incident. Operator deviations logged: probe-worker malformed `tag_evidence`
corrected by same-worker continuation + orchestrator bare-token
normalization (batch-04 iter1); one verify-transition `--verdict` misuse
retried (batch-01); plan phase-3 manifestation-id paraphrase corrected by
spec quotation in dispatch (batch-01).

**Recurring authoring failure class worth carrying into batches 05-08
dispatch prompts**: same-pair structural copying (5 HIGH findings across 3
batches), oracle workdir mutation, tie-break coverage gaps, strawman
symptom branches keyed on input mix.

**RESUME executed 2026-08-11 (codex seat recovered before the posted
reset)**: ① writer-check clean ② batch-04 CLOSED PASS — primary codex
VERIFY judge re-run on diff `dc53576...1e40f67` (spec sha 6aaad08f…
re-verified; 204s, 0 findings), merge PASS 3/3 evidence-valid; the state's
prior fail-open `verify: PASS` is superseded (product finding 1 itself
still stands as a registered class). Bonus live receipt: the first merge
attempt without `claude-judge.stdout` in `.devlyn` root correctly fired
`verify-pair-required-output-missing` — the pair spawn-evidence gate
works as designed. Remaining: ③ batches 05-08 sequentially (per-batch
flow identical to 03; carry the four recurring authoring failure classes
into dispatch prompts) ④ candidate seal → calibration → both-seat
pre-arm audit → 128-run matrix per the frozen recipe above.
