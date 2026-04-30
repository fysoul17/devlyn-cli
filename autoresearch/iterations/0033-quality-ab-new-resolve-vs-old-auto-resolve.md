---
iter: "0033"
title: "Quality A/B (C1) — NEW `/devlyn:resolve` L1 vs OLD `/devlyn:auto-resolve` L1 on F1-F8"
status: PROPOSED
type: measurement — partial gate for Phase 4 cutover (paired with iter-0033a)
shipped_commit: TBD
date: 2026-04-30
mission: 1
codex_r0: 2026-04-30 (494s, 6 blocking findings adopted; original draft rescoped)
codex_r05: 2026-04-30 (256s, 5/6 closed + Gate 2 contradiction + dirty-SHA mechanical gate + F8 wall-time exempt + variant strictly diagnostic + sequencing flip)
---

# iter-0033 — Quality A/B (C1): NEW L1 vs OLD L1 on F1-F8

## Why this iter exists (PRINCIPLES.md pre-flight 0)

Partial gate for **iter-0034 Phase 4 cutover**. Paired with iter-0033a (F9 fixture redesign). Together they unlock Phase 4 deprecation of `/devlyn:auto-resolve`.

Original iter-0033 draft (F1-F9 + S1, L1 + L2 arms) was REJECTED at Codex R0 (2026-04-30, 494s, model_reasoning_effort=xhigh) on 6 blocking findings. Rescoped to C1 here; the carved-out work moves to iter-0033a.

## Mission 1 service (PRINCIPLES.md #7)

Single-task L1 surface quality. The 2-skill redesign Phases 1-3 SHIPPED skill bodies (iter-0029/0031/0032) without comparative measurement. Mission 1 hard NOs untouched.

## R0 falsification adopted (Codex GPT-5.5, 2026-04-30)

| # | Codex finding | Disposition |
|---|---|---|
| 1 | S1 mixed-suite is unsupported (`run-suite.sh --suite` is mutex; `judge.sh` reads only `fixtures/`) | **Drop S1 from this iter.** S1 measurement defers to iter-0033b (post-Phase-4) or returns when iter-0030 phase B ships multi-suite report. |
| 2 | F9 fixture is the old 3-skill novice contract (ideate→auto-resolve→preflight); new 2-skill design has no preflight | **Carve F9 out → iter-0033a (F9 fixture redesign).** Redesign Phase 3.5: bring F9 into 2-skill contract before re-measuring. |
| 3 | New ideate emits `docs/specs/<id>/spec.md`; F9 expected requires `docs/VISION.md` + `docs/ROADMAP.md` + `docs/roadmap/phase-1/*.md` | Rolls into iter-0033a fixture rewrite. |
| 4 | NEW prompt swap must use `/devlyn:resolve --spec <path>` explicitly; bare command-name routes to free-form classifier (PHASE 0 confound) | **Adopted.** F1-F8 NEW prompts hardcode `--spec` to the staged spec at `docs/roadmap/phase-1/<FIXTURE>.md` (same path the OLD harness pre-stages, see `run-fixture.sh:267-269`). |
| 5 | L2 architecture is non-comparable: OLD L2 = Codex BUILD/FIX; NEW L2 = Claude IMPLEMENT + VERIFY/JUDGE pair only. Same-label ≠ same-mechanism | **Drop L2 arms from this iter.** L2 measurement is its own future iter once F9 is rebuilt and VERIFY/JUDGE pair gating is exercised across more fixtures. iter-0033 measures L1 only — single-LLM users are first-class per NORTH-STAR test #1-#4. |
| 6 | Same-HEAD claim is false with a dirty `--resolve-skill` flag; `summary.json` records only `git rev-parse HEAD` | **Adopted.** Harness change commits BEFORE both suite passes. Same SHA, clean tree, deterministic provenance. |

Additional Codex direct answers adopted in gates below.

## Hypothesis

Greenfield `/devlyn:resolve` (175-line SKILL + 5 phase prompts + 2 references + iter-0029 adapter system) preserves load-bearing mechanisms (state discipline, BUILD_GATE, fresh-subagent VERIFY, mechanical spec-verify) while removing surface-area accretion. On F1-F8 (excluding F9, deferred), NEW L1 should match or exceed OLD L1.

**Falsifiable predictions (BEFORE run):**

