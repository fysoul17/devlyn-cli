---
iter: "0021"
title: "Principle-bin calibration overlay on iter-0020 9-fixture data"
status: shipped
type: calibration (no new arms, no new ship gates, no new fixtures)
shipped_commit: 9a9947f
date: 2026-04-29
mission: 1
---

# iter-0021 — Principle-bin calibration overlay

## Why this iter exists (PRINCIPLES.md pre-flight 0)

**This iter exists to make the next harness intervention impossible to fake.** Mission 1 binding gate is L1-L0 quality (≥+5 floor; current +4.4 in iter-0020). Aggregate margin alone does not name *which* failure class L1 is weakest on. Without that, the next harness change risks score-chasing the suite avg rather than removing a categorical user failure.

**Decision this iter unlocks**: the next iter (iter-0022 candidate) targets the principle bin where L1 is empirically weakest on existing data. That bin's mechanism, however, requires further investigation BEFORE iter-0022 fix design — the iter-0021 readout itself surfaced an unexplained judge-vs-spec-carve-out interaction that needs a Round 0 diagnostic (see "Open mechanism question" below).

This is the **last attribution run before a harness intervention** per PRINCIPLES.md:22. iter-0022 must be a behavior change (harness or spec edit), not another measurement iter.

This iter is the textbook overlay-only shape Codex GPT-5.5 (xhigh, 2026-04-29 R-pre) blessed: tag existing fixtures, re-read existing artifacts, enrich rule_id→principle map. NO new ship gates (RUBRIC.md:3 contract during benchmarking window). NO new fixtures. NO new arms. NO paid runs.

## Mission 1 service (PRINCIPLES.md #7)

Mission 1 gate 1 (L1 vs L0 quality) is failing at +4.4 < +5 floor. This iter does not move that number directly, but it identifies the principle bin where the gap lives most concretely so the next iter can investigate and close the most actionable piece. Mission 1 hard NOs untouched (no worktree, no parallel, no resource lease, no run-scoped state migration).

## Pre-readout hypothesis (NOT independently timestamped — see Codex R-final Q5)

Direction predictions written before tabulating per-axis sums. Cannot prove pre-data ordering with an immutable draft; readers should treat as "what I expected" not "what I provably predicted."

H1 (expected): L1's lift over L0 is concentrated on Constraint Respect and Code Quality axes, not Spec Compliance or Scope Discipline.

H2 (expected): L1 has at least one axis where it does NOT clearly beat L0 — predicting Scope based on prior iter-0018.5 F5 frontmatter signal (which seemed to fold into a different mechanism than scope penalty).

H3 (expected): L2's regression vs L1 (iter-0020 closeout already established) is concentrated on Constraint + Quality (the same axes where L1 lifted).

H4 (expected): The bare → solo → pair compounding North-Star contract holds on small-magnitude axes (Spec/Scope) but fails on large-magnitude axes (Constraint/Quality).

## Method

Read existing artifacts at `benchmark/auto-resolve/results/20260428T131713Z-91994db-iter-0020-9fixture-verify/`. For each fixture × arm:
1. Pull `judge.json` per-axis breakdown (`spec` / `constraint` / `scope` / `quality`, each 0-25).
2. Compute L1-L0 and L2-L1 deltas per axis per fixture.
3. Sum across 9 fixtures.
4. Map per-axis to the 6 principle lenses the user articulated.
5. Cross-reference with `changed-files.txt` AND `diff.patch` content (NOT just file names) for any anomalous axis result.

## Fixture → primary principle map

Each fixture exercises multiple principles, but one is primary based on what its `Constraints` and `Verification` sections actually penalize. Listed primary first; secondary in parens.

