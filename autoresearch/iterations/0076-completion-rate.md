# iter-0076 — completion-rate: SC-format run-lethality + terminal-claim source authority (REGISTERED-FROZEN 2026-07-21)

**Why (pre-flight 0)**: FS-0075-B FIRED (0075 §ADJUDICATION): complete-verify
4/7, third consecutive cohort <5 — frozen consequence: completion before any
wall work. User-visible failure: 3/7 hands-free runs fail to complete VERIFY;
the one receipt-traced eliminable class this cohort is SC-adjudication-format
run-lethality (K1). Mission 1, ceiling addendum: completion is a floor
property of hands-free value.

**Round record**: three-way R0+R1+R2 2026-07-21 (packets + logs
/tmp/threeway-0076-r0/). R0 both seats GO-WITH-EDITS; R1 Grok CONFIRM FREEZE
+ 3 precision edits (all adopted; named deltas: withdrew broad-M0 and the
reason-suffixed carrier, conceded its F23-CLEAN repro was an artifact of
installing archived state as active), Codex OBJECT ×2 (both receipts
verified, adjudicated in §R2); R2 both seats CONFIRM FREEZE. Load-bearing R0
corrections, orchestrator-verified at the cited files before adoption:
- **Grok**: FS1 K1 narrative wrong — FS1 is a phase-ORDER violation
  (BUILD_GATE 47ms at 14:25 pre-SC; verify 14:27; SC spawned mid-verify
  14:40), not "halt then continue"; F23 is the only pure contractual halt.
  Orchestrator follow-up receipt: FS1's pair judge caught the order violation
  in-run (CRITICAL `verify.state.surface-close-skipped` in
  verify-merged.findings.jsonl) and that CRITICAL — not the judge's
  NEEDS_WORK — forced verify verdict BLOCKED, foreclosing the fix-loop.
- **Codex**: (1) bare BLOCKED phase verdict is run-terminal by contract
  (state-schema.md § Terminal verdict precedence 1) — original M0 carrier
  self-contradicted; (2) rollback is blind to ignored-file + `.devlyn` writes
  (surface_delta_paths state-phase-write.py:188-202 — `--exclude-standard` +
  devlyn-prefix exclusion) — a real contamination path; (3) F23's production
  C2 classification was NOT_APPLICABLE, not CLEAN — archive_run.py moved the
  active state before terminal-claim-check.py read it
  (terminal-claim-check.py:86-89; hole pre-named DECISIONS 0074.2, first live
  production receipt); (4) legitimate pre-VERIFY halts are broader than
  infra: plan-empty SKILL.md:116, risk-halt :117, implement-empty :227,
  gate exhaustion :235/:262.
- **Both**: objective-causality correction — neither discarded repair was
  objective-decisive (FS1 oracle: exception-hierarchy bug,
  `ScheduleValueError` not matching `pytest.raises(ValueError)`; F23 oracle:
  missing `single_warehouse` type validation, exit 0 vs expected 2). 0075.5's
  "(FS1 … its hidden-test target)" was an overclaim — corrected in DECISIONS
  0076.1. K1's measured harm = completion loss + repair-machinery foreclosure
  + collateral discarded correct work. N/A-line reject shape: 2 live
  occurrences; "3rd" belongs only to the broader
  correct-repair-discarded-by-discipline-gate family (0072.19 =
  execution-audit violation; 0072.26 = fix-loop revert — different
  mechanisms).

R1 adjudications (named criteria): M0 narrowed to the adjudication-format
class only (**Recoverable-State Equivalence** — only that class has observed
receipts + a complete retained worker transcript + clean-rollback proof);
M0 carrier = skip-carrier; M2 rebuilt around Codex's run-state
**source authority** with Grok's structural rule as the CLEAN condition
inside it (**production-path truth**); C1 wiring stays out unanimously
(**Mechanism-Separable Attribution** / confound-free cohort).

