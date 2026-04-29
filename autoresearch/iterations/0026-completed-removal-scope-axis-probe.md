---
iter: "0026"
title: "`completed:` removal — F2 scope-axis mechanism falsification probe"
status: shipped-mechanism (conclusion-deferred to iter-0027)
type: targeted-mechanism-probe (single-fixture re-run, mechanism confirmed; net L1 conclusion deferred to paired variance)
shipped_commit: pending
date: 2026-04-29
mission: 1
---

# iter-0026 — `completed:` removal Scope-axis mechanism probe

## Why this iter exists (PRINCIPLES.md pre-flight 0)

iter-0021 readout pre-registered: F2/F4 L1 lost -2 scope each because DOCS phase wrote `status: done + completed: <today>` to roadmap frontmatter, and judge debited the `completed:` field as un-licensed metadata (spec lifecycle note licenses only `status` flip). iter-0022/0023/0024/0025 closed measurement-trust + framing issues in the chain. iter-0026 is the **direct mechanism falsification**: drop `completed:` from PHASE 4 DOCS Job 1 and re-run F2; predict L1 scope axis 23 → 25.

**Decision this iter unlocks**: whether the "Scope -4 = `completed:` field" mechanism story from iter-0021 is real, partial, or false. Closes one of the four open principle-bin questions from iter-0021 readout.

## Mission 1 service (PRINCIPLES.md #7)

Serves Mission 1 gate 1 (L1 vs L0 quality) by removing a known L1-only scope debit. Mission 1 hard NOs untouched.

## Hypothesis

H1 (predicted by iter-0021 + Codex iter-0026 R0): F2 L1 scope axis 23 → 25 after dropping `completed:` from DOCS Job 1.

