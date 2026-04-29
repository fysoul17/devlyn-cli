---
iter: "0027"
title: "F2 paired variance N=5 — characterize BUILD-side variance + DQ rate"
status: data (variance characterized; full prescription deferred to next-iter pivot)
type: measurement-trust (5 paired single-fixture re-runs at b06fffd; mechanism + categorical reliability data)
shipped_commit: 4feae35
date: 2026-04-30
mission: 1
---

# iter-0027 — F2 paired variance N=5

## Why this iter exists (PRINCIPLES.md pre-flight 0)

iter-0026 (single-shot F2 re-run) showed L1 swung from 94 (iter-0020) to 81 (iter-0026) on a docs-only edit that should have moved one axis by +2. Per-fixture variance was overshadowing the +5 floor signal that iter-0021/0023/0025 depended on. Codex iter-0026 R-final prescribed F2 N=5 + F3/F9 N=3 paired variance.

**Decision this iter unlocks**: whether iter-0021/0023's L1 floor reasoning is meaningful at single-shot or only at N≥3 paired; whether silent-catch DQ on F2 is a tail event or a structural BUILD failure mode that needs prompt/CRITIC redesign.

## Mission 1 service (PRINCIPLES.md #7)

Single-task L1 measurement trust on F2. No Mission 2/3 surface. Mission 1 hard NOs untouched.

## Hypothesis (pre-registered by Codex iter-0027 R0)

Decision rules at N=5:
- DQ ≥ 2/5 → structural F2 silent-catch problem; stop broad expansion; run categorical-reliability iter.
- DQ = 1/5 → ambiguous; expand or pivot judgement-call.
- DQ = 0/5 → iter-0026 was tail; expand F3/F9.

Tight-path requirement (skip pivot, expand cross-fixture): `L1-L0 stdev < 3 AND L1 score stdev < 3 AND no L1 DQ AND no axis stdev > 3`.

## Method

Sequential single-fixture 3-arm runs at commit `b06fffd` (post iter-0026 `completed:` removal). 5 separate RUN_IDs:
- n1: `20260429T134348Z-b06fffd-iter-0027-f2-n1`
- n2: `20260429T141802Z-b06fffd-iter-0027-f2-n2`
- n3: `20260429T150528Z-b06fffd-iter-0027-f2-n3`
- n4: `20260429T155419Z-b06fffd-iter-0027-f2-n4`
- n5: `20260429T164550Z-b06fffd-iter-0027-f2-n5`

iter-0026 sentinel kept for context but excluded from the N=5 sample (different commit `b5a2a60`).

Two Codex rounds: R0 (iter-0027-r0, ~87k tokens xhigh, 172s — pre-registered the DQ rate decision rules and tight-path criteria) + R-final (iter-0027-rfinal, ~9k tokens xhigh, 24s — adopted "DATA — variance characterized at N=3; full prescription deferred" framing on the partial N=3 result; instructed expansion to N=5 before any pivot decision).

## Findings (the data)

### Per-run results (F2 fixture, judge=GPT-5.5)

| run | L0 (bare) | L1 (solo) | L2 (variant) | L1-L0 | L1 DQ |
|---|---|---|---|---|---|
| n1 | 83 | 98 | 99 | +15 | clean |
| n2 | 83 | 91 | 97 | +8 | **DQ silent-catch** |
| n3 | 81 | 96 | 97 | +15 | clean |
| n4 | 78 | 93 | 94 | +15 | **DQ silent-catch** |
| n5 | 52 | 52 | 96 | 0 | clean (invalid) |

### N=5 raw stats

- L1 scores: [98, 91, 96, 93, 52], mean=86.0, stdev=19.20
- L1-L0 margins: [15, 8, 15, 15, 0], mean=10.6, stdev=6.66
- L1 DQ rate: **2/5 (40%)**
- Scope axis: stdev=0.00 (all 25 — `completed:` removal stable across N=5)

### N=5 with n5 excluded (n5 = invalid measurement)

n5's `result.json`: L0 and L1 BOTH produced `files_changed=0` and `verify_score=0.167` (no code written). Variant produced 2 files / `verify_score=1.0`. n5 L0/L1 were upstream BUILD interruptions (no real measurement of L1 quality — both arms scored 52 because neither produced output). Excluding n5 as a measurement-invalid sample:

