# iter-0019.6 acceptance — F9-only paid suite verifies mechanical output-contract gate

**Status**: **SHIPPED-VERIFIED** (this iter file commits the verdict). RUN_ID `20260427T235114Z-da3eef5-iter-0019-6-acceptance`. Suite completed 2026-04-28T01:01:42Z.
**Date**: 2026-04-28
**Branch**: benchmark/v3.6-ab-20260423-191315
**Commit at start of paid run**: `660871c` (CLAUDE.md subtractive-first + goal-locked rules — variant arm copied pre-edit CLAUDE.md at startup, see "Asymmetry note" below).
**Cost**: ~$5-10 paid run (1 fixture × 3 arms + 1 judge invocation)
**Wall**: ~70min total (variant 2632s, solo_claude 1369s, bare 70s)

## Why this iter exists (Pre-flight 0)

This iter exists because it **closes the acceptance gate for iter-0019.6** — the harness-side mechanical output-contract enforcement that bound to verdict option (a) of iter-0019 part 2. iter-0019.6 shipped to commit but its real-mechanism behavior was unproven outside unit-style staging. Without this acceptance run we would not know whether the BUILD_GATE invocation, fix-loop routing, and findings-schema integration actually fire on a real F9 paid arm. **User-visible failure being closed**: F9 verify_score=0.4 ceiling across all engines (iter-0019 paid run); iter-0018.5 prompt-only fold-in was empirically dead.

This iter does NOT do "more measurement" without behavior change — the acceptance verdict directly determines whether iter-0020 (cost-aware pair policy) starts now or whether iter-0019.7 fix-loop enrichment fires instead. Pre-flight 0 PASSES.

## Hypotheses (locked BEFORE data)

