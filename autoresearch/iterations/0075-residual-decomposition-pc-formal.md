# iter-0075 — residual decomposition instrument + formal P-c cohort (REGISTERED-FROZEN 2026-07-20)

**Why (pre-flight 0)**: the wall bottleneck read is unanimous across 9
measured rows (implement 2.6-27%; non-phase residual up to 84%) but the
residual is ONE UNATTRIBUTED LUMP (attribution.py: elapsed −
clipped-union of completed phase spans) — no wall lever can be
registered without naming the component (No-guesswork). The frozen P-c
rule (0073.1) also remains formally unadjudicated (INCONCLUSIVE-by-rule
at 4<5 complete rows). Single claim: MEASUREMENT ONLY — the lever build
is 0076+, keyed on this iter's decomposition data.

**Round record**: three-way R0+R1 2026-07-20 (packets + logs
/tmp/threeway-0075-r0/). R0 both seats GO-WITH-EDITS; R1 Grok CONFIRM
FREEZE + CONFIRM adjudication (named delta: withdrew its declared
state.started_at proxy — its own R0 (a) flagged proxy arithmetic);
Codex R1 CONFIRM adjudication + two precision OBJECTs, both adopted
(amendments A1/A2 below). Decisive criteria: **Instrument-gated formal
adjudication before any wall lever** (Grok) + **Identifiable
Conservation** (Codex — every bucket uniquely derivable from immutable
receipt bytes, disjoint partition of residual).

## Stage A — instrument + receipt contract (Codex sol build, benchmark-only)

1. **timing-v2**: run-ceiling-arm.sh timing.json gains `schema_version:
   2`, `invoke_started_at`, `invoke_completed_at` (ISO-8601 UTC ms).
   Additive; legacy readers unaffected. (elapsed_ms derivable from the
   stamps — explicit field nonblocking per Codex R1.)
2. **Decomposition** in attribution.py: merged interval union across
   ALL archived runs + root/current state (fixes the latest-run-only
   read at attribution.py:65; nodeg-20260720a two-run receipt is the
   fixture). Buckets: `startup_ms` / `interphase_gap_ms` /
   `outer_loop_gap_ms` / `censored_open_span_ms` (orphan incomplete
   spans — NEVER called tail) / `tail_ms`; emits `phase_union_ms` +
   `decomposition_status` (complete | legacy-partial | failed);
   fail-loud negative spans; internal conservation check ±1s →
   status=failed on violation. `startup_ms`/`tail_ms` identifiable ONLY
   on timing-v2 rows; legacy rows put BOTH edges in
   `legacy_edge_residual_ms` (A1). `judge_durations_ms` stays
   REPORTING-ONLY — residual buckets are phase-span/timestamp-derived;
   judge wall is never a residual bucket (A3).
3. **Self-tests from REAL receipts**: -19g F11 (single-run clean),
   -20260720a (two-run outer-loop), -19g F7 (premature-terminal
   censored span), -19g F12 (timed-out + verify_complete edge).
4. **Driver 79 regression test**: synthetic exit-79 row proves
   eval/judge/verdict continuation + attempted-on-resume
   (test-nodeg-cell.sh has zero 79 coverage; flow verified by both
   seats at run-nodeg-cell.sh:84-159, run-ceiling-arm.sh:816-879).
5. **Codex seat pin hardening**: run-owned codex binary copy, version
   FROZEN NOW = codex-cli 0.144.5 (A2), sha256 in the isolation receipt
   (parity with claude pin; today codex is PATH-resolved with no sha —
   run-ceiling-arm.sh:420).
6. **Cohort-level adjudication artifact**: deterministic aggregator
   script emitting P-A/P-B/P-C verdicts from per-row attribution +
   verdict inputs (the driver verdict loop does not aggregate
   attribution — nodeg-cell.py:776).

**Stage A gates (ALL before Stage B)**: (i) back-test decomposes ≥7/9
legacy rows at legacy-partial or better with INTERIOR conservation —
interphase + outer_loop + censored_open vs residual minus
legacy_edge_residual_ms, ±1s; tail EXCLUDED from the legacy equation
(A1); (ii) one timing-v2 CANARY row reaches decomposition_status
complete with FULL conservation (startup + interphase + outer_loop +
censored_open + tail = residual ±1s); (iii) all self-tests + driver
79-test green.

## Stage B — one 7-row cohort

Frozen post-Stage-A main SHA; explicit CSV "F7,F25,F26,F11,F12,F23,FS1"
F7-first; updater-proof RUN-OWNED pins both engines (claude 2.1.215
copy + codex 0.144.5 copy, both sha256-receipted) — NEW-COHORT
identity, explicitly NOT 0073 closure identity (Treatment-Seat Identity
Fidelity untouched); node v20.19.0; dual blind judges + verdict via
existing driver; frozen best_B STATUS baseline as 0073 Stage B.

**Frozen definitions**: complete-verify row := attribution.
verify_complete (verify completed_at AND verdict non-null); P-c primary
population INCLUDES timed-out rows iff verify_complete (F12 -19g
precedent); P-B eligibility = decomposition_status complete rows only;
"half" := ceil(N/2).

**Frozen predictions**:
- P-A completeness: complete-verify ≥5/7 (prior interval 5-7;
  mechanism = exact-pin prevents SC degradation; C2 labels only).
- P-A adjudication: IF ≥5 complete rows, the frozen 0073.1 two-sided
  rule adjudicates addendum-5 formally. Orchestrator PREDICTION (not
  entailment): REFUTE — no observed row of 9 exceeds 0.23 implement
  share.
- P-B (weak prior): startup + interphase + outer_loop ≥50% of residual
  on ≥ceil(N/2) of decomposition-complete rows.
- P-C stability: quality 0/7; wall median ≥8×.

**Falsifiers**:
- FS-0075-A: back-test <7/9 legacy-partial → Stage B blocked, redesign.
- FS-0075-B: complete-verify <5 → completion-rate hypothesis dead; next
  iter targets completion BEFORE wall work.
- FS-0075-C: conservation violation on any decomposition_status=
  complete row → instrument dead.
- FS-0075-D (two-legged, A4): **D1 pre-launch** — unallocated interior
  remainder ≥20% of (residual − legacy_edge) on ≥ceil(M/2) of the M
  cleanly-decomposed legacy rows → Stage B launch BLOCKED (instrument
  not decision-unlocking; Grok R0 original strength restored); **D2
  post-cohort** — unallocated remainder ≥20% of residual on ≥ceil(N/2)
  of decomposition-complete rows → no Stage B verdict adoption, no 0076
  lever.
- FS-0075-E: timing-v2 canary fails full conservation → receipt
  contract wrong, Stage B blocked.

**Out of scope (frozen)**: any lever build; C1 product wiring; corpus
changes.
