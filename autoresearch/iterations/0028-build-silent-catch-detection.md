---
iter: "0028"
title: "BUILD-time silent-catch / forbidden-pattern detection — mechanical gate before EVAL"
status: implemented + R1 D1/D2/D3 fixes shipped (F2 N=5 paired acceptance pending)
type: mechanism (closes BUILD silent-catch DQ via fix-loop visibility, mirrors iter-0019.6 spec-verify pattern)
shipped_commit: 547d95a
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

## R-final (post F2 N=5 acceptance) — measurement-artifact discovery

Acceptance loop ran sequentially at commit `4f100bd`. Raw per-arm DQ (post-run scanner judgment, with `disqualifier` from `verify.json` propagated through `summary.json`):

| run | bare DQ | bare score | L1 DQ | L1 score | L2 DQ | L2 score | L2 timed_out |
|-----|---------|-----------|-------|----------|-------|----------|--------------|
| n1  | True    | 78        | False | 93       | False | 96       | False |
| n2  | True    | 77        | False | 93       | False | 99       | True |
| n3  | True    | 79        | False | 96       | False | 92       | True |
| n4  | True    | (skipped) | True  | 95       | MISSING | MISSING | MISSING |
| n5  | True    | 85        | True  | 91       | False | 97       | False |

L1 DQ rate **2/5 (40%)** → fails the +5-floor acceptance gate (`L1 DQ ≤ 1/5`). L1-vs-bare gap **60pp** → passes the categorical-vs-bare reframe (≥30pp). Initial reading: ambiguous outcome.

### Discovery (the load-bearing finding of R-final)

The F2 fixture forbidden-pattern regex was over-matching legitimate structured-error returns. The pattern at `expected.json:59` was:

```
catch\s*\([^)]*\)\s*\{[^}]*return\s+(\[\]|null|undefined|\{|false|'')
```

The `\{` branch matches **any** `return {` followed by anything, because `[^}]*` greedily traverses newlines. Running the actual scanner logic on every diff in iter-0027 N=5 (15 arm-runs) and iter-0028 N=5 (14 arm-runs, n4 variant missing) — total **29 arm-runs** — using a NARROW regex that flags only true silent values (`return\s+(null|undefined|''|false|\[\])`) gave **0 matches in all 29 runs**. Every "silent-catch DQ" we tracked across two iters was the broad regex flagging code of this shape:

```js
} catch (err) {
  if (err.code === 'ENOENT') {
    return {
      level: 'fail',
      message: `~/.claude not found: ${claudeDir}`,
    };
  }
  if (err.code === 'EACCES') {
    return { ... };
  }
  throw err;
}
```

This is **not** a silent catch. F2 spec.md:36 explicitly defines silent catch as `catch { return fallbackValue }` and demands errors be "visible to the user with actionable messages" — exactly what `return { level: 'fail', message }` provides. Other fixtures (F1, F3, F7) use a narrower regex (`null|undefined|''` only, no `\{` branch) and don't show this artifact; F4, F5, F6, F8, F9 don't use return-shape regex at all. F2 alone was the artifact source.

### Codex R-final pair-review (`/tmp/iter0028-rfinal-stdout.txt`)

Codex independently (R-final prompt did NOT include the 29/29 narrow=0 sweep — that was discovered after Codex was invoked) confirmed:

1. **R1**: Regex over-matches; `return { level: 'fail', message }` is structured error reporting, not silent fallback. Cited F2 spec.md:36, expected.json:59-63, n5 diff.patch:97.
2. **R2**: BUILD-time scanner did NOT effectively fire on the L1 DQ runs. Direct evidence from `/private/tmp/bench-...n4-...solo_claude/.devlyn/build_gate.log.md` line 27: `Carrier file '.devlyn/forbidden-patterns.json' not present — silent no-op`. n5 was worse: the staged skill mirror was pre-iter-0028, so `build-gate-verifiers.sh` never ran; only spec-verify-check.py ran (n5 archived `build_gate.log.md` confirms). The acceptance run never validly exercised iter-0028's mechanism.
3. **R3**: L2 0/4 DQ rate = generation-style avoidance of `catch { return { ... } }` shape under Codex BUILD pair, not proven scanner help. n=4 too small.
4. **R4**: Verdict **HOLD — partial restore + F2 regex fix + carrier-resilience fix + rerun**. Don't ship as-is, don't reject; fix the oracle and rerun under a valid measurement.

