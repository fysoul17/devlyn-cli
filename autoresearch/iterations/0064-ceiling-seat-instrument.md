# iter-0064 — ceiling & seat-fitness instrument family v0

status: PRE-REGISTERED 2026-07-07 (design contract locked 2026-07-07 prior
session; pre-registration frozen below BEFORE any arm run; Codex R0
SHIP-WITH-EDITS — all 5 MUST-FIX adopted below; archive
`/tmp/codex-iter0064/r0-response.log`)

**Serves**: Mission 1 ceiling axis (NORTH-STAR ceiling contract + ops test
#17, added 2026-07-06) + HANDOFF Block 7 (user ceiling mandate + seat
question verbatim).

## Why this exists (pre-flight 0)

Two user-visible gaps, one instrument family:

1. **Ceiling gap**: no instrument in the repo can distinguish "good" from
   "world-best" (golden suite retired for solo-saturation 88-99; the
   violation-rate axis measures failure absence, not excellence). Every
   ceiling lever (design-pair depth, knowledge compounding) is
   unfalsifiable until this exists.
2. **Seat gap (user 2026-07-07 verbatim)**: "모델의 버전이 바뀔때, 정확하게
   어떤 모델이 어떤 포지션에서 가장 강한가를 측정할수 있는 것도 있어야 그
   자리를 체크해서 가장 적합한 모델로 사용할수 있을 것 같아." Model versions
   churn (GPT-5.5→5.6 imminent; Fable availability not guaranteed →
   Opus fallback). Today seat assignment is convention + stale memory;
   it must become a measured matrix consumable by `.devlyn/engines.json`
   pins (and omp per-situation model pinning).

One harness serves both because they share arms, blind judging, and corpus:
the ceiling comparison's per-seat sub-scores ARE seat-fitness cells.

## Product 1 — ceiling verdict (the losable 세계최고 test)

Three arms, blind, matched wall-time, real-shaped holdout tasks:

- **A: devlyn** — `/devlyn:resolve` (or ideate→resolve) with current
  measured seat pins.
- **B: bare-best-of-N** — strongest single frontier model, bare prompt,
  N invocations where N = wall ratio, best output selected.
- **C: copycat-best-of-N** — same frontier models explicitly prompted to
  imitate devlyn's approach from public docs (Codex R0 upgrade, adopted:
  the direct moat test — lift that survives C is product; lift C
  reproduces is prompt engineering).

Adjudication order (anti-Goodhart, binding): (1) objective acceptance
checks (tests pass, spec verification commands, runtime behavior) decide
first; (2) calibrated cross-vendor judge panel (blind, artifact-only,
forced ranking, decorrelated) breaks ties on ceiling axes: design
coherence, API ergonomics, runtime performance, robustness under
adversarial review, long-horizon consistency. Judge calibration is a
PREREQUISITE, not an afterthought — iter-0055/0056 measured a judge with
100% false positives; the judge-quality bench must certify every panel
member before its verdicts count.

Loss conditions pre-registered at run time (examples to be frozen then):
A ≤ B on objective checks; A ≤ C on ranked ceiling axes; wall ratio above
cap. A run that cannot lose is invalid.

Corpus: real-shaped holdout — real OSS features/bugs (SWE-bench-bridge
precedent, extended to feature-shaped tasks) + at least one task from the
user's real projects (test-#15 lineage). Hidden from arms; no fixture
literals; clean-twin discipline.

## Product 2 — seat-fitness matrix (모델 × 포지션 측정기)

Rows = seats; columns = installed engines/models. Cells come from
instruments that ALREADY exist plus Product 1:

| Seat | Instrument (exists?) |
|---|---|
| Orchestrator (pipeline fidelity) | compliance cells + `finish_gate_ran` + F6-class probes (YES) |
| Drift resistance (contract under temptation) | violation-rate matrix `run-violation-matrix.sh` (YES) |
| VERIFY primary judge | judge-quality bench (YES — 0055/0056) |
| VERIFY pair judge | frozen-VERIFY pair-lift gate (YES) |
| IMPLEMENT executor | fixture verify-score under harness (YES, saturating — refresh from Product 1 objective checks) |
| PLAN / ideate designer | Product 1 per-phase attribution (NEW — the only seat with no instrument today) |