R2 (bounded, licensed by Codex R1 OBJECT with new receipts — both verified
by orchestrator):
- **Objection 1 (verdict floor)** — Codex receipts CONFIRMED: finish-gate
  reverts unauthorized paths AND floors terminal at PASS_WITH_ISSUES
  (finish-gate.py:214-234; SKILL.md:318; state-schema.md:117), and the
  original "byte-identical to skip" premise was wrong as written (the phase
  ENTRY fields differ by design). Floor still NOT adopted, under the
  replacement criterion Codex's objection invited: **Judged-Surface
  Integrity** — a terminal floor is warranted iff the discarded/reverted
  material was part of, or arrived after, the surface the VERIFY verdict
  claims to cover. Finish-gate residue exists in the final tree AT terminal
  time, post-VERIFY — verify never judged that state → floor is epistemically
  required. M0's discard happens PRE-BUILD_GATE; every downstream gate judges
  the post-rollback surface; terminal PASS covers exactly what shipped → no
  qualification. The shipped skip path (also unadjudicated obligations, no
  floor) sits on the same side. Corrected identity claim: tracked-worktree
  SURFACE entering BUILD_GATE is identical between skip and rolled-back
  (rollback-verified + write-audit); state.json receipts intentionally
  differ.
- **Objection 2 (run-id authority)** — ADOPTED, superseding the R1
  "just-finished run" wording; M2v2 rewritten to invocation-owned set
  quantification (see Mechanisms).

## Loss-class map (receipts, nodeg-20260720e)

| Class | Rows | Receipt | 0076 action |
|---|---|---|---|
| K1 SC-adjudication-format run-lethality | F23 (halt, verify never ran); FS1 (collateral within order violation) | SURFACE_ROW_RE state-phase-write.py:46-49; surface-close.md:23-24; SKILL PHASE 2.5 halt sentence + autonomy halt list; verbatim N/A rows missing `:<line>` (FS1 stdout L4, F23 stdout L1 — FIRED lines format-perfect in both) | M-RE + M0 |
| K2a voluntary exit mid-VERIFY | F25 (invoke_exit 0, verify open 552,991 ms censored; C2 fired INCOMPLETE:verify live) | attribution.json + terminal-claim.json | out (C1 wiring = own registration; FS-0076-B pulls it forward) |
| K2b VERIFY overrun under wall cap | F12 (invoke_exit 124, two verify attempts) | timing.json + attribution | out (wall-lever iter) |
| C2 archived-terminal invisibility | F23 (no terminal-claim.json) | terminal-claim-check.py:86-89 + archive move | M2v2 |
| L-phase-order (named, recorded) | FS1 | state timestamps + pair-judge CRITICAL | out — candidate own registration |

## Mechanisms (frozen)

- **M-RE**: SURFACE_ROW_RE two-branch — FIRED requires `<path>:<line>`; N/A
  requires `<path>` with `:<line>` OPTIONAL; evidence mandatory on N/A
  (existing :319-323 check stays); in-surface + file-existence mandatory
  always; line-existence checked when present; regex must not swallow ` — `
  into `path` when line absent. surface-close.md:23-24 updated to match.
  FIRED strictness untouched.
- **M0 (narrow)**: on `BLOCKED:surface-close-adjudication-malformed` →
  mechanical rollback (existing) → transcript write-audit (every Edit/Write
  target in surface-close.worker-session.<round>.jsonl must be within
  authorized_surface; any other target → halt stands) → complete phase with
  skip-carrier (`verdict: null` + `skipped_reason:
  "surface_close_rolled_back_adjudication_malformed"` +
  `continued_after_block: true`) → pipeline continues to BUILD_GATE.
  ALL other SC failure classes (timeout, input/prompt mismatch, attestation
  failure, execution-audit violation, out-of-surface delta, rollback failure)
  KEEP the halt, enumerated in the amended PHASE 2.5 sentence + autonomy
  halt list line. No terminal-precedence edit (null verdict never fires
  precedence 1). Grok R1 precision edits (adopted): (1) stock `do_complete`
  rejects a null verdict and `do_surface_skip` is pre-spawn-only
  (state-phase-write.py:1170-1173 vs :1123-1143) — M0 ships a named
  **complete-after-spawn** SPW writer (keeps `started_at`/`duration_ms`,
  sets the carrier fields; pure pre-spawn skip stays a separate path);
  (2) state-schema.md `phases.surface_close` documents the two new
  nonterminal fields beside the auto-skip sentence; (3) when
  `continued_after_block` is set, the final report carries one explicit
  line (reason + "pipeline continued to BUILD_GATE") — the differential
  stays out of the terminal verdict.