| Fixture | Primary principle (judge axis) | Secondary | Mechanism evidence |
|---|---|---|---|
| F1 trivial-flag | Goal-fit (Spec) | Best-practice (Quality) | Trivial impl; principle exercise is "do what the spec says" |
| F2 cli-doctor | No-workaround (Constraint) | Goal-fit (Spec) | spec.md:`No silent catches`, EACCES-specific, TTY gating, no hardcoded paths |
| F3 backend-pagination | Goal-fit (Spec) | No-workaround (Constraint) | strict envelope + 400 on invalid params; constraint forbids dep additions |
| F4 web-whisper | No-bug / production-ready (Quality + tooling) | Best-practice | UI behavior + Playwright spec; tooling lift expected |
| F5 fix-loop-count | Goal-fit (Spec) | Convergence (fix-loop) | Failing tests must be made to pass; convergence is the test |
| F6 dep-checksum | No-workaround (Constraint) | No-bug (Quality) | `No new npm deps`, distinct exit codes for missing/dir, EACCES-specific |
| F7 out-of-scope-trap | Scope discipline (Scope) | Goal-fit (Spec) | Explicit out-of-scope test — fixture *designed* to penalize scope creep |
| F8 known-limit-ambiguous | Better-method-recognition / Abstention | Scope discipline | Spec deliberately under-specified; correct response is small defensible change + documenting what was NOT done |
| F9 e2e-novice-flow | Goal-fit (Spec) | Best-practice + integration | gitstats subcommand + JSON output + ideate→preflight chain artifacts |

## CRITIC rule_id → principle bin map

From `findings-schema.md:38-50`:

| Principle lens | rule_id categories | Severity bands typical |
|---|---|---|
| Goal-fit | `correctness.spec-literal-mismatch`, `correctness.spec-verify-malformed` | CRITICAL (always) |
| No-workaround | `constraint.silent-catch`, `constraint.hardcoded-value`, `constraint.any-cast`, `correctness.silent-failure`, `correctness.null-access` | CRITICAL/HIGH |
| Scope discipline | `scope.out-of-scope-violation` | HIGH/MEDIUM |
| No-bug / production-ready | `design.*` (incl `design.non-atomic-transaction`, `design.hidden-assumption`, `design.overengineered`), `security.*` (12 OWASP children) | CRITICAL/HIGH for security; HIGH/MEDIUM for design |
| Best-practice | `design.unidiomatic-pattern`, `architecture.duplication`, `architecture.pattern-violation` | MEDIUM |
| Better-method-recognition | `design.unidiomatic-pattern` (narrow stdlib subset only — Codex Q2 verdict: broad architecture comparison becomes judge taste) | MEDIUM |
| Hygiene (orthogonal) | `hygiene.*`, `types.*`, `style.*`, `performance.*` | LOW |

Interpretive overlay on existing rule_ids. NO code change. NO schema edit.

## Per-axis L1-L0 and L2-L1 readout (the load-bearing data)

Source: iter-0020 `judge.json` per-fixture `_blind_mapping` resolved arms. 4-axis breakdown (Spec / Constraint / Scope / Quality, each 0-25) summed across 9 fixtures.

| Axis | Mapped principle | L1-L0 sum | L2-L1 sum |
|---|---|---|---|
| Spec | Goal-fit | **+7** | **-6** |
| Constraint | No-workaround | **+18** | **-11** |
| Scope | Scope discipline | **-4** | **-3** |
| Quality | No-bug / Best-practice | **+19** | **-12** |

### Per-fixture detail (L1 vs L0 / L2 vs L1)

| Fixture | L1-L0 (spec/cons/scope/qual) | L2-L1 (spec/cons/scope/qual) |
|---|---|---|
| F1 trivial-flag | +0/+4/+0/+2 | +0/+0/+0/-1 |
| F2 cli-doctor | +2/+8/-2/+1 | -3/-9/+2/-1 |
| F3 backend-pagination | +0/+0/+0/-1 | -3/+0/-5/-8 |
| F4 web-whisper | +4/+0/-2/+9 | +0/+0/+0/+1 |
| F5 fix-loop-count | +0/+2/+0/+2 | +0/-2/+0/-2 |
| F6 dep-checksum | +0/+4/+0/+5 | +0/+0/+0/-2 |
| F7 out-of-scope-trap | +1/+0/+0/+1 | +0/+0/+0/+1 |
| F8 known-limit | +0/+0/+0/+0 | +0/+0/+0/+0 |
| F9 e2e-novice-flow | +0/+0/+0/+0 (rate-limited, never executed) | +0/+0/+0/+0 |

