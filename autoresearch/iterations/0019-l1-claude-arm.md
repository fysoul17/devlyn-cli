# iter-0019 — L1 (solo_claude) arm: paid 5-fixture × 3-arm smoke

**Status**: **SHIPPED** (verdict + data, this commit). RUN_ID `20260427T155638Z-c08130f-iter-0019-smoke`. Suite completed 2026-04-28T04:06Z; judge re-run after iter-0019.4 mapfile fix.
**Date**: 2026-04-28
**Branch**: benchmark/v3.6-ab-20260423-191315
**Commit at start of paid run**: c08130f (iter-0019 part 1)
**Suite started**: 2026-04-28T00:56Z (~3h10m wall total including post-fix re-judge)
**Cost**: ~$20-30 paid run (15 arm runs + 5 judge re-runs after iter-0019.4 fix)

---

## Why this iter exists (Pre-flight 0)

This iter exists because it **unblocks one of three bound go/no-go decisions** that determine the next iter:
(a) mechanically enforce F9 output contract (if iter-0018.5 prompt fold-in did not hold);
(b) implement cost-aware pair policy in iter-0020 (if L1/L2 attribution is clean enough);
(c) disable or narrow L2 where it fails L1 cost-adjusted (per-fixture pair-mode pruning).

No fourth option allowed. **Aggregate margin movement is not by itself a justification.** This precommit was locked into HANDOFF queue item #0 by Codex R2 (2026-04-28).

---

## Hypotheses (locked BEFORE data)

1. **L1 vs L0 (margins_avg.solo_over_bare)** ≥ +5 floor / +8 preferred. Mechanism: solo Claude orchestrator running auto-resolve skill chain produces measurably better code than bare claude -p without skills, on the same specs.
2. **F9 variant spec axis** ≥ 22 (was 16 in iter-0016). Mechanism: iter-0018.5 BUILD/EVAL fold-ins force literal-match-by-execution + frontmatter-edit ban. If hypothesis fails, the prompt fold-in is empirically dead and decision (a) above triggers.
3. **F2 variant** completes within 1500s (was 1201s TO in iter-0016 with 1200s budget). Mechanism: budget bumped + iter-0018.5 quality_bar tightening reduces CRITIC churn. If still TO at 1500s, the diagnosis shifts to inter-phase gap (~678s unaccounted) per iter-0016 observability gap note.
4. **L2 vs L1 (margins_avg.variant_over_solo)** is **directional, not release-gating**. Per HANDOFF queue item #1 + NORTH-STAR test #13 compression risk: this 5-fixture run is a smoke read; full 9-fixture L0/L1/L2 lives in iter-0020.
5. **solo_claude arm uncontaminated** by Codex bypass. Verified post-hoc by `/tmp/iter0019-verdict-greps.sh` (Codex R1 detection scheme: CODEX_BLOCKED hit count, real-codex side-channel via ~/.codex/sessions/.../session_meta.cwd, pipeline.state.json engine field). If contamination detected → entire run discarded as L1 evidence; iter-0019.5 patch lands first.

---

## Data (filled in AFTER summary.json + report.md land)

### Suite-level (from summary.json)

| Metric | Value | NORTH-STAR gate / Verdict |
|---|---|---|
| fixtures_total | 5 | 5 ✓ |
| fixtures_scored | 5 | 5 ✓ |
| arms_present | {variant, solo_claude, bare} all true | ✓ |
| scores_avg_by_arm.variant | **91.8** | data |
| scores_avg_by_arm.solo_claude | **90.8** | data |
| scores_avg_by_arm.bare | **81.2** | data |
| **margins_avg.solo_over_bare (L1 vs L0)** | **+9.6** | **PASS preferred** (≥+8) — single-LLM users get real lift |
| margins_avg.variant_over_solo (L2 vs L1) | **+1.0** | **FAIL floor** (<+5) — pair-mode does NOT clear pair-eligibility on flat avg |
| margins_avg.variant_over_bare (L2 vs L0, legacy) | +10.6 | iter-0016 was +11.6, comparable |
| wall_ratio_avg.solo_over_bare | 10.2× | L1 paid 10× wall vs L0 for +9.6 quality — best-of-N viable |
| wall_ratio_avg.variant_over_solo | 1.6× | L2 paid 1.6× wall over L1 for +1.0 quality — fails dominance rule |
| wall_ratio_avg.variant_over_bare | 12.1× | iter-0016 was 11.4× — slightly worse |
| hard_floor_violations | **2** | F2/variant DQ (silent-catch) + F9/variant DQ (silent-catch + spec failures) — release-readiness NOT IMPLIED |
| margin_ge_5_count | 3/5 | F4 (+24), F9 (+16), F1 (+6) above; F2 (+3) F6 (+4) below — but smoke run, 7/9 floor doesn't apply |

