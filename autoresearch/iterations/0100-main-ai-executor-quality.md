---
id: "0100-main-ai-executor-quality"
title: "Main-AI executor/design quality cell (pair_calibration stage 1) — opus-5 vs fable baseline under a mechanical multi-manifestation oracle"
kind: instrument
status: REGISTERED 2026-08-09 — R0 converged; R1 Codex sol REVISE + Grok 4.5 REVISE (liveness R1-0100-LIVE-sol / R1-0100-LIVE-grok, both 2026-08-09), all required edits ADOPTED in-text; contested estimand adjudicated (see Metrics). CORPUS BUILD A LANDED same day (run rs-20260809T044614Z-58fec95f19be, PASS: 5 exec phases + verify fix round 1; validate-task.py + score-cohort.py + EQ-UA1/EQ-MI1/EQ-AF1; primary codex judge caught the same-binding equality gap round 0, fixed 78d1334; pair claude judge executed boundary probes incl. Δ=0.15 equality → INCONCLUSIVE and byte-determinism). Next = corpus build B (9 tasks, one spec reusing the admitted template) → post-build pre-arm freeze audit (both seats) → 48-run matrix
complexity: high
depends_on: []
---

# iter-0100 — main-AI executor quality cell

## Why this iter exists (pre-flight 0)

User-reported live signal (2026-08-09): when claude-opus-5 is the MAIN
AI doing hands-on design+coding and Codex gpt-5.6-sol pair-checks it,
opus-5 concedes to verified-real findings in the large majority of
rounds; fable-5 draws only minor objections on same-tier work. The
2026-08-05 recert (ckf0099) certifies opus-5 STRICTLY BETTER than
opus-4-8 on drift (0.875 vs 0.583) and perfect on judge quality — the
bench and the live signal do not contradict because **no CURRENT
`implement_executor` cell exists for ANY engine**
(`benchmark/seats/seat-matrix-2026-08-05.md:8-18,32-39`; recommendation
literally "recert required"). The R0 three-way round (2026-08-09)
decomposed the live signal into H1 (real executor/design defects), H2
(over-deference), H3 (critic false positives), H4 (task-shape
confound), H5 (fix-loop contract artifact — findings are binding work
orders, `config/skills/devlyn:resolve/SKILL.md:292,306`). Since then:

- **H3 first bound is IN**: judge_quality re-run under CURRENT codex
  identity (run `ckf0809-sol-recheck`, codex-cli 0.146.1 /
  gpt-5.6-sol, banner-attested): recall 16/16, FP 0/8, parse 0/24.
  Caveat: 0/8 one-sided 95% upper bound ≈ 31% (small corpus; first
  bound, not proof for live multi-axis critiques).
