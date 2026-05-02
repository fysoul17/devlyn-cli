---
iter: "0033c"
title: "NEW L2 vs NEW L1 — pair-mode lift on `/devlyn:resolve` VERIFY/JUDGE"
status: PROPOSED
type: measurement — third gate for Phase 4 cutover
shipped_commit: TBD
date: 2026-04-30
mission: 1
gates: iter-0034-Phase-4-cutover (paired with iter-0033a + iter-0033 C1)
codex_r05: 2026-04-30 (256s §G — adopt: NEW L2 vs NEW L1, NOT vs L0; gate on no-regression + lift on pair-eligible fixtures + efficiency)
codex_r0_iter0033c: 2026-04-30 (226s — Option A confirmed dead; B2 primary + diagnostic forced; Gate 3 single threshold; pair-eligible frozen pre-registered; attribution 4-class causality; engine-config locked to same IMPLEMENT engine; Codex availability smoke added)
codex_r05_iter0033c: 2026-04-30 (196s — Gate 3 promoted to ship-blocker (Phase 4 loophole closed); Gate 6 fixture-level concrete rule; Codex availability check moved to harness layer with explicit L2 arms; pair-eligible refined (F1/F5 conditional, F8 reporting-only); implementation-confound smoke pre-suite; contract-mismatch deferred to doc-fix iter; sequencing: pre-commit selection rule + manifest checksum)
codex_r06_iter0033c: 2026-04-30 (28s — SIGN-OFF after one risk-register text fix: empty pair-eligible mitigation no longer says "Phase 4 not gated on Gate 3"; now says "Phase 4 remains blocked unless explicit NORTH-STAR amendment". Loophole closed.)
codex_r0_infra: 2026-05-02 (341s — REJECT-AS-DRAFTED on infra design. 9 corrections adopted: F3 OLD score 62 unusable (judge-DQ from old carrier — rerun L1 at iter-0033c HEAD); manifest input is canonical bundle {c1_summary selection-only, f9_judge, l1_rerun_summary} not single summary; smoke 1c on F2+F3 not F1+F2 (F1 901s flaky); L1 baseline rerun mandatory (carrier changed post-3bc86dd); CODEX_BLOCKED **omit** on L2 arms not =0 (shim blocks any non-empty); l2_gated/l2_forced plumbing across run-fixture.sh:38/100/156-178/223-241/261/269/413-420 + run-suite.sh:168/203-209 + judge.sh:43/326-336 + compile-report.py:69/137-147/179-200; --resolve-skill is benchmark flag not skill flag.)
codex_r05_infra: 2026-05-02 (248s — SIGN-OFF on revised design after 5 acceptance verdicts (Q2/Q3/Q4/Q5 agree, Q1 partial). Q1 manifest hash adopts pair-plan-lint.py:81-91 pre-stamp pattern (deepcopy + zero out manifest_sha256 + canonical compact JSON `sort_keys=True, separators=(",",":"), ensure_ascii=False, allow_nan=False`). Q6 surfaced 5 additional holes: spec-verify staging at 223-241 needs l2_*; shim PATH injection at 413-420 needs l2_*; judge.sh:326-336 hardcoded margin keys; compile-report.py 68/137/179 hardcoded arm assumptions; ship-gate.py:41-64 enforces variant/bare gates so new orchestrator MUST bypass it. Decision: write dedicated `scripts/run-iter-0033c.sh` orchestrator that calls run-fixture.sh per-fixture-per-arm and skips run-suite.sh/ship-gate.py entirely; iter-0033c-compare.py emits its own gate table.)
codex_rfinal_smoke: 2026-05-02 (284s — NO-GO on full suite as drafted. Two blockers cleared in same commit: (Q2) archive_run.py glob extended with `verify-judge-*.md` so pair-judge transcripts get archived (Gate 8 false-fail mitigated; both config + .claude mirrors); (extra miss #1) iter-0033c-compare.py placeholders for `pair_findings_distinguishable` and `impl_confounded` replaced with real evidence readers (audit anchor = whichever pair-firing arm is present; impl_confounded = symmetric_difference(solo, l2_forced) of changed-files.txt). One blocker DEFERRED for user decision (Q5): F2 fixed-diff `--verify-only` smoke per registered mitigation (line 153) — F2 confounded (solo touched 1 file vs l2_forced 2; l2_forced added test file solo skipped). Choice (b) is right per Codex; choice (a) "drop F2 from Gate 3" was my shortcut, rejected. F3 NOT confounded (both touched same 2 files). Smoke 1a PASS: `pair_judge: PASS_WITH_ISSUES` populated, Codex pair-JUDGE surfaced 4 medium findings Claude missed (deliberation_lift signal even when verdict-binding rule excluded them). Schema drift findings: `pair_merge_note` field (orchestrator wrote it, not in state-schema.md), `artifacts` documented as object but written as array in smoke 1a state (Codex Q1) → follow-up doc-fix iter.)
---

# iter-0033c — NEW L2 vs NEW L1 on the `/devlyn:resolve` skill surface

## Why this iter exists (PRINCIPLES.md pre-flight 0)

Phase 4 cutover deletes `/devlyn:auto-resolve`. Post-cutover, OLD L2 (Codex BUILD/FIX + Claude orchestrator) is gone forever. NORTH-STAR.md "two user groups, both first-class" requires **L2 to be measurable on the NEW skill surface** before the OLD surface is deleted — otherwise we ship Phase 4 with the L2 contract claim degraded to "unproven/disabled".

Codex R0.5 §G (2026-04-30): "If you skip iter-0033c, Phase 4 can only honestly ship an L1 cutover while marking L2 unproven/disabled. That conflicts with the current NORTH-STAR first-class L2 contract."

User adjudication 2026-04-30: include iter-0033c (= keep L2 first-class).

The user-visible failure this closes: shipping Phase 4 without L2 measurement = silently downgrading the multi-LLM-pair experience for users who installed Codex CLI. They get a harness whose pair-mode mechanics are documented in NORTH-STAR but never measured on the surface they're invoking.

## Mission 1 service (PRINCIPLES.md #7)

L2 measurement is single-task scope (one fixture at a time, no parallel-fleet). Mission 1 hard NOs untouched.

## Hypothesis

NEW `/devlyn:resolve` confines pair-mode to **VERIFY/JUDGE only** (per iter-0020 falsification + NORTH-STAR pair-vs-solo policy table, 2026-04-30 lock). The hypothesis under test:

> **For fixtures where L1 was tied or lost vs L0** (the "pair-eligible" set), enabling L2 (`--pair-verify` or coverage-failed-triggered pair-JUDGE) materially lifts judge-axis margins via second-model deliberation in VERIFY, without regressing easy fixtures or violating wall-time efficiency.

This is the empirical question NORTH-STAR test #11 ("tool-lift vs deliberation-lift") is set up to answer. If pair-JUDGE produces conclusions different from solo-JUDGE often enough to shift the verdict on hard fixtures, L2 earns its budget. If pair-JUDGE merely re-confirms solo, L2 is theatre.

**Falsifiable predictions (BEFORE run):**

- **No regression**: every fixture in F1-F8 (F9 included once iter-0033a passes): `(NEW L2-gated) − (NEW L1) ≥ −3` axes (Codex R0: matches NORTH-STAR no-regression).
- **Lift on pair-eligible fixtures (single threshold)**: on the **frozen pre-registered** pair-eligible set, `(NEW L2-gated) − (NEW L1) ≥ +5` on **at least 50%** of those fixtures. The `+3 / 75%` alternative becomes a reporting sensitivity metric ONLY, not a pass path. (Codex R0: disjoint thresholds = gameable; single gate.)
- **No hard-floor violations**: zero NEW L2 disqualifier on previously-clean L1 fixtures; zero NEW L2 CRITICAL/HIGH `design.*` / `security.*` findings on previously-clean L1 fixtures; zero L2 watchdog timeouts.
- **Efficiency** (Codex R0 §3 reframed): `L2_wall / L1_wall ≤ 2.0×` per fixture as a **wall budget**, NOT a dominance proof. At ratio 2.0×, L2's quality lift must exceed what L1-best-of-2 would erase given judge variance (±3/axis). Therefore `+5` lift is **provisional dominance only**; final dominance evaluation uses the L1 variance evidence captured during iter-0033 (C1). The `≤ 3.0×` ceiling is reserved exclusively for **categorical rescue** (a fixture where L2 catches a disqualifier-class issue L1 missed) — NOT triggered by `(L2-L1) > +5` alone.
- **Pair short-circuit discipline** (NORTH-STAR test #9): pair fires only when `coverage_failed=true` OR MECHANICAL warning findings present OR `--pair-verify` set. No vibe-confidence pair fires recorded in archive.
- **Attribution causality** (NORTH-STAR test #11, Codex R0 §5 reframed):
  - `no_material_lift`: score / verdict not materially changed even if extra findings appeared.
  - `implementation_confounded`: L1 and L2 implementations diverged (caused by `--pair-verify` upstream effects or non-determinism); cannot attribute lift to pair-JUDGE itself.
  - `tool_or_trigger_lift`: mechanical / coverage finding caused axis or verdict change.
  - `deliberation_lift`: pair_judge uniquely surfaces a verdict-binding finding OR axis rationale absent from both solo judge and mechanical findings.
  Count-of-findings differences alone are NOT attribution.

## Pair-eligible fixture set (FROZEN PRE-REGISTRATION, Codex R0 §4)

Per NORTH-STAR.md test #7 + 2026-04-30 lock: `pair-eligible = high-value fixtures (security/scope/spec-compliance regions) + any fixture where NEW L1 ≤ L0`.

**Frozen high-value list** (Codex R0.5 §D refined — committed before iter-0033c runs):
- **F2-cli-medium-subcommand** — silent-catch detection; spec-compliance / no-workaround region. **Pair-eligible.**
- **F3-backend-contract-risk** — contract violation detection; spec-compliance + design region. **Pair-eligible.**
- **F4-web-browser-design** — browser flow + design region. **Pair-eligible.**
- **F6-dep-audit-native-module** — security (dep audit) region. **Pair-eligible.**
- **F7-out-of-scope-trap** — scope discipline region. **Pair-eligible.**
- **F1-cli-trivial-flag** — **EXCLUDED from semantic list** (trivial; pair-JUDGE deliberation has no foothold). Promoted to pair-eligible only if iter-0033 (C1) shows `NEW L1 ≤ L0` on F1.
- **F5-fix-loop-red-green** — **EXCLUDED from semantic list** (fix-loop is BUILD_GATE concern, not VERIFY-JUDGE). Promoted only if iter-0033 (C1) shows `NEW L1 ≤ L0` on F5.
- **F8-known-limit-ambiguous** — **REPORTING-ONLY**. Counted toward attribution data and gate 5 wall-time observation, but excluded from Gate 3 pass calculation. Reason: F8 is excepted from quality gates suite-wide per RUBRIC; conscripting it as pair-eligible inflates Gate 3 denominator without adding signal.
- **F9-e2e-ideate-to-resolve** — only included if iter-0033a PASS landed first. **Pair-eligible** when included.

**Frozen-from-iter-0033 list** (added after iter-0033 (C1) results land but BEFORE iter-0033c runs):
- Any fixture where `NEW L1 vs L0 margin ≤ 0` per iter-0033 (C1) data. iter-0033 (C1) MUST emit per-fixture `NEW L1 vs L0` margin in summary.json (already added to iter-0033 redraft).

**Selection rule pre-commit** (Codex R0.5 §G): the high-value list above + the `L1 ≤ L0` selection rule are **committed BEFORE iter-0033 runs**, not derived after. Post-iter-0033, a manifest with checksum is generated from iter-0033's `summary.json` capturing which fixtures actually fell into `L1 ≤ L0`; iter-0033c uses the manifest, not on-the-fly computation. Same SHA preserved across both runs.

**Empty-set rule**: if frozen high-value list (post-exclusions) is empty AND no iter-0033 fixture has `NEW L1 ≤ L0`, Gate 3 evaluates to **NOT ASSESSABLE**, not pass. Phase 4 cutover then requires NORTH-STAR amendment ("L2 first-class temporarily disabled until pair-eligible fixtures exist") — not silent skip.

## Predicted directions (filled BEFORE run)

- Easy fixtures (F1, F5): L2-gated ≈ L1 within ±2. Pair short-circuits to solo most rounds.
- Frozen high-value fixtures (F2, F3, F7): L2-gated lifts L1 by +3 to +6 on ≥ 2 of these (forced arm provides upper-bound estimate).
- Wall-time: L2-gated / L1 ratio ≈ 1.0-1.4× on average (since pair fires sparingly under the gating policy); L2-forced ratio ≈ 1.5-2.0× on pair-eligible fixtures only.
- Attribution priors: ~50% deliberation_lift, ~30% tool_or_trigger_lift, ~15% no_material_lift, ~5% implementation_confounded. (Numbers are hypotheses; iter measures actual.)

## Scope (locked)

### Ships in this iter

1. **Pre-suite smokes** (cheap, gate the suite run):
   - **1a. L2 mode wiring**: `--pair-verify` on F1 produces `state.phases.verify.sub_verdicts.pair_judge` + archived `pipeline.state.json` + distinguishable second-judge findings.
   - **1b. Codex availability (harness layer)**: hard `command -v codex` check in iter-0033c suite-runner; fail fast if absent. Confirms `CODEX_BLOCKED=0` env in L2 arms.
   - **1c. Implementation-confound**: F1 + F2 each run NEW L1 vs NEW L2-forced; compare IMPLEMENT diff fingerprints (`git diff --stat` post-IMPLEMENT phase). If diffs differ materially across the same fixture between L1 and L2 runs, switch to **fixed-diff smoke**: capture L1's IMPLEMENT diff once, run `/devlyn:resolve --verify-only <diff> --spec <path>` for both L1 (solo) and L2 (forced), compare ONLY VERIFY-phase outputs.
2. **New harness L2 arms (Codex R0-infra adoption)**: add `l2_gated` and `l2_forced` arms across all benchmark plumbing. Pattern matches existing `variant` arm (codex unblocked, shim+wrapper routing) but routes IMPLEMENT to Claude (`--engine claude`) and uses NEW skill surface only.
   - **`l2_gated`** arm: env = `CODEX_BLOCKED` **omitted** (the shim refuses on any non-empty value, so 0 ≠ unset; existing variant arm pattern at run-fixture.sh:165-176 only writes the var when ARM=solo_claude), `CODEX_REAL_BIN` + `CODEX_MONITORED_PATH` exported, prompt invokes `/devlyn:resolve --spec <path> --engine claude` (no `--pair-verify`; pair fires only on natural triggers — coverage_failed OR MECHANICAL warning).
   - **`l2_forced`** arm: same env as l2_gated, prompt invokes `/devlyn:resolve --spec <path> --engine claude --pair-verify`.
   - **`--resolve-skill new` is REQUIRED** for any `l2_*` arm (refused at arg-parse). Reason: NEW skill surface is the only one with `--pair-verify` semantics; OLD `/devlyn:auto-resolve` would silently ignore the flag.
   - **Plumbing scope** (Codex R0-infra Q6 — minimum 7 sections):
     - `run-fixture.sh:38` — arm validation accepts l2_gated/l2_forced.
     - `run-fixture.sh:100` — staging block (skills + shim copy) extends to l2_*.
     - `run-fixture.sh:156-178` — env writer treats l2_* as unblocked (no CODEX_BLOCKED export).
     - `run-fixture.sh:223-241` — spec-verify carrier staging extends to l2_*.
     - `run-fixture.sh:261` — ENGINE_CLAUSE/ENGINE_PROMPT_HINT branches add l2_* cases.
     - `run-fixture.sh:269` — F9 prompt selection treats l2_* like variant (NEW chain ideate→resolve).
     - `run-fixture.sh:413-420` — invocation-time PATH shim injection extends to l2_*.
     - `judge.sh:43` — ARMS_PRESENT discovery loop adds l2_gated/l2_forced.
     - `judge.sh:326-336` — margin keys add `l2_gated_over_solo`, `l2_forced_over_solo`, `l2_gated_over_bare` (legacy variant_over_* preserved for backward compat).
   - **Bypass legacy aggregators**: dedicated `scripts/run-iter-0033c.sh` orchestrator skips `run-suite.sh:203-209` (which auto-calls ship-gate.py) and `compile-report.py:68-200` (which hardcodes 3-arm aggregation). iter-0033c emits its own gate table via `scripts/iter-0033c-compare.py`. Rationale: ship-gate.py:41-64 enforces variant/bare semantics that don't apply to L1-vs-L2 comparison.
3. **Manifest input bundle (Codex R0-infra correction §2)**: not single summary. Inputs to `scripts/build-pair-eligible-manifest.py`:
   - `--c1-summary <path>` — selection-grounds only; never a comparison baseline.
   - `--f9-judge <path>` — F9 inclusion proof from iter-0033a.
   - `--l1-rerun-summary <path>` — fresh L1 baseline at iter-0033c HEAD.
   - Output: `.devlyn/manifests/iter-0033c-pair-eligible.json` with `sources.<key>.{path, sha256}` triples + selection_rule + fixtures_pair_eligible + Gate 3 thresholds + `manifest_sha256` (computed via `pair-plan-lint.py:81-91` pre-stamp pattern: deepcopy + zero `manifest_sha256` field + canonical JSON `sort_keys=True, separators=(",",":"), ensure_ascii=False, allow_nan=False` + sha256). Verifier recomputes the same way. Manifest is the immutable input to iter-0033c-compare.py.
4. **Engine config locked**: NEW L1 baseline = `--engine claude` (Claude IMPLEMENT). NEW L2 = `--engine claude` + `--pair-verify` (forced) or natural triggers (gated). pair-JUDGE = Codex (via "OTHER engine" rule). Codex-primary L2 deferred to iter-0036+.
5. **L1 baseline RE-RUN (Codex R0-infra correction, 2026-05-02)**: iter-0033 (C1) `solo_claude` numbers are at HEAD `3bc86dd`; iter-0033c HEAD is post-2638891 (carrier fix for F3/F6 `stdout_not_contains: ["not ok "]`). Same-SHA+same-env reuse condition is broken — NORTH-STAR §"Measurement validity ≥ mechanism cleverness" rejects comparing new L2 against an invalidated baseline. Action: `solo_claude` arm rerun on F1-F8+F9 at iter-0033c HEAD alongside L2 arms. C1 numbers retained for selection-grounds documentation only.
6. **Attribution script** (Gate 7): per-fixture classification per Codex R0 §5 (4-class verdict-binding causality).
7. **Comparison artifact**: `scripts/iter-0033c-compare.py` emits gate table (1a-8) + attribution rows + Gate 6 fixture-level cross-check rows.

### Sequencing per Codex R0.5 §G (mechanical, not vibey)

Step-by-step:
1. Commit pair-eligible selection rule + high-value list (iter-0033c file). [Already committed in iter-0033 split commit `5ad7de9`.]
2. iter-0033a executes (smokes + benchmark).
3. iter-0033 (C1) executes; emits per-fixture `NEW L1 vs L0` margin in `summary.json`.
4. **`scripts/build-pair-eligible-manifest.py`**: input = iter-0033 (C1) `summary.json`; output = `.devlyn/manifests/iter-0033c-pair-eligible.json` with `{summary_sha256, manifest_sha256, fixtures: [...]}`. Both hashes recorded.
5. iter-0033c executes at same HEAD, reading the manifest (immutable input).
6. Results committed in iter-0033c bake commit.

### Does NOT ship in this iter

- BUILD pair-mode (iter-0020-falsified, NORTH-STAR-locked).
- L2 vs L0 comparison (must be vs L1 to avoid compression risk per NORTH-STAR test #14).
- Changes to NEW skill prompts (this is measurement, not tuning).
- **Contract repair** (verify.md:55 vs state-schema.md:76 mismatch on `pair_judge`): per Codex R0.5 §F, this is a separate doc-fix iter that runs AFTER smoke 1a confirms which contract wins in actual runs. iter-0033c does not edit either file.
- Phase 4 cutover.

### Subtractive-first check (PRINCIPLES.md #1)

- Could we skip iter-0033c entirely and ship Phase 4 with L2-disabled? **Possible** but requires explicit NORTH-STAR contract amendment ("L2 first-class on Codex" → "L2 will be re-enabled post-cutover when measurable on the NEW surface"). User adjudicated 2026-04-30 against this. iter-0033c is the cheaper path.
- Could we use diagnostic data already collected from iter-0033 (C1) variant arm? **Partially**, but iter-0033 (C1) variant is non-gated and not paired-against-L1-in-same-run. iter-0033c needs a clean paired run for honest L2-vs-L1 comparison. The iter-0033 (C1) variant data informs hypothesis priors, doesn't substitute for the gated run.

## Codex pair-review plan

- **R0** (BEFORE harness change): send this design + Option A/B decision + tool-lift attribution script outline. Falsification ask: does the predicted-direction match what we know from iter-0020 + iter-0028 evidence? Is the +3 no-regression / +5 lift threshold the right place on the curve? Does Option A actually trigger pair-JUDGE in NEW design (verify by reading `references/phases/verify.md`)?
- **R-final smoke** (AFTER L2 mode wiring smoke): if smoke surprises (e.g. `pair_judge` not populated even with `--pair-verify`), open root-cause iter for the NEW skill before proceeding.
- **R-final** (AFTER suite run): raw numbers + tool-lift split + my draft conclusion.

## Acceptance gate (pre-registered)

| Gate | Threshold | Source |
|---|---|---|
| 1a. L2 mode wiring smoke | `state.phases.verify.sub_verdicts.pair_judge` populated; second-model JUDGE log archived; `.devlyn/runs/<run_id>/pipeline.state.json` preserved post-run | Codex R0 §6 |
| 1b. Codex availability check (HARNESS layer) | hard `command -v codex` fail-fast in iter-0033c suite-runner BEFORE any L2 arm spawns. NEW L2 arms run with explicit env: `--engine claude`, `CODEX_BLOCKED=0`, Codex CLI on PATH. `--pair-verify` only for forced arm. | Codex R0.5 §C |
| 1c. Implementation-confound smoke | pre-suite smoke on **F2 + F3** (Codex R0-infra correction §3 — F1 901s flaky, F3 known fabrication site): run NEW L1 (`--engine claude`) vs NEW L2-forced (`--engine claude --pair-verify`) and compare IMPLEMENT diff fingerprints (`git diff --stat` against scaffold). If symmetric difference of file lists non-empty, switch to fixed-diff `--verify-only` pair smoke that isolates VERIFY/JUDGE lift from IMPLEMENT non-determinism. | Codex R0.5 §E + R0-infra §3 |
| 2. No regression vs L1 (gated arm) | every fixture: `(NEW L2-gated) − (NEW L1) ≥ −3` axes | NORTH-STAR test #6 |
| 3. Lift on pair-eligible (gated arm, single threshold, **SHIP-BLOCKER**) | on the **frozen pair-eligible set** (above, F8 reporting-only excluded): `(NEW L2-gated) − (NEW L1) ≥ +5` on ≥ 50% of those fixtures. `+3 / 75%` is reporting metric only, NOT pass path. **NOT ASSESSABLE** if set empty → requires explicit NORTH-STAR amendment marking L2 unproven/disabled before Phase 4 ships. (Codex R0.5: Gate 3 promoted to ship-blocker — closes Phase 4 loophole.) | Codex R0.5 (promoted) |
| 4. Hard-floor violations | zero L2 disqualifier on previously-clean L1 fixtures; zero L2 CRITICAL/HIGH `design.*`/`security.*` on previously-clean L1; zero L2 watchdog timeouts | PRINCIPLES.md #4 |
| 5. Efficiency (wall budget, not dominance) | per-fixture `L2-gated_wall / L1_wall ≤ 2.0×`. Final L1-best-of-M dominance evaluated using L1 variance from iter-0033 (C1) data. `≤ 3.0×` ceiling **only** for fixtures with categorical rescue (L2 catches disqualifier L1 missed). | Codex R0 §3 reframed |
| 6. Trigger-policy discipline (FIXTURE-LEVEL rule) | **For each pair-eligible fixture `f`**: if `L2-forced_delta(f) ≥ +5` OR forced catches categorical rescue, AND forced is not implementation-confounded, AND forced `pair_judge` is present → `L2-gated` MUST have `pair_judge` present on the same fixture `f`. Otherwise Gate 6 FAILS on `f`. (Suite-level "forced lifts but gated never fires" is too weak — fixture-level required.) Edge cases: forced +5 + gated fires + gated only +4 = Gate 6 PASSES, Gate 3 may still fail. Forced +6 on F2, gated skips F2 but fires F3 = Gate 6 FAILS on F2. | Codex R0.5 §A/B |
| 7. Attribution causality (4-class) | per-fixture classification: `no_material_lift` / `implementation_confounded` / `tool_or_trigger_lift` / `deliberation_lift`. Recorded for design-space update. Not pass/fail; data-gathering. | NORTH-STAR test #11 + Codex R0 §5 |
| 8. Artifact contract (L2-specific) | inherits iter-0033 Gate 9 contract; PLUS `state.phases.verify.sub_verdicts.pair_judge` non-null on every fixture where pair fired; PLUS pair_judge findings archive distinguishable from solo judge findings | iter-0033 mirror + Codex R0 §6 |

**Ship-blockers**: 1a, 1b, 1c, 2, 3, 4, 6. (Gate 3 ship-blocker per Codex R0.5 — closes Phase 4 first-class-L2 loophole.) Gate 5, 8 quality gates (failure → root-cause). Gate 7 data-gathering.

**Forced arm (diagnostic only)** — does NOT count toward Gate 3 pass. Used exclusively for Gate 6 fixture-level cross-check and Gate 7 attribution.

## Phase 4 cutover dependency

iter-0034 Phase 4 cutover gates on **all three**:
- iter-0033a Gates 1-8 PASS.
- iter-0033 (C1) Gates 1-9 PASS.
- iter-0033c Gates 1a, 1b, 1c, 2, 3, 4, 6 PASS (ship-blockers per Codex R0.5).
  - Gate 3 NOT ASSESSABLE (empty pair-eligible set) → requires explicit NORTH-STAR amendment marking L2 unproven/disabled before Phase 4 proceeds. Not a silent skip.
  - Gates 5, 8 quality gates → failure opens root-cause iter; Phase 4 holds.

## Why this is not score-chasing (PRINCIPLES.md #0)

This iter cannot move benchmark margins on its own; it measures an L2 product surface that the cutover needs measured. Real shipping decision (Phase 4 cutover) — case (b) of pre-flight 0.

## Risk register

| Risk | Mitigation |
|---|---|
| L2 mode wiring smoke fails (NEW skill doesn't actually trigger pair-JUDGE OR `pair_judge` not surfaced in state) | Gate 1a catches. Failure → root-cause iter on NEW skill VERIFY output contract (verify.md vs state-schema.md mismatch flagged by Codex R0 §6). iter-0033c suite run blocked until smoke passes. |
| Codex CLI absent → silent degrade to solo would hide L2 failure | Gate 1b — fail fast at suite start. |
| L2-forced shows lift but L2-gated doesn't fire (trigger policy too tight) | Gate 6 trigger-policy failure rule. Phase 4 still blocks; design iter to widen triggers. |
| Pair-eligible set empty | Gate 3 = NOT ASSESSABLE. **Phase 4 remains blocked** unless NORTH-STAR is explicitly amended to mark L2 unproven/disabled before cutover; otherwise open a root-cause iter on fixture saturation. (Codex R0.6 — closes silent-skip loophole introduced by an earlier draft.) |
| Tool-or-trigger-lift dominates deliberation-lift (≥ 80% L2 lift attributed to tool) | Gate 7 records this. NOT a fail — narrows L2 design space (NORTH-STAR test #11). Future iter-0036+ trigger to make pair cheaper / more solo-default. |
| Pair fires on every gated fixture (short-circuit broken) | Gate 6 catches. Failure → tune VERIFY/JUDGE short-circuit conditions in NEW skill. |
| Wall-time blows past 2.0× ceiling | Gate 5 catches. Failure → tune pair-JUDGE prompt for terminal verbosity, or narrow short-circuit. iter-0033c re-runs after fix. |
| L2 lifts on easy fixtures but not on pair-eligible (expensive theatre) | Gate 3 specifically targets pair-eligible. Failure → Phase 4 blocks; design rethink. |
| `implementation_confounded` rate high (≥ 30% of fixtures) | Indicates `--pair-verify` upstream non-determinism affects IMPLEMENT. Investigate before treating L2 vs L1 as comparable. |

## Principles check

- **#0 pre-flight**: ✅ closes user-visible failure (L2 contract claim).
- **#7 mission-bound**: ✅ Mission 1 single-task L2 surface measurement.
- **#1 no overengineering**: ✅ measurement-only; the L2 mode wiring already exists in NEW skill — this iter validates and gates it.
- **#2 no guesswork**: ✅ predictions filled BEFORE run; gates pre-registered.
- **#3 no workaround**: ✅ root-cause framing for failures.
- **#4 worldclass**: ✅ enforced via gate 4.
- **#5 best practice**: n/a (no skill code change).
- **#6 layer-cost-justified**: ✅ — this is the iter that operationalizes layer-cost-justified for L2.

## Smoke 1a/1b/1c verdicts (2026-05-02)

| smoke | result | evidence |
|---|---|---|
| 1b (codex availability) | PASS | `command -v codex` → `/Users/aipalm/.superset/bin/codex` (codex-cli 0.128.0) |
| 1a (mode wiring on F2 l2_forced) | PASS | `state.phases.verify.sub_verdicts.pair_judge: PASS_WITH_ISSUES` populated; pair_merge_note: "Claude judge PASS 0 findings; Codex pair-judge PASS_WITH_ISSUES 4 medium" — deliberation_lift signal. terminal verdict PASS. Run dir: `bench-iter0033c-smoke1a-20260502T094207Z-F2-cli-medium-subcommand-l2_forced/.devlyn/runs/run-20260502T184311Z/` |
| 1c (impl-confound F2 + F3) | PARTIAL | F2 confounded (solo touched `bin/cli.js` only; l2_forced touched `bin/cli.js` + `tests/cli.test.js` — l2_forced added a test file solo skipped, even though F2 spec verification commands don't require tests). F3 NOT confounded (both arms touched `server/index.js` + `tests/server.test.js`). |

**Suite gating from smoke verdicts** (Codex R-final-smoke-adopted):
1. Archive contract bug **FIXED in this commit** — `archive_run.py` glob now includes `verify-judge-*.md`. Synthetic test confirmed (3 sample files moved, including future-engine wildcard).
2. Compare placeholders **REPLACED in this commit** — `iter-0033c-compare.py` `impl_confounded` and `pair_findings_distinguishable` populated from real evidence; remaining two (`pair_judge_unique_finding`, `mechanical_finding_drove_change`) stay conservative-default with TODO marker (deferred to follow-up audit script).
3. **F2 fixed-diff `--verify-only` smoke is the remaining gate** before suite. Per Codex Q5: option (b) — fixed-diff for confounded fixtures only. Implementation: capture F2 solo_claude diff once, run /devlyn:resolve --verify-only against the fixed diff for both `solo_claude` and `l2_forced` mode, compare verify findings + verdict. If solo and pair verdicts converge on the fixed diff → IMPLEMENT non-determinism is the only confound (paired-arm comparison usable with `impl_confounded` flag in attribution). If they diverge → pair-mode genuinely sees something solo misses (deliberation_lift confirmed for F2).
4. Schema drift (Codex Q1) — `pair_merge_note` field + `artifacts` documented as object vs written as array. Filed as follow-up doc-fix iter; non-blocking.

## Open questions (resolved post-R0)

1. ~~Option A vs B~~ → **Resolved (Codex R0 §1)**: Option A dead. Use B2 (gated, primary) + diagnostic forced (B1 on pair-eligible only).
2. F9 inclusion: iter-0033a sequenced first; if F9 NEW passes, include in iter-0033c; if F9 NEW fails iter-0033a, iter-0033c runs F1-F8 and F9 L2 deferred.
3. ~~Attribution heuristic~~ → **Resolved (Codex R0 §5)**: 4-class verdict-binding causality, not finding count.
4. Pair-eligible set empty? → **Resolved (Codex R0 §4)**: NOT ASSESSABLE rule + frozen high-value list as floor.
5. (NEW post-R0) verify.md vs state-schema.md contract mismatch on pair_judge sub-verdict surface → **Smoke 1a tests this**. If smoke fails, opens contract-fix iter on NEW skill VERIFY output.

## Deliverable execution order

1. ~~R0~~ → complete (226s, all 7 substantive findings adopted).
2. ~~R0.5~~ → complete (196s, 7 corrections adopted: Gate 3 promoted, Gate 6 fixture-level, harness-layer Codex check, pair-eligible refined, confound smoke, contract deferred, sequencing manifest).
3. **R0.6** with Codex on this redraft (short confirmation round; if rejected again, apply corrections and re-run).
4. iter-0033a executes first (smokes + F9 NEW benchmark).
5. iter-0033 (C1) executes; emits per-fixture `NEW L1 vs L0` margin.
6. `scripts/build-pair-eligible-manifest.py` produces immutable input for iter-0033c.
7. Run pre-suite smokes (1a wiring, 1b Codex availability, 1c implementation-confound).
8. If smokes pass → run iter-0033c gated arm at same HEAD as iter-0033 (C1).
9. Run iter-0033c forced arm (pair-eligible only) at same HEAD.
10. Apply ship-gate via `scripts/iter-0033c-compare.py` (8 gates + Gate 6 fixture-level cross-check + Gate 7 attribution).
11. **R-final** with Codex on raw numbers + attribution split.
12. Update HANDOFF.md + DECISIONS.md.
13. Combined with iter-0033a + iter-0033 (C1), file iter-0034 Phase 4 cutover.