H2 (predicted): F2 L1 spec / constraint / quality axes unchanged within ±1 (the `completed:` field doesn't affect those).

H3 (predicted): L1 disqualifier still 0 (the iter-0020 L1 was clean — no DQ).

## Method

### Codex R0 (~292k tokens xhigh, 392s)

Pre-registered mechanism + acceptance gates. Important Codex catches:
- `completed:` field has no hard consumer (auto-resolve dependency-preflight checks `status: done` only; SCHEMA.md frontmatter requires `id` only; ideate archive falls back to today when `completed:` absent). Soft risk: preflight `triage-templates.md:55` listed `status:, completed:` as part of STALE_DOC handling; cleaned up.
- Use `run-suite.sh` (3-arm), not `run-fixture.sh` (single arm).
- Acceptance refinements: read axis values directly from `judge.json` (compile-report.py doesn't expose breakdowns); require `_axis_validation.out_of_range_count == 0`; treat non-scope axis drift >1 as inconclusive (not auto-fail); core falsifier is "no `completed:` in diff AND L1 scope still 23 AND notes still debit docs/frontmatter."
- Caveat noted: Opus already scored F2 L1 scope = 25 in iter-0025 sidecar with the `completed:` field present, so the mechanism is GPT-judge-specific, not universal.

### Edits

`config/skills/devlyn:auto-resolve/SKILL.md:223` — DOCS Job 1 step 2 changed from *"Set status: done + completed: <today> in frontmatter"* to *"Set status: done in frontmatter. Do not add completed: or any other field beyond what the spec lifecycle note licenses."* Mirror to `.claude/skills/devlyn:auto-resolve/SKILL.md`.

`config/skills/devlyn:preflight/references/triage-templates.md:55` — STALE_DOC update line changed from *"`status:`, `completed:`"* to *"`status:` only — do not add `completed:` or other un-licensed fields per iter-0026; spec lifecycle notes typically license `status` flip only."*

### Run

`bash benchmark/auto-resolve/scripts/run-suite.sh --run-id 20260429T130040Z-b5a2a60-iter-0026-b5 --accept-missing F2-cli-medium-subcommand`. F2 single fixture, 3 arms (variant / solo_claude / bare), wall ~33 min total.

## Findings

### iter-0026 F2 result vs iter-0020 baseline

| Arm | iter-0020 score | iter-0026 score | Δ |
|---|---|---|---|
| bare (L0) | 85 | 89 | +4 |
| solo_claude (L1) | **94** | **81** | **−13** |
| variant | 83 | 93 | +10 |

L1 axis breakdown:
| Axis | iter-0020 L1 | iter-0026 L1 | Δ |
|---|---|---|---|
| Spec | 24 | 21 | -3 |
| Constraint | 25 | 17 | **-8** (silent-catch DQ) |
| Scope | **23** | **25** | **+2 ✓ predicted** |
| Quality | 22 | 18 | -4 |
| **Total** | **94** | **81** | **-13** |

L1-L0 margin: iter-0020 +9 → iter-0026 -8 (swing of 17 on a single fixture from a single docs-prompt change).

### What the run actually showed

- **H1 confirmed**: scope 23 → 25 exactly as predicted. `completed:` mechanism is real on the GPT-5.5 judge. Codex R-final caveat: same-prompt rerun could still score 25 by chance, so the +2 is not causal-estimate-grade — but the mechanism IS confirmed.
- **H2 falsified**: spec / constraint / quality drifted by -3 / -8 / -4. None caused by the docs-prompt edit; they reflect BUILD-side variance.
- **H3 falsified**: L1 hit a silent-catch DQ in `findSkillFiles` (judge note: *"Disqualified by an actual silent catch in findSkillFiles that returns on ENOENT"*). iter-0020 L1 had no DQ.

### The single load-bearing finding

**Single-shot BUILD variance is enormous.** F2 L1 score moved 94 → 81 (−13) on a docs-prompt change that should affect only Scope by +2. The remaining −15 of swing is BUILD-side variance — Claude solo on F2 produced *different code* this run than iter-0020 (silent ENOENT in findSkillFiles vs no DQ at all in iter-0020).

This **directly answers the user's "+5 신뢰성" pushback**: per-fixture variance ≥ ±13 axis-sum on a single run is larger than the suite-avg L1-L0 signal (+4.4). iter-0021/0023/0025's reasoning about the +5 floor is honest only at the aggregate level; per-fixture single-shot scoring is too noisy to be load-bearing.

## What this iter unlocks

- **Mechanism**: `completed:` removal is now the canonical DOCS behavior (Codex Q2: do not revert; current prompt encodes the correct narrow license; reintroducing the field would knowingly restore a judged scope debit).
- **iter-0027 (paired variance) becomes mandatory, not optional**: Codex R-final verdict was *"choose (b), with (c) folded into analysis — F2 N=5, F3/F9 N=3."* Per-arm BUILD variance, DQ rate, axis stddev, paired L1-L0 delta distribution all need to be reported.
- **Provisional L1 conclusion**: any L1-L0 reasoning between iter-0021 and iter-0027 closure is *provisional*. iter-0023 ship-gate L1 enforcement still works correctly; the *interpretation* of L1-L0 = +4.4 is what's been weakened.

## Principles check

### Pre-flight 0 — not score-chasing
✅ PASS. Mechanism falsification, exact prediction, surfaced a load-bearing surprise (BUILD variance dominates the signal we were trying to measure).

### 1. No overengineering / Subtractive-first
✅ PASS. One-line edit (`+ "completed: <today>"` removed from DOCS prompt) plus one-paragraph rewrite of the prompt sentence + one preflight triage-template cleanup. Subtractive: dropped a field from a docs prompt.

### 2. No guesswork
⚠️ BORDERLINE → ✅ rescued by R-final discipline. H1 was tightly predicted (Scope 23→25, +2 exactly); H2 falsified; H3 falsified. The honest framing per Codex R-final Q4 is **"SHIPPED-MECHANISM / CONCLUSION-DEFERRED"** — mechanism is real, net L1 conclusion is deferred to iter-0027 paired variance, not claimed here.

### 3. No workaround
✅ PASS. Root-cause fix: spec lifecycle note licenses `status` only; harness was adding un-licensed `completed:`; harness now matches license. No silent fallback.

### 4. Worldclass production-ready
⚠️ BORDERLINE. iter-0026 L1 produced a silent-catch DQ in BUILD output. That's a BUILD-side regression *on this single run* — not iter-0026's code change (the change is docs-only). Without iter-0027 we don't know if the DQ is run-to-run noise or a regression. Codex R-final: "regression is consistent with BUILD variance but not yet attributed." Acceptance: provisional ship pending iter-0027.

### 5. Best practice
✅ PASS. Re-uses existing run-suite.sh single-fixture path. No new helpers. Idiomatic edit.

### 6. Layer-cost-justified
✅ PASS. Single-fixture single-shot (~33 min wall). The finding (variance dominates) is itself decision-grade for iter-0027 sequencing.

### 7. Mission-bound
✅ PASS. Single-task, single-worktree, no Mission 2 surface.

## Drift check (산으로?)

- **Removes a real user failure?** Mechanism: yes (un-licensed metadata removed from DOCS prompt). Net L1 quality: TBD pending iter-0027.
- **Expands scope?** No. Single fixture, single change.
- **Sets up a multi-iter chain?** Yes — intentionally. iter-0027 (F2 N=5 + F3/F9 N=3 paired variance) is the load-bearing follow-up.
- **"While I'm here" cross-mission?** None.

## Codex pair-review trail

### R0 — sequencing + design (~292k tokens xhigh, 392s; transcript at `/Users/aipalm/.claude/projects/-Users-aipalm-Documents-GitHub-devlyn-cli/78008a93-84ed-4c44-a393-85338f6f2b4c/tool-results/b2jbygqr1.txt`)

Approved B-5 first (vs B-3 F9 re-run). Verified no hard consumer of `completed:` field. Provided exact run-suite.sh command. Refined acceptance gates. Caught Opus-already-scored-25 caveat (mechanism is GPT-judge-specific).

### R-final — surprising-result interpretation (~116k tokens xhigh, 168s; transcript at `/Users/aipalm/.claude/projects/-Users-aipalm-Documents-GitHub-devlyn-cli/78008a93-84ed-4c44-a393-85338f6f2b4c/tool-results/bq4rqm8xa.txt`)

Verdict adopted verbatim:
- Q1: mechanism confirmed; exact +2 not causal-estimate-grade.
- Q2: do NOT revert. Current prompt encodes correct narrow license; reverting would knowingly restore a judged scope debit.
- Q3: iter-0027 = F2 N=5, F3/F9 N=3 (within the already-written N=3-5 plan).
- Q4: status `SHIPPED-MECHANISM / CONCLUSION-DEFERRED`. *"completed: removal confirmed on F2 scope axis. Same run regressed L1 net 94→81 with silent-ENOENT DQ; regression is consistent with BUILD variance but not yet attributed. Stable L1 conclusion deferred to iter-0027."*

## Cumulative lessons

1. **Single-shot BUILD variance can drown the signal you're measuring.** F2 L1 swung 94 → 81 on a docs-prompt change that should have moved one axis by +2. The other 15 points of swing is BUILD-output variance. Any future iter that measures a single change with a single run is suspect.
2. **Mechanism confirmation ≠ effect-size confirmation.** Codex Q1 caveat: *"a no-change rerun could still score scope 25 by chance."* The +2 prediction landing is consistent with `completed:` causation but doesn't prove the +2 effect size — it only proves the mechanism story (the field was the GPT-judge's stated reason for the debit) is honest at the prompt-text level.
3. **The user's pushback on +5 floor reliability was deeper than first read.** I (Claude) initially answered "iter-0025 cross-judge confirmed +4.4." That's true *at the aggregate*, but iter-0026 reveals per-fixture single-shot variance ≥ ±13. The user's question really wanted N>1 paired variance, not just cross-judge. iter-0027 is the long-due response.
4. **R-final discipline saved the framing.** I was about to ship as "SHIPPED — mechanism confirmed" with a subordinate caveat about variance. Codex's correct status is `SHIPPED-MECHANISM / CONCLUSION-DEFERRED` — promotes the variance finding from caveat to first-class deferred decision. iter-0021's R-final fabrication-rescue lesson generalizes: when the result surprises you, pair-review *before* committing the framing.

## Falsification record (in-session)

| Pre-registered prediction | Outcome |
|---|---|
| F2 L1 scope axis 23 → 25 | scope = 25 ✓ |
| F2 L1 spec / constraint / quality axes unchanged within ±1 | -3 / -8 / -4 ✗ (BUILD variance, not docs edit) |
| F2 L1 disqualifier = 0 | DQ silent-catch in findSkillFiles ✗ (BUILD variance) |
| Suite-avg L1-L0 floor reasoning is robust | per-fixture variance > suite-avg signal — needs iter-0027 |

Net: mechanism confirmed; effect-size deferred; variance finding promoted to next-iter load-bearing.