- **M2v2**: terminal-claim-check.py + run-ceiling-arm.sh — (1)
  **invocation-owned set quantification** (Codex R2 objection 2 adopted;
  receipt: nodeg-20260720a FS1 A1 archived TWO runs in one invocation —
  "just-finished run" is ill-defined): the arm captures the `.devlyn/runs/`
  id set before invoke; after invoke, C2 classifies EVERY new archived run
  state PLUS any active state; the invocation outcome is INCOMPLETE if ANY
  member classifies incomplete, CLEAN iff every member is individually
  CLEAN-or-witnessed; no member and no active state → NOT_APPLICABLE
  (unchanged). No ordering, no correlation rule, no timestamp/latest
  selection anywhere. (2) Per-member CLEAN iff verify completed with valid
  verdict AND final_report/archive valid, OR terminal-halt witness matches
  the frozen phase+reason matrix (plan-empty, risk-halt, implement-empty,
  BUILD_GATE/VERIFY exhaustion, fresh-context/engine-unavailable infra) with
  topology check (all later phases null); (3) open `history[]` spans →
  INCOMPLETE; (4) completed final_report with null/invalid verdict →
  MALFORMED. Post-M0, SC-rolled-back is NOT a witness (verify must run).
- **M1 (bounded format-repair re-prompt)**: NOT built; enters a v2
  registration only if FS-0076-A fires.

## Stage A gates (ALL before Stage B; hard rule 7 inner loop)

(i) SPW self-tests extended from REAL receipts: FS1 L4 + F23 L1 verbatim PASS
under M-RE; missing-row / duplicate / PASS-placement / evidence-empty /
out-of-surface / line-cited-but-absent still reject; rollback + write-audit
unit tests green.
(ii) M2v2 fixtures green: F23 archived state flips under source authority
(contract-version-qualified historical fixture); F25 stays INCOMPLETE (also
exercises open build_gate history[0]); FS1 classifies CLEAN (verify completed
with valid verdict); one synthetic witness row per matrix entry (FS-0076-D
guard).
(iii) Sonnet live probe (SC product engine IS sonnet — SKILL PHASE 2.5;
test-tiering directive 2026-07-21: claude arms → sonnet): the two REAL frozen
SC prompts × N≥10 draws under M-RE contract → format-validity ≥9/10 AND zero
false-N/A (known FIRED/N/A dispositions per prompt).
(iv) lint-skills + token gauge + config↔.claude sync green.

## Stage B — one 7-row cohort

CSV "F7,F25,F26,F11,F12,F23,FS1" F7-first; run-owned pins both engines,
sha-receipted; fresh post-Stage-A SHA; NEW-COHORT identity; node v20.19.0;
frozen best_B STATUS baseline unchanged. Report MUST partition incomplete
rows {K1-eliminated, K2a, K2b, other} mechanically.

**Frozen predictions**:
- P-0076-A (roadmap): complete-verify ≥5/7.
- P-0076-B (mechanism, decisive): zero K1 events — no
  `BLOCKED:surface-close-adjudication-malformed` anywhere, zero
  correct-repair-discarded-by-format events.
- P-0076-C (stability): quality 0/7; wall median ≥8×. No objective-lift
  claim (causality correction above).

**Falsifiers**:
- FS-0076-A: Stage A probe format-validity <9/10 OR any false-N/A → M-RE
  insufficient/unsafe; M1 or contract redesign enters a v2 registration.
- FS-0076-B: complete-verify <5/7 with zero K1 events → K2 dominates; next
  registration = C1 product wiring (claude route), still before wall work.
- FS-0076-C: any SPW self-test regression or new CRITICAL on the
  adjudication path → block ship.
- FS-0076-D: M2v2 flags FS1-shape, a clean full run, or a legitimate witness
  fixture → M2 overreach; redesign before cohort.

