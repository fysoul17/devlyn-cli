# 0002 — Fixture spec annotation: DOCS lifecycle status flip is not a scope violation

**Status**: SHIPPED (F6 confirmed; F7 invalidated by codex MCP race, queued as iter 0003)
**Started**: 2026-04-25
**Decided**: 2026-04-25

## Hypothesis

F6 and F7 regressed in iteration 0001 (v3.7-final) because each fixture's spec.md `## Constraints` section says "only touch X" but the harness's DOCS phase Job 1 legitimately flips the spec's own frontmatter status. The judge correctly enforced the spec text; the spec text was missing the lifecycle disclaimer. Adding a one-line "lifecycle note" to each affected fixture's Constraints section will recover F6/F7 margins to ≥+5 without changing skill behavior.

## Mechanism

Why-chain:
1. Why did F6/F7 score Scope penalty? → Judge saw `docs/roadmap/phase-1/<fixture>.md` modified.
2. Why was that file modified? → DOCS Job 1 flipped `status: planned → done` after implementation.
3. Why did the judge consider that out of scope? → Spec said "only touch bin/cli.js and tests/cli.test.js" with no carve-out for harness lifecycle bookkeeping.
4. Why didn't the spec carve it out? → Spec author wrote constraints for *implementation*; harness lifecycle wasn't in their model.
5. Root: spec contract is missing a clause that documents legitimate harness-lifecycle behavior. Fix at level 5: add the clause.

The asymmetry test: bare arm has no DOCS phase, so bare never triggers this. A penalty that fires only against the variant for doing correct lifecycle work is measuring the wrong thing. Per codex 5.5 round 1: "fix the spec" — confirmed B (benchmark-mode flag) and C (rubric tweak) both rejected.

## Predicted change

- F6 margin: −3 → ≥+5 (recovery into ship-eligible territory).
- F7 margin: −12 → ≥+5 (same root cause, larger swing because F7 is a stricter "out-of-scope-trap" fixture).
- No other fixture moves materially (annotation is judge-prose, not behavior).
- No wall-time change.

## Diff plan

One commit (`695050a`): a single bullet inserted in each of 8 fixtures' `## Constraints` sections. F8 not affected (no docs/roadmap touch in its v3.7-final result). The bullet:

> *Lifecycle note: the harness's DOCS phase flips this spec's frontmatter `status` after implementation completes — that is benchmark lifecycle bookkeeping, not a scope violation.*

## Principles check

| # | Principle | Status | Evidence |
|---|---|---|---|
| 1 | No overengineering | ✅ | One bullet × 8 fixtures = 8 line edits. Surgical. |
| 2 | No guesswork | ✅ | Predictions made and recorded before re-run. |
| 3 | No workaround | ✅ | Fix lands at the spec-contract level (root cause), not at scoring or skill behavior. |
| 4 | Worldclass production-ready | ✅ | F6 variant: 91 → 98 score; zero CRITICAL/HIGH findings. |
| 5 | Best practice | ✅ | Zero MEDIUM unidiomatic-pattern findings. |

## Actual change

F6+F7 subset re-run (label `v3.7-fix-f6f7`):

| Fixture | v3.7-final | v3.7-fix-f6f7 | Δ | Status |
|---|---|---|---|---|
| F6-dep-audit | -3 | **+7** | **+10** | ✅ Recovery as predicted (variant 91 → 98) |
| F7-out-of-scope-trap | -12 | -27 | -15 | ❌ INVALIDATED — codex MCP race hung the variant arm pre-session-init for 55 min; killed by operator; resulting partial diff scored 67 (50% verify). Not a real regression — measurement failure. |

Wall times:
- F6 variant: 1400s (23 min) — slower than v3.7-final's 297s but still in normal range.
- F7 variant: 3623s elapsed before kill, 0 work done.

Oracle findings (post-annotation, F6 final state):
- scope-tier-a: 0 (was 1 in v3.7-final; spec file now exempt via auto-exempt added in `f2ec62f`)
- scope-tier-b: 1 (README still flagged — leftover from prior DOCS Job 2 wider behavior; not addressed by annotation)

## Lessons

1. **Spec annotation works.** F6's +10-margin swing on a one-line spec edit is a clean signal that the judge reads spec prose seriously and updating the contract there is the right surface for benchmark-design-bug fixes.

2. **F7 surfaced a different bug.** The 55-min stall pre-session-init was caught only because we were watching this run closely. codex 5.5 attributed it to MCP-server-init race against lingering `codex-mcp-server` processes from earlier sessions. Diagnostic evidence supported this:
   - All codex processes `STAT=S/Ss`, 0% CPU sustained for 54 min.
   - No rollout file in `~/.codex/sessions/2026/04/25/` for this codex invocation.
   - `/dev/fd` of codex node showed only stdin (TTY) and stdout (pipe). No network connections.
   - Standalone codex calls during the same window worked fine.
   - Conclusion: codex CLI stuck during local startup, before MCP handshake completed.

3. **Mitigation for F7 is harness-side.** The right next iteration is to wrap each codex invocation in a wall-clock timeout with explicit BLOCKED verdict on timeout. codex 5.5 supplied a `sleep + kill` watchdog pattern that doesn't require coreutils. Queued as iteration 0003.

4. **Don't trust a measurement when the harness misbehaves.** F7's -27 number is meaningless. Iteration files should distinguish a real-data result (F6 +7) from an instrumentation-failure result (F7 −27, invalidated). DECISIONS.md log already calls this out.

## Decision

ACCEPT (partial). F6 recovery confirmed. F7 invalidated by separate harness bug; the annotation itself is correct, the test was contaminated. Append F7 retry to "Next hypotheses" downstream of the MCP-race timeout fix (iteration 0003) — once the timeout fix lands, re-run F7 alone and confirm margin ≥ +5.

Baseline frozen as `baselines/v3.7-fix-f6f7.json` for the F6 dimension; v3.7-final remains the authoritative baseline for the other 8 fixtures.