1. **F9/variant.verify_score ≥ 0.6** under iter-0019.6 mechanical gate (was 0.4 across all 3 arms in iter-0019). Mechanism: spec-verify-check.py emits CRITICAL `correctness.spec-literal-mismatch` on round-1 BUILD_GATE; PHASE 2.5 fix-loop picks them up; round-2 BUILD_GATE re-runs and all 5 verification_commands pass.
2. **Fix-loop converges in ≤2 rounds.** Mechanism: canonical finding fields (rule_id, fix_hint, criterion_ref) carry enough signal for a Claude orchestrator to perform the contract-aligning edit in one round.
3. **iter-0019.6.1 (F9 cmd #5 false-positive fix) is load-bearing.** Mechanism: without dropping `stdout_not_contains: ["fail "]`, Node's `# fail 0` summary trips the literal scrape on every healthy run, BUILD_GATE loops on an unfixable contract, fix-loop exhausts.
4. **Mechanical gate produces strictly more output coverage than the prompt-only iter-0018.5 fold-in.** Refutation: same shape failures (wrong JSON keys, wrong exit code) recur post-iter-0019.6 — falsifies the mechanism.

## Data (filled in AFTER summary.json + per-arm artifacts landed)

### Acceptance gate (load-bearing)

| Field | Value | Threshold | Verdict |
|---|---|---|---|
| F9/variant.verify_score | **1.0** | ≥ 0.6 | **PASS** by 67% |
| F9/variant.disqualifier | false | false | **PASS** |
| F9/variant `correctness.spec-literal-mismatch` CRITICAL findings post-EVAL | **0** | 0 | **PASS** |
| F9/variant.commands_passed | **5/5** | n/a | All staged contracts satisfied |

**Codex GPT-5.5 wording correction adopted (R-verdict, 2026-04-28)**: the "0 CRITICAL findings post-EVAL" claim is namespaced to `correctness.spec-literal-mismatch` (iter-0019.6 scope). The benchmark JUDGE still emits 2 critical findings on F9/variant — "Human author output does not follow the required lines 3-5 ranked format" and "Non-git error message does not match the required exact stderr text" — these are non-DQ, out of iter-0019.6 scope, and queued for iter-0020+ gate enrichment (richer-than-literal contract enforcement).

### Mechanism trace (work_dir `pipeline.state.json` + transcript narrative)

| Phase | Round | Verdict | Duration | Notes |
|---|---|---|---|---|
| BUILD | 0 | PASS | 557s | Initial implementation followed ideate-generated spec text (`topAuthors`/exit 1) |
| BUILD_GATE | 1 (round_0) | **FAIL** | — | spec-verify-check.py fired: 2/5 commands failed → 2 CRITICAL `correctness.spec-literal-mismatch` |
| fix_loop_round_1 | 1 | PASS | 399s | triggered_by=build_gate; orchestrator aligned implementation to harness contract (`authors`/exit 2) |
| BUILD_GATE | 1 (round_1 re-run) | PASS | 5s | spec-verify 5/5 pass |
| EVALUATE | 1 | PASS_WITH_ISSUES | 120s | 3 LOW findings only (no CRITICAL/HIGH) |
| final_report | 1 | PASS_WITH_ISSUES | 15s | run terminal verdict |

**Fix-loop convergence**: 1 round (Hypothesis 2 PASS).

**Round-1 BUILD_GATE finding shape** (from `build_gate.log.md:18-24` + `fix-batch.round-1.json:10,20`):
- 2 CRITICAL `correctness.spec-literal-mismatch` findings
- Specifically: `topAuthors` ≠ `authors` (JSON key); exit 1 ≠ exit 2 (out-of-repo failure)
- Same shape iter-0019 saw across all 3 arms with verify=0.4 — Hypothesis 4 PASS (mechanism caught the exact iter-0018.5 failure mode).

**Post-EVAL findings** (from `evaluate.findings.jsonl`):
- LOW × 2: `scope.spec-vs-spec-verify-conflict` — User-readable spec said `topAuthors`/exit 1 but code emits `authors`/exit 2 to satisfy harness. **This is the gate winning**: the harness contract binds; ideate-spec divergence is flagged for follow-up correction (LOW), code is correct against the binding ground truth.
- LOW × 1: `hygiene.dead-code` — spurious `tests/index.js` (single-line require shim).

### Comparison vs iter-0019 (no gate)

Same fixture, same workflow, gate added:

| Metric | iter-0019 (no gate) | iter-0019.6 (with gate) | Delta |
|---|---|---|---|
| F9/variant.verify_score | 0.4 | 1.0 | **+0.6** |
| F9/variant.score (judge) | 74 | 88 | **+14** |
| F9/variant.disqualifier | true (silent-catch + spec) | **false** | spec-DQ resolved |
| F9/variant.wall_s | 1278 | 2632 | +106% (1 fix-loop round added 399s + extra build re-run) |

**Mechanism is content-agnostic**: spec-verify-check.py loops over all `verification_commands` with no hard-coded count assumption (`spec-verify-check.py:80`); per-command 60s timeouts (`:99`); silent no-op when `.devlyn/spec-verify.json` absent (`:52`).

### Side data (NOT acceptance, context for iter-0020 design)

| Metric | Value | Note |
|---|---|---|
| F9/L1 (solo_claude) score | 73 ⚠DQ | silent-catch DQ — solo Claude itself produced fallback patterns; NOT codex contamination (settings.json shows no `CODEX_REAL_BIN`) |
| F9/L0 (bare) score | 70 ⚠DQ | silent-catch + JSON shape + missing planning artifacts |
| L2-L1 margin (F9) | +15 | iter-0019 was −7. Big swing partly L1 falling to DQ, partly L2 rising via iter-0019.6 mechanism |
| L1-L0 margin (F9) | +3 | Below NORTH-STAR floor of +5; this is 1-fixture smoke read, not the L1 release gate (that's iter-0020's 9-fixture run) |
| Wall L2/L1/L0 | 2632s/1369s/70s | wall ratios 37.6× (L2/L0), 19.6× (L1/L0), 1.9× (L2/L1) |

## Codex GPT-5.5 R-verdict (2026-04-28, post-suite, 138k tokens, 256s, xhigh)

**Verdict**: **ship-as-PASS**. No data gap requiring hold or rerun.

Codex evidence path (cited):
- HANDOFF defines this as F9-only paid acceptance gate, not 9-fixture release gate (`HANDOFF.md:34`, interpretation #1 at `:64`).
- Variant numbers pass at `result.json` lines 5-8 (`disqualifier=false`, `verify_score=1.0`, `commands_passed=5`, `commands_total=5`).
- Mechanism fired on intended failure: `build_gate.log.md:18` 2/5 failed with 2 CRITICAL; `:23` `topAuthors` vs `authors`; `:24` exit 1 vs 2.
- Fix-loop consumed canonical findings: `fix-batch.round-1.json:10,20` both `correctness.spec-literal-mismatch`; `:16` 5 spec-verify pass post-fix.
- Final gate converged: `pipeline.state.json:178,192,221`; `evaluate.log.md:3` 3 LOW 0 CRITICAL; `:5` spec-verify green 5/5.

**Codex Q answers** (all confirm draft):
- **Q1** (1-fixture sufficient?): YES, HANDOFF explicitly scoped acceptance to F9. NOT sufficient for NORTH-STAR release readiness — `NORTH-STAR.md:83` forbids release-readiness language until iter-0020's 9-fixture run.
- **Q2** (judge findings invalidate?): NO. Two judge criticals are outside the staged literal contract. Record explicitly as residual; do not imply "no criticals anywhere."
- **Q3** (L1 silent-catch DQ contaminates?): NO. Solo settings show only `PATH` and `CODEX_BLOCKED=1`, no `CODEX_REAL_BIN` (`.claude/settings.json:2`). DQ is judge-side silent-catch behavior, not codex leakage.
- **Q4** (L1-L0=+3 NORTH-STAR violation?): NO. F9-only run is not the L1 release gate.
- **Q5** (iter-0020 unblock pre-flight 0?): CONFIRMED. iter-0019.6 passing only unblocks iter-0020 starting; iter-0020 has its own hard acceptance at `HANDOFF.md:156`.
- **Q6** (mechanism fragility?): Main fragility is claim-boundary, not mechanism. Helper has no hard-coded command count. **Real-user runs without staging are deliberate no-op** (`spec-verify-check.py:52`) — do NOT claim real-user coverage yet. iter-0020 must address how /devlyn:ideate generates `.devlyn/spec-verify.json` from a spec's "## Verification" section before real-user runs benefit from this gate.

Codex's wording correction adopted in the verdict statement above.

## What this iter unlocks

**iter-0020** (cost-aware pair policy + 9-fixture L0/L1/L2 paid run) is **UNBLOCKED**. Per HANDOFF queue item #1 + Codex R3 hard acceptance: iter-0020 ships only if it produces ALL FIVE — per-fixture-class routing table, at least one routing decision differing from current behavior, deterministic short-circuit/abort enforced in code, coverage.json proving every changed route was exercised, recorded rollback condition. Aggregate score movement alone is non-acceptance evidence.

**iter-0019.7 (fix-loop enrichment) is NOT triggered.** Mechanism converged in 1 round on the canonical schema; no enrichment needed.

**Real-user contract generation gap is queued**: spec-verify-check.py is silent no-op without `.devlyn/spec-verify.json`. iter-0020 OR a new iter-0019.8 must address how /devlyn:ideate emits this from spec's "## Verification" section so non-benchmark users get the same gate.

**Gate enrichment for richer-than-literal contracts is queued**: F9/variant has 2 residual JUDGE-side critical findings (ranked format, exact stderr text) the mechanical gate did NOT catch. iter-0020+ should evaluate whether to extend the gate's vocabulary (regex contracts, line-position contracts) vs leaving these for the judge.

## Asymmetry note (transparent)

The acceptance suite ran on commit `660871c` which had two CLAUDE.md edits committed mid-suite:
1. `da3eef5` (iter-0019.6.1) — F9 cmd #5 false-positive fix. Pre-suite, load-bearing for the acceptance run itself.
2. `660871c` (subtractive-first + goal-locked rules) — committed AFTER variant arm copied pre-edit CLAUDE.md at startup (`run-fixture.sh:84-86`). solo_claude and bare arms started after this commit and copied the new CLAUDE.md. **The load-bearing iter-0019.6 acceptance metric (F9/variant.verify_score) is on the variant arm only, which used pre-edit CLAUDE.md** — the verdict is uncontaminated. solo_claude/bare data carries mild CLAUDE.md asymmetry but is not load-bearing for this gate.

## Principles 1-6 check

- **Pre-flight 0 (not score-chasing)**: ✅ PASSES. The verdict directly maps to a binding go/no-go: iter-0020 unblock vs iter-0019.7 enrichment fire. Single-fixture acceptance is not an aggregate-margin claim.
- **#1 No overengineering**: ✅ PASSES. iter-0019.6 helper script is 250 lines (single-purpose, no abstractions); iter-0019.6.1 fix is 1-key removal; this acceptance run is 1 fixture, not a 9-fixture re-baseline.
- **#2 No guesswork**: ✅ PASSES. Hypotheses 1-4 named direction + metric + mechanism BEFORE the run; data table filled AFTER; no retroactive prediction edit. Surprise outcome (L2-L1=+15 vs iter-0019's -7) recorded with attribution split between L1 falling and L2 rising.
- **#3 No workaround**: ✅ PASSES. Root-cause: prompt-only contract enforcement is dead at scale (iter-0008 lesson, iter-0018.5 confirmed); mechanical bash-gate is the level the why-chain reaches. No `any`, no silent catch, no hardcoded fallback. iter-0019.6.1 fixed an unsatisfiable contract, not a symptom.
- **#4 Worldclass production-ready**: ✅ PASSES on iter-0019.6 scope (`correctness.spec-literal-mismatch` cleared, disqualifier=false). 2 residual JUDGE-side critical findings are out of iter-0019.6 scope and queued for iter-0020+ enrichment — flagged in verdict, not hand-waved.
- **#5 Best practice**: ✅ PASSES. Helper uses standard Python `subprocess.run` + canonical findings schema (no hand-rolled invariants); fix-loop routing reuses existing PHASE 2.5 (no parallel pipeline).
- **#6 Layer-cost-justified**: ✅ ITERATION-LOOP scope passes (Codex pair-review on launch + verdict; cost amortized over every future harness change reading the iter-0019.6 mechanism). AUTO-RESOLVE scope is N/A for this iter — F9 acceptance does not change pair-vs-solo routing; that's iter-0020.

## Lessons (cumulative, for future iters)

1. **Mechanical bash-gates beat prompt-only contracts on every dimension that matters at scale.** iter-0008 → iter-0009 (orchestrator banned shape) lesson now confirmed at second mechanism scope (iter-0018.5 → iter-0019.6, output-contract). Future "we'll just tell the orchestrator in the prompt" candidates should be considered prompt-only-dead by default.
2. **Pre-launch Codex pair-review on paid-run gates pays for itself.** R-launch caught iter-0019.6.1 (F9 cmd #5 false-positive) before $5-10 was spent; without it the acceptance run would have looped on an unfixable contract until exhaustion. iter-0007 / iter-0010 / iter-0013 lessons reinforced.
3. **Promotion of weak signal to strong gate requires fixture-contract audit.** When tightening a signal layer (verify-score noise → CRITICAL block), audit the contracts beneath for runner-output self-references and other unsatisfiable shapes. Same anti-pattern as iter-0019.5's CODEX_REAL_BIN export ("diagnostic visibility justifies bypass weapon export"): "weak-signal noise" can become "fatal block" simply by tightening the layer beneath the contract.
4. **Aggregate margin volatility on small-N reads is real.** F9 L2-L1 went from -7 (iter-0019, 5-fixture suite) to +15 (this acceptance, 1-fixture). The +15 is mostly L1 falling to DQ, not L2 rising. Single-fixture per-arm margins are noisy; statistical claims must wait for iter-0020's 9-fixture run.
5. **The mechanical gate addresses literal contracts, NOT judge-quality contracts.** F9/variant has 2 residual JUDGE-side critical findings (ranked format, exact stderr text) — these are richer-than-literal and require either (a) extending the gate's vocabulary or (b) leaving them for the judge. iter-0020+ design call.
6. **Real-user coverage is silent no-op without spec-verify.json staging.** Benchmark fixtures get this for free via run-fixture.sh; real /devlyn:ideate users do not until ideate generates the JSON from a spec's "## Verification" section. Out of scope for iter-0019.6 but front-of-queue for iter-0020 design.