**Out of scope (frozen)**: C1 wiring; wall levers; corpus changes; FIRED
strictness; execution audit; L-phase-order mechanical order-gate;
L-terminal-misattribution beyond M0's carrier; false-N/A detection beyond the
Stage A accuracy gate.

**Build**: Codex sol (workspace-write, detached, one silent-hang retry;
orchestrator commits builds).

## STAGE A RESULTS (2026-07-21, raw before interpretation)

Build: Codex sol, committed 22d22ff (contract deviations: none;
orchestrator fixed one garbled autonomy-contract sentence). Gates (i)
SPW self-tests PASS incl. both real replies verbatim; (ii) M2v2 15
fixtures PASS + LIVE replay on real -20260720e snapshots: F23
INCOMPLETE:verify (archived-terminal hole closed), FS1 CLEAN (no
overreach), F25 INCOMPLETE via open build_gate history[0]; (iv) lint +
token gauge + mirrors green.

Gate (iii) sonnet probe — 12 draws (6×FS1, 6×F23), product spawn recipe,
reconstructed pre_sha worktrees, M-RE contract:
- format-validity **11/12 = 0.917 ≥ 0.9 → format gate PASS** (the two
  live-cohort malformed shapes now parse valid; the single invalid draw
  is a NEW variance shape: two comma-joined paths in the path slot —
  fs1-3, rejected by citation-existence, same as product would).
- false-N/A **4 events → FS-0076-A FIRED** (fs1-6 UVR-STALE N/A vs
  expected FIRED; f23-2/3/6 PATH-TEST N/A vs expected FIRED — F23 split
  3/3, a genuine judgment-boundary case). over-fired: 0.
- **Frozen consequence binds: Stage B BLOCKED; M1 or contract redesign
  enters a v2 registration (not ad-hoc).** Attribution caveat recorded
  at firing time: no baseline arm was frozen into gate (iii), so
  whether false-N/A is M-RE-caused or baseline sonnet disposition
  variance is UNMEASURED — a 12-draw baseline probe under the OLD
  contract (same worktrees/prompts) was launched immediately as
  diagnostic input to the v2 round.

**Baseline attribution probe (raw, same session — 12 draws, OLD contract,
same worktrees/prompts/recipe)**: format-validity 10/12 = 0.833 (both
invalid draws are the LIVE K1 kill shape reproduced — `N/A missing :line`,
fs1-4/fs1-5); false-N/A **5** (fs1 UVR-STALE 2/6; f23 PATH-TEST 3/6);
over-fired 0. Cross-arm read: false-N/A rate is baseline sonnet
disposition variance, present under BOTH contracts (4 new vs 5 old, same
task split); M-RE improved format validity 0.833→0.917 and eliminated
the run-lethal shape. The fired gate's zero-false-N/A bar measured an
uncontrolled baseline variable (ops test #10 oracle-correctness class).
Disposition variance = the already-named out-of-scope class
L-format-valid-false-N/A, now with 24 draws of receipts. v2 round
opened on gate-(iii) re-specification; raw results committed BEFORE the
v2 round returned.

## Principles check

- **0**: closes the FS-0075-B-frozen user failure (hands-free runs dying on a
  reply-format slip; authority blind to archived terminals). Unlocks the
  next go/no-go: completion ≥5/7 vs C1-wiring pull-forward.
- **7**: Mission 1 — floor property of single-task hands-free value.
- **1**: three mechanisms, each bound to an opened receipt; M1 explicitly NOT
  built (no observed non-N/A-line format kill); M-RE is net-subtractive on
  the contract.
- **2**: predictions + falsifiers frozen above before any build.
- **3**: why-chain landed on violated invariants: (K1) a mechanically
  recoverable reply defect in an advisory phase must not be run-lethal —
  proportionality; (C2 gap) the authority must read the state where
  production puts it.
- **4/5**: Stage A self-tests + fixtures from real receipts; standard
  primitives (existing skip-carrier, existing rollback, git-free id-set
  diff).
- **6**: no new pair surface; probe is minutes-tier; cohort is the existing
  periodic exam.
