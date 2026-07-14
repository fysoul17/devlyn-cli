# iter-0072 — changed-surface closure (quality axis): PRE-REGISTRATION (frozen 2026-07-14, three-way converged R0+R1)

Status: PRE-REGISTERED, NOT STARTED. No lever ships outside this
registration (user directive 2026-07-14). Archives (ephemeral):
/tmp/quality-round/{packet,r1-packet}.md + {codex,grok}-r{0,1}.log.

## Problem (measured)

nodeg-20260713: objective 7/7 PASS, blind quality 0/7 (codex judge 28/28
axes prefer frozen bare B), wall 0/7. Quality-omission class on saturated
rows: A ships the literal floor; B additionally closes the CHANGED
SURFACE — help/usage of the changed command (same authorized file),
error-path tests of the changed behavior, error text carrying the observed
value (F7), plus design-level closure (F25 catalog parse handling, all
matching promotions).

## Root cause (three-way converged, receipts)

Causal chain: free-form synthesis "when in doubt, narrower"
(free-form-mode.md:62) → criteria.generated.md narrows explicit goal
clauses (F25 "file-read failures" → --input only; F7 --help declared out
of scope) → PLAN EXCLUDES the closure work verbatim ("Refuse: touching
USAGE"; error-path regression test labeled "unrequested addition" — F7
plan.md:15,22; F25 plan.md:14,22 in the archived A-arm workspaces) →
IMPLEMENT obeys (implement.md:6,:35) → VERIFY grades against generated
criteria (verify.md:9), structurally cannot re-open. Always-loaded
anti-drift prose (CLAUDE.md:80,109,110,122; runtime-principles.md:25,54,55,
66-67; E1 = measured suppressor iter-0062) is the background field the
narrowing agent runs under — plausible co-cause, held for isolation.

## Decisive criterion (both engines, near-identical)

**Changed-Surface Coherence Is Requested; Cross-Surface Expansion Is
Drift** (Grok) ≡ **Frozen-Boundary Changed-Surface Closure** (Codex): an
addition is in scope only when it (a) preserves an explicit goal clause,
(b) updates an existing user-visible reference made stale by the named
change, or (c) regression-tests a specified success/failure path — all
inside the frozen file/behavior boundary. Other behaviors/files, drive-by
cleanup, speculative handlers for cases the change does not create remain
drift.

## Stage 1 (the only shipping lever until its falsifier resolves)

free-form-mode.md:62 (+ .claude/.agents mirrors), one-clause substitution:
- OLD: "every assumption scope-narrowing and reversible — when in doubt,
  narrower"
- NEW (candidate wording, final at build time): "every assumption
  reversible; narrow only unspecified behavior outside the named change —
  never an explicit clause, its existing user-visible references, or
  focused tests of specified success/failure paths"

Token caps: root/shared delta = 0; resolve load-set ≤ +0.1% (both gauge
approximations).

## Stage 2 (HELD; unlocks only per ladder branch 2)

L1 E1-sentence carve + L2 CLAUDE.md:122 completeness-bullet narrowing +
L3 edge-cases-created-by-this-change exception (CLAUDE.md:80 region) +
L4 implement.md:17 quality_bar expansion. Caps: always-loaded ≤ +6 lines
net across the three mirrors; L4 resolve-load ≤ +0.1%. Attribution caveat
(Codex R1): Stage-2 recovery attributes to the downstream composite, not
to any single sentence.

## Falsifier ladder (5 branches, frozen)

1. Stage-1 ARTIFACT predictions fail (regenerated F7 criteria/PLAN still
   exclude banner update + unsupported-format regression test, or F25
   criteria drop catalog failure clauses) → lever wording falsified; STOP;
   fresh pre-registration required; does NOT unlock Stage 2.
2. Artifacts open + objective 7/7 + quality floor FAILS (< 2/7 or F7/F25
   not both passing "no B_win on any axis from either judge") → Stage 2
   unlocks.
3. Stage 2 reruns identical gates (objective, quality, drift, compliance,
   stable-clean, token).
4. Artifacts open + quality ≥ floor → STOP, Stage 2 stays unshipped
   (subtractive-first).
5. Stage 2 also fails → next pre-registered locus: PLAN "simplest tactic"
   (implement.md:6), then VERIFY advisory-quality threshold. Never "more
   completeness prose".

## Merged gates (ship = ALL pass)

- Artifact predictions (branch-1 early kill, before any full re-measure).
- nodeg re-run, same 7 rows, same frozen B hashes (nodeg-verdict.json
  frozen_b_sources), same seats (sonnet orchestrator/judge + terra
  executor/judge), --pair-verify parity: objective stays 7/7; quality
  0/7 → ≥2/7 with F7+F25 mandatory; any timeout/objective loss = no-ship.
- Advisory (not gating): codex B_win 28/28 → ≤22/28 (style-match risk noted).
- Drift non-regression: violation-matrix N=4 within established flip
  bands; stable-clean B2/B5/DB-failing-adjacent-test stay 0/4; six-probe
  resolve-framed drift-bait hidden verifiers all pass.
- Compliance cells: 3 CLI × 2 size all pass (state, ordered phases, VERIFY
  evidence, archive, finish-gate).
- Token caps per stage (above).
- Wall axis explicitly OUT of this iter's success claim (iter-0071's
  mechanism).

## Sequencing note

Runs AFTER the iter-0071 nodeg re-measure (P1/P2'/P3' baseline capture) so
the two levers' effects don't confound: 0071 re-measure first (no 0072
edits in tree), then Stage 1 lands, then the 0072 nodeg run doubles as the
quality gate.
