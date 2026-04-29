---
iter: "0028"
title: "BUILD-time silent-catch / forbidden-pattern detection — mechanical gate before EVAL"
status: implemented + R1 D1/D2/D3 fixes shipped (F2 N=5 paired acceptance pending)
type: mechanism (closes BUILD silent-catch DQ via fix-loop visibility, mirrors iter-0019.6 spec-verify pattern)
shipped_commit: TBD (will be baked in after acceptance)
date: 2026-04-30
mission: 1
---

# iter-0028 — BUILD-time silent-catch detection

## Why this iter exists (PRINCIPLES.md pre-flight 0)

iter-0027 N=5 paired variance on F2 measured **L1 silent-catch DQ rate 2/5 (40%)** at the same git baseline (`b06fffd`), same engine (Claude solo), same prompt. n2 hit `catch-return fallback` (`catch (e) { return null }`); n4 hit `catch returning an object` (`catch (e) { return {} }`). Two distinct silent-catch sites in two of five fresh runs — not noise, structural BUILD failure mode.

The runtime-principle prose at `config/skills/devlyn:auto-resolve/references/phases/phase-1-build.md:61-67` ("no silent catch / `@ts-ignore` / hardcoded workaround") is empirically not preventing the violation. Same prompt-only-dead-end pattern as iter-0008 (engine constraint) and iter-0019.6 (spec-literal verification). The fix is not "stronger prose" but "mechanical fix-loop signal."

**Decision this iter unlocks**: whether BUILD-time mechanical forbidden-pattern enforcement (with the violation routed back to BUILD via fix-loop) drops L1 silent-catch DQ rate from 40% (2/5) to ≤ 1/5 (Codex R0 pre-registered acceptance gate). If yes → iter-0029 expands cross-fixture (F3 N=3 + F9 N=3 + shadow-suite v0). If no → escalate to Candidate C (pre-EVAL CRITIC) in iter-0029.

## Mission 1 service (PRINCIPLES.md #7)

Single-task L1 quality on F2. No Mission 2/3 surface. Mission 1 hard NO list (HANDOFF L271-282) untouched: no worktree, no parallel, no lease, no run-scoped state migration, no team coordination beyond pipeline.state.json.

## Hypothesis (pre-registered before R0; reframed per Codex R0 verdict)

**Mechanical hypothesis**: A BUILD_GATE-phase regex scanner that flags `disqualifier`-severity forbidden patterns introduced in this build's diff, then routes the finding back to BUILD via the existing fix-loop, will drop L1 silent-catch DQ rate from 40% (iter-0027 N=5) to ≤ 20% (≤ 1/5 in iter-0028 acceptance N=5).

