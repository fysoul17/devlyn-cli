---
iter: "0033b'"
title: "iter-0033b' — F6 NEW N=3 paired variance (Phase 4 HOLD adjudication)"
status: PROPOSED
type: variance-measurement (Path B per Codex R3)
shipped_commit: TBD
date: 2026-05-02
mission: 1
parent: iter-0033b
codex_pair: R-final R3 (249s, xhigh) — converged Path B; pre-registered exit criteria
---

# iter-0033b' — F6 NEW paired variance (Path B)

## Why this iter exists (PRINCIPLES.md pre-flight 0)

iter-0033b validated the carrier-fix mechanism (Gate 2 PASS, no fabrication recurs). After substituting the corrected F3 + F6 numbers into iter-0033 (C1):

- Gate 1 (suite-avg ≥ −1.0): PASS (+1.14)
- Gate 2 (per-fixture ≥ −5): **FAIL on F6 (−6, marginal)**
- Gate 3 (DQ rate): **FAIL** — NEW=1 (F6 judge-DQ for `try { fs.unlinkSync(fixture); } catch (_) { /* already gone */ }` in `tests/checksum.test.js`), OLD=0
- NORTH-STAR test #1 + RUBRIC.md:69: **≥7 of 9 fixtures with margin ≥+5** — currently 4/7 (F2/F3/F4/F5). Suite-avg PASS does not satisfy this hard floor.

iter-0033 (C1) FAILS strict gates under corrected measurement. Phase 4 cutover blocked. iter-0033c deferred. The remaining open question is **whether F6 NEW silent-catch judge-DQ is single-shot variance (per iter-0027 N=4 doctrine ±3-15) or stable failure mode**.

This iter exists to answer that question with paired variance, not to chase scores.

## Mission 1 service (PRINCIPLES.md #7)

L1 measurement validity. Whether F6 NEW silent-catch is variance or stable directly determines:
- Phase 4 cutover go/no-go.
- iter-0033c (NEW L2 vs NEW L1) sequencing.
- Whether iter-0033c'-style architectural iter (VERIFY MECHANICAL test-diff silent-catch scan) is needed.

PRINCIPLES.md #0 test: this iter changes shipping behavior + routing policy. NOT score-chasing per Codex R3 cite.

## Codex pair-collab trail

