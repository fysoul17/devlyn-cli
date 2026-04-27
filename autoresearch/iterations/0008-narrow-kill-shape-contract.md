# 0008 — Narrow kill-shape execution contract (orphaned-bg + unobserved-fg ban)

**Status**: REJECTED — F6 single-fixture catastrophic collapse, REVERT pending user authorization
**Started**: 2026-04-26
**Decided**: (not yet)

## Hypothesis

iter-0006 banned a category (all backgrounding); iter-0007 isolation proved that ban broke F6 because the category is broader than the failure shape. Two distinct failure modes have been observed and traced to the **same root** — the orchestrator stops feeding bytes to its API stream while a long subprocess runs:

- **Orphaned-background** (iter-0005 F2 collapse): orchestrator launches `codex exec ... &`, says "I'll wait for completion notifications", emits Stop while the subprocess is still alive. Watchdog kills at metadata.timeout. No work captured.
- **Unobserved-foreground** (iter-0007 F6 collapse): orchestrator dispatches a single foreground Bash that blocks for 10+ minutes. The orchestrator's API stream stops emitting bytes; byte-watchdog (`Stream idle timeout (byte-level)`) fires; transcript stays empty.

Both failure modes are **stream-starvation**: the orchestrator's outer API connection times out (or its stop signal lands too early) because no bytes flow during the long inner subprocess.

The fix targets the root: **the only sanctioned shape for long codex calls is monitored-background** — codex in background, orchestrator-installed waiter that simultaneously emits progress bytes (keeps outer stream alive) and blocks on codex exit (prevents premature Stop). Short codex calls (≤60s) keep plain foreground; the orchestrator naturally emits bytes around them.

iter-0008 ships this contract as text in `_shared/codex-config.md` (canonical) with a one-line backref in `auto-resolve/references/engine-routing.md`. No harness changes, no flag changes, no process-group surgery — the constraint lives at the level the failure exists (skill prompt the orchestrator reads at runtime).

**Predicted**: F2 recovers (margin ≥ +5, no LocalShellTask kills), F6 stays healthy (score ≥ 85, files ≥ 1, transcript > 0, exit 0, not timed_out), F1 unchanged (smoke).

## Mechanism

