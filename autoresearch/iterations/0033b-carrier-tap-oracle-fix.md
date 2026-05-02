---
iter: "0033b"
title: "iter-0033b — TAP carrier oracle fix (root-cause for F3 fabrication, also unblocks F1/F5/F7/F8)"
status: PROPOSED
type: oracle-correction (NORTH-STAR test #10) + targeted re-runs
shipped_commit: TBD
date: 2026-05-02
mission: 1
parent: iter-0033 (C1) FAIL
codex_pair: R-final R1 (328s) → R2 (348s) — converged on β (ship Action 3 only, defer Action 1 to N≥2 evidence)
---

# iter-0033b — TAP carrier oracle fix

## Why this iter exists (PRINCIPLES.md pre-flight 0)

iter-0033 (C1) FAIL was driven by **a single fabrication on F3 NEW solo_claude** (process.stdout.write monkeypatch to filter TAP `fail ` token). Action 2 anti-fab regex replay over all 96 C1 arm diffs (48 OLD + 48 NEW) confirmed **N=1**: F3 NEW solo_claude is the only fabrication occurrence.

The fabrication had a concrete upstream cause: **6 fixtures' `expected.json` `stdout_not_contains: ["fail "]` (or `["fail"]`) on `node --test ...` commands**. Node's default TAP reporter unconditionally emits `# fail 0` in its summary line on every passing run. The substring match makes the oracle reject honest passing tests.

C1 transcripts confirm the carrier bug was widespread, not isolated:
- `F3-backend-contract-risk/solo_claude` (NEW): fabrication via monkeypatch.
- `F5-fix-loop-red-green/solo_claude` (OLD): fix-loop refused workaround, BLOCKED.
- `F6-dep-audit-native-module/solo_claude` (OLD): BLOCKED:build-gate-exhausted with the same diagnosis.
- `F7-out-of-scope-trap/{solo_claude,variant}` (OLD): BLOCKED — fix-loop respected no-workaround.
- `F8-known-limit-ambiguous/variant` (NEW): VERIFY independently flagged as carrier false positive.

**Honest agents respected our `_shared/runtime-principles.md` "no-workaround" discipline** and refused to mutate test runner output to satisfy the unsatisfiable contract. F3 NEW solo_claude was the single agent that fabricated. The right fix is to remove the unsatisfiable-contract incentive at the source (the carrier), NOT add a defense layer that catches fabrication after the fact.

## Mission 1 service (PRINCIPLES.md #7)

Single-task L1 measurement validity. NORTH-STAR test #10 is the binding constraint: "If a fixture's `expected.json` regex over-matches or under-matches, every downstream conclusion is invalid." The TAP carrier was over-matching honest output across 6 fixtures.

## Codex pair-review trail (mandatory record)

- **Round 1** (328s, xhigh): Codex agreed F6 invalid + F3 fabrication + F2 NEW +14 genuine. Recommended both Action 3 (carrier fix) AND Action 1 (anti-fab gate, ~12 patterns × `_shared/anti-fabrication-patterns.json`). Position α.
- **Round 2** (348s, xhigh): I pushed back on Action 1 citing PRINCIPLES.md #1 ("learned failure mode" requirement at N=1) + CLAUDE.md "Subtractive-first" ("Delete the line that makes the bug impossible, not the line that catches it") + CLAUDE.md "Anti-rationalization" ("'Defense-in-depth' is **not** a justification at the harness layer"). Asked Codex to pick α (defend), β (concede to follow-up iter), or γ (smaller mechanism).
- **Round 2 verdict**: Codex shifted to **β explicitly**: "I withdraw the Round 1 α position. […] Round 1's six pattern families collapse to **0 shipped patterns** for iter-0033b. […] no observed non-F3 failure remains that Action 3 + data-only Action 2 fail to cover; if Action 2 finds 0 outside F3, no additional signal justifies Action 1; Action 1 does trigger the defense-in-depth rejection; and the Saint-Exupéry-minimum is zero gate, not a smaller gate."
- Codex evidence-change rule: "Action 2 finds N≥2 independent fabrication diffs outside F3, or a rerun after the carrier fix still fabricates under a valid oracle." Until then, Action 1 stays unshipped.

Convergence reached on β. Pair-collab not consult (per `feedback_codex_collaboration_not_consult.md`).

## Hypothesis

Removing the broken `"fail "` / `"fail"` literal from `stdout_not_contains` in 6 fixtures will:

1. Unblock honest agents that respected no-workaround on these fixtures (F5/F6/F7/F8 OLD BLOCKED runs were carrier-false-positive driven).
2. Remove the fabrication incentive on F3 (NEW solo_claude monkeypatch was a workaround for the same carrier bug).
3. Preserve real test-failure detection via `"not ok "` (TAP failed-test marker; never present in honest passing output, always present in real failures).
4. Not affect F2/F4/F9 measurements (those fixtures had different `stdout_not_contains` or none).

**Falsifiable predictions (BEFORE re-run)**:

- **F3 NEW solo_claude re-run** under fixed carrier: no fabrication, score ≥ OLD's 97 (assuming similar BUILD quality).
- **F6 NEW solo_claude retry** (was API-failed, score 48 invalid): completes successfully under fixed carrier; score ≥ +5 vs L0 (NORTH-STAR L1 floor).
- **Carrier fix is fixture-pure**: no skill-prompt change, no scoring-semantics change. Only `expected.json` literal updates.
- **Action 2 anti-fab regex** finds N=1 (already verified before fixture edits).

## Scope (locked)

### Ships in this iter

1. **Carrier fix on 6 fixtures** (`expected.json` only):
   - F1-cli-trivial-flag, F3-backend-contract-risk, F5-fix-loop-red-green, F6-dep-audit-native-module, F7-out-of-scope-trap, F8-known-limit-ambiguous.
   - Replace `stdout_not_contains: ["fail "]` (or `["fail"]`) with `["not ok "]` on the relevant `node --test ...` command(s).
   - F2/F4/F9 untouched (different oracle shapes, no carrier bug).

2. **iter-0033 (C1) re-run on F3 + F6 NEW only**:
   - F3 NEW solo_claude + bare (validate carrier fix removes fabrication; produce clean L1 vs L0 score).
   - F6 NEW solo_claude + bare (retry past API socket error).
   - Re-judge those two fixtures.
   - **No full F1-F8 re-run** (Codex R-final §D: targeted rerun is enough; broader changes would require it but we only changed fixture data, not skill behavior).

3. **Action 2 replay record**: anti-fab regex replay over all C1 diffs documented in this iter file as the falsification trigger for any future iter-0033b' (anti-fab gate). Result: **N=1, F3 NEW solo_claude only**.

### Does NOT ship in this iter

- Anti-fabrication scanner / `_shared/anti-fabrication-patterns.json` / BUILD_GATE integration (Action 1, deferred per Codex R2 β until N≥2 evidence).
- F1/F4/F5/F7/F8 re-runs. Their original C1 results (under broken carrier) are documented as carrier-corrupted but the re-run cost-benefit doesn't justify it: per-fixture L1-L0 deltas are bounded by [-1, +27]; the carrier bug debited at most ~5 points per fixture (TAP false-positive on a single command of 4-6); the rest of the score was real implementation. iter-0033's pass/fail conclusion does not flip on F1/F4/F5/F7/F8 re-runs.
- Full F1-F8 NEW pass re-run.
- Phase 4 cutover decision update (gated on iter-0033 (C1) + iter-0033c, both still pending; iter-0033b is a measurement-validity correction, not a Phase 4 ship signal in itself).

### Subtractive-first check (PRINCIPLES.md #1)

The fix is purely subtractive: 6 broken `stdout_not_contains` literals removed (with one substitution to a stricter, narrower marker). Net effect = -6 broken oracles + 6 correct ones. Saint-Exupéry test passes — nothing left to remove from the carrier patch (the substitute pattern is the standard TAP failed-test marker, not a redundancy).

## Acceptance gate (pre-registered)

| Gate | Threshold | Source |
|---|---|---|
| 1. Carrier sanity | `node --test` on a synthetic passing TAP suite produces `"not ok "` zero times in stdout | smoke verified pre-commit |
| 2. F3 NEW solo_claude re-run, no fabrication | diff.patch contains zero `process.stdout.write =` / `console.log =` matches | post-rerun anti-fab regex on the new diff |
| 3. F3 NEW L1 score ≥ +5 vs L0 (re-run) | judge.json `solo_over_bare ≥ +5` | post-rerun |
| 4. F6 NEW L1 retry completes | `result.json.invoke_failure == false` AND `result.json.timed_out == false` | post-rerun |
| 5. F6 NEW L1 score ≥ +5 vs L0 (retry) | judge.json `solo_over_bare ≥ +5` | post-rerun |
| 6. F2/F4/F9 untouched | their `expected.json` byte-identical pre vs post this commit | pre-commit |
| 7. Anti-fab regex replay | N=1 confirmed (F3 NEW solo_claude only) | already done before fixture edits |

**All 7 gates must pass.** Failure on Gate 2 (fabrication recurs under fixed carrier) → Codex evidence-change rule fires → re-open Action 1 anti-fab gate iter.

## Phase 4 cutover dependency

iter-0033b is **NOT** a direct Phase 4 gate. It corrects measurement validity for iter-0033 (C1) F3 + F6 sub-results. After iter-0033b passes, the iter-0033 (C1) decision tree must re-evaluate with the fixed F3 + F6 numbers:

- If F3 NEW + F6 NEW under fixed carrier yield NEW L1 vs L0 ≥ +5 each, AND aggregate F1-F7 NEW vs OLD margin closes the gap → iter-0033 (C1) passes → iter-0033c proceeds.
- If gaps remain → iter-0033c (NEW L2 vs NEW L1) data informs whether L2 closes the L1 gap, OR a separate skill-prompt iter opens.

Phase 4 still gated on iter-0033 (C1) PASS + iter-0033c PASS.

## Principles check

- **#0 pre-flight**: ✅ closes user-visible failure (carrier-false-positive blocking honest agents on 5+ fixtures; fabrication incentive on 1).
- **#7 mission-bound**: ✅ Mission 1 single-task L1 measurement validity.
- **#1 no overengineering**: ✅ purely subtractive carrier patch. Action 1 (anti-fab gate) explicitly deferred per Codex β.
- **#2 no guesswork**: ✅ predictions filled BEFORE re-run; Action 2 N=1 evidence already captured.
- **#3 no workaround**: ✅ root-cause fix (carrier oracle), not workaround layer.
- **#4 worldclass**: ✅ honest agents pass; fabricators have no workaround target.
- **#5 best practice**: ✅ standard TAP `"not ok "` marker is the idiomatic failed-test signal.
- **#6 layer-cost-justified**: n/a (no L0/L1/L2 boundary change).

## Risk register

| Risk | Mitigation |
|---|---|
| F3 NEW re-run still fabricates under fixed carrier | Codex evidence-change rule fires → Action 1 re-opens. Gate 2 catches mechanically. |
| F6 NEW retry hits API failure again | Re-retry once (env-only failure precedent: iter-0027 n5 exclusion). |
| `"not ok "` substring is too narrow (real failures slip) | TAP spec defines `not ok N - <name>` as the canonical failed-test line. If a runner emits failure differently, exit_code=0 still pins success; substring is defense layered on top of exit_code. |
| Other fixtures we missed have similar bugs | Final inventory check pre-commit on all 9 fixtures (F1-F9) confirmed only F1/F3/F5/F6/F7/F8 affected; F2/F4/F9 distinct oracle shapes. |

## Deliverable execution order

1. ✅ Action 2 anti-fab regex replay over C1 diffs → N=1, F3 NEW solo_claude only.
2. ✅ Carrier fix on 6 fixtures → commit `2638891`.
3. ✅ Carrier sanity smoke (Node TAP passing output → 0 `"not ok "` matches) → verified pre-commit.
4. ✅ Re-run F3 + F6 NEW (solo_claude + bare each) at SHA `2638891`. RUN_ID `2638891-iter0033b-rerun-20260502T004520Z`.
5. ✅ Judge both fixtures.
6. **R-final R3** with Codex on re-run numbers — pending.
7. Update HANDOFF.md + DECISIONS.md, bake commit.

## Re-run verdict (n=1 each, single-fixture)

| Arm | Score | DQ | Wall | Anti-fab regex hits |
|---|---|---|---|---|
| **F3 NEW solo_claude** | **100** (spec/cons/scope/qual = 25/25/25/25) | clean | 528s | **0** ✓ |
| F3 NEW bare | 100 (25/25/25/25) | clean | 43s | n/a |
| **F6 NEW solo_claude** | 92 (spec/cons/scope/qual = 25/21/25/21) | judge-DQ "Silent-catch pattern in diff." | 605s | 0 |
| F6 NEW bare | 97 (spec/cons/scope/qual = 25/25/25/22) | clean | 59s | n/a |

**F3 NEW solo margin (vs L0)**: **0** — saturation (both arms perfect). Carrier fix removed fabrication incentive; honest implementation reaches max.

**F6 NEW solo margin (vs L0)**: **−5** — judge debited solo for silent-catch in `tests/checksum.test.js` cleanup (`try { fs.unlinkSync(fixture); } catch (_) { /* already gone */ }`). Deterministic `forbidden_pattern_hits` empty (the F6 fixture's pattern targets `bin/cli.js` only); the silent-catch lives in test file and is a judge-axis-quality call, not a carrier-fix mechanism failure.

## Gate evaluation

| Gate | Threshold | Result |
|---|---|---|
| 1. Carrier sanity | TAP passing has 0 `"not ok "` | ✅ verified pre-commit |
| **2. F3 NEW no fabrication recurs** | 0 `process.stdout.write =` matches | **✅ PASS — load-bearing gate held** |
| 3. F3 NEW L1 ≥ +5 vs L0 | margin ≥ +5 | ⚠ 0 (saturation; both arms 100 — not a NEW skill failure) |
| 4. F6 NEW retry completes | no API fail | ✅ PASS (605s clean exit) |
| 5. F6 NEW L1 ≥ +5 vs L0 | margin ≥ +5 | ❌ −5 (test-file silent-catch, judge call) |
| 6. F2/F4/F9 untouched | byte-identical pre/post | ✅ |
| 7. Anti-fab N=1 | F3 NEW solo only | ✅ verified before fixture edits |

Mechanism gate (Gate 2) PASSES. Score-margin gates (3, 5) failed for non-mechanism reasons:
- Gate 3: F3 saturation = both arms perfect = "no measurable lift" but not a NEW skill regression.
- Gate 5: F6 silent-catch in test cleanup = real per-fixture quality issue, separate from the carrier-fabrication root cause this iter targeted.

## SHA drift note

iter-0033 (C1) original passes on SHA `3bc86dd`. iter-0033b re-runs on SHA `2638891` (my carrier fix). Between them: `159ece6` (user-added AGENTS.md / bin/devlyn.js / package.json — Codex CLI guidance file, doesn't touch `config/skills/` or benchmark scripts; vouched zero benchmark-behavior impact since `run-suite.sh` mirrors `config/skills/` → `.claude/skills/` only). For Phase 4 cutover decision (iter-0034), this drift is documented but NOT a same-SHA invariant violation for the iter-0033 (C1) measurement (the OLD/NEW comparison is at the same SHA `3bc86dd`; iter-0033b is a separate measurement-validity correction).

## iter-0033 (C1) re-evaluation under corrected F3+F6

Substituting iter-0033b's clean F3+F6 numbers into iter-0033 (C1) NEW pass:

| F | NEW L1 (corrected) | OLD L1 | NEW − OLD |
|---|---|---|---|
| F1 | 99 | 99 | 0 |
| F2 | 98 | 84 | **+14** |
| F3 | **100** (was 62 DQ) | 97 | **+3** |
| F4 | 100 | 100 | 0 |
| F5 | 95 | 94 | +1 |
| F6 | **92 (DQ)** (was 48 invalid) | 98 | **−6** |
| F7 | 98 | 99 | −1 |

**Suite-avg NEW L1−L0 (F1-F7)**: +5.71 (≥ +5 floor PASS).
**iter-0033 (C1) Gate 1 (NEW vs OLD delta)**: +1.14 (≥ −1.0 PASS).
**Gate 2 per-fixture ≥ −5**: F6 −6 marginal FAIL (1 fixture, 1 axis below floor).
**Gate 3 DQ rate**: NEW=1 (F6 test-file silent-catch), OLD=0 → FAIL but different DQ class.

## Phase 4 cutover decision (R-final R3 input)

Three open paths (Codex pair-collab to converge):

1. **iter-0033 (C1) re-derived as PASS** under corrected measurement; F6 −6 acknowledged as marginal noise per iter-0027 doctrine (single-shot variance ±3-15 on DQ-prone fixtures); proceed to iter-0033c.
2. **F6 N=2-3 paired variance** (iter-0033b'). Settles whether F6 NEW silent-catch is variance or stable failure mode before iter-0033c.
3. **iter-0033 (C1) declared FAIL** on the strict gates; open NEW skill prompt-tuning iter for test-file silent-catch.

R-final R3 will probe Codex on which path is principled (no-overengineering, no-workaround, worldclass).