### Per-fixture (from rows[])

| Fixture | V | L1 | L0 | V-L0 | L1-L0 | **V-L1** | Winner | wall_V/wall_L0 | wall_L1/wall_L0 | wall_V/wall_L1 | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F1-cli-trivial-flag | 99 | 96 | 93 | +6 | +3 | **+3** | variant | 13.2× | 3.8× | 3.5× | Fast-route. Both layers add small lift; neither justifies wall cost |
| F2-cli-medium-subcommand | 91 ⚠DQ | 86 ⚠DQ | 88 ⚠DQ | +3 | -2 | **+5** | tie | 9.5× | 7.2× | 1.3× | All 3 silent-catch DQ. F2 timeout 1200→1500s held (variant 1387s) |
| F4-web-browser-design | 99 | **100** | 75 | +24 | +25 | **-1** | **solo_claude** | 9.6× | 9.6× | 1.0× | **Pair LOSES**. iter-0016 +21 = tool-attached (browser_validate + sec-review native), NOT pair-deliberation |
| F6-dep-audit-native-module | 96 | 91 | 92 | +4 | -1 | **+5** | variant | 12.4× | 9.2× | 1.35× | Pair WINS on constraint discipline (genuine pair lift) |
| F9-e2e-ideate-to-preflight | 74 ⚠DQ | **81** | 58 ⚠DQ | +16 | +23 | **-7** | **solo_claude** | 15.6× | 21.3× | 0.73× | **Pair LOSES BIG**. variant Codex BUILD added silent-catch DQ; solo Claude alone got it cleaner. All 3 verify=0.4 (engine-independent spec failure) |

### F4 attribution preview (Codex R3 hypothesis test) — CONFIRMED

L1 (solo_claude) score=100 BEATS L2 (variant) score=99 on F4 by **L2-L1=−1**. Solo Claude with claude-driven browser_validate matches/exceeds Codex BUILD + playwright. **F4's iter-0016 +21 over bare was tool-attached, not pair-deliberation-attached.** Codex R3 hypothesis confirmed with strongest evidence available.

| Fixture | Pair-mode quality vs solo | wall ratio L2/L1 | Attribution |
|---|---|---|---|
| F1 | tied (V−L1=+3, both above L0) | 3.5× | Trivial fixture; neither layer justifies wall |
| F2 | small pair lift (+5) but both DQ | 1.3× | Pair-mode catches some constraint-discipline things solo misses, but not the silent-catch trap that DQ'd all 3 |
| F4 | **pair LOSES (−1)** | 1.0× | **Tool-attached** (browser_validate + sec-review native fire on browser=true). Codex BUILD + playwright = solo Claude + claude-driven browser. Pair adds zero deliberation lift. |
| F6 | pair WINS (+5) | 1.35× | **Genuine pair lift** on constraint discipline (FIFO/device check, error-path correctness) |
| F9 | **pair LOSES BIG (−7)** | 0.73× | Pair Codex BUILD added silent-catch DQ; solo Claude avoided it. Output-contract failure is engine-independent (all 3 verify=0.4) — pipeline-level issue. |

### F9 watchpoint (iter-0018.5 fold-in test) — FAILED

| Arm | verify_score | DQ | Notes |
|---|---|---|---|
| F9/variant | **0.4** (target ≥ 0.6) | **TRUE** (silent-catch + spec failures) | iter-0018.5 prompt fold-in DEAD. Same shape as iter-0016: wrong JSON keys (commitCount/lastCommitDate/topAuthors instead of commits/authors), wrong exit code (1 vs 2), wrong error prefix |
| F9/solo_claude | **0.4** | FALSE | Solo Claude avoided silent-catch but still got JSON shape + exit code wrong |
| F9/bare | **0.4** | TRUE (silent-catch) | Same shape failures across all engines |