- **Suite-avg margin (NEW vs L0) ≥ Suite-avg margin (OLD vs L0) − 1.0** — Codex R0 tightened from −2.0; one-axis judge variance is ±3 but suite-avg over 8 fixtures has lower noise.
- **Per-fixture regression**: every fixture (F1-F8): `(NEW − OLD) ≥ −5` axes.
- **Categorical reliability**: NEW L1 disqualifier rate ≤ OLD L1 disqualifier rate on identical fixtures.
- **Wall-time (layered)**: suite-total NEW L1 ≤ 1.15× suite-total OLD L1 (soft); per-fixture fail if ratio > 1.25× AND absolute delta > 120s; per-fixture > 1.50× = hard fail.
- **CRITICAL/HIGH findings**: zero NEW-arm CRITICAL or HIGH `design.*` / `security.*` findings on previously-clean fixtures.
- **Watchdog**: zero NEW-arm timeouts.
- **Artifact contract** (Codex Gate 9): NEW arm produces `.devlyn/runs/<run_id>/pipeline.state.json` archived, `state.phases.final_report.verdict` non-null, `state.source.spec_path` correct, build_gate + verify findings files present, `spec.expected.json` present where contract requires.

## Predicted directions (filled BEFORE run)

- Suite-avg delta in [−1.0, +2.0]; net ≈ 0.
- F1 (trivial), F2 (medium silent-catch) → NEW slightly cleaner.
- F4 (browser), F6 (dep-audit), F7 (out-of-scope trap) → tighter contest, NEW could be ±2.
- Wall-time: NEW slightly faster (greenfield SKILL is leaner) — predicted F1-F7 ratio ≈ 0.95-1.05.

## Scope (locked)

### Ships in this iter (single commit before suite runs)

1. **Harness change**: `benchmark/auto-resolve/scripts/run-fixture.sh` — add `--resolve-skill <new|old>` flag (default `old`). When `new`:
   - Replace standard variant/solo_claude prompt body (currently `run-fixture.sh:270-274`) with: `Use the /devlyn:resolve --spec docs/roadmap/phase-1/<FIXTURE>.md ${ENGINE_CLAUSE} skill to implement the spec…`
   - F9 branch (line 250+): emit a hard error `--resolve-skill new is not supported on F9 until iter-0033a redesigns the fixture; skip F9 or pass --resolve-skill old`. Refuse to run instead of producing invalid data.
2. **`run-suite.sh`** propagates `--resolve-skill` flag.
3. **Lint check** in `scripts/lint-skills.sh`: when `--resolve-skill new` is passed and any fixture is F9, exit non-zero (defense in depth against accidental F9 contamination).
4. **Two suite passes** at the same committed HEAD:
   - `iter-0033-old`: `--resolve-skill old`, fixtures `F1 F2 F3 F4 F5 F6 F7 F8`. All three arms (variant, solo_claude, bare) re-run for full isolation.
   - `iter-0033-new`: `--resolve-skill new`, same 8 fixtures. solo_claude (NEW L1) and bare (re-run); variant captured for diagnostics, NOT gated.
5. **Comparison artifact**: small Python script `scripts/iter-0033-compare.py` reads both runs' `summary.json` and emits the gate table.

### Does NOT ship in this iter

- F9 (carved to iter-0033a).
- S1 / shadow suite (defers to iter-0030 phase B or post-Phase-4).
- L2 arm gating (variant captured for diagnostics only; no gate fires on it).
- Any change to NEW skill prompts (this is measurement, not tuning — failures open separate root-cause iter).
- Phase 4 cutover.

### Subtractive-first check (PRINCIPLES.md #1)