- N=4 effective L1 scores: [98, 91, 96, 93], mean=**94.5**, stdev=**2.89**
- N=4 effective L1-L0 margins: [15, 8, 15, 15], mean=**+13.25**, stdev=**3.50**
- N=4 effective L1 DQ rate: **2/4 (50%)**
- Per-axis stdev: spec 0.50, constraint 1.83, scope 0.00, quality 0.71

### Cross-comparison

- iter-0020 baseline F2 single-shot (commit `91994db`, with `completed:` field): L1=94, L1-L0=+9.
- iter-0026 F2 single-shot (commit `b5a2a60`, post-`completed:` removal): L1=81, L1-L0=-8 (tail event).
- iter-0027 F2 N=4 effective mean (commit `b06fffd`, post-`completed:` removal): L1=94.5, L1-L0=+13.25.

## Interpretation (per Codex R-final caveats)

### What's robust
1. **`completed:` removal mechanism confirmed N=4 wide**: scope axis = 25 in every fresh run. iter-0021's mechanism story is real on the GPT judge.
2. **iter-0026 was a tail event, not a regression**: the N=4 mean recovers to 94.5 (slightly above iter-0020's 94 baseline).
3. **L1 mean L1-L0 = +13.25 above the +5 NORTH-STAR floor**: F2 alone is well clear of the floor when the run produces clean code.

### What's load-bearing — and what flips the L1 story
**L1 DQ rate ≥ 2/5 (Codex's pivot threshold) on silent-catch failure**. n2 hit `Forbidden disqualifier-severity catch-return fallback`; n4 hit `Forbidden-pattern hit for catch returning an object`. Two distinct silent-catch sites in two different runs. **The same L1 BUILD prompt / engine produces silent-catch DQs on F2 ~40-50% of runs.** That is structural, not noise.

This **invalidates the iter-0021/0023/0025 framing** that L1 sits "just below +5 floor." The honest framing:
- L1 produces a clean BUILD with strong L1-L0 lift on F2 ~50-60% of runs (when no DQ).
- L1 produces a silent-catch-DQ'd BUILD on F2 ~40-50% of runs.
- The single-shot suite-avg +4.4 (iter-0020 readout) is a *blend* of these two regimes — not a stable per-fixture estimate.

### What this changes
**iter-0028 pivot to categorical reliability**. Per Codex iter-0027 R-final Q2: *"If F2 N=5 ends at ≥2/5 silent-catch DQ, I would stop broad fixture expansion and run iter-0028 as categorical-reliability: prompt/CRITIC must detect silent catches before EVAL."*

The structural DQ rate is far more important than another decimal-place on the suite-avg. Single-task quality (Mission 1 gate 1) is failing not because of small axis margins but because L1 has a recurring BUILD failure mode that the pipeline doesn't catch before EVAL gates it.

Cross-fixture generalization (F3 N=3 + F9 N=3) deferred to a later iter once iter-0028's categorical fix lands.

### Codex R-final Q3: ship-gate language change
Codex prescribed updating iter-0023 ship-gate language: single-shot can be smoke evidence only; ship-readiness requires N≥3 paired. Queued for iter-0028 (or a follow-up cleanup iter) — out of scope for iter-0027's data role.

## Principles check

### Pre-flight 0 — not score-chasing
✅ PASS. Closes the variance question that iter-0026 surfaced. Output reframes the L1 floor decision (DQ rate, not suite-avg, is the dominant Mission 1 signal).

### 1. No overengineering / Subtractive-first
✅ PASS. 5 sequential identical-shape runs; no new abstraction; no new harness code; no new ship-gate. Pure measurement.

### 2. No guesswork
✅ PASS. Codex iter-0027 R0 pre-registered DQ rate decision rules + tight-path criteria. Result lands in the "≥2/5 → pivot" bucket exactly as pre-registered.

### 3. No workaround
✅ PASS. n5 invalid-measurement exclusion is documented with file-level evidence (`files_changed=0`, `verify_score=0.167`), not silenced or averaged-in.

### 4. Worldclass production-ready
⚠️ This iter's data shows L1 production-readiness is worse than previously reported. The "≥2/5 silent-catch DQ on F2" is the failure to address; iter-0028 will. iter-0027 itself ships only the data, not a fix.

### 5. Best practice
✅ PASS. Standard Python `statistics.stdev`, `statistics.mean`. Re-uses iter-0023's `_axis_validation` records.

### 6. Layer-cost-justified
✅ PASS. Iteration-loop measurement work; no auto-resolve hot-path cost change.

### 7. Mission-bound
✅ PASS. Single-task / single-worktree. Mission 1 hard NO list untouched.

## Drift check (산으로?)

- **Removes a real user failure?** Surfaces one (silent-catch DQ rate 40-50% on F2). iter-0028 will close it.
- **Expands scope?** No. F2 only. Cross-fixture deferred.
- **Multi-iter chain?** Yes — iter-0028 categorical-reliability work is the load-bearing follow-up.
- **"While I'm here" cross-mission?** None.

## Codex pair-review trail (this iter)

### R0 — paired variance design (iter-0027-r0, ~87k tokens xhigh, 172s)
Pre-registered: DQ rate decision rules (≥2/5 → pivot to iter-0028 categorical), tight-path criteria, "use run-suite.sh per RUN_ID since `--n N` is not wired", same-commit `b06fffd` baseline (iter-0026 sentinel for sensitivity only). Operational catch: `run-suite.sh` exits non-zero on DQ → wrap loop with `|| true`.

### R-final — N=3 partial result interpretation (iter-0027-rfinal, ~9k tokens xhigh, 24s)
Adopted verbatim:
- Q1: expand to N=5 (categorical DQ is main signal, not mean score).
- Q2: 2/5 DQ ⇒ iter-0028 categorical-reliability iter (silent-catch detection before EVAL).
- Q3: ship-gate language requires N≥3 paired for floor enforcement; single-shot is smoke only.
- Q4: status `DATA — variance characterized at N=3; full prescription deferred`. Not SHIPPED.
- Q5: don't overread N=3 mean +12.7 as the `completed:` lift; mean did not collapse, iter-0026 was tail-ish, DQ is the dominant risk.

R-final post-N=5 update (in this iter file): DQ rate 2/5 (or 2/4 excluding invalid n5) confirms the pivot. iter-0028 categorical-reliability iter is the load-bearing next step.

## Cumulative lessons

1. **Single-shot per-fixture suite-avg is unsafe for floor decisions.** N=4 effective F2 L1-L0 ranges from +8 to +15; the +5 floor sits well inside that range. iter-0021/0023/0025's framing held at the aggregate level (cross-judge agreement on +4.4) but per-fixture single-shot was over-confident.
2. **DQ rate is the dominant signal**. The mean L1 score lift from `completed:` removal (~+0.5) is dwarfed by the silent-catch DQ rate (40-50%). Floor reasoning that ignores DQ classification is wrong-shaped.
3. **iter-0026 was a tail event**, but the tail is *real* — it's the realized DQ outcome. Saying "iter-0026 was an outlier" hides the fact that ~40% of runs hit a silent-catch. The outlier was on the *score axis*, not on the *DQ classification*.
4. **n5 invalid-measurement detection matters**. Both L0 and L1 producing `files_changed=0` indicates upstream BUILD interruption, not BUILD-output variance. Excluding n5 as invalid (vs. averaging it in) is the principle-#3 root-cause approach.

## Falsification record

| Pre-registered prediction | Outcome |
|---|---|
| DQ rate decisive: ≥2/5 → pivot to categorical | DQ 2/5 → pivot fires |
| Tight path: L1-L0 stdev <3 + L1 score stdev <3 + no DQ + no axis stdev >3 | Failed: stdev OK without n5 but DQ 2/5 vetoes |
| `completed:` removal stable scope=25 across N | scope stdev = 0.00 across all 5 ✓ |
| iter-0026 was tail event | Confirmed: N=4 effective mean L1=94.5 vs iter-0026 L1=81 |
| `+4.4` suite-avg framing was decision-grade | Falsified: per-fixture variance ±3-15 (DQ-dependent), suite-avg unstable |

Net: variance characterized; categorical-reliability pivot pre-registered and triggered; iter-0028 = silent-catch detection in BUILD output before EVAL gates it.