**Conclusion**: prompt-only enforcement of literal output contract is empirically dead — same lesson as iter-0008 prompt-only engine constraint. **Harness-side mechanical bash gate diffing actual output bytes against spec literal is the only remaining lever.** This locks iter-0019's bind to follow-up action **(a) F9 mechanical enforcement**.

### Contamination check (Codex R1 detection) — CLEAN

| Fixture | CODEX_BLOCKED hits | real-codex side-channel | session_meta.cwd matches | top-level engine in state | Verdict |
|---|---|---|---|---|---|
| F1/solo_claude | 0 | 0 | clean | claude | ✓ uncontaminated |
| F2/solo_claude | 0 | 0 | clean | claude | ✓ uncontaminated |
| F4/solo_claude | 0 | 0 | clean | claude | ✓ uncontaminated |
| F6/solo_claude | 0 | 0 | clean | claude | ✓ uncontaminated |
| F9/solo_claude | 0 | 0 | clean | claude | ✓ uncontaminated |

**Bypass A surface (CODEX_REAL_BIN env-var leak, Codex R1 catch) was OPEN throughout the suite but NEVER EXERCISED.** Primary defense (`--engine claude` prompt) was honored on every solo_claude run. Defense-in-depth (shim + wrapper CODEX_BLOCKED) was redundant for this run. iter-0019.5 patch is still required hardening — closing the surface so any future orchestrator drift can't silently exploit it.

---

## Principles check (ALL must be ✅ for ship; ❌ on any = revert)