**Falsifiable prediction (categorical reliability gate, per user 2026-04-30 reframe)**: At iter-0028 commit, F2 N=5 paired valid will satisfy ALL of:
1. L1 silent-catch DQ rate ≤ 1/5 absolute.
2. Zero scanner-miss silent-catch DQs (any DQ that occurs MUST be one the scanner caught and the fix-loop failed to clear, OR a regex-hole variant the current pattern set doesn't cover — the latter is honest scope-limit, not failure of the mechanism).
3. L1 DQ rate < bare DQ rate by ≥ 30 percentage points (the categorical-vs-bare signal — the real Mission 1 quality gate per user direction).
4. Clean-run F2 L1-L0 mean ≥ +10 (sanity check that the new gate doesn't regress quality on already-clean runs).

If all four pass → mechanism shipped, iter-0029 unblocked. If (1) fails → mechanism is wrong layer; pivot to Candidate C in iter-0029.

## Codex pair-review (R0 — done; convergence reached)

Single round. Verdict: **Conditional Go on Candidate B-minus** (narrowed from our pre-R0 Candidate B+).

Five falsification asks were sent. Verdicts (full text in this file's `## Codex R0 transcript` appendix below):

| Ask | Codex verdict | Adopted |
|---|---|---|
| F1: regex won't catch enough variants | **Partial hold** — current regex covers `[]\|null\|undefined\|{\|false\|''` but not `return 0`. Gate is "scanner caught what it claimed to catch", not "scanner caught all possible silent-catches." | YES — acceptance criterion (2) reflects this: "zero scanner-miss" not "zero DQ." Honest gate. |
| F2: real-user default policy is overreach | **Holds** — pure addition with no measurement, Subtractive-first violation. | YES — `_shared/forbidden-patterns.default.json` REMOVED from iter-0028 scope; deferred to a future iter with drift parity + false-positive acceptance. |
| F3: wrong layer (BUILD_GATE vs new phase) | **Wrong** — BUILD_GATE already hosts mechanical correctness checks (spec-verify-check.py:correctness.spec-literal-mismatch); separate phase is overengineering with no demonstrated benefit. | YES — kept in BUILD_GATE. |
| F4: N=3 ≤ 1/3 too lenient | **Holds** — HANDOFF itself says "0/3 or close"; ≤ 1/3 is barely below current 40%. | YES — gate tightened to N=5, ≤ 1/5. |
| F5: defaults file content drift | **Holds** (moot since F2 dropped the file) — if it ever lands later, semantic drift parity required, not just JSON shape lint. | YES — deferred entirely with this constraint recorded. |

Codex also flagged two implementation details we missed: **don't read `expected.json` directly from the script** (stage `.devlyn/forbidden-patterns.json` via `run-fixture.sh`, mirroring spec-verify staging), and **preserve severity** (only `disqualifier` → CRITICAL/blocking; `warning`-severity patterns like F6's `npm install --no-save` advisory must NOT become CRITICAL or F6 regresses).

**Convergence reached after R0**. No R1 design round needed; jumping to R1 = diff review post-implementation.

## Method

### Implementation (Candidate B-minus)

Five touchpoints, all under PRINCIPLES.md #1 (smallest change that closes the hypothesis):

1. **NEW**: `config/skills/devlyn:auto-resolve/scripts/forbidden-pattern-check.py` (~250 LOC).
   - Reads `.devlyn/forbidden-patterns.json` carrier.
   - Scans unified diff (`git diff HEAD`) sliced to per-pattern allowlisted files.
   - Emits CRITICAL `correctness.silent-catch-introduced` (catch-pattern) or `correctness.forbidden-pattern-introduced` (other) for each `disqualifier`-severity hit; `warning`-severity recorded but non-blocking.
   - Real-user mode (no carrier) = silent no-op. Malformed carrier / invalid regex = exit 2.
   - 6 edge-case smoke tests passed pre-commit: clean diff, warning-only, no carrier, malformed JSON, bad regex, file-scope mismatch.

2. **EDIT**: `benchmark/auto-resolve/scripts/run-fixture.sh` (~12 LOC change in the existing spec-verify staging block).
   - Stages `.devlyn/forbidden-patterns.json` from `expected.json:forbidden_patterns` alongside `.devlyn/spec-verify.json`. Same staging contract; skill scripts stay benchmark-agnostic.

3. **EDIT**: `config/skills/devlyn:auto-resolve/references/build-gate.md` (~25 lines added under new "## Forbidden-pattern check (iter-0028)" section).
   - Documents the script, carrier shape, severity preservation, merge step, and the iter-0027 lesson it closes.

4. **EDIT**: `config/skills/devlyn:auto-resolve/SKILL.md:122` (BUILD_GATE phase prompt).
   - Extends the spawn-Agent prompt to invoke `forbidden-pattern-check.py` after `spec-verify-check.py`, with explicit fail-routing language ("exit 1 → BUILD_GATE verdict FAIL → fix-loop reruns BUILD with the violation visible").

5. **EDIT**: `scripts/lint-skills.sh` Check 6 mirror list — add new script path so source ↔ installed parity is enforced for the new file.

Mirror sync: `cp` the two new/edited files into `.claude/skills/...` (devlyn-cli pattern; iter-0007 auto-mirror in `run-suite.sh:33-72` will also catch this on the next variant arm spin-up).

### Acceptance run

F2 N=5 paired (bare + L1 + L2 arms) at iter-0028 ship commit. Apply iter-0027 invalid rule (HANDOFF L233): replace any sample with `files_changed=0` until N=5 valid pairs collected.

Per-run capture mandatory: `verify.json:forbidden_pattern_hits` (post-run scanner — independent oracle of whether silent-catch shipped) AND `forbidden-pattern-findings.jsonl` (BUILD-time scanner — proves the gate fired). Cross-tabulate to compute "scanner-miss DQ count" (post-run hits NOT seen by BUILD-time scanner — those are the regex-hole cases acceptance criterion (2) tracks).

Two Codex rounds planned for the run: R1 (diff review pre-measurement), R-final (post-measurement interpretation, especially if results surprise). Convergence is the stop, not "Codex agreed" (per `feedback_codex_collaboration_not_consult.md`).

## Hard NO list for this iter

- ❌ NO `_shared/forbidden-patterns.default.json` (Codex R0 F2 — defer).
- ❌ NO judge.sh / RUBRIC.md / judge-prompt.txt change (binding freeze).
- ❌ NO new fixture.
- ❌ NO multi-agent coordination beyond pipeline.state.json.
- ❌ NO ideate / preflight / team-* default change.
- ❌ NO Mission 2 surface touch.
- ❌ NO "while I'm here" cleanup of unrelated code paths (Goal-locked execution).
- ❌ NO change to `--engine claude` runtime default.

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Regex hole (`return 0` etc) — fix-loop never sees the DQ-causing line | Acceptance criterion (2) makes this an explicit honest gate. If scanner misses dominate, iter-0029 = pattern-set extension, not iter-0028 retry. |
| F6 / other warning-severity patterns become blocking → cross-fixture regression | Severity preservation explicit in script (line ~190); Codex R0 F5 caveat. F6 expected.json has 1 warning-severity entry that MUST stay non-blocking. |
| Fix-loop never converges — model sees finding, makes "fix" that re-introduces the pattern in different shape, infinite loop | Existing fix-loop already has round budget (`state.route.fix_round` cap in pipeline-state.md:154-163). iter-0028 inherits that cap; nothing new needed. |
| Real-user runs without `.devlyn/forbidden-patterns.json` accidentally fire the gate | Script silent no-op when carrier absent (smoke edge3 confirmed). Real-user surface unchanged this iter. |

## Lint state

`bash scripts/lint-skills.sh` clean post-changes (Check 1-13 all PASS). Check 6 mirror list extended; new script present in both source and installed trees (verified via `diff -q`).

## Next iter sequence (only if iter-0028 acceptance passes)

Per HANDOFF L251-269 (Codex 2026-04-30 deep R0):

- **iter-0029** = shadow-suite v0 (6 tasks, 1 per failure-class) AND F3 N=3 + F9 N=3 paired re-runs on golden suite. Cross-fixture confirmation that the bare-vs-L1 categorical gap holds beyond F2.
- **iter-0030** = shadow-suite v1 (18 tasks).
- **iter-0031** = shadow-suite decision-grade (30 tasks; 8-condition trust rule applies).
- **iter-0032** = ship-gate language reframe (+5 absolute floor → categorical-vs-bare gap).

## Codex R0 transcript

Stored at `/tmp/iter0028-r0-output.txt` at write time (transient — captured here for the iter-file record). Verdict: **Conditional Go**. Counter-proposal: **Candidate B-minus**. Five hard acceptance criteria adopted into this iter's `## Hypothesis` section (translated 1:1 from Codex's "4. Hard Acceptance Criteria" block).

## Codex R1 transcript + fixes

R1 verdict: **No Go as-staged** — three real findings forced rework before any acceptance run.

| Finding | Codex evidence | Fix shipped |
|---|---|---|
| **D1** (real bug) | `forbidden-pattern-check.py` used `git diff HEAD`. Auto-resolve commits with `git add -A && git commit -m "...build complete"` at SKILL.md:113-117 BEFORE BUILD_GATE runs, so HEAD already includes BUILD's changes → diff is empty → scanner silently disabled. run-fixture.sh:308-311 already captures `SCAFFOLD_SHA` for exactly this case (post-run scanner uses it). | Script now honors `DEVLYN_DIFF_BASE_SHA` env var (fallback to `HEAD`). run-fixture.sh:391-396 exports `DEVLYN_DIFF_BASE_SHA="$SCAFFOLD_SHA"`. Verified by smoke test: without env var → exit 0 / 0 findings (bug reproduced); with env var → exit 1 / 1 finding (`correctness.silent-catch-introduced`). |
| **D2** (low blast radius) | `classify_rule_id` matched `description + ("catch" in pattern)`. F2 fine, but future fixtures with non-silent catch-mentioning patterns would mislabel. | Classification is now description-only (`SILENT_CATCH_HINT` regex covers `silent[-_ ]?catch \| empty[-_ ]?catch \| swallow…`). |
| **D3** (real risk) | spec-verify + forbidden-pattern findings merge onto `build_gate.findings.jsonl` was natural-language Agent instruction. Same prompt-only-dead-end pattern as iter-0008, iter-0019.6. If Agent forgets, fix-loop visibility dies silently. | NEW `build-gate-verifiers.sh` wrapper (52 LOC bash). Always runs both checkers, appends both findings files, propagates worst exit. SKILL.md:122 simplified to invoke wrapper. lint Check 6 mirror list extended; executable-bit check added. End-to-end smoke verified: pre-wrapper Agent gate findings preserved, two verifier findings appended, wrapper exit propagates correctly. |

D4 (acceptance gate criterion 3 trivially satisfied) and D5 (use historical baseline) were dismissed as wrong by Codex — current acceptance gate is correct, current tip is the right ship-candidate baseline.

R1 acceptance smoke (Codex checklist 3+4) all 3 tests pass at this iter's commit:
1. Lint full pass (Check 1-13).
2. Mirror parity clean across 4 mirrored files (`SKILL.md`, `build-gate.md`, `forbidden-pattern-check.py`, `build-gate-verifiers.sh`).
3. Committed-silent-catch smoke: post-BUILD-commit scenario, `DEVLYN_DIFF_BASE_SHA=baseline` → wrapper exit 1, `correctness.silent-catch-introduced` finding merged into `build_gate.findings.jsonl` alongside Agent's own gate findings.

Convergence reached at R1. Acceptance run (F2 N=5 paired) is next; R-final pair-review fires on the result interpretation.