### Carrier-loss root cause (identified post-R-final)

Side-by-side `.devlyn/` content between variant n4 (mechanism worked) and solo_claude n4 (mechanism silent no-op):

- variant n4: `forbidden-patterns.json` 502 bytes timestamped 10:30 (original staging). Preserved through pipeline.
- solo_claude n4: `forbidden-patterns.json` ABSENT. `spec-verify.json` timestamped **10:55**, not 10:30 — meaning spec-verify-check.py self-staged (per its `## Verification`-block self-stage path) AFTER something wiped the original 10:30 staging. PHASE 0 PARSE in the L1 path is the suspected wiper.

spec-verify-check.py self-stages from `pipeline.state.json:source.spec_path` and survives the wipe. forbidden-pattern-check.py is **benchmark-agnostic by design** (does not read `expected.json` directly — Codex iter-0028 R0 verdict) and cannot self-recover. variant arm avoided this because (most likely) PHASE 0 PARSE in the Codex-pair path doesn't wipe `.devlyn/` the same way; needs a follow-up trace to confirm.

### Fixes shipped in this commit (R-final follow-up)

1. **F2 regex narrowed** (`fixtures/F2-cli-medium-subcommand/expected.json:59`):
   ```
   catch\s*\([^)]*\)\s*\{[^}]*return\s+(?:\[\]|null|undefined|false|''|\{\s*\})
   ```
   Replaces `\{` branch with `\{\s*\}` (empty object only). Switched to non-capturing group; description updated to call out structured returns explicitly. Smoke-tested: 8/8 positive cases (true silent catches) match, 5/5 negative cases (legitimate structured errors) don't match. Re-ran scanner on all iter-0028 N=5 diffs: every prior `YES` becomes `no`, every prior `no` stays `no`. Zero acceptance-run DQs would have fired under the corrected regex.

2. **Carrier resilience** — backup-and-restore against PHASE 0 wipe:
   - `run-fixture.sh:215`: stages `spec-verify.json` + `forbidden-patterns.json` to **both** `.devlyn/` (current path) AND `.devlyn-source/` (stable backup outside `.devlyn/`).
   - `build-gate-verifiers.sh:30-37`: at start, restores carriers from `.devlyn-source/` if missing in `.devlyn/`. Idempotent — never overwrites a fresher carrier.

3. **Loud-fail in bench mode** — `forbidden-pattern-check.py:167`: if `BENCH_WORKDIR` set AND carrier missing, exit 2 with explicit error. Real-user mode (no `BENCH_WORKDIR`) keeps silent no-op. Smoke-tested: bench mode exits 2, real-user mode exits 0.

### Why HOLD then partial restore (not full revert)

The 29/29 narrow=0 sweep argues iter-0028 mechanism is solving a non-problem (no LLM-generated silent catches occurred in any of our measurements). Subtractive-first principle would say: revert iter-0028.

But Codex R-final's R2 evidence shows **the mechanism never effectively ran** in the failing acceptance runs (carrier missing in n4, pre-wrapper mirror in n5). Reverting based on a measurement that didn't measure the thing is principle-#2 violation (no guesswork). The honest path: fix the oracle + carrier, rerun under valid measurement, then decide ship vs revert based on real signal.

### Acceptance reframed for F2 N=3 (this iter's true ship gate)

Pre-registered before A4 run starts:

- **Mechanism validity**: every L1/L2 BUILD_GATE invocation must include `bash .claude/skills/devlyn:auto-resolve/scripts/build-gate-verifiers.sh` per its log AND `forbidden-pattern-check.py` must execute with carrier present (visible in `build_gate.log.md`).
- **DQ rate**: bare DQ rate ≥ 2/3 OR L1 DQ rate ≤ 0/3 (categorical-vs-bare gap preserved). Specifically:
  - If bare drops to 0/3 too (likely outcome given the regex fix), conclude no real silent-catch problem exists; iter-0028 mechanism is not load-bearing for F2 → revert iter-0028 + keep regex fix in a follow-up commit.
  - If bare stays ≥ 2/3 with L1 < bare by ≥ 30pp, conclude iter-0028 mechanism prevents real silent-catches → keep iter-0028.
- **Clean-run F2 L1-bare margin** ≥ +5 (reporting only — not decisive after the +5 floor reframe).
- **Lint full pass** post-mirror.

If the run shows zero DQs across all 9 arm-runs (`bare 0/3, L1 0/3, L2 0/3`) the conclusion is the strongest possible "iter-0028 prevents nothing on F2" evidence, and revert is justified. But that's a measurement, not a guess.

### Codex R-final-2 trigger condition

Will fire after F2 N=3 completes, with the new evidence (the 29/29 sweep + carrier-resilience fix + actual N=3 results) in the prompt. Convergence target: clear ship-or-revert verdict on iter-0028 mechanism load-bearing-ness.

## R-final-2 (post-rerun convergence) — 2026-04-30

### Fresh F2 N=3 acceptance @ commit `e60092c` (regex narrow + carrier resilience + loud-fail)

| run | bare DQ | bare score | L1 DQ | L1 score | L2 DQ | L2 score | L1-bare | L2-bare |
|-----|---------|-----------|-------|----------|-------|----------|---------|---------|
| n1  | False   | 86        | False | 91       | False | 92       | +5      | +6      |
| n2  | False   | 82        | False | 90       | False | 97       | +8      | +15     |
| n3  | False*  | 76        | False | 96       | False | 99       | +20     | +23     |
| **mean** |     | **81.3**  |       | **92.3** |       | **96.0** | **+11.0** | **+14.7** |

(* n3 bare deterministic dq=False but **judge dq_judge=True** for semantic silent-catch — see falsification R1 below.)

`disqualifier` column = deterministic post-run scanner verdict. The narrow regex caught zero false positives across all 9 arm-runs (vs 7+ broad-regex artifacts in iter-0028 N=5).

**Cumulative narrow-regex sweep across iter-0027 N=5 + iter-0028 N=5 + iter-0028 R-final N=3 = 38 arm-runs total. Narrow regex matches = 0/38. `@ts-ignore` matches = 0/38.**

### Codex R-final-2 (`/tmp/iter0028-rfinal2-stdout.txt`)

Verdict: **Partial revert. Revert the iter-0028 forbidden-pattern BUILD_GATE mechanism. Keep F2 regex narrow.**

Critical pushback on my "silent-catch is a non-problem" claim:

> Fresh n3 has a **judge semantic DQ** on bare. Judge reason: "The recursive skill walker catches readdirSync errors and returns without surfacing non-EACCES failures." Verified at `bare/diff.patch:126`:
> ```js
> } catch (e) {
>   if (e.code === 'EACCES' && !permError) { permError = { path: dir }; }
>   return;
> }
> ```
> The deterministic regex did not catch this (returns plain `return;`, not `return null/{}/...`). Judge caught it semantically.

So the corrected framing is: **the configured deterministic regex is not load-bearing on F2** (because the silent-catches that DO occur are semantic, not the literal-fallback shape the regex looks for). The regex-based mechanism iter-0028 ships fundamentally cannot detect semantic silent-catches — that requires a judge or LLM-pass evaluator, which the post-EVAL judge already provides.