## Findings

### F1 — H1 confirmed: L1 lift is on Constraint + Quality, not Spec/Scope.

L1 added **+18 Constraint** + **+19 Quality** vs L0. Spec was +7 (mostly F4's +4). Scope was **-4** (negative).

Mechanism evidence:
- F1 (+4 cons +2 qual): bare missed unknown-flag rejection (judge.json:F1).
- F2 (+8 cons): bare hits silent-catch DQ on doctor subcommand.
- F4 (+9 qual): tooling lift (Playwright + browser_validate) drives quality gap.
- F6 (+4 cons +5 qual): bare misses ENOENT-specific exit code distinction.

L1 categorically writes code that respects constraints (silent-catch ban, EACCES-specific handling, idiomatic stdlib usage) and reaches higher quality scores.

### F2 — Per-axis Scope -4 confirmed. Mechanism partially understood, partially open.

L1 introduced -2 scope penalty on each of F2 and F4 vs L0. Mechanism trace:

**`changed-files.txt` shows L1 touched a docs/roadmap/phase-1/<fixture>.md file that bare didn't:**
- F2 L1: `bin/cli.js`, `docs/roadmap/phase-1/F2-cli-medium-subcommand.md`, `tests/cli.test.js`
- F2 L0: `bin/cli.js` only
- F4 L1: `docs/roadmap/phase-1/F4-web-browser-design.md`, `tests/e2e/whisper.spec.js`, `web/index.html`
- F4 L0: `tests/e2e/buttons.spec.js`, `web/index.html`

**Actual diff content** (verified via `diff.patch`, NOT just `changed-files.txt`):
- F2 solo_claude diff.patch:315 — frontmatter changes are `status: planned → status: done` PLUS `completed: 2026-04-28` (new field added).
- F4 solo_claude diff.patch:9 — same shape: `status: planned → status: done` PLUS `completed: 2026-04-28`.

**Spec lifecycle note presence** (verified via judge-prompt.txt — the prompt the judge actually saw):
- F2 judge-prompt.txt:225 contains: `**Lifecycle note.** The harness's DOCS phase flips this spec's frontmatter status after implementation completes — that is benchmark lifecycle bookkeeping, not a scope violation.`
- F4 judge-prompt.txt:219 contains the same text.

**Judge behavior despite note**:
- F2 judge.json:18 — solo_claude scope = 23 (penalty -2 vs bare's 25).
- F4 judge.json (similar) — solo_claude scope = 23 (penalty -2 vs bare's 25).

**Open mechanism question.** The lifecycle note is in the prompt; the judge saw it; the judge penalized scope anyway. Three plausible explanations exist; this iter does NOT distinguish between them (would require a diagnostic Round 0 in iter-0022):

1. **Note-scope-narrow hypothesis**: the note carves out `status` field but the actual diff also adds a NEW `completed:` field that the note doesn't explicitly cover. Judge interpreted the `completed:` addition as out-of-scope.
2. **Note-ignored hypothesis**: the LLM judge read the note but didn't operationalize it consistently — judge prompt doesn't have explicit instruction "respect spec lifecycle carve-outs."
3. **Note-vs-diff-existence hypothesis**: judge has an implicit prior that "any docs file diff is scope leak" that overrides spec text carve-outs.

The earlier draft of this iter file claimed (incorrectly) that F2/F4 specs LACK the lifecycle note — that was unverified and false. Codex R-final caught this and required diff verification before any mechanism claim.

### F3 — H3 + H4 confirmed: L2 regression concentrated on Constraint + Quality.

L2-L1 = -11 Constraint + -12 Quality. F2 variant DQ'd by silent-catch (cons -9, drove most of the L2 Constraint loss). F3 variant introduced mock-test fakery (qual -8). F5/F6 variant dropped quality 2 each. **Bare → solo → pair compounding fails on Constraint and Quality** — Codex BUILD on this fixture set systematically writes worse code than Claude solo.

L2 lifted Quality on F4 (+1) and F7 (+1). Spec axis: F2 and F3 lost 3 each. iter-0020 closeout decision (revert e2e routing, runtime default `claude`) remains correct.

### F4 — F8 + F9 contribute zero.

F8 all 3 arms scored 80 (judge calls all defensible answers tied — by spec design). F9 all 3 arms `invoke_failure=true` because the suite hit a provider/account limit at ~5h17m wall (transcripts: "You've hit your limit"; F9 wall 2s/6s/2s); arms produced empty diffs. These two fixtures provide no L1-vs-L0 or L2-vs-L1 information in this run.

## What this iter unlocks

### Decision: iter-0022 candidate target = Scope axis on F2 + F4 + diagnose lifecycle-note-vs-judge interaction

**Why this is the right next intervention** (PRINCIPLES.md pre-flight 0 + #7):

- Removes a measurable Mission 1 weakness: L1 currently scores -4 on scope axis vs L0. Eliminating that delta lifts L1-L0 by ~+0.44 (from +4.4 to ~+4.84 — **still below +5 floor**, NOT a Mission 1 unblock by itself).
- The scope-axis mechanism is the most concretely **bounded** in iter-0020 data: two fixtures, same DOCS-phase metadata family, exact mechanism narrowed (see judge-evidence below) but not yet behavior-tested.
- iter-0022 framing follows Codex R-final² guidance: **R0 chooses between Scope-vs-F3 first**; if Scope wins, **R1 runs exactly one diagnostic** (omit `completed:` from harness DOCS output and re-run F2 — single fixture, single behavior change, single signal). Avoids measurement chain.

**Mechanism evidence updated post-Codex-R-final²**: F2 judge.json `solo_claude` breakdown notes (`b_breakdown.notes`) literally say:
> "Minor scope debit for editing roadmap status/completed metadata, **though the lifecycle note makes status flipping acceptable**."

This **confirms note-scope-narrow** as the operative hypothesis with judge's own reasoning: judge read the note, accepted `status` flip, debited the `completed:` field addition the note does not carve out. Note-ignored hypothesis is therefore weakened (judge cited the note); note-vs-diff-existence is also weakened (judge said status flip is fine — only `completed:` is the issue). The hypothesis set remains open as a falsification frame, but current evidence favors note-scope-narrow.

**iter-0022 R0 single decision**: Scope axis vs F3 quality. Choose ONE based on per-fixture lift potential and mechanism clarity.

**iter-0022 R1 (if Scope wins)**: harness drops `completed:` field addition in DOCS phase (subtractive, matches spec note's exact carve-out). Re-run F2 single fixture; if scope axis returns to 25/25, confirmed; if not, reconsider mechanism. NO judge-prompt edit (RUBRIC.md:3 freeze contract). NO benchmark-mode carve-out (cleaner subtractive fix exists at the harness output level).

**What this iter explicitly does NOT do** (Codex Q4/Q7 guidance):
- ❌ Add new fixtures to "test better-method-recognition" — premature; iter-0021 readout did not show that lens as the binding gap.
- ❌ Change ship-gate definition — RUBRIC.md:3 freeze contract holds during the benchmarking window.
- ❌ Change rubric weighting per principle — would invalidate comparability with iter-0006/0016/0019/0020 history.
- ❌ Add per-principle ship-gate floors — same reason.
- ❌ Run dual-judge sidecar — not necessary because per-axis L1-L0 already shows the categorical signal cleanly. Save for if iter-0022 lift is borderline.
- ❌ Pre-commit to (a) spec-side or (b) harness-side fix without iter-0022 R0 mechanism diagnostic — Codex R-final showed my pre-decision was based on false premises.

**What this iter does NOT claim**:
- ❌ "Closing scope axis closes Mission 1 gate 1." Math: -4 → +0.44 → +4.84, still < +5 floor. Mission 1 needs additional lift elsewhere (probably Quality on F3).
- ❌ "Lifecycle note absence is the F2/F4 scope mechanism." False — note is present; judge penalized anyway. Mechanism is open.
- ❌ "iter-0022 = scope axis" is automatically the right call. F3's L0-beats-L1 by -1 quality is a more striking categorical signal even if smaller magnitude. iter-0022 R0 should weigh both candidates.

## Principles check

### Pre-flight 0 — not score-chasing
**Status: ✅ PASS.** This iter unblocks a specific go/no-go decision (iter-0022 = Scope F2+F4 diagnostic OR F3 quality investigation). Aggregate margin doesn't move; per-axis principle-bin readout makes the next intervention impossible to fake.

### 1. No overengineering
Diff: this single iter file. ZERO code change, ZERO schema change, ZERO new abstractions. Pure subtractive iter from a measurement standpoint. ✓

### 2. No guesswork
**⚠️ PASS with rescue note.** Hypotheses H1-H4 stated as "expected directions" before tabulating sums but not independently timestamped — Codex R-final Q5 caught the over-confident self-attestation. Rephrased to "pre-readout expectation" honestly. Crucially, Codex R-final caught a load-bearing fabricated mechanism claim ("F2/F4 lack lifecycle note" — false; specs DO carry the note per judge-prompt.txt:225/:219) that would have shipped to iter-0022 design without pair-review intervention. The original draft cited evidence I had not actually opened. Adopted Codex findings; rewrote with verified citations. **This iter ships only because pair-review rescued it from a P2 violation that would have propagated.** Pair-review IS the work — not optional, not background, not advisory. Future calibration iters MUST verify every cited file:line before drafting mechanism claims.

### 3. No workaround
No code changes. No new env vars, no new flags. Mechanism trace cites actual `diff.patch` content (verified via Codex R-final correction, not assumed). ✓

### 4. Worldclass production-ready
This iter introduces no code that ships. ✓

### 5. Best practice
Iter file follows existing convention. Mappings cite file:line evidence (RUBRIC.md, findings-schema.md, judge-prompt.txt:225/:219, diff.patch:315/:9, judge.json:18). ✓

### 6. Layer-cost-justified
Iteration-loop work, not auto-resolve-pair work. The Codex pair-review (R-pre + R-final, ~270k tokens xhigh combined) cost is amortized over future harness improvements. R-final caught a load-bearing factual error that would have produced a wrong iter-0022 design. ✓

### 7. Mission-bound
Serves Mission 1 gate 1. Identifies the categorical L1 axis gap. Does NOT touch Mission 2 or Mission 3 surfaces. Hard NO list untouched. ✓

## Codex pair-review trail (this iter)

### R-pre (2026-04-29, principle-bench proposal consult, ~78k tokens xhigh, 131s)

User pivoted from real-project trial → "longmemeval-style benchmark" → refined to "principles × layers benchmark." Codex falsified each in turn:

- **First consult (longmemeval-style)**: full redesign rejected as drift. Verdict: pick C (calibration iter). Strongest weakness: longmemeval mechanical scoring doesn't transfer to devlyn's "shipped code quality" surface.
- **Refined consult (principles overlay)**: mostly isomorphic to first verdict ("ability tag → principle tag"). Survives pre-flight 0 ONLY as overlay. Q7 pick (iii): fixture tags + iter-0020 re-read + CRITIC rule_id→principle map. NO new arms, NO new ship gates, NO new fixtures. REJECT (iv).

Adopted verbatim. This iter file implements (iii) without (iv).

### R-final (2026-04-29, ~193k tokens xhigh, 224s)

Verdict: **No-Go-as-drafted.** Strongest objection: drafted F2/F4 mechanism was factually wrong.

Findings adopted in this rewrite:
1. **Q1+Q3 mechanism falsified** — F2+F4 specs DO carry the lifecycle note (judge-prompt.txt:225/:219); diff includes `status` flip AND `completed: 2026-04-28` field addition (diff.patch:315/:9); judge saw the note and penalized scope 23 anyway (judge.json:18). My drafted "specs LACK lifecycle note" claim was unverified and false. Spec-side fix candidate (a) is no-op as drafted. Mechanism for the penalty is now open (3 hypotheses listed above).
2. **Q2 math correction** — closing -4 scope = +0.44 lift, takes +4.4 → +4.84, still below +5 floor. My drafted "+0.6 gap lives in scope" overclaimed. Now corrected.
3. **Q4 framing** — harness-side BENCH_WORKDIR skip is benchmark-instrument work, not real-user behavior. Removed "real user failure" claim from harness-side fix candidate framing.
4. **Q5 hypothesis honesty** — H1-H4 cannot be proven pre-data. Rephrased as "pre-readout expectation, not independently timestamped."
5. **Q6 verification gap** — diff content verification was required, not implied done. Corrected to actually verify diff.patch content before mechanism claim.
6. **Q7 prose softening** — "single mechanism" overstated; "traceable" too strong. Removed.

**Critical lesson**: the mechanism story I drafted (lifecycle note absent → spec-side fix lands) was a fabrication built on unverified evidence. Pair-review caught it before it propagated to iter-0022 design — saving a paid run on a wrong-mechanism fix. This is exactly the value of Codex companion pair-review per `feedback_codex_cross_check.md`.

## Drift check (산으로?)

- **Removes a real user failure?** Partially. The L1 -4 scope penalty is measurable; the underlying mechanism is now open and needs iter-0022 R0 diagnostic.
- **Expands scope beyond calibration?** NO. Zero code change. Zero schema change. Zero ship-gate change. One iter file. No "while I'm here" additions.
- **Sets up a multi-iter measurement chain?** Borderline. iter-0022 R0 IS another diagnostic, but it's bounded: a single fixture, single targeted question, single behavior change. Not "another suite measurement" — exactly the kind of mechanism falsification PRINCIPLES.md:22 allows as the LAST attribution before behavior change.

## Cumulative lessons

1. **Per-axis readout extracts categorical signal that suite-avg hides.** Suite-avg L1-L0=+4.4 collapses to `(spec=+7, cons=+18, scope=-4, qual=+19)` per axis — totally different story per principle bin.

2. **L1 wins on what it was designed to win on (constraints + quality), loses on something it wasn't designed to lose on (scope).** The harness's value-add is intact; its scope cost is real and partially understood.

3. **The L2 regression on this fixture set is categorical, not noise.** -11 cons + -12 qual across 9 fixtures = systematic Codex BUILD weakness on this benchmark family. iter-0020 closeout to disable L2 product surface remains correct.

4. **iter-0019.6/.8/.9 spec-verify carrier did its job invisibly.** F2/F3/F5 verify=1.0 across both pair arms — the carrier mechanism is what made per-axis Spec scores high enough to be informative.

5. **Codex R-final caught a load-bearing fabrication.** I drafted "F2/F4 lack lifecycle note" without verifying the judge prompt or diff content. Codex's evidence-citation falsification (judge-prompt.txt:225, diff.patch:315) is the failure mode `feedback_codex_cross_check.md` is designed to catch. Pair-review IS the work, not optional.

6. **Pre-flight 0 absolves an iter from "fix the gate" pressure but NOT from honest mechanism reporting.** This is a calibration iter; it's not supposed to lift L1-L0. But it IS supposed to ground what iter-0022 should target — and grounding requires the mechanism story to be true, not invented.