- **R1** (328s): recommend carrier fix + 12-pattern anti-fab gate. α.
- **R2** (348s): conceded β — anti-fab gate at N=1 violates #1 + Subtractive-first + defense-in-depth-rejection. Action 1 deferred to N≥2 evidence.
- **R3** (249s): Path B converged. Both: Path A defeated by NORTH-STAR ≥7/9 floor; Path C blocked at N=1 (#1 speculative bullet); Path B is principled ONLY if pre-registered with strict exit rules.

Convergence reached. No R4 needed.

## Hypothesis

The F6 NEW solo silent-catch DQ in iter-0033b retry is **either** (i) single-shot variance similar to iter-0027 F2 (DQ rate 50% N=4) or (ii) stable per-fixture failure mode driven by NEW skill's IMPLEMENT/VERIFY phase missing test-file silent-catch hygiene.

**Falsifiable predictions (BEFORE re-runs)**:

iter-0027 F2 baseline: DQ rate 50% across N=4 paired runs (silent-catch in `bin/cli.js` source, similar pattern). If F6 NEW is variance-equivalent: ~50% probability of clean run.

- **Predicted**: 1-2 of additional 2 runs hit silent-catch DQ (variance hypothesis); 0-1 hit (lucky), 2 hit (stable).

## Pre-registered adjudication rules (Codex R3 verbatim)

**Setup**: 2 additional F6 NEW solo + bare runs, same SHA `2638891`. Total N=3 (1 from iter-0033b retry + 2 here). Bare arm re-run paired for environmental control.

**Exit criteria (decided BEFORE results)**:

| Outcome | Adjudication | Phase 4 |
|---|---|---|
| **Both additional NEW solo runs clean (no DQ)** | F6 silent-catch = single-shot tail variance. iter-0033 (C1) gate marked **"PASS via variance adjudication"** (NOT just PASS — variance-stamped). Proceed to iter-0033c. | UNBLOCKED (still gated by iter-0033c PASS) |
| **1 additional DQ** | F6 = recurring (≥40% DQ rate per N=3). Phase 4 HOLD. Open root-cause iter (likely VERIFY MECHANICAL test-diff silent-catch scan, the architectural gap Codex R3 §3 flagged at `verify.md:20`). | BLOCKED |
| **2 additional DQs** | F6 = stable failure on NEW skill. Phase 4 HOLD. Architectural fix mandatory. | BLOCKED |
| **API/socket/zero-file invalid** | 1 replacement run allowed. Beyond that = environmental signal to escalate. | n/a |

**Stopping rule (anti-score-chase)**: AT MOST 2 additional NEW solo runs (3 if one invalid). NO further runs to "improve the number." Adjudication is mechanical per the table above.

## Scope (locked)

### Ships in this iter

1. **2 paired F6 runs** at SHA `2638891`:
   - F6 NEW solo_claude × 2
   - F6 NEW bare × 2 (paired control — accounts for environmental drift)
2. **Per-run anti-fab regex check** on each NEW solo diff (still N=1 evidence so far).
3. **Adjudication** per the table above. Output: this iter file's verdict block.
4. **HANDOFF + DECISIONS update** with iter-0033 (C1) final status.

### Does NOT ship in this iter

- Any skill-prompt change (Path C deferred per Codex R3).
- Any fixture change (carrier fix already shipped in iter-0033b).
- VERIFY MECHANICAL architectural fix (deferred unless adjudication points to it).
- iter-0033c. iter-0034. Both gated.

## Acceptance gate (pre-registered)

| Gate | Threshold | Source |
|---|---|---|
| 1. Both additional runs complete (no API failure) | `invoke_failure == false`, `timed_out == false` on both NEW solo runs | iter-0027 invalid-run precedent |
| 2. Anti-fab regex N=1 holds | 0 fabrication-pattern matches across the 2 new diffs | iter-0033b Gate 2 mirror |
| 3. DQ rate adjudication | per the table above | Codex R3 verbatim |
| 4. iter-0033 (C1) gate disposition | "PASS via variance adjudication" (clean) OR "FAIL recurring F6" (any DQ) — recorded explicitly | NORTH-STAR test #1 honesty |

All 4 must be evaluated honestly. Gate 4 decides Phase 4 cutover unlock.

## Phase 4 + iter-0033c sequencing

iter-0033c remains DEFERRED until iter-0033b' adjudicates. Possible paths:

- **Both clean**: iter-0033 (C1) PASS via variance adjudication → iter-0033c proceeds → iter-0034 cutover gated as originally designed.
- **Any DQ**: iter-0033 (C1) FAIL on F6 → root-cause iter opens (likely VERIFY MECHANICAL gap fix) → that ships, F6 measured again, then iter-0033c reconsidered.

## Risk register

| Risk | Mitigation |
|---|---|
| Both runs DQ → easy adjudication but bad news | That IS the signal we need; root-cause iter is principled (architectural gap exists). |
| 1 DQ + 1 clean → ambiguous | Codex rule: "1 additional DQ → recurring." This is by-design strict. Don't soften the rule mid-iter. |
| Both clean but next 5 fixtures regress on iter-0033c | Outside this iter scope. iter-0033c is a separate measurement. |
| API failures recur | F6 was the API-fail site once already. If it happens again here, that's environmental signal to escalate. |
| User wants Path A retroactively | NORTH-STAR + RUBRIC explicit "≥7/9" rule blocks; would require explicit NORTH-STAR amendment to ship Phase 4 with current data. |

## Principles check

- **#0 pre-flight**: ✅ changes shipping behavior (Phase 4 ship/hold).
- **#7 mission-bound**: ✅ Mission 1 single-task L1 measurement validity.
- **#1 no overengineering**: ✅ smallest-possible scope (2 runs, no code changes).
- **#2 no guesswork**: ✅ predictions + exit criteria pre-registered.
- **#3 no workaround**: ✅ measurement, not fix.
- **#4 worldclass**: ✅ honest "≥7/9" floor adjudication.
- **#5 best practice**: n/a (no skill change).

## Deliverable execution order

1. Commit this iter file.
2. Run F6 NEW solo + bare × 2 (paired) at SHA `2638891`. ~30-40min total.
3. Judge both fixtures.
4. Adjudicate per the table above. Update this iter file's verdict block.
5. Update HANDOFF + DECISIONS with iter-0033 (C1) terminal disposition.
6. If clean: file iter-0033c execution iter. If DQ: file root-cause iter.

## Verdict block (filled post-adjudication)

[Pending — populated after re-runs + judge]