- **User adjudication (binding delta, 2026-08-09)**: the live
  concessions were CODE-VERIFIED real errors ("codex가 설계의 결함이나
  실수를 많이 잡아주고 opus도 코드 검증을 통해서 인정") → **H1 is the
  lead hypothesis**; the H2 deference probe (R0 stage 3) is DEMOTED to
  a pre-named successor, not part of this registration.

This iter builds the ONE missing cell: mechanically-scored executor/
design quality of the **main-AI seat** (single agent, full task
end-to-end in plain-conversation shape — NOT the pipeline IMPLEMENT
worker), claude-opus-5 vs a fable-5 baseline. **Fable participation is
a scoped user exception** (directive 2026-08-09 "fable 포함해서 등록안
진행해줘") to the test-engine tiering rule: seat-certification baseline
only, one-shot, re-run only on model change; benchmark cohorts remain
fable-free.

## Decisive criterion (R0-adopted): ORACLE-IDENTIFIED SEPARATION

Every scored quantity's ground truth is independent of any model under
comparison (mechanical oracle; no LLM meta-judging — same law as
`benchmark/probes/judge-quality/README.md:90`). The cell must produce a
different reading under H1-true vs H1-false; inability to discriminate
(saturation) is reported as its own honest terminal, never as a pass.

## Design

### Corpus (new, frozen before any arm runs)

- **N = 12 tasks**, each a small self-contained repo fixture (~5-15
  files) whose goal REQUIRES a design decision + implementation. Defect
  classes = the predeclared taxonomy from the 0070 lineage (Blind
  Design-Defect Differential: unsupported assumption / missed repo
  invariant / broken dependency / absent failure mode), materialized as
  BEHAVIORAL invariants (ordering, rollback, idempotency, auth-order,
  error-priority — the interaction classes VERIFY's own rubric names,
  SKILL.md:286).
- **Multi-manifestation oracle per task** (Root-Cause Recurrence
  pattern, 0070 STUB): the 12 tasks contain exactly three tasks per
  predeclared taxonomy class. Each task declares one primary
  visible-contract behavioral invariant and maps every manifestation to
  that invariant/class before any arm runs. Freeze requires (NORTH-STAR
  oracle law): the gold fix passes every manifestation; no-op fails; a
  planted symptom patch passes at least one manifestation AND fails at
  least one independent manifestation of the same invariant (a
  completely broken patch demonstrates nothing about recurrence);
  known-good/bad scorer controls separate. Every hidden input and
  oracle assertion carries a visible-contract excerpt, content-hash
  binding, and executable validator under the hidden-conformance
  protocol (0070a:211 lineage); any failure kills the task before
  scoring. No task is repaired-and-rerun after scored results open
  (noncoding binding rule 1).
- Freshly authored for this corpus (coordination boundary, judge-quality
  precedent) — no reuse of live drift-bait/ceiling fixture files.
  Corpus digest sealed at freeze; prompts carry no ground truth
  (conformance-gate class check).
- Corpus authoring routes through /devlyn:resolve (executor pin codex +
  --pair-verify) with the oracle smoke gates as spec verification.

### Arms

- Engines: `claude-opus-5` and `claude-fable-5` (exact IDs; canonical
  identity attested via modelUsage — recert chain supports exact IDs,
  `c0a3b20`+`d824d6b` lineage).
- **2 reps × 12 tasks = 24 runs per engine, 48 total.** Identical
  prompt bytes and pristine visible-fixture bytes; identical tool
  allowlist **`Read,Grep,Glob,Edit,Write,Bash`** (without Bash the arm
  is static editing, not end-to-end main-AI inspect–implement–test);
  identical explicit effort pin; `--strict-mcp-config` empty MCP;
  `--output-format json` so every successful attempt carries
  `modelUsage` — each attempt must contain exactly the requested exact
  model ID; a mismatch or multiple effective models invalidates the
  cohort. Same pinned CLI (updater-proof run-owned copy), per-run
  bound 900s (`run-bounded.py`), fresh opaque workdir per attempt (the
  hidden oracle absent from workdir and environment), task order
  ABBA-interleaved. Model timeout/no-artifact is SCORED;
  auth/quota/pinned-runner/identity/host failures are
  infrastructure-invalid and close the cohort UNSCORED under a fresh
  run ID. No pipeline phases, no pair judge in the loop — the measured
  seat works alone; the oracle runs AFTER, offline.
- Isolation: existing ceiling isolation recipes (opaque roots,
  `--dangerously-skip-permissions`, no MCP); no `.devlyn` writer may be
  live at launch (0099 operator rule, iterations/0099:219); long cohort
  detached via `python os.setsid` (0099 operator rule); never launch
  near the 12am KST quota boundary (0097 lesson).

### Metrics (frozen; computed mechanically from oracle output)

Per run `r` of engine `e` on task `t`: `f[e,t,r]` = failed
manifestations / total manifestations, with catastrophic
(crash/timeout/no-artifact) or incomplete runs scored `f = 1`.
`q[e,t]` = mean of the two reps; `R[e]` = unweighted mean of `q[e,t]`
over the 12 tasks; paired per-task difference
`d[t] = q[opus,t] − q[fable,t]`. **Primary contrast: `Δ = mean(d[t])`**,
two-sided 95% interval from a frozen paired-task bootstrap over the 12
task pairs (100,000 resamples, predeclared seed). Reps and
manifestations never increase statistical N. Secondary output:
failed-invariant task count by predeclared taxonomy class (not
inferred defect count); rep discordance is stability telemetry only.

[R1 adjudication, contested estimand: Grok proposed binary task-fail
(`max` over reps) + Wilson n=12; Codex proposed the paired continuous
estimand above. Adopted Codex's under the named criterion
**PAIRED-DESIGN FIDELITY + EXHAUSTIVE TERMINALS** — the corpus is
matched by construction, so an unpaired statistic discards the power
the design pays for, and Grok's decision rule retained a
bound-vs-point comparison; Grok's substance (unique evaluability with
no post-hoc choice) is fully satisfied by the frozen definitions.
Grok's residual attack right stands at the post-build audit: the
dry-arm scorer must implement these definitions end-to-end.]

### Decision rule (frozen BEFORE results)

- δ_defect = 0.15 on the paired estimand Δ.
- After validity checks, terminal precedence — every valid ledger
  reaches exactly ONE terminal:
  1. **SATURATED**: both engines ≥ 23/24 runs all-manifestations-clean
     → corpus failed to discriminate; honest terminal, no routing
     change; pre-named successor = harder corpus, new registration.
  2. **H1 CONFIRMED**: lower 95% bound of Δ > 0.15 → routing: opus-5
     lanes keep pair-verify mandatory + mechanical-oracle gates on
     design-bearing tasks; no solo-trust promotion; seat matrix
     records the CURRENT cell.
  3. **H1 MATERIAL-GAP REFUTED**: upper 95% bound of Δ < 0.15 → a
     live-signal-sized (≥15pp) gap is excluded at this shape; routing
     unchanged.
  4. **INCONCLUSIVE AT PILOT N**: interval contains 0.15 (covers
     point-gap-above-δ-with-underpowered-bound, null, and reverse
     gaps) → the live signal remains UNIDENTIFIED at this shape/N;
     routing unchanged (pair-verify default). Follow-up candidate
     order for a NEW registration only — H4 task-matching, then the
     demoted deference probe. No terminal causally re-attributes the
     live signal to H4.
- Only CONFIRMED changes routing. Terminals 3/4 are the falsifiers the
  orchestrator pre-accepts. No mid-flight re-scoping; predictions
  recorded before the first arm.

### Pre-registered predictions

- **P-0100-1**: opus-5 manifestation-fail rate exceeds fable's by
  ≥ δ_defect (the user's live signal under H1).
- **P-0100-2** (weaker): opus-5's per-task `catastrophic OR incomplete`
  union rate is STRICTLY greater than fable's; equality refutes
  P-0100-2.
- Both refuted → the registered directional pattern is falsified on
  this corpus (this does NOT kill a smaller H1 effect and does NOT
  establish H4); the deference probe (demoted stage 3) and H4
  task-matching become the follow-up frontier.

### Matrix integration

`executor_quality` becomes a DEDICATED suite in
`benchmark/seats/recert-seats.sh` (manual checkup trigger, same as
every suite — nothing is scheduled; folding in means the next 모델
체크업 command runs it without anyone remembering it separately). Its
runner invokes the fixed opus-5/fable-5 pair INTERNALLY;
`claude-fable-5` must never enter the shared recert `--engines`
arrays (recert-seats.sh:102 routes every Claude token to
violation/compliance/judge suites — passing fable there would breach
the scoped exception). `seat-matrix.py` `SEATS` gains
`main_ai_executor` collecting `manifestation_fail_rate`,
`completion_rate`, the paired interval, corpus/scorer digests, and the
terminal verdict from the dedicated artifact; current/stale keyed to
attested CLI + exact `modelUsage` identity.
`recommendation()['executor']` remains unchanged and must not consume
this seat. The cell also serves as the closest CURRENT evidence for
the empty `implement_executor` hole until a pipeline-shaped cell
exists (noted, not conflated).

## Freeze protocol

1. Corpus + oracles land via /devlyn:resolve (spec carries smoke gates);
   corpus digest sealed.
2. Seat-executed satisfiability: one full dry arm (sonnet, non-scoring)
   must produce a complete oracle scorecard end-to-end before any
   scored arm — a freeze is not frozen until a seat has tried to
   satisfy every conjunct by execution (0081-0083 law).
3. Post-build pre-arm freeze audit by both seats (liveness markers) on
   the frozen corpus digest + scorer; scorer frozen and pair-audited
   BEFORE results complete (0099 operator rule). Both R1 seats'
   accepted falsifiers bind here: the frozen scorer must map every
   valid synthetic ledger to one unambiguous paired
   estimate/interval/terminal, and a full dry arm under the frozen
   invocation must demonstrate genuine inspect–implement–test
   completion with exact `modelUsage` attestation.
4. Fresh run-ids, fresh workdirs, sealed arm order, then the 48-run
   matrix, detached.

## Budget/wall (informational)

~0.4-2.4M tokens per engine (agentic runs 30-100k each, anchored by
measured judge-quality single-shots at 6.2k mean); wall ≈ one detached
overnight window at 2-lane parallelism. One-shot certification;
re-run trigger = model change via 모델 체크업, manual.

## Receipts

`~/.local/share/nx01/pair-calibration-r0/` (R0 packet + sol + grok
full responses; R1 sol-r1-final.md + grok-r1.log);
`benchmark/probes/judge-quality/results-ckf0809-sol/` (H3 bound,
identity.json + per-attempt banner receipts); memory
`project_pair_calibration_design_2026_08_09.md` (diagnosis + user
delta); `feedback_test_engine_tiering_2026_07_04.md` (fable scoped
exception, user-verbatim trigger).