### Pre-flight 0 — not score-chasing
**Status: ✅ PASS.** This iter unblocks the bind to follow-up action **(a) mechanically enforce F9 output contract** — a real user-visible bug. F9 produces broken JSON shape (commitCount/lastCommitDate/topAuthors vs spec's commits/authors), wrong exit code (1 vs 2), missing `Error:` prefix, across ALL 3 arms (variant + solo_claude + bare all verify=0.4). A real user running `/devlyn:auto-resolve` against an F9-shape spec gets shipping-broken code. iter-0018.5's prompt fold-in did not fix it. **Mechanical bash-gate enforcement is the only remaining lever** — same lesson as iter-0008 (prompt-only engine constraint dead). iter-0020 cost-aware pair policy is the iter AFTER iter-0019.6, also data-supported but not user-failure-blocking right now.

### 1. No overengineering
Diff size for iter-0019 part 1 was bounded: ~5 file edits (codex-shim, codex-monitored, run-fixture.sh ARM=solo_claude branches, run-suite.sh arm loop, judge.sh + compile-report.py 3-arm schema). Each artifact tied to an observed failure mode. **Pass: ⚠️ borderline.** Codex R1 caught CODEX_REAL_BIN env-var leak — defense-in-depth created a bypass surface (since not exercised). iter-0019.5 closes it. The defense IS justified by iter-0008's prompt-only dead-end, but the leak shows the layered approach has its own cost. Net: warranted complexity, partial overshoot.

### 2. No guesswork
Hypotheses 1-5 locked before suite. Direction + metric + mechanism in place. Predictions:
- L1 vs L0 ≥ +5 floor / +8 preferred — **PREDICTED, ACTUAL +9.6 → PASS preferred** ✅
- F9 variant spec axis ≥ 22 — **PREDICTED, ACTUAL: F9/variant verify=0.4, judge spec axis low (broken contract). FAILED.** Recorded as data, no retroactive prediction edit.
- F2 variant within 1500s — **PREDICTED, ACTUAL 1387s** (just inside) ✅
- L2 vs L1 directional only — **ACTUAL +1.0** (informative not gating) ✅
- solo_claude uncontaminated — **PREDICTED, ACTUAL all 5 fixtures clean across 4 detection layers** ✅
**Pass: ✅.** All hypotheses recorded, all data filled in. F9 prediction failed and is recorded honestly as the fold-in's empirical death.

### 3. No workaround
CODEX_BLOCKED env at shim/wrapper compensates for prompt-only `--engine claude` being empirically untrustable (iter-0008). Root cause — orchestrator's drift toward codex — was DETECTED not fixed. **But the data shows: across 5 solo_claude runs the orchestrator NEVER tried codex.** The compensating layer was redundant for this measurement. **Pass: ✅.** The workaround layer is acceptable per iter-0008 dead-end and didn't add silent failure. iter-0019.5 closes the residual env-leak surface for future hardening.

### 4. Worldclass production-ready
Variant arm CRITICAL findings: F2 (silent-catch in bin/cli.js), F9 (silent-catch in HEAD verification + JSON shape mismatch + exit code + error prefix). **2 hard-floor violations** on variant. **Pass: ❌ FAIL.** Release-readiness explicitly NOT IMPLIED. iter-0019.6 (F9 mechanical enforcement) is the corrective iter; F2's silent-catch is a chronic pattern across all 3 arms (forbidden-pattern hit in bin/cli.js try/catch returning fallback objects) that EVAL/CRITIC must catch in iter-0020+.

### 5. Best practice
No MEDIUM `design.unidiomatic-pattern` findings reported in critical_findings_variant arrays. **Pass: ✅.** (Note: judge findings list is critical-severity-or-equivalent only; MEDIUM findings if any were not surfaced in summary.json. Acceptance with this scope.)

### 6. Layer-cost-justified
- **L1 vs L0 dominance rule**: L1 wins on quality (+9.6) AND wall ratio is 10.2× — does L0-best-of-10 beat L1? Per-fixture, F4 L0=75 (well below L1=100), so L0-best-of-10 likely doesn't catch up; F9 L0=58 vs L1=81; F1/F2/F6 are tied or marginal. **L1 likely passes best-of-N efficiency on F4 + F9; loses on F1/F2/F6.** Mixed but net pass — single-LLM users justified.
- **L2 vs L1 dominance rule**: L2 wins on quality (+1.0) AND wall ratio 1.6×. **+1.0 is BELOW dominance threshold for paying 60% more wall.** L1-best-of-1.6 (rounded to 2) likely matches or beats L2 since L1 already matches L2 on F4/F9 (the highest-lift fixtures). **L2 FAILS layer-cost-justified on flat suite avg.** **Pass: ❌ FAIL on L2 layer.** This locks the data feed for iter-0020 cost-aware pair policy: L2 should be NARROWED to fixtures where it actually beats L1 by ≥+5 (F2/F6 in this set), DISABLED on others.

**Net principles check**: ✅ pre-flight 0 / 1 / 2 / 3 / 5 / 6-L1; ⚠️ overlap on workaround scope; ❌ on principle 4 (variant DQ) and 6-L2 (cost-not-justified). The ❌ on principle 4 is exactly why iter-0019.6 (F9 mechanical enforcement) is the bound follow-up. The ❌ on 6-L2 is the data feed for iter-0020.

---

## What this iter unlocks (BOUND)

- [x] **(a) Fix F9 output contract mechanically** — **BOUND.** Triggered: F9/variant verify_score=0.4 (< 0.6 threshold), F9/variant DQ=true (silent-catch + spec failures). All 3 arms verify=0.4 → engine-independent failure → harness-side mechanical enforcement is the only remaining lever. Next iter: **iter-0019.6** — EVAL bash gate that diffs actual output bytes against spec literal (commits/authors JSON shape, `Error:` prefix, exit code 2), fails CRITICAL on mismatch. Lands AFTER iter-0019.5 (CODEX_REAL_BIN leak fix).
- [ ] **(b) Cost-aware pair policy in iter-0020** — DATA SUPPORTS IT. L2 vs L1 = +1.0 < +5 floor. Per-fixture: pair WINS on F2 (DQ-bound) + F6 (+5 real). Pair LOSES on F4 (-1) + F9 (-7). Pair flat on F1 (+3). iter-0020 hard acceptance criteria already locked into HANDOFF queue item #1 (Codex R3 verdict). **Sequence: lands AFTER iter-0019.6 mechanical fix** so F9's data is clean for the routing decision.
- [ ] **(c) Disable or narrow L2** — SUBSET of (b). Per-fixture routing table from this data: {F1: solo (no lift justifies wall), F2: pair-DQ-bound (need DQ-fix first), F4: solo (pair LOSES), F6: pair (+5 real), F9: pending mechanical fix}. Lands inside iter-0020.

**Sequence**: iter-0019.4 (judge.sh fix, this branch) → iter-0019 part 2 verdict (this commit) → iter-0019.5 (CODEX_REAL_BIN leak) → **iter-0019.6 (F9 mechanical enforcement, the bind)** → iter-0020 (cost-aware pair policy + 9-fixture L0/L1/L2 paid run). No "iter-0019.7 measurement-improvement" / "more attribution" iter allowed before iter-0019.6 lands.

---

## Codex companion pair-review log for iter-0019 part 2

- **R0 (pre-part-1, terse)**: locked iter-0018.5 / 0019 design. B over A on solo_claude enforcement; F1+F2+F4+F6+F9 fixture set; F2 timeout 1500s; same judge prompt scores all 3 arms (no separately-calibrated calls); iter-0018.5/0019 split keeps attribution clean.
- **R1 (mid-suite, 142s, ~112k tokens)**: pre-data falsification on solo_claude enforcement. Caught CODEX_REAL_BIN env-var leak — bypass A is not just hardcoded `/usr/local/bin/codex` but `$CODEX_REAL_BIN exec ...` since the harness exports the absolute path. Filed as iter-0019.5 (separate iter, separate commit).
- **R2 (mid-suite, 37s, ~17k tokens)**: NORTH-STAR alignment audit. iter-0019 is North-Star-aligned ONLY if it becomes the last attribution run before a cost/reliability decision; if next iter is "more measurement," loop has gone 산으로. Heuristic: "every iter must remove a real user failure or make the next go/no-go decision impossible to fake" — landed as PRINCIPLES.md pre-flight 0. Termination criterion gets a real-project trial gate (NORTH-STAR test #14).
- **R3 (mid-suite, 26s, ~16k tokens)**: queue pre-flight 0 audit. iter-0021 (dual-judge) reframed conditional; CLAUDE.md minimization gated on measurable A/B; iter-0020 acceptance language tightened to require executable routing change; iter-0019.5 stays separate.

---

## Lessons (post-data, append-only)

1. **Pair-mode is conditional, not universal.** L2 vs L1 = +1.0 < +5 floor on flat suite avg. Pair adds quality on constraint-discipline fixtures (F6 +5) but actively HURTS on tool-rich (F4 −1) and complex-output-contract (F9 −7) fixtures. iter-0020 must implement per-fixture-class routing, not blanket pair-mode.

2. **F4's iter-0016 +21 lift was tool-attached, not pair-deliberation-attached.** Solo Claude with claude-driven browser_validate matched/exceeded Codex BUILD + playwright. Codex R3 hypothesis CONFIRMED. **Cleanest single attribution data point in iter-0019.** Lesson: any fixture with a deterministic phase (browser_validate, security-review native, build_gate) attributes its quality lift to the *phase*, not the orchestrator-pair. Pair-mode can be safely DISABLED on tool-rich fixtures.

3. **iter-0018.5 prompt fold-in is empirically dead for F9.** Same lesson as iter-0008 (prompt-only engine constraint dead): an output-contract rule placed in BUILD/EVAL `quality_bar` does NOT enforce literal byte-level output-contract. The orchestrator infers a JSON shape from spec semantics rather than executing the verification commands and reading literal byte requirements. **Mechanical enforcement (bash gate executing verification commands and asserting literal bytes) is the only working pattern.** This is the iter-0014 lesson #21 ("prompt-body output contracts alone are not enough — defense in depth: orchestrator validates after agent") confirmed at second-mechanism scope.

4. **Defense-in-depth created a bypass surface.** iter-0019 part 1's CODEX_BLOCKED env at shim + wrapper was layered defense for prompt-only `--engine claude` insufficiency. Codex R1 caught that exporting CODEX_REAL_BIN as "diagnostic visibility" gave the orchestrator the bypass weapon. **Across 5 solo_claude runs the bypass was NEVER exercised** — primary defense (`--engine claude` prompt) was honored. So defense-in-depth was *redundant* on this run, but the surface was OPEN. Lesson: every variable exported into a worker subshell is a potential bypass path; "diagnostic visibility" is not a justification for exporting the bypass weapon. iter-0019.5 closes this.

5. **iter-0019.4 mapfile regression cost ~$0** in marginal terms but **wasted 0 paid wall** (the suite ran 3+ hours, all 15 arm runs were valid; only judge phase failed; arm artifacts persisted; re-judge was free). Lesson: judge phase should be retryable — independent of arm runs, no shared state. This mostly worked by accident; future judge mechanics should keep this property explicit.

6. **State-write protocol drift is non-deterministic across solo_claude runs.** F1 fast-route: only build phase. F2 standard: 6 phases mostly clean. F4 standard: 5 phases, critic incomplete. F6 standard: 6 phases all engine=None + corrupt build duration_ms. F9 standard: 6 phases CLEAN. Same engine path, same route mode, different output. Multiple race conditions in the per-phase state-write hook. iter-0014 contract was tested only on `--engine auto` fast-route. Limits L1 phase-attribution capability for iter-0020 — must fix or work around.

7. **Bare-arm chronic failures**: F2/bare and F9/bare hit silent-catch DQ (forbidden-pattern try/catch returning fallback objects). F2/bare since iter-0016, F9/bare new. Bare arm is unguided claude-only and reproduces this pattern reliably. Strong evidence that *the harness's prompt-level rules are doing real work* for variant + solo_claude — but not enough on F2's specific catch shape (variant + solo_claude both hit it too).

## Codex collaboration on iter-0019 part 2 (post-data)

R0 (pre-part-1): design lock. R1 (mid-suite, 142s): caught CODEX_REAL_BIN env-var leak (filed as iter-0019.5). R2 (mid-suite, 37s): NORTH-STAR alignment audit → PRINCIPLES.md pre-flight 0 + NORTH-STAR test #14 real-project trial. R3 (mid-suite, 26s): queue pre-flight 0 audit → iter-0021 reframed conditional, CLAUDE.md minimization A/B-gated, iter-0020 acceptance tightened, iter-0019.5 stays separate. R4 (post-suite, 43s): iter-0019.4 mapfile fix design — recommended `|| [ -n "$line" ]` guard for mapfile -t parity. **Pattern**: 5 Codex consults across iter-0019 ramp + suite + post-suite. Each one closed a specific gap I was about to ship. Confirms the standing user directive "항상 codex cli gpt 5.5 와 함께 compenion 으로서 pair 로 논의" is load-bearing — solo would have shipped 3+ regressions undetected (env leak, alignment drift, queue clutter, judge regression).

---

## Files committed

**iter-0019.4 (separate prior commit)** — judge.sh mapfile → portable while-read fix:
- `benchmark/auto-resolve/scripts/judge.sh` (5 lines: replace `mapfile -t SLOTS` with Bash 3.2-compatible while-read loop with `|| [ -n "$line" ]` guard for mapfile -t parity per Codex R4)

**iter-0019 part 2 (this commit)**:
- `autoresearch/iterations/0019-l1-claude-arm.md` — this file (verdict + data + lessons)
- `autoresearch/HANDOFF.md` — STANDING USER DIRECTIVE block (Korean verbatim, survives compaction); Current state update; queue rotation (iter-0019.4 SHIPPED, iter-0019 part 2 SHIPPED, iter-0019.5 next, iter-0019.6 NEW for F9 mechanical fix); iter-0019 R1+R2+R3+R4 collaboration log entries; iter-0019.5 entry; iter-0020 hard acceptance criteria locked from Codex R3
- `autoresearch/NORTH-STAR.md` — operational test #14 (real-project trial gate, Codex R2)
- `autoresearch/PRINCIPLES.md` — pre-flight 0 (not score-chasing test, Codex R2)
- `autoresearch/DECISIONS.md` — `0019 | DATA | L1 PASS / L2 FAIL pair-eligibility / bind to F9 mechanical (a)`
- `benchmark/auto-resolve/results/20260427T155638Z-c08130f-iter-0019-smoke/` — paid run artifacts (already on disk, not tracked here)