Deliverables:
1. `seat-matrix-<date>.json` — one aggregation script walking existing
   result artifacts + Product 1 outputs; per-cell: score, N, date,
   instrument, model id.
2. **Re-certification runner** — one command that, given the engine list,
   re-runs the bounded per-seat suites (N=4 cells, existing runners) and
   emits the matrix + recommended `.devlyn/engines.json` pins. Trigger
   contract: any model/version change (5.5→5.6, fable→opus) re-certifies
   BEFORE re-pinning; stale matrix (engine id absent) = "unmeasured",
   never assumed. This is what makes the loop survive model churn without
   any particular orchestrator's memory.

## Design constraints (binding at pre-registration)

- Oracle correctness before mechanism cleverness (ops test #10): corpus
  oracles + judge calibration smoke-tested before any arm runs.
- Relative outcomes only; absolute scores banned as ceiling evidence.
- Engine tiering for test arms per standing memory (codex/sonnet/opus; no
  fable arm); Fable/strongest-available orchestrates + verifies.
- Wall-time: bounded tranches, resumable (SWE-bench matrix precedent);
  never one unbounded interactive run.
- Anti-Goodhart guards enumerated in Codex R0 (`/tmp/codex-northstar2/
  r0-response.log`, archived in HANDOFF Block 7 record): hidden holdout,
  artifact-only blind judging, panel decorrelation, raw artifacts
  preserved, pre-registered loss conditions, no optimizing to known probes.

## What this iter does NOT do

- No new ceiling levers ship here (design-pair, knowledge retrieval wait
  for the instrument's baseline).
- No runner/skeleton work (R0: directionally right, NOT next; re-enters on
  skip-rate evidence + post-0064).
- No Mission 2 surfaces (hard NOs binding).

## Pre-registration (frozen 2026-07-07, before any arm run)

### Corpus — tranche 1 (frozen)

Selection rule (mechanical, no cherry-picking): first django instances of
SWE-bench Lite at dataset rows ≥ 51 (rows 1-50 were prior frozen-VERIFY
corpus; contamination grep over the repo returned 0 references for every
candidate). django-only for local arm64 docker eval feasibility.

| id | task | source | objective oracle |
|---|---|---|---|
| SW1 | `django__django-13230` (row 51) | SWE-bench Lite | official harness: FAIL_TO_PASS resolved, PASS_TO_PASS clean |
| SW2 | `django__django-13265` (row 52) | SWE-bench Lite | same |
| FS1 | `dbader/schedule` @ `82a43db1b938d8fdf60103bd41f329e06c8d3651`: add `Job.max_runs(n)` run-budget (chainable; self-unschedules after n runs; first-limit-wins with `.until()`; invalid n → ValueError; docs). Feature verified ABSENT upstream (grep `max_runs` exit 1 at pin SHA) — no gold in training data | authored this session | hidden pytest suite (behavior-only; API surface pinned in task text) |

Ordered replacement list (used ONLY on oracle-smoke failure, in order):
`django__django-13315`, `13321`, `13401`. Tranche 2 (NOT this iter's gate):
next rows in order + one user-supplied real-project task (reserved; cannot
be pre-registered without the user, iter-0035 rule).

Freeze mechanism: `benchmark/ceiling/corpus/manifest.json` with sha256 of
every task text, hidden oracle, and the copycat doc bytes — committed before
any arm runs. Arms see ONLY task text + base checkout; oracles live under
`hidden/` and are never staged into arm workspaces.

Oracle smoke (ops test #10, must PASS before arms): SW tasks — gold patch
evaluated through the official harness (`uvx --python 3.11 --from swebench
… run_evaluation`, local docker build, `-d` = local instances JSONL) must
report resolved; FS1 — hidden tests FAIL at base SHA and PASS on a reference
implementation (reference stays in `hidden/`, never shown to arms).

### Arms (engine tiering: codex/sonnet only; Fable orchestrates, never an arm)

**Claim shape (R0 MUST-FIX)**: A-vs-B/C measures the **current devlyn
stack** (sonnet orchestrator + codex executor + pair-verify) vs codex
bare/copycat — NOT model-neutral "harness-only" lift. Every report uses
this label.

- **A devlyn ×1/task**: fresh solver worktree + devlyn context staged
  (`.claude/skills`, `CLAUDE.md`, `AGENTS.md`, `.devlyn/engines.json` =
  `{"executor":"codex"}`); orchestrator = headless claude `MODEL=sonnet`
  (run-compliance-cell.sh invocation shape) driving `/devlyn:resolve
  "<task>" --pair-verify` (production convention for executor=codex).
  Any claude-side sub-invocation pinned/recorded as sonnet; exact model ids
  recorded from artifacts.
- **B bare-best-of-N**: `codex exec -s workspace-write` in fresh worktree,
  task text + minimal "fix/implement and verify" instruction. N independent
  runs.
- **C copycat-best-of-N**: identical to B + prompt carries the devlyn public
  README (frozen bytes) + "follow this methodology end-to-end yourself
  (plan → implement → build gate → cleanup → fresh-eyes verify)". Same N
  as B.

**N rule**: run B once → `N = clamp(round(wall_A / wall_B_first), 1, 3)`
per task; run remaining B and all C at that N. Per-run timeout 3600s
(timeout = recorded failed run, never silently dropped). **Usable
denominator (R0 MUST-FIX)**: `wall_B_first` must come from a SUCCESSFUL
bounded B run — provider/transport failure or timeout never sets N or the
LC3 denominator; retry once, then the task row is `INVALID-infra`
(excluded from verdicts, reported).

**Best-of selection (B, C)**: (1) max objective-oracle pass; (2) tie →
fewer PASS_TO_PASS regressions (SW) / fewer hidden-test failures (FS1);
(3) tie → blind panel rank; (4) tie → earliest run.

### Blind judging

Panel: sonnet + codex. **Fresh certified identity (R0 MUST-FIX): BOTH
judges are re-certified in THIS iter** on the judge-quality corpus (12
cases × 2 reps each; codex needs a new judge route), with the exact model
identity recorded (`claude --version`+model id / `codex --version`+model).
iter-0055 sonnet numbers (recall 16/16, FP 0/8) are prior evidence, not
this run's certification. Certification bar per judge: per-axis recall
≥ 0.75 AND FP ≤ 0.125 at rep level. If only one judge certifies, ranked
axes CANNOT decide LC2 — they are reported as a low-confidence annex and
LC2's moat half falls back to the objective aggregate only.

Per task: 3 anonymized packets (task text + final source diff, `.devlyn/`
and any state stripped), labels removed, order = deterministic shuffle
seeded by sha256(task_id) (mapping stored outside packets). Ranking 1-3
per axis: design_coherence, robustness, spec_long_horizon_consistency,
maintainability_api_ergonomics. A judge may mark an axis
`indistinguishable` — that axis counts as a TIE (never a win); every
ranked win requires a one-sentence concrete delta cited from the diffs
(R0 SHOULD-FIX adopted). Objective checks decide FIRST; panel ranks break
ties / decide ceiling axes only.

### Loss conditions (pre-registered; a run that cannot lose is invalid)

- **LC1 (stack ≤ bare; tie-is-not-lift, R0 MUST-FIX)**: resolved(A) <
  resolved(best-B) summed over tasks → FAIL-pilot; resolved(A) ==
  resolved(best-B) → BARE-LIFT-NOT-SHOWN (a tie is never a positive
  outcome).
- **LC2 (no moat)**: NOT(A > C on objective aggregate) AND NOT(A wins
  strict majority of ranked axes vs C across tasks) → MOAT-NOT-SHOWN.
- **LC3 (efficiency)**: mean over tasks of `wall_A / wall_B_first` > 3.0 →
  efficiency FAIL regardless of LC1/LC2.
- **LC4 (instrument invalid)**: oracle smoke fails after replacement list
  exhausted, or zero certified judges → INVALID, no verdict, fix instrument.

**Claim boundary**: tranche 1 can yield at most "instrument live + pilot
direction". No 세계최고/대체불가능/압도적 claim from n=3 — ops test #17
needs a larger corpus + the real-project task. Absolute scores banned;
relative outcomes only. Reporting is per-task with a leave-one-out
sensitivity note (especially excluding FS1 — if FS1 alone flips the pilot
direction, say so). Optional sonnet bare/copycat lane = tranche-2
candidate, not v0.

### Predictions (before any run; retroactive edits are dishonest)

- **P1**: A ≥ best-B on objective aggregate, with A resolving ≥ 2/3 tasks.
  Mechanism: enforced BUILD_GATE/VERIFY loop catches failures bare leaves.
- **P2**: A > C on objective aggregate; C ≥ B on at least one ranked axis.
  Mechanism: prompt-imitation reproduces style but not enforced mechanical
  gates (state files, finish-gate, fresh-context VERIFY) under temptation.
- **P3**: codex judge passes certification (both axes).
- **P4**: `wall_A / wall_B_first` lands in [1.5, 3.0] → N ∈ {2,3}.
- **P5**: seat matrix populates ≥ 5 of 6 seats from existing artifacts;
  PLAN seat starts `unmeasured` until Product 1 attribution lands.

### Product 2 freeze — sources, schema, runner

Cell sources (inventoried 2026-07-07): drift seat ←
`benchmark/probes/results/iter0058-base-matrix.json` +
`iter0062-{a,b}-matrix-corrected.json` (sonnet/opus); orchestrator seat ←
`compliance-check.json` cells incl. iter0060/0061 (claude/codex/omp);
VERIFY primary judge ← judge-quality results (sonnet PASS, gemma3:4b DQ);
pair judge ← `swebench-lite-proof-gate-n11.json` + combined-proof; IMPLEMENT
executor ← combined-proof per-arm `result.json`/`judge.json` (stale-labeled);
PLAN seat ← Product 1 run archives (pilot). Completed-run detection keys off
gate JSONs / `compare.json` presence — 443/458 frozen-verify dirs are stubs.

Cell schema: `{seat, engine_alias, model_version:{value|null, source},
metric, value, n, date, artifact, status: current|stale|unmeasured}`.
Alias-only cells get `model_version.value=null` + stale flag; any
model/version change ⇒ recert before pin (NORTH-STAR ceiling contract).

Runner: `benchmark/seats/recert-seats.sh --engines <list>` re-runs bounded
per-seat suites (violation matrix N=4; compliance small cell per CLI;
judge-quality 2 reps/judge), then `seat-matrix.py` emits
`seat-matrix-<date>.json` + recommended pins `{executor,
pair_judge_priority}` with rationale. It NEVER writes `.devlyn/engines.json`
(pins stay a human/orchestrator act). **Pin actionability (R0 MUST-FIX)**:
a pin recommendation is emitted ONLY from cells with `status: current` AND
exact model identity; if the would-be winner rests on stale or alias-only
cells, the runner fails closed with `recert required` for that seat.

### Implementation deliverables (Codex CLI, workspace-write)

Reuse-Before-New-Script is binding (R0 synthesis #8): new scripts are thin
adapters over `prepare-swebench-solver-worktree.py`,
`run-swebench-solver-batch.sh` mechanics, and `run-compliance-cell.sh`
invocation shapes — never reimplementations.

1. `benchmark/ceiling/scripts/run-ceiling-arm.sh` (A/B/C single run;
   reuses `prepare-swebench-solver-worktree.py`; FS1 workspace prep).
2. `benchmark/ceiling/scripts/ceiling-eval.sh` (objective checks: official
   SWE-bench eval on local JSONL; FS1 hidden pytest).
3. `benchmark/ceiling/scripts/ceiling-judge.py` (blind packets, panel
   invocation, forced ranking, aggregation).
4. `benchmark/ceiling/scripts/ceiling-gate.py` (LC1-LC4 → verdict JSON).
5. `benchmark/seats/seat-matrix.py` + `benchmark/seats/recert-seats.sh`.
6. codex judge route in `benchmark/probes/judge-quality/run_judge_quality.py`.
7. Corpus freeze: `benchmark/ceiling/corpus/` (SW manifests + FS1 authored
   task + hidden oracle) + `manifest.json` hashes.
Self-tests per repo precedent (`test-*.sh`); lint + mirrors clean.

### Execution record (filled as gates clear; raw numbers only)

- **Oracle smoke (ops #10) — PASS, 2026-07-07, before any arm**: SW1+SW2
  gold patches resolved 2/2 via official harness (local x86_64 docker,
  report `benchmark/ceiling/results/oracle-smoke/`); FS1 hidden tests 14/14
  FAIL at base → 14/14 PASS on reference, upstream suite green. Corpus
  frozen with hashes at `benchmark/ceiling/corpus/manifest.json`. No
  replacement-list use.
- **Judge certification — BOTH PASS, 2026-07-07, fresh run**: sonnet
  (CLI 2.1.201, exact model `claude-sonnet-5` via modelUsage probe): recall
  16/16 = 1.00 both axes, FP 1/8 = 0.125 — passes exactly at the bar (note:
  iter-0055 had FP 0/8; the WD3-CLEAN FP is new this run). codex (CLI
  0.141.0, exact model `gpt-5.5` via stderr banner artifact): recall 16/16
  = 1.00, FP 0/8 = 0.00, parse 0/24. Panel = 2 certified judges → LC2
  ranked axes decision-capable. P3 CONFIRMED.
- **Live-caught route defect (fixed pre-arms, surfaced for reconciliation)**:
  first codex calibration run failed 24/24 `transport_error` — `codex exec`
  refuses non-git scratch dirs; fix = `--skip-git-repo-check` in
  `call_codex` (one flag, applied by orchestrator, mirrored into call-2
  spec). Fake-binary self-tests cannot catch real-CLI contract gaps —
  standing lesson (iter-0063 lens 3 analog). Known cosmetic: parallel
  per-judge invocations last-writer-win `summary.json`; per-rep files are
  authoritative (aggregator reads those).

### Pair rounds

- **R0** (2026-07-07, read-only xhigh, archive
  `/tmp/codex-iter0064/r0-response.log`): SHIP-WITH-EDITS. All 5 MUST-FIX
  adopted (LC1 tie-is-not-lift → BARE-LIFT-NOT-SHOWN; fresh dual-judge
  certification with exact identity, single-judge cannot decide LC2; claim
  shape = current-stack; usable-denominator rule for N/LC3; seat-pin
  fail-closed). SHOULD-FIX adopted: per-task + leave-one-out reporting,
  indistinguishable-as-tie + cited-delta wins, Reuse-Before-New-Script;
  sonnet bare/copycat lane deferred to tranche 2.

## Hand-off contract for the running session

1. Read HANDOFF § START-HERE → this file → NORTH-STAR ceiling contract +
   ops test #17 → judge-quality bench README.
2. Pre-register: corpus freeze (task list + hashes), N per arm, loss
   conditions, judge panel + calibration results, predictions — BEFORE any
   arm runs.
3. Codex (or strongest OTHER engine) R0 on the pre-registration; R1 on raw
   results. Protocol v2 (new-evidence rule for extra rounds).
4. Closure: matrix artifact + ceiling verdict + seat pins recommendation;
   HANDOFF rotates; DECISIONS appends.
