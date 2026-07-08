# iter-0068 (STUB) — attack-the-wall: measured decomposition + strategic fork

status: STUB 2026-07-08 — A-arm wall decomposed; direction pending user
adjudication of a strategic fork (my HANDOFF flagged #2 claim-shape as
"may need user"; the evidence below says the first-listed frontier item
#1 "shave the wall" may be the wrong mountain).

## Measured A-arm wall decomposition (iter0067-t2, tranche-2, 3 fresh django rows)

From each A-arm's archived `pipeline.state.json` (phases + inter-phase gaps):

| row | wall | plan | probe | implement | build_gate | cleanup | VERIFY | gaps | hidden rounds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| SW3 | 2277s | 164 | — | 353 | 172 | 128 | **800** | 504 | build_gate ×1 |
| SW4 | 2005s | 100 | 251 | 171 | 118 | 203 | **628** | 235 | — |
| SW5 | 2689s | 94 | — | 185 | 78 | 127 | **488** | **1604** | impl/bg/cl/vf |

Bare (B best_B) walls for the same rows: 356 / 207 / 302s → LC3 mean 8.33×.

## What the data says (no guesswork)

1. **VERIFY (pair-verify) is the biggest consistent phase: 488-800s.** And
   `sub_verdicts` across all 3: **pair_judge agreed with the primary judge
   3/3 — it never changed a verdict** (PASS/PASS/PASS; SW5 primary
   PASS_WITH_ISSUES, pair PASS, primary's stricter held). So pair-VERIFY
   spent a large share of a 500-800s phase and added ZERO verdict value on
   this task class — and the judge's own 16:3 quality loss shows VERIFY did
   not catch the shared-fixture-mutation anti-pattern either.
2. **Orchestrator inter-phase gaps: 235-1604s**, dominated by SW5's 1485s
   pre-implement correction loop (sonnet orchestrator re-working between
   phases — same class iter-0066 partially addressed; still large, highly
   variable).
3. **Core phases (plan/implement/build/cleanup) are 78-353s each —
   reasonable.** They are NOT the wall problem.

## Why this is a strategic fork, not a mechanism edit

Neither dominant chunk is a clean "delete this line":
- pair-VERIFY is FORCED by the executor=codex convention
  (`feedback_executor_codex_always_pair_verify`: always --pair-verify to
  avoid codex-on-codex solo self-review). Making it conditional changes a
  user-established convention.
- The orchestrator correction-loop overhead is behavior-variable, not a
  single mechanism.
- Most importantly: **all three tranche-2 rows are well-specified SWE bug
  fixes that bare codex solves in 200-350s with equal/better quality.**
  Optimizing the pipeline's wall on tasks where it fundamentally should not
  win is 산으로 (the wrong mountain). The pipeline's designed value is
  categorical reliability (adversarial specs / scope leaks / silent-catch /
  multi-file — MISSIONS.md), which this corpus does not exercise.

## The fork (user to adjudicate; recommendation = corpus pivot)

- **A. Corpus pivot (recommended)**: build a discriminating ceiling corpus
  where bare FAILS and the pipeline's categorical-reliability value should
  show, and measure "does the pipeline earn its 8× wall where its value
  actually lives" — before shaving wall on a corpus where it can't win.
- **B. Wall-shave mechanism**: conditional pair-VERIFY short-circuit
  (pair 0/3 verdict-changes = evidence) + orchestrator inter-phase overhead
  reduction, on the current SWE corpus. Touches the executor=codex→always-
  pair convention.
- **C. Claim-shape**: add a codex-only current-method single-agent arm as
  the honest ceiling competitor (isolate harness-method quality from pair
  overhead) — the tranche-2 finding hints the pair stack may not be the
  right thing to measure.

Not mutually exclusive, but the primary direction of iter-0068 is the
user's call. Evidence archive: this file + `iter0067-t2` states.