- **Could we delete instead of adding `--resolve-skill`?** No — git-flipping mid-iter contaminates SHA capture (Codex R0 #6).
- **Could we delete the variant arm from the NEW pass?** Considered. Diagnostic capture is cheap and aids interpretation if NEW L1 surprises us. Variant runs but does NOT gate.
- **Flag deletion plan**: removed in iter-0034 once OLD skill is gone.

## Codex pair-review plan

- ✅ **R0** complete (494s, 6 blockers adopted). This redraft IS the R0 disposition.
- **R0.5** (BEFORE harness change commit): send this redraft to Codex. Falsification ask: "Does the rescope close the original 6 findings? Does the artifact contract gate include everything I should check, or is there a missing artifact?"
- **R-final** (AFTER both runs): raw numbers + draft conclusion.

## Acceptance gate (pre-registered)

| Gate | Threshold | Source |
|---|---|---|
| 1. L1 suite-avg margin delta | NEW − OLD ≥ −1.0 (suite-avg over F1-F7; F8 reporting only) | Codex R0 + R0.5 |
| 2. L1 per-fixture regression | every fixture **F1-F7**: NEW − OLD ≥ −5. F8 captured for record, not gating. | Codex R0.5 (Gate 2 contradiction fix) |
| 3. L1 disqualifier rate | NEW ≤ OLD on F1-F7 (F8 excepted) | original |
| 4. Wall-time suite-total | F1-F7 only: NEW ≤ 1.15× OLD | Codex R0.5 |
| 5. Wall-time per-fixture | F1-F7: fail if ratio > 1.25× AND delta > 120s; > 1.50× = hard fail. F8: warning only; hard fail only if > 1.5× AND delta > 300s OR timeout/invoke failure. | Codex R0.5 |
| 6. CRITICAL/HIGH | zero NEW findings on previously-clean F1-F7 | PRINCIPLES.md #4 |
| 7. Watchdog | zero NEW-arm timeouts (all 8 fixtures) | original |
| 8. Clean-tree provenance | both runs' `summary.git_sha` identical AND clean-tree-at-start sentinel present (no dirty harness diff between passes) | Codex R0.5 (mechanical close of dirty-SHA blocker) |
| 9. Artifact contract | full list in `<artifact_contract>` block below | Codex R0.5 expansion |

**All 9 gates must pass to clear iter-0033.** F9 NEW PASS is iter-0033a's gate (separately required for Phase 4). iter-0033c (NEW L2 vs NEW L1) is the third gate before Phase 4 cutover.

<artifact_contract>
Per Codex R0.5 §C — both NEW arms (solo_claude, variant) must produce these. Missing any item = Gate 9 fail.

**Run-level provenance**:
- `summary.git_sha` identical for `iter-0033-old` and `iter-0033-new` runs.
- Clean-tree sentinel: `git status --porcelain` empty at suite start, captured to `summary.clean_tree: true`.
- Fixture list exactly `F1 F2 F3 F4 F5 F6 F7 F8`; no F9 in either run.
- **Per-fixture `NEW L1 vs L0` margin** (Codex R0 iter-0033c §4 dependency): `summary.json` rows for the NEW pass MUST include the per-fixture margin between `solo_claude` and `bare`. iter-0033c freezes its pair-eligible "L1 ≤ L0" subset from this column. Without it, iter-0033c Gate 3 cannot be evaluated.

**Per-arm prompt fingerprint** (in `result.json` or transcript scan):
- OLD arm prompt contains `auto-resolve`. NEW arm prompt contains `resolve --spec`. NEW arm prompt does NOT contain `auto-resolve` or `preflight`.
- NEW arm: no free-form route triggered. State `mode == "spec"`, `source.type == "spec"`, `complexity == null`, `criteria_path == null`.

**Per-arm invocation health**:
- `result.json.invoke_exit == 0`, `invoke_failure == false`, `timed_out == false`.

**Judge artifacts**:
- raw `judge.json` exists per fixture.
- `_axis_validation.out_of_range_count == 0`.

**Pipeline state (NEW arms only — solo_claude + variant)**:
- archived `.devlyn/runs/<run_id>/pipeline.state.json` exists.
- `state.source.spec_path == docs/roadmap/phase-1/<FIXTURE>.md` (NEW path).
- `state.source.spec_sha256` matches sha256 of the staged spec.md.
- every phase `plan/implement/build_gate/cleanup/verify/final_report` has non-null `verdict`, `completed_at`, `duration_ms`.
- `state.phases.final_report.verdict ∈ {PASS, PASS_WITH_ISSUES, NEEDS_WORK, BLOCKED}` (no null).

**Spec-verify carrier**:
- archived `.devlyn/spec-verify.json` exists; `len(commands) == len(fixture expected.json verification_commands)`.
- post-BUILD_GATE/VERIFY `spec-verify.results.json` exists.

**Verify sub-verdicts**:
- `state.phases.verify.sub_verdicts.mechanical` non-null.
- `state.phases.verify.sub_verdicts.judge` non-null.
- (pair_judge sub-verdict NOT required since L2 not gated this iter.)

**Findings JSONL**:
- `.devlyn/build_gate.findings.jsonl`, `.devlyn/verify-mechanical.findings.jsonl`, `.devlyn/verify.findings.jsonl` parse as valid JSONL.
- severity counts non-negative, total per file matches line count.

**Cleanup invariant**:
- `state.phases.cleanup.pre_sha` present.
- if cleanup produced a diff outside the allowlist, a `cleanup.findings.jsonl` revert finding was emitted (regression check).
</artifact_contract>

## Phase 4 cutover decision tree (Codex R0 root-cause framing)

- **Measurement bug** (judge inconsistency, harness drift, env contamination) → fix the bug, rerun iter-0033.
- **Product-contract break** (NEW skill missing artifact, wrong path, mode mismatch) → block Phase 4. Open root-cause iter.
- **Fixture-local quality regression** (1-2 fixtures, NEW − OLD < −5) → open iter-0033b targeted-tuning iter; rerun.
- **Wall-time regression** (gate 4/5 fails) → tune NEW skill prompts; rerun.
- **CRITICAL/HIGH on NEW** (gate 6) → root-cause iter; do NOT proceed to Phase 4 until clean.

Phase 4 cutover requires: iter-0033a PASS (F9 NEW ≥ +5 vs L0) + iter-0033 (C1) PASS (8 fixtures, 9 gates) + iter-0033c PASS (NEW L2 vs NEW L1).

## Why this is not score-chasing (PRINCIPLES.md #0)

Measurement-only. Cannot move scores. Unlocks a real shipping decision (Phase 4 cutover) — case (b) of PRINCIPLES.md #0.

## Risk register

| Risk | Mitigation |
|---|---|
| Suite-noise (judge variance ±3/axis) at n=1 | Gate 1 tightened to ≥ −1.0 over F1-F7; gate 2 (per-fixture −5) is at-noise hard floor; both must pass jointly. F8 reporting-only — excluded from gates 1/2/3/4/5/6 per Codex R0.5. |
| Variant arm runtime costs in NEW pass when not gated | Codex R0.5: variant in NEW pass is **strictly diagnostic, not gated**. If runtime is prohibitive, drop variant from NEW pass entirely; iter-0033c is the proper L2 measurement iter. |
| `--resolve-skill new` accidentally tries to run F9 | Lint check (scope §3) exits non-zero. Defense in depth. |
| Sequencing: iter-0033a should run BEFORE iter-0033 (Codex R0.5 §F) | Updated order below: iter-0033a first → iter-0033 (C1) → iter-0033c → iter-0034 Phase 4. |

## Principles check

- **#0 pre-flight**: ✅ unlocks iter-0034 (paired with iter-0033a).
- **#7 mission-bound**: ✅ Mission 1 single-task L1.
- **#1 no overengineering**: ✅ scope reduced post-R0; flag is the smallest reversible mechanism.
- **#2 no guesswork**: ✅ predictions filled BEFORE run; gates pre-registered.
- **#3 no workaround**: ✅ measurement, root-cause framing for failures.
- **#4 worldclass**: ✅ enforced via gate 6.
- **#5 best practice**: n/a (no skill code change).
- **#6 layer-cost-justified**: ✅ L1-only gating; L2 deferred to evidence-based future iter.

## Deliverable execution order

iter-0033a sequenced FIRST per Codex R0.5 §F. iter-0033 begins after iter-0033a passes (or is explicitly deferred by user). iter-0033c follows iter-0033 (C1).

1. **iter-0033a** completes (F9 fixture redesign + smokes #1-#3 + benchmark gate 4).
2. **R0.5 disposition complete** (this redraft).
3. Apply harness change (`run-fixture.sh` + `run-suite.sh` flag plumb + lint check + clean-tree sentinel + prompt fingerprint capture).
4. Commit harness change. Capture committed SHA → `iter-0033-old` and `iter-0033-new` both run on this SHA.
5. Run `iter-0033-old` (F1-F8, all 3 arms).
6. Run `iter-0033-new` (F1-F8, solo_claude + bare gated; variant strictly diagnostic).
7. Apply ship-gate via `scripts/iter-0033-compare.py` → produce 9-gate table.
8. **R-final** with Codex on raw numbers.
9. Update HANDOFF.md + DECISIONS.md.
10. **PASS path**: proceed to iter-0033c. **FAIL path**: branch on root-cause tree above.