Falsification answers (Codex):
- **R1**: 0/38 narrow hits insufficient to declare silent-catch a non-problem; sufficient to say the configured regex rarely fires. Real silent-catches DO happen but in shapes the regex misses.
- **R2**: My real-user cost estimate was too low. Wrapper invocation in SKILL.md prompt + always-runs-both-checkers in build-gate-verifiers.sh = runtime + prompt + maintenance + failure-surface cost. Subtractive-first defaults to revert when no load-bearing hit observed AND known scope holes.
- **R3**: 0 `@ts-ignore` hits across all 38 F2 diffs (verified). Mechanism not secretly load-bearing on the second pattern either.
- **R4**: HANDOFF should say "iter-0028 closed as measurement correction, regex narrowed; mechanism reverted as not proven load-bearing; iter-0029 = shadow-suite v0".

### Convergence — what ships at this commit (e60092c → revert commit)

**KEEP** (real bug fix, retained):
- `benchmark/auto-resolve/fixtures/F2-cli-medium-subcommand/expected.json` — narrowed regex `(?:\[\]|null|undefined|false|''|\{\s*\})`. Still distinguishes literal silent-fallbacks from structured error returns. Smoke-tested 8/8 positive + 5/5 negative.

**REVERT** (mechanism not load-bearing, demoted):
- `config/skills/devlyn:auto-resolve/scripts/forbidden-pattern-check.py` — deleted.
- `config/skills/devlyn:auto-resolve/scripts/build-gate-verifiers.sh` — deleted.
- `config/skills/devlyn:auto-resolve/SKILL.md` — wrapper invocation reverted to direct `spec-verify-check.py` call (same as pre-iter-0028).
- `config/skills/devlyn:auto-resolve/references/build-gate.md` — Auxiliary Verifiers section reverted to spec-verify-only.
- `benchmark/auto-resolve/scripts/run-fixture.sh` — `forbidden-patterns.json` staging removed; `.devlyn-source/` backup removed (spec-verify-check.py self-stages already, the resilience layer was load-bearing only for the now-removed forbidden-pattern carrier).
- `scripts/lint-skills.sh` — Check 6 mirror-parity entries for forbidden-pattern-check.py + build-gate-verifiers.sh removed; executable-bit check for build-gate-verifiers.sh removed.

Net diff at the revert commit: **466 deletions, 12 insertions.** Subtractive-first honored.

### What this iteration empirically established (lessons for the next session)

1. **Fixture regex correctness is itself a measurement axis.** The F2 broad-regex `\{` branch contaminated iter-0027's `L1 60% silent-catch DQ` reading, which drove iter-0028 design. Future iters should validate fixture oracle shape before treating its output as a quality signal — open the regex, compute matches on a known-good diff, confirm it discriminates intended vs unintended.

2. **Deterministic regex gates and semantic LLM-judge verdicts are different layers.** The judge catches what the regex can't (semantic silent-catch shape `return;` after dropping non-EACCES). For iter-0029+ work that needs to surface failure modes mid-build, a semantic check must be built; a regex check covers a narrow slice and can have known holes.

3. **Subtractive-first applies to mechanisms-that-don't-fire.** A mechanism that doesn't catch real failures within the measurement window is debt regardless of LOC count. iter-0028 mechanism = 281+91+~50 LOC + Agent prompt cost + carrier protocol + lint footprint, all for unobserved-failure-mode protection.

4. **Carrier loss under PHASE 0 is real but decoupled from this iter.** spec-verify-check.py self-stages and survives. The deeper "PHASE 0 PARSE wipes L1 .devlyn/ but not L2 .devlyn/" trace is a follow-up filing, not a blocker for iter-0028 close-out (the carrier-resilience layer added in e60092c is reverted along with the forbidden-pattern mechanism since the only file that needed it is removed).

### Status: iter-0028 CLOSED — measurement correction shipped, mechanism reverted.

Next session: iter-0029 = shadow-suite v0 per HANDOFF L251-260. Cross-fixture variance (F3/F9) sequenced after, not as the immediate next move.
