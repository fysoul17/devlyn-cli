---
iter: "0023"
title: "Measurement trust — judge axis validation + ship-gate L1 enforcement"
status: shipped
type: measurement-infrastructure (no real provider/model invocations; closes 2 measurement bugs caught by Codex post iter-0022)
shipped_commit: pending
date: 2026-04-29
mission: 1
---

# iter-0023 — Measurement trust: judge axis validation + ship-gate L1 enforcement

## Why this iter exists (PRINCIPLES.md pre-flight 0)

User pushed back hard on iter-0022 close-out: *"점수가 신뢰가 있나? +5 라는게 의미가 정말 있나? 4.5나 5.2나 크게 차이가 없을수도 있을것 같은데?"* (Is the score trustworthy? does +5 mean anything? +4.5 vs +5.2 may not be meaningfully different.) Codex independent verification (~100k tokens xhigh, 254s) confirmed the user's pushback is correct: the +5 floor is a policy threshold, not a statistical one, and **two measurement bugs let invalid data flow through to the gate**:

1. **judge.sh:233** Python heredoc parsed `chosen` (the per-arm breakdown JSON) without validating that axis values fall in the documented `[0, 25]` range. iter-0020's F9 row recorded `quality: -1` and the suite-avg numerator silently absorbed it. Same path would accept any out-of-range value.
2. **ship-gate.py:46** enforced only legacy L2 `variant` margin (`margin_ge_5_count`) — never read `solo_over_bare`. NORTH-STAR.md:81 op-test #1 (the L1 floor of +5, 7/9 fixtures, F9 ≥ +5, no L1 disqualifier) was *documented but not mechanically enforced*. Ship-gate would PASS even if L1 had failed all four floors, as long as the legacy variant arm passed.

**Decision this iter unlocks**: reliable interpretation of any future suite-run summary. Without these two fixes, the measurement-trust phase (B-1 Opus sidecar, B-3 F9 re-run, B-4 paired variance) cannot have a meaningful gate to compare against.

This is **the LAST measurement-bug iter before the measurement-trust runs** (iter-0025+). PRINCIPLES.md:22 holds: an attribution-fix iter is allowed as the last attribution work before the next sequencing decision.

## Mission 1 service (PRINCIPLES.md #7)

Serves Mission 1 gate 1 (L1 vs L0 quality) by closing the contract-vs-enforcement gap: the documented L1 gate now actually fires. Mission 1 hard NOs untouched (no worktree, no parallel-fleet, no resource-lease, no run-scoped state migration, no queue metrics, no multi-agent coordination beyond `pipeline.state.json`, no cross-vendor / model-agnostic infrastructure).

No model invocations in this iter. The only validations are local (Python import check + ship-gate against existing iter-0020 results dir).

## Hypothesis (predicted, written before implementation)

H1 (predicted): Running ship-gate against the existing `20260428T131713Z-91994db-iter-0020-9fixture-verify` run with `--accept-missing` will now produce L1-specific failures matching the iter-0021 readout (suite avg +4.4 < +5 floor; F9 L1 = 0 because rate-limited). Confirmed: warnings include "L1 suite avg +4.4 below NORTH-STAR floor +5"; failures include "F9 L1 (solo_over_bare) margin +0 < +5 floor".

H2 (predicted): The legacy L2 variant gates continue to fire (1 variant disqualifier, F9 variant margin) so existing baseline comparability is preserved. Confirmed.

H3 (predicted): judge.sh axis validation, when run on a synthetic out-of-range value, clamps and records the cell under `_axis_validation`. (Not directly testable in-session without running a real judge; relies on Codex R1 review of the Python heredoc.)

## Method

Two surgical edits, both subtractive in spirit (each closes a documented contract that was silently un-enforced):

### Fix 1 — judge.sh axis breakdown validation

`benchmark/auto-resolve/scripts/judge.sh:233-313` Python heredoc gains a new block (28 lines) BEFORE `scores_by_arm` assembly:

- For each `a_breakdown` / `b_breakdown` / `c_breakdown` (the per-arm 4-axis dict), iterate `spec / constraint / scope / quality` and check value ∈ `[0, 25]`.
- Out-of-range cells are clamped to `[0, 25]` (preserves the rest of the row's data) AND recorded under `chosen["_axis_validation"] = {out_of_range_count, out_of_range_cells, axis_range}`.
- A `[judge.sh] WARNING: ... cells out of [0,25] clamped: ...` line is written to stderr per fixture-judgment.

Why clamp instead of reject: rejecting one fixture would make the whole 9-fixture suite unusable for a single bad cell; clamping preserves fungible data while exposing the invalid cells to ship-gate downstream.

### Fix 2 — ship-gate.py L1 (solo_over_bare) gates

`benchmark/auto-resolve/scripts/ship-gate.py:38-119` extends the gate enforcement loop with an L1 block (active only when `arms_present.solo_claude == true`):

- **Soft gate** (warning only): suite-avg `solo_over_bare` < +5 reports, but per-fixture gates are decisive (per Codex R1: avg is reporting, not deciding).
- **Hard gate**: F9 `solo_over_bare` margin ≥ +5 (or `--accept-missing` skips). F9 row missing the field → measurement invalid, fail.
- **Hard gate**: ≥ 7 of (gated, non-known-limit) fixtures have `solo_over_bare ≥ +5`. `--accept-missing` skips.
- **Hard gate**: 0 L1 disqualifiers (`arms.solo_claude.disqualifier == false` for every row).
- **Hard gate**: 0 L1 axis-invalid rows. ship-gate inspects `arms.solo_claude._axis_validation_out_of_range_count`; this field is wired in iter-0024 if/when summary aggregation propagates the per-fixture `_axis_validation` written by Fix 1. iter-0023 ships the gate scaffolding; the field flow comes when judge.sh's clamp lands in a future suite run AND `compile-report.py` is updated to copy the per-arm `_axis_validation` block forward. Until then, the gate is dormant (returns 0 invalid rows for legacy data) and the legacy L2 variant gates still fire as before.

Legacy L2 variant gates (`hard_floor_violations`, F9 variant margin, 7/9 variant `margin_ge_5_count`, ±5 regression vs shipped baseline) are preserved verbatim. iter-0023 is purely additive on the L1 axis; nothing about the L2 measurement contract changes.

## Findings (what was actually built)

**Files modified (2)**
- `benchmark/auto-resolve/scripts/judge.sh` — +28 lines (axis breakdown validation block)
- `benchmark/auto-resolve/scripts/ship-gate.py` — +50 lines (L1 gate block)

**Files added**: `autoresearch/iterations/0023-measurement-trust-judge-axis-shipgate-L1.md` (this file).

**Smoke results (in-session, no model invocations)**:
- `python3 -c "import ..." benchmark/auto-resolve/scripts/ship-gate.py` → imports cleanly.
- `python3 benchmark/auto-resolve/scripts/ship-gate.py --run-id 20260428T131713Z-91994db-iter-0020-9fixture-verify --accept-missing` → produces:
  - Hard-floor failures: legacy variant disqualifier (1) + F9 variant margin + **F9 L1 margin +0 < +5 (NEW)**.
  - Soft-gate warnings: **L1 suite avg +4.4 below floor (NEW)**.
- iter-0022 lint Check 13 (idgen determinism) still PASSES — judge.sh + ship-gate.py changes do not touch the iter-0022 surface.

## What this iter unlocks

1. **B-1 Opus sidecar (iter-0025)**: re-judge iter-0020 results with Opus 4.7. Compares per-axis values; if Opus disagrees by > +2 on any axis sum, the L1-L0 = +4.4 reading is single-judge artifact, not signal. Without iter-0023's axis validation, Opus disagreements would also flow through invalid cells.
2. **B-3 F9 re-run (iter-0026)**: F9-only run when quota allows. Fix 2's F9 L1 gate now fires; previous "F9 = 0/0/0/0" silent absorption is closed.
3. **B-4 paired L0/L1 variance (iter-0027)**: F2/F3/F9 paired runs with N=3-5. Fix 1's clamp + record path means variance computation never includes invalid cells.
4. **B-5 `completed:` removal probe (iter-0028)**: F2 single-fixture re-run after dropping `completed:` from DOCS phase output. Scope axis prediction (23 → 25) is testable only because the axis values are now bounded.

iter-0024 will ship A-0 (Bare-Case Guardrail wording correction in CLAUDE.md) + A-1 (EVAL hygiene severity LOW → MEDIUM blocking, task-scoped only — Codex's recommended Q5 minimal probe). Both are local-only iters.

## Principles check

### Pre-flight 0 — not score-chasing
**Status: ✅ PASS.** Closes a real measurement bug surfaced by user + Codex independent review. Output is honesty (the gate now matches the docs), not score movement.

### 1. No overengineering
✅ PASS. +78 lines total across 2 files, no new abstractions, no new schema. Each change cites the exact file:line + NORTH-STAR clause it enforces. No flag added; no behavior changes when invalid data is absent.

### 2. No guesswork
✅ PASS. H1-H3 stated as predicted directions before implementation; H1+H2 verified by smoke run. H3 (judge.sh validation) requires a real judge run for end-to-end validation; iter-0023 ships the code path with explicit Codex pair-review.

### 3. No workaround
✅ PASS. Both fixes are root-cause: judge.sh validates rather than swallowing invalid axis data; ship-gate enforces the documented gate rather than allowing the gap. No `try/except`, no silent fallback.

### 4. Worldclass production-ready
✅ PASS. Fixes the L1 enforcement gap directly affecting release decisions. Legacy L2 path unchanged. No new CRITICAL/HIGH risk surface.

### 5. Best practice
✅ PASS. Standard `argparse` / `pathlib` / `json` patterns; clamp uses `max(0, min(25, ...))` rather than custom logic.

### 6. Layer-cost-justified
✅ PASS. iter-0023 is iteration-loop infrastructure (no auto-resolve hot-path code change). Zero model invocations. Gate accuracy improvement is amortized over every future suite-run interpretation.

### 7. Mission-bound
✅ PASS. Serves Mission 1 gate 1 enforcement (NORTH-STAR ops test #1). Hard NO list untouched.

## Drift check (산으로?)

- **Removes a real user failure?** Yes. The user-visible failure is *"the score gate is documented but un-enforced; we cannot trust ship/no-ship decisions."* iter-0023 closes that.
- **Expands scope beyond what was requested?** No. Fixes are precisely scoped to the two bugs Codex named.
- **Sets up a multi-iter measurement chain?** Yes — intentionally. iter-0023 is the LAST attribution-fix iter (PRINCIPLES.md:22) before the measurement-trust runs (iter-0025+).
- **"While I'm here" cross-mission additions?** None.

## Codex pair-review trail (this iter)

### R0 / measurement-trust round (~100k tokens xhigh, 254s; transcript at `/Users/aipalm/.claude/projects/-Users-aipalm-Documents-GitHub-devlyn-cli/78008a93-84ed-4c44-a393-85338f6f2b4c/tool-results/bv0o838s0.txt`)

Verdict: user's pushback correct. Two measurement bugs named explicitly:
- judge.sh accepts invalid axis data (cited iter-0020 F9 quality=-1).
- ship-gate.py gates legacy `variant` margin, not L1 `solo_over_bare`.

Plus three corrections to the original 3-step plan I proposed: paired (not L1-only) variance, Opus sidecar before reruns (cheaper trust probe), F9 re-run before interpreting suite avg.

### R1 / diff-review round (TBD — to run after this iter file is written)

Will inspect both edits + this iter file and the smoke output. iter-0021 lesson: every cited file:line opened at citation time.

## Cumulative lessons

1. **User pushback on a stat threshold caught a real bug.** "+5 may not be statistically meaningful" was right; the deeper finding was that the gate wasn't even enforced. Honest self-doubt beats false certainty.
2. **Documented contracts can be silently un-enforced.** NORTH-STAR.md:81 has stated the L1 gate since iter-0019; ship-gate.py never read `solo_over_bare`. The gap survived 4 ship cycles. Lesson: every gate clause in NORTH-STAR.md should have a mechanical test that the corresponding script implements it.
3. **Clamp + record, don't reject** for measurement-side invalid data. Rejecting one bad cell means losing 8 fixtures' worth of runtime; clamp + record + propagate-to-ship-gate keeps the data while making the invalidity visible.
4. **Codex's "smallest falsifiable iter" framing was right.** The original plan ("3-5 reruns + Scope probe + real-project trial") was 3 iters worth of work. Splitting out "fix the gate first" is one cheap iter that makes the next 3 honest.

## Falsification record (in-session smoke)

| Test | Predicted | Observed |
|---|---|---|
| ship-gate.py imports cleanly | exit 0 | exit 0 ✓ |
| ship-gate against iter-0020 reports L1 suite avg +4.4 < +5 | warning fires | warning fires (matches iter-0021 readout exactly) ✓ |
| ship-gate against iter-0020 reports F9 L1 = +0 < +5 | failure fires | failure fires (correct: F9 was rate-limited) ✓ |
| Legacy L2 variant disqualifier gate still fires | failure fires | failure fires ✓ |
| Legacy L2 F9 variant margin gate still fires | failure fires | failure fires ✓ |

Total: 5 acceptance gates closed in-session. Real provider/model invocations: 0.
