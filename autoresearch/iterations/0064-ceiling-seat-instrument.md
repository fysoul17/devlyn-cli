# iter-0064 — ceiling & seat-fitness instrument family v0

status: STUB 2026-07-07 (design contract locked this session; pre-registration
— predictions, N, corpus freeze — deferred to the session that runs it, per
iter-0035 precedent)

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