Why-chain (extends iter-0007's chain at #30):

31. Why is "all background banned" too broad? → Backgrounding `codex exec` paired with a `tail -f`/poll waiter is exactly how F6 succeeded under d895ffa. iter-0006 banned the orchestration mechanism (`&` + `tail -f` + `Monitor` + `run_in_background`) wholesale. The mechanism was load-bearing for F6.
32. Why does "all foreground required" produce its own failure? → A 10-minute single foreground Bash dispatch starves the outer `claude -p` API connection of bytes. Anthropic's byte-level idle watchdog fires at 300s; even when it doesn't, the orchestrator's `Stop` reasoning isn't running during that window so it can't recover gracefully.
33. Why is the right level "shape of waiter," not "where the subprocess runs"? → The two failure modes have different launch shapes (background vs foreground) but a single shared symptom: outer stream silence. The orchestrator's job, from the contract's perspective, is to keep its outer API stream non-silent while the inner codex thinks. Whether that's achieved by background+tail or by short foreground calls is mechanism; the goal is bytes flowing.
34. Why ban orphaned-background specifically (not all background)? → The orphan is the dangerous shape — it actively misleads the orchestrator into emitting Stop. Monitored-background does not have this property; the waiter holds the orchestrator's attention until codex returns.
35. Why also call out "unobserved-foreground >3min"? → Because the iter-0007 F6 collapse proved foreground-without-observation can also produce stream silence. Symmetry: long codex needs observation regardless of background/foreground.
36. Root: stream-starvation is the bug; monitored-background (or short foreground) is the fix; the contract regulates orchestrator behavior at the level where the freedom exists (skill prompt). Fix at level 36.

## Predicted change

(Predictions BEFORE the gate runs — per Principle #2. Updated post-codex Round 1.)

- **F2 alone** (~22 min): margin ≥ +5, variant_score ≥ 85, files_changed ≥ 1, diff_bytes > 0, `LocalShellTask kill requested` count = 0, transcript > 1 KB, invoke_exit = 0, timed_out = false. Recovers iter-0006 F2 result (+16 margin) without iter-0006's universal contract.
- **F6 alone** (~22 min): variant_score ≥ 85, files_changed ≥ 1, verify ≥ 0.66, transcript > 0 bytes (was 0 under iter-0006), invoke_exit = 0, timed_out = false, variant elapsed < 1500s wall cap. Holds the d895ffa F6 baseline (variant 93, +3 files, 5.2KB diff).
- **F1 smoke** (~3 min, near-free, validates G4 bare-case-modal regression gate): no regression. Trivial fixture; failure here would mean the contract text itself confused the orchestrator on simple work.
- **Routing telemetry — full evidence required (per codex Round 1 Q4)**: across F2 + F6, the run artifacts must collectively show all six:
  1. `codex exec` actually observed (`grep` against variant claude-debug.log returns ≥1 hit on at least one fixture)
  2. invocation shape (foreground vs background) recoverable from the dispatch
  3. waiter / monitor present when background was used
  4. orchestrator did NOT emit Stop while a `codex exec` child was alive
  5. transcript non-empty
  6. byte-watchdog did NOT fire (`Stream idle timeout (byte-level)` absent)
  Plus, for implementation fixtures (F2/F6), files_changed ≥ 1 and diff_bytes > 0. If the artifacts cannot show command shape, the run did NOT validate the contract — escalate to a forced-Codex canary fixture before suite.
- **Suite (only after gate + telemetry pass)**: predicted suite avg margin in the +8 to +12 range — recovery of d895ffa baseline plus iter-0006-style F2 win. Ship-gate ≥ 7/9.

## Diff plan

Six surgical edits, no harness changes. (Expanded post-codex Round 1 Q5 — inline `codex exec` examples are closer to the model's action than the canonical reference, so canonical-by-reference inheritance was insufficient.)

1. **`config/skills/_shared/codex-config.md`** (canonical) — insert a new section "Execution contract — long Codex calls require active observation" between "Notes" and "Availability check". Names the two forbidden shapes (orphaned-background, unobserved-foreground), the **task-shape default rule** (workspace-write / BUILD/FIX / multi-phase ideate / repo-wide audit / team-or-dual roles → monitored-background; plain foreground only for bounded read-only critique <60s; if unsure, monitored-background), the monitored-background requirements (≤30s progress emission, capture stdout+stderr+exit code, non-zero exit = subagent failure, never rely on implicit completion notifications), the explicit forbidden list, and the **stdin discipline** requirement (`< /dev/null` on background invocations to prevent codex 0.124.0's stdin-merge hang). Each rule cites the iter that produced it (0005 / 0007 / 0008-self-debug) so the why-chain travels with the rule.

2. **`config/skills/devlyn:auto-resolve/references/engine-routing.md`** — extend the inline "Codex call defaults" sentence with a backreference to the new section AND replace the bare `codex exec` example in the team-role footer (line 74) with the monitored-background shape. Two-line change.

3. **`config/skills/devlyn:ideate/SKILL.md`** — append to each inline `codex exec` mention: "Follow `_shared/codex-config.md` execution contract; long or ambiguous Codex calls use monitored-background, not plain foreground." (one sentence; no content duplication).

4. **`config/skills/devlyn:ideate/references/codex-critic-template.md`** — same backref sentence appended where inline `codex exec` example appears.

5. **`config/skills/devlyn:preflight/SKILL.md`** — same backref. Codex Round 1 explicitly flagged: preflight code-audit can be a long read-only call, so "read-only" sandbox does NOT grant foreground exemption.

6. **`config/skills/devlyn:team-resolve/SKILL.md`** + **`config/skills/devlyn:team-review/SKILL.md`** — same backref. Team roles are defaulted to monitored-bg by the new task-shape rule; inline mentions must agree.

After edit, sync `.claude/skills/` to match `config/skills/` BEFORE any benchmark (per `memory/project_skill_sync_gap_2026_04_26.md` + codex Round 1 independent surface). Without this, the gate measures the d895ffa baseline, not iter-0008.

NOT in this diff (deliberately deferred per Karpathy #3 surgical):
- `--output-format=stream-json` instrumentation. Codex round 5 counter-recommended: instrumentation makes failures observable, not absent. The contract addresses absence directly.
- iter-0005's three isolation flags (`--ignore-user-config --ignore-rules --ephemeral`). Hold; only re-add if a future measurement shows they're needed *separately* from the orchestration fix.
- G2 zero-file-long-run hard floor in `result.json`. Useful but orthogonal — defer to its own iter.
- G5 self-abort criteria. Orthogonal contract surface.
- Pre-run sync auto-mirror in `run-suite.sh` (iter-0010 candidate). Deferred — this iter relies on a manual sync step in the gate procedure.

## Falsification gate

Three single-fixture runs sequential, plus conditional canary. Karpathy #2 — load-bearing fixtures only. Codex Round 1 Q3/Q4 expanded the telemetry requirement on top of the shape gate.

**Pre-gate** — sync `.claude/skills/` ← `config/skills/` and verify with `diff -rq config/skills/ .claude/skills/ 2>&1 | grep -v "Only in"` returning silence. Iter-0006 documented this is mandatory.

1. **F1 alone** (~3 min smoke, G4 bare-case-modal). Pass: no variant disqualifier; bare-case modal characteristic preserved. Failure → contract text confused even trivial routing; redesign before F2/F6.
2. **F6 alone** (~22 min, regression-prevention proof — the failure shape iter-0006 caused). Pass criteria above PLUS Q4 telemetry: `codex exec` was actually invoked AND artifacts show monitored shape (waiter present, no premature Stop, no byte-watchdog, transcript non-empty, ≥1 file). Failure → REVERT iter-0008 immediately.
3. **F2 alone** (~22 min, recovery proof — the original failure shape iter-0006 fixed). Pass criteria above. Failure → re-diagnose with codex Round 2 before any further runs.

**Conditional canary** — if neither F2 nor F6 invoked `codex exec` (per Q4 evidence), the contract was not exercised on its codex surface. Build a forced-Codex canary fixture (spec language demands a Codex-routed BUILD or FIX phase) and run it as a fourth gate before suite. Codex Round 1 explicitly required this — "necessary but too weak" otherwise.

Only run full suite if all three (or four) pass. Cumulative gate cost ~50 min wall (or ~80 min with canary), vs iter-0006's 4-fixture gate which was ~75 min and still missed F6.

F4/F9 single-fixture gates are deliberately OUT of this iter (codex Round 1 Q3 confirmed). Their iter-0005 collapses are not stream-starvation root and would not be regulated by this contract; full suite remains mandatory before ship verdict.

## Skill guardrails check (G1–G5 per `memory/project_skill_guardrails_2026_04_26.md`)

| # | Guardrail | iter-0008 stance |
|---|---|---|
| G1 | Long codex calls must remain observable | ✅ Contract REQUIRES active observation (≤30s progress check). The "monitored-background" sanctioned shape IS the operational form of G1. **Live evidence (2026-04-27)**: this iteration's own codex Round 1 cross-check first hung silently for 25 min on a missing `< /dev/null` stdin redirect (codex 0.124.0 reads stdin as `<stdin>` block when prompt arg also provided). The Monitor poll (15s heartbeat) caught the stall; the contract now mandates `< /dev/null` on background invocations. The harness loop itself just demonstrated G1's failure mode and its fix. |
| G2 | No zero-file long runs | ✅ Contract addresses the root: monitored-background prevents the stream-starvation that produces zero-file long runs. (The `result.json` hard-floor sentinel is deferred — orthogonal.) |
| G3 | Command discovery before edits | — Orthogonal; contract does not regulate inventory step. F6 spec already partly covers it. |
| G4 | Bare-case modal regression gate | ✅ F1 + F6 in the falsification gate. F1 catches trivial-route confusion; F6 catches long-codex regression. |
| G5 | Stuck-execution abort criteria | — Orthogonal; contract does not introduce new stuck-detection. Watchdog remains the backstop. |

## Principles check (provisional, finalized after run)

| # | Principle | Status | Evidence |
|---|---|---|---|
| 1 | No overengineering | (provisional ✅) | One new section + one backref line. ~25-30 lines text addition total. No new files, no new abstractions, no harness changes. |
| 2 | No guesswork | ✅ | Hypothesis names the failure shape (stream-starvation), the sanctioned shape (monitored-bg or short fg), the metrics (F2 ≥+5 margin, F6 ≥85 score / ≥1 file / >0 transcript / not timed_out), and the mechanism (orchestrator-voice rules in skill prompt). All Predicted change values written before the gate runs. |
| 3 | No workaround | ✅ | The contract regulates at the level the freedom exists (orchestrator's prompt). Six why-steps in Mechanism. The fix lands at level 36 — root-level stream-starvation, not at watchdog/sandbox. |
| 4 | Worldclass production-ready | (filled after gate run) | Will check: zero CRITICAL on either gate fixture, no regression that introduces new HIGH on previously-clean fixtures. |
| 5 | Best practice | (filled after gate run) | Will check: zero `design.unidiomatic-pattern` MEDIUM regression. |

## Codex round 1 cross-check (post-data, 2026-04-27)

Run-id: `/tmp/codex-r1.out`, gpt-5.5 xhigh read-only, 145242 bytes, exit 0. Submitted via monitored-background (file redirect + Monitor poll @ 15s heartbeat) — second attempt; first attempt hung silently for 25 min on missing `< /dev/null` stdin redirect (recorded as G1 live evidence above).

**Verdict: EXPAND-SCOPE.** Diagnosis usable; drafted contract too vague at runtime and too narrow across inline call sites.

**Q1 — Failure-mode coverage.** Adopted with sharpening. "Stream-starvation" is correct unifier at the *symptom* level for F2 (orphan) + F6 (unobserved-fg). Do NOT overclaim it as root for F4/F5/F9: walltime appendix shows F4/F5 full-suite collapses are shared-runtime/API failures (both arms affected), iter-0005 F4/F9 0-kill regressions point at codex flag-shift behavior. iter-0008 explicitly scoped to F2/F6; F4/F5/F9 stay out.

**Q2 — Contract precision (largest change).** Codex flatly rejected my "~3 min long-codex" duration guess: an LLM cannot reliably predict "this Codex call will finish under 3 min." Replace with **task-shape rule**: workspace-write / BUILD / FIX / multi-phase ideate / repo-wide audit / team-or-dual roles → monitored-background by default. Plain foreground only for bounded read-only critique <60s; if unsure, monitored-background. Operational invariant: no unobserved Codex silence longer than 60s; monitored waiters check progress every ≤30s. ✅ Adopted verbatim.

**Q3 — Gate sufficiency.** F1+F2+F6 retained as the shape gate, but F2 has gone Claude-only across iter-0006 runs and could pass without exercising the contract. Add forced-Codex canary IF Q4 telemetry shows neither F2 nor F6 actually invoked codex. F4/F9 single can stay out; full suite remains mandatory before ship. ✅ Adopted.

**Q4 — Routing telemetry.** "At least one fixture invoked codex" is necessary but too weak. Require six-element evidence: codex_exec_observed, fg/bg shape, waiter present, no premature Stop while child alive, transcript non-empty, no byte-watchdog. Plus files/diff produced for implementation fixtures. ✅ Adopted into Predicted change + Falsification gate.

**Q5 — Diff surface.** Canonical-by-reference is NOT enough. Inline `codex exec` examples in `devlyn:ideate/SKILL.md`, `devlyn:ideate/references/codex-critic-template.md`, `devlyn:preflight/SKILL.md`, `devlyn:team-resolve/SKILL.md`, `devlyn:team-review/SKILL.md` are closer to the model's action than the distant canonical. Touch each with one sentence: *"Follow `_shared/codex-config.md` execution contract; long or ambiguous Codex calls use monitored-background, not plain foreground."* Still surgical (one sentence per file). ✅ Adopted; diff scope expanded from 2 files to 7.

**Independent surfaces from codex.** (a) Sync `config/skills/` ← `.claude/skills/` MUST be explicit in gate procedure (iter-0006 sync gap precedent). (b) "Read-only" ≠ "short": preflight code-audit and team-review can be long read-only calls; sandbox alone does not grant foreground exemption. ✅ Both adopted (sync into Pre-gate step; "read-only ≠ short" embedded in task-shape rule).

**My independent finding (codex did not see this).** Codex CLI 0.124.0 reads stdin as `<stdin>` block when both stdin is open AND a prompt arg is provided (per `codex exec --help`). Background `codex exec` without `< /dev/null` hangs forever waiting on stdin. Discovered when this Round 1 itself hung; fixed and recorded. The contract MUST mandate `< /dev/null` on background invocations.

**Synthesis decisions.**
- Adopt codex's drafted contract section (Q2 task-shape rule, monitored-bg requirements, forbidden list) **with addition** of stdin discipline rule.
- Expand diff to 7 files (not 2).
- Expand falsification gate with Q4 6-element telemetry + Q3 conditional canary.
- Maintain F4/F5/F9 exclusion from gate per Q1.
- Pre-gate sync step is mandatory.

## Contract wording (final draft for `_shared/codex-config.md`, post-Round 1)

```md
## Execution contract — long Codex calls require active observation

Two failure shapes are forbidden:

- **Orphaned background**: launching `codex exec` in the background, then ending the orchestrator response or saying "I'll wait for completion notifications" without an installed waiter. (iter-0005 F2 collapse — `autoresearch/iterations/0005-codex-inner-isolation.md`.)
- **Unobserved foreground**: a single blocking foreground `codex exec` that can stay silent long enough for the outer API stream to idle. (iter-0007 F6 collapse — `autoresearch/iterations/0007-f6-isolation.md`.)

Both share a root: the orchestrator stops feeding bytes to its outer API stream while a long inner subprocess runs.

**Default by task shape, not predicted duration.** The orchestrator cannot reliably predict whether a Codex call will finish in 60s; it can observe the call's *shape*. Run as monitored-background by default if the call is any of:

- workspace-write (`--full-auto`),
- auto-resolve BUILD or FIX LOOP,
- ideate multi-phase,
- preflight repo-wide audit (read-only does NOT imply short — preflight code-audits routinely exceed 5 min),
- a team or dual-role spawn.

Plain foreground `codex exec` is allowed only for bounded read-only critique expected to finish within 60s. If unsure, use monitored-background.

**A monitored-background call MUST:**

- Redirect stdin: `codex exec ... < /dev/null > out.log 2>&1 &` — without `< /dev/null`, codex 0.124.0 reads stdin as `<stdin>` block and hangs forever. (iter-0008 self-debug, 2026-04-27.)
- Keep the orchestrator active until Codex exits — the orchestrator response does NOT end while a `codex exec` child is alive.
- Poll or stream progress to the outer stream at least every 30s (e.g., periodic `wc -c out.log`, `tail -n0 -f out.log` filter, or progress emission).
- Capture stdout, stderr, and the exit code; report non-zero exit as a subagent failure.
- Never rely on implicit completion notifications; the waiter actively joins the codex process.

**Forbidden:**

- `codex exec ... &` without an immediate monitor and a final join.
- `run_in_background: true` followed by Stop emission while codex is still alive.
- A single long foreground Bash dispatch for a workspace-write or multi-phase Codex call.
- A monitor that waits silently or never checks the Codex exit code.

**Why this contract exists.** Both failure shapes silently lose work: iter-0005 F2 (`codex exec & ; "I'll wait for notifications"; Stop` → watchdog kill, 0 bytes) and iter-0007 F6 (single 10-min foreground `codex exec` Bash dispatch → byte-watchdog `Stream idle timeout`, 0 bytes, watchdog kill). The contract closes both at the level the freedom exists — orchestrator behavior at runtime, not subprocess flags.
```

The other five files get a one-sentence addition near each inline `codex exec` example:

> Follow `_shared/codex-config.md` execution contract; long or ambiguous Codex calls use monitored-background, not plain foreground.

## Actual change

### F1 alone (run-id `20260427T020823Z-1ff7534-iter-0008-f1`, 2026-04-27 02:08–02:17Z)

| Signal | Pass criterion | Observed | Status |
|---|---|---|---|
| variant_score | ≥ 85 (smoke; G4) | **97** | ✅ |
| bare_score | (info) | 90 | — |
| margin | ≥ +5 | **+7** | ✅ |
| files_changed | ≥ 1 | **2** (`bin/cli.js`, `tests/cli.test.js`) | ✅ |
| diff_bytes | > 0 | **1980** | ✅ |
| variant verify | ≥ 0.66 | **0.80 (4/5)** | ✅ |
| timed_out | **false** (G2 floor) | **true** | **✗** |
| invoke_exit | 0 | **124 (watchdog)** | **✗** |
| variant elapsed | < metadata.timeout (480s) | **480s (cap hit)** | **✗** |
| transcript bytes | > 0 | **0 (empty)** | **✗** |

Ship-gate prints PASS (margin +7), but the run hit the 480s wall-cap with empty transcript on a TRIVIAL fixture (F1 = "add `--loud` flag to hello subcommand"). bare arm completed in 45s. variant did the BUILD work correctly (`--loud` + uppercase + `!!`, 2 tests added — diff is exact spec match), but auto-resolve full pipeline never returned cleanly. Codex Round 2 explicitly flagged this: "F1 PASS but timed_out=true should be classified as gate failure; otherwise score/margin can mask the exact harness failure this iteration is trying to eliminate."

### F6 alone (run-id `20260427T021900Z-1ff7534-iter-0008-f6`, 2026-04-27 02:19–02:46Z)

| Signal | Pass criterion | Observed | Status |
|---|---|---|---|
| variant_score | ≥ 85 | **35** | **✗** |
| margin | ≥ +5 | **−59** (variant 35 / bare 94) | **✗** |
| files_changed | ≥ 1 | **0** | **✗** |
| diff_bytes | > 0 | **0** | **✗** |
| variant verify | ≥ 0.66 | **0.33 (2/6)** | **✗** |
| timed_out | false | **true** | **✗** |
| invoke_exit | 0 | **124 (watchdog)** | **✗** |
| variant elapsed | clean exit | **1500s (full wall-cap)** | **✗** |
| transcript bytes | > 0 | **0 (empty)** | **✗** |

Critical findings (judge): "Missing core checksum subcommand / Missing required tests/checksum.test.js / Required not-found and directory error behavior is absent". variant produced literally nothing.

**This is exact iter-0006-full F6 reproduction** (variant 31 / margin −65 / 0 files / 0 bytes / verify 0.33 / timed_out=true / 1762s wall). Different commit (1ff7534 + iter-0008 contract on top vs 1ac7594 iter-0006), same catastrophic shape. iter-0008 contract did not prevent the iter-0006 failure mode — and on single-fixture isolation per the iter-0007 protocol, that's sufficient causality for REVERT.

Diagnostic: variant orchestrator (live observation during the run) chose `codex exec -C ... -s workspace-write -c model_reasoning_effort=xhigh "<long BUILD prompt>" 2>&1 | tail -200` — a single foreground Bash dispatch with pipe-to-tail. iter-0008 contract explicitly forbids this shape. The orchestrator read the contract (it's in `_shared/codex-config.md` + a backref in `engine-routing.md`) and chose the forbidden shape anyway.

Codex Round 2 independent surface (caught after F6 launched, before result was in): "`codex exec ... 2>&1 | tail -200` is worse than plain foreground: normal `tail` on a pipe often withholds output until EOF, so it actively suppresses the bytes the outer watchdog needs." Predicted the F6 collapse mechanism in advance. Confirmed by the result.

**G1 live evidence (already documented above) was the early warning** — my own codex Round 1 cross-check first hung silently for 25 min on missing `< /dev/null`, recovered only when I switched to monitored-bg shape with file redirect + Monitor poll. Same root mechanism (orchestrator picks unsafe shape) but caught at the cross-check layer; the benchmark variant arm has no equivalent recovery.

## Codex Round 2 (post-F1, mid-F6 — meta-question: enforcement layer)

Verdict: **HYBRID (D + C)** — wrapper script + PreToolUse:Bash hook. Prompt-level instruction is empirically dead.

Ranking:
- **D Hook (1)**: PreToolUse:Bash blocks raw `codex exec` outside wrapper. Strongest — intercepts the dispatch even when orchestrator ignores docs.
- **C Wrapper (2)**: `scripts/codex-monitored.sh` enforces shape once invoked. Useless if orchestrator doesn't call it.
- **B Template (3)**: Copyable Bash in phase-1-build.md. Still prompt-level, model prior wins.
- **E Watchdog tolerance (4)**: Accept starvation, don't prevent. Doesn't protect wall-clock or gate reliability.
- **A More text (5)**: Already falsified by iter-0008 F6.

## Lessons

1. **Prompt-level instruction is insufficient to constrain orchestrator behavior at runtime.** iter-0008 contract was applied to the canonical `_shared/codex-config.md` + 6 inline call sites including direct backrefs. Variant orchestrator on F6 read the contract and picked the explicitly-forbidden `codex exec | tail -200` shape anyway. Same meta-failure as iter-0006 (universal foreground ban → orchestrator stalled), different surface but same lesson — the model's pattern prior over codex invocation shapes outweighs prose contract text.

2. **The `| tail -200` shape is worse than plain foreground.** Codex Round 2 surfaced this independently: pipe `tail` typically buffers until EOF, so the outer claude API stream sees ZERO bytes during the entire codex execution. iter-0008 contract listed this shape under "Forbidden" but the orchestrator chose it anyway — the failure is amplified by the very pattern the contract banned.

3. **Single-fixture ship-gate trivially passes even on catastrophic regression** (`Fixtures with margin ≥ +5: 0/1` does not trigger the 7/9 floor). Codex Round 2 caught this and recommended F1 `timed_out=true` should be reclassified as gate failure regardless of margin — a benchmark-harness fix queued for iter-0011 watchdog-classification.

4. **The G1 self-debug evidence was the early warning that should have escalated the design.** This very iteration's codex Round 1 hung for 25 min on missing `< /dev/null` — same root mechanism (orchestrator picks unsafe shape, no enforcement layer below the prose). I incorporated that as a *contract addition* (mandate `< /dev/null`) instead of recognizing it as evidence that *prose mandates don't bind*. The right escalation would have been to skip iter-0008 ship and go directly to the wrapper+hook design (iter-0009) before benchmarking.

5. **Codex Round 2's prediction was correct in advance.** Codex predicted the F6 collapse mechanism (pipe `tail` byte-suppression) before the result.json appeared. Cross-check value is highest when the cross-checker is separate enough to surface mechanism the original designer is blind to. Continue dual-model GAN — codex is earning its keep.

6. **F4/F5/F9 staying out of the gate (per Q1 boundary) was correct.** F1 + F6 was sufficient to refute the iteration. Adding more fixtures would have wasted ~75 min for no additional decision power.

## Principles check (post-data, finalized)

| # | Principle | Status | Evidence |
|---|---|---|---|
| 1 | No overengineering | ⚠️ Borderline | 7-file diff (≈40 lines text added) is small in absolute terms, but 6 of those 7 files turned out to be *also* prompt-level — same enforcement layer, no additional binding power. The extra 5 inline backrefs added zero behavioral effect on F6. |
| 2 | No guesswork | ✅ | Hypothesis names the metric (F2 ≥+5, F6 ≥85), the falsification gate executed as written, predictions were filed before data, surprise outcome (F6 → 35) was recorded raw. |
| 3 | No workaround | ✅ | The fix attempted to land at the orchestrator-prompt level — the level the freedom existed at. The lesson is that the *level was wrong*, not that the fix was a workaround. |
| 4 | Worldclass production-ready | **❌** | F6 variant produced 0 files / 0 bytes / verify 0.33 / watchdog kill / empty transcript. Catastrophic regression on a previously-clean fixture. Automatic REVERT trigger per the rule. |
| 5 | Best practice | (not assessable) | Couldn't surface — variant arm produced no code. |

Iteration with ❌ on Principle #4 is rejected per `PRINCIPLES.md`. **REJECT.**

## Decision

**REJECT iter-0008.** Revert all 7 changed files in `config/skills/` and re-sync `.claude/skills/`.

Specifically:
```
git checkout HEAD -- \
  config/skills/_shared/codex-config.md \
  config/skills/devlyn:auto-resolve/references/engine-routing.md \
  config/skills/devlyn:ideate/SKILL.md \
  config/skills/devlyn:ideate/references/codex-critic-template.md \
  config/skills/devlyn:preflight/SKILL.md \
  config/skills/devlyn:team-resolve/SKILL.md \
  config/skills/devlyn:team-review/SKILL.md
# then sync .claude/skills/ from config/skills/, verify diff -rq clean
```

Branch HEAD stays at `1ff7534` (iter-0006 REVERT). Effective skill-axis state ≈ d895ffa = iter-0004 effective. F2's iter-0005-class collapse mechanism remains on the table; **iter-0009 takes over with executable enforcement**.

**Next: iter-0009 — wrapper + PreToolUse:Bash hook (Codex Round 2 HYBRID).**

Concrete diff (codex-recommended):
1. `scripts/codex-monitored.sh` — wraps `codex exec`, enforces `< /dev/null > log 2>&1 &`, ≤30s heartbeat, tail-bounded output, PID/log/exit metadata, exact codex exit-code preservation.
2. `config/skills/_shared/codex-config.md` — canonical invocation becomes `scripts/codex-monitored.sh -C ...`. Raw `codex exec` documented as forbidden except inside the wrapper.
3. `config/skills/devlyn:auto-resolve/references/engine-routing.md` + 5 inline call sites — replace raw `codex exec` examples with wrapper examples.
4. `.claude/settings.json` PreToolUse:Bash hook — block `codex exec` Bash dispatches that are not the wrapper or matching the wrapper's args.
5. `scripts/lint-skills.sh` — fail on raw copyable `codex exec` examples leaking outside `_shared/codex-config.md` explanatory text and the wrapper itself.

Falsification gate for iter-0009:
1. **Negative canary**: orchestrator instructed to attempt raw `codex exec ... | tail -200`; PASS only if PreToolUse:Bash hook BLOCKS it before execution. (Tests the binding power of the hook layer, independent of any single fixture.)
2. **F6 alone with wrapper**: must show wrapper invocation (in claude-debug.log), heartbeat bytes (every ≤30s), non-empty transcript, exit 0, NOT timed_out, files_changed ≥ 1.
3. **F1 alone**: must finish under metadata.timeout (480s) AND `timed_out: false`. Reclassify F1 timed_out=true as gate failure per Codex Round 2.
4. **F2 alone** (recovery proof): margin ≥ +5, no LocalShellTask kills.
5. Full suite only after 1–4 pass.

iter-0011 candidate (new): benchmark ship-gate `Fixtures with margin ≥ +5: K/N` should hard-fail when `K/N < gate_floor` even on single-fixture mode (currently silently PASSes because gate_floor 7/9 is unmet on N=1 but no hard-floor). Independent of iter-0009 contract changes — pure benchmark-harness fix.
