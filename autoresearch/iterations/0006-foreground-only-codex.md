# 0006 — Foreground-only `codex exec` execution contract

**Status**: PROPOSED
**Started**: 2026-04-26
**Decided**: (not yet)

## Hypothesis

The iter-0005 full suite traced F2 (−82), F5 (−35), and F6's transcript-empty signature to a single behavioral pattern: the prompt-driven orchestrator non-deterministically chose to background `codex exec` (often piped to `tail -f` or wrapped in `Monitor`/`TaskOutput`), then issued Stop while that backgrounded subprocess was still running. The watchdog later killed the orphaned Codex + monitor pair, but no work product was captured. F4, F7, F8 — which used foreground `codex exec ... | tail -N` patterns — completed cleanly. Adding an explicit "foreground only" execution contract to `_shared/codex-config.md` and the inline auto-resolve default in `engine-routing.md` removes the orchestrator's choice between background and foreground; the only sanctioned shape is foreground. Predicted: F2 variant recovers (LocalShellTask kills → 0, transcript non-empty, margin ≥ +5), F5 follows, full suite returns to roughly the v3.7-final +10.6 region with the F7 win preserved.

## Mechanism

Why-chain (continues from iter 0005's full-suite refutation):

20. Why did iter 0005 fail full-suite even after fixing F7? → F2/F5 collapsed because Codex was backgrounded and never returned. F4/F9 also regressed on 0-kill / natural-exit runs, indicating the iter 0005 flags themselves shifted Codex behavior subtly (likely losing project-trust state).
21. Why does the orchestrator sometimes background Codex and sometimes not? → The orchestrator is a model interpreting a markdown skill file. Multiple `codex exec` examples exist in the codebase (some inline, some referenced); when the model improvises an invocation, it picks foreground or background based on local prompt context, recent tool-use patterns in the conversation, or simple sampling variance.
22. Why is background-with-tail unsafe specifically? → Background-with-tail introduces TWO long-running processes: the Codex subprocess and the `tail -f`/`Monitor` watcher. When the model issues Stop, the orchestrator's response ends but those background processes do not. macOS does not auto-reap them. The watchdog cleans them at metadata.timeout but no useful state was produced in the meantime.
23. Why is foreground-only the right level of fix? → It eliminates one bit of nondeterminism by removing a choice. The skill-prompt contract — read by the model at runtime — explicitly forbids the bad shape and prescribes the good one. No sandbox, flag, or process-group manipulation is required at the harness layer.
24. Why now and not iter 0005? → Iter 0005 reverted; we are choosing the next single hypothesis. Codex round 5 explicitly recommended `(a) foreground-only contract` over `(b) stream-json instrumentation` on the grounds that instrumentation makes failures observable but does not stop them.
25. Root: orchestrator pattern, not subprocess flags. Fix at level 25 — explicit skill-prompt contract that names the failure shape and the sanctioned shape.

## Predicted change

- F2 variant: LocalShellTask kills 2 → **0**, transcript ≥ 1 KB, diff_bytes ≥ 1 KB, score ≥ 85, margin ≥ +5.
- F5 variant: similar — LocalShellTask kills 1 → 0, score recovers, margin ≥ +5.
- F4 variant: no regression vs current iter-0005 state (already 0 kills); maybe small wall-time reduction.
- F7 variant: holds at margin +3-or-better (the iter-0005 win was independent of background pattern).
- F6 variant: LocalShellTask kills 1 → 0; the timed_out=false / invoke_exit=124 anomaly stops appearing (separate watchdog-classification fix is still warranted, but won't trigger as often).
- Suite avg margin: −7.1 → +10 region (return to v3.7-final ballpark, with F7 retained as a real win).
- Ship-gate: 2/8 → ≥7/9.

## Diff plan

Two surgical edits, no harness changes:

1. **`config/skills/_shared/codex-config.md`** — add a new section "Execution contract — foreground only" between the Notes block and the Availability check. The section names the failure shape (`&`, `tail -f`, `run_in_background`, `Monitor`/`TaskOutput`) and the sanctioned shape (single foreground, stream stdout, wait, capture). Includes a brief `Why this contract exists` paragraph pointing at iter 0005's full-suite evidence so future readers see the motivation.

2. **`config/skills/devlyn:auto-resolve/references/engine-routing.md`** — extend the "Codex call defaults" inline sentence with the same foreground-only constraint and a backreference to the canonical Execution contract section. This is the file the BUILD/FIX/etc. phases actually read at runtime; it must agree with `_shared`.

NOT in this diff:
- `--output-format=stream-json` instrumentation. Codex round 5 explicitly counter-recommended; instrumentation makes failures observable, not absent.
- Re-introducing iter 0005's three isolation flags. Those are on hold until a future measurement shows they are needed *separately* from the orchestrator fix.
- Inline `codex exec` mentions in `devlyn:ideate`, `devlyn:preflight`, `devlyn:team-resolve`, `devlyn:team-review`. None on the F2/F5 path; deferred to per-skill iterations as their own fixtures exercise them.

## Principles check (provisional, finalized after run)

| # | Principle | Status | Evidence |
|---|---|---|---|
| 1 | No overengineering | (provisional ✅) | Two text edits, ≈15 lines added. No new files, no harness changes, no flags. |
| 2 | No guesswork | ✅ | Hypothesis names the failure shape (background-with-tail), the metric (LocalShellTask kills = 0, margin ≥ +5 on F2), and the mechanism (orchestrator no longer chooses unsafe shape). Iter 0005's full-suite data already isolated the failure pattern. |
| 3 | No workaround | ✅ | The contract closes the orchestrator's degrees-of-freedom at the level the freedom exists (skill prompt). Not a sandbox flag, not a process-kill heuristic. |
| 4 | Worldclass production-ready | (filled after run) | |
| 5 | Best practice | (filled after run) | |

## Falsification gate

Before any full suite, gate sequentially. Codex round 6 (2026-04-26, GPT-5.5, xhigh, read-only) inserted F4 + F9 after F5 because iter 0005's full suite regressed those fixtures by −13 / −17 on **0-kill / natural-exit** runs — a different signature than the F2/F5 background-with-tail collapse. The contract this iteration ships only addresses the kill-class shape; F4/F9 must clear independently before a full suite is justified.

1. **F2 alone** (~22 min). Pass criteria: `LocalShellTask kill requested` count = 0 in claude-debug.log; `diff_bytes > 0`; `files_changed > 0`; variant score ≥ 85; margin ≥ +5. Failure → re-diagnose with codex round 7 before any further runs.
2. **F5 alone** (~22 min). Same pass criteria as F2 but with F5's verify shape (4/5 expected since fixture's `node --test` passes). Failure → re-diagnose.
3. **F4 alone** (~22 min). Different signature than F2/F5 — sentinel for the iter-0005 0-kill regression class. Pass criteria: `invoke_exit = 0`, `timed_out = false`, `LocalShellTask kill requested = 0`, `diff_bytes > 0`, `files_changed > 0`, margin ≥ +5, AND no variant-score regression worse than −5 vs v3.7-final (F4 baseline 100 → variant ≥ 95).
4. **F9 alone** (~30 min — F9 is the e2e fixture, longer wall). Same pass criteria as F4, with v3.7-final F9 baseline as the reference (margin ≥ +5; verify ≥ 40%/40% per v3.7-final).
5. **Full suite** (~3-4 hr). Required for ship verdict per playbook. Run only after F2 + F5 + F4 + F9 all pass.

If F4 or F9 fail with the current diff (and F2 + F5 pass), the right next move is NOT to ship-and-revert again — it is a separate iter-0007 hypothesis on the residual mode-shift, with iter 0006's contract retained.

### Routing telemetry — orthogonal observability criterion (Codex round 8, post-F2)

F2's gate pass was mechanism-indeterminate: the metrics passed, but `codex exec` was never invoked (the orchestrator routed F2 entirely through Claude this run), so the contract itself was not directly exercised. Codex round 8 added a **routing-telemetry observability criterion** that is orthogonal to the per-fixture metric gates above:

- Across F5 + F4 + F9 (any one of the three is enough), require **at least one variant arm where `codex exec` actually ran** AND that arm had **zero LocalShellTask kills** AND completed within wall-time budget.
- If all three are also Claude-only — i.e., the suite naturally avoids codex on these fixtures — the contract has not been validated on the codex path. Before any ship, build a **codex-forced canary fixture** whose spec demands a Codex-routed BUILD or FIX phase, and run it as a fifth gate.

Why this is not contract drift: the contract regulates execution shape *when* codex is invoked; it does not change routing. This criterion only verifies that the contract was tested on its stated surface area at least once. Treat it like failover testing — optional in steady state, mandatory in ship evidence.

## Pre-run process discovery (2026-04-26)

Before the F2 falsification gate could run cleanly, we discovered a harness sync gap. The benchmark variant arm copies its skill payload from `$REPO_ROOT/.claude/skills/`, not from `config/skills/`. The two trees are kept aligned by `node bin/devlyn.js -y` (the install path), which copies `config/` → `.claude/`. Iteration commits 0001–0005 were measured after that sync ran; iter 0006's commit (1ac7594) was made without re-running it, so the variant arm of any benchmark started at iter 0006 HEAD would have been silently testing the iter-0004 + iter-0005-revert state (i.e., no foreground-only contract).

We caught this because a first F2 run was kicked off, then `diff -rq config/skills .claude/skills` was run to verify; only the two iter-0006 files differed, and the absence of the `Execution contract — foreground only` section in `.claude/skills/_shared/codex-config.md` was confirmed. The first F2 run was stopped before any model invocation completed (no result.json was produced) and the partial run dir was removed. The two files were then `cp`'d into `.claude/skills/` so the contract is live in the variant arm.

**Filed as iter-0007 candidate** (separate concern, infra-level): add a sync-or-warn step to `run-suite.sh` that compares `config/skills/` to `.claude/skills/` at the top of every run and either auto-syncs the tracked managed dirs or aborts with a clear error. Without this, a future iteration is one missed `npx devlyn-cli -y` away from a silently-invalid measurement.

This discovery does NOT invalidate iter 0001–0005 data — the user manually ran the install path between those iterations, which is how the timestamp on `.claude/skills/_shared/codex-config.md` lines up with prior commits (file became `gpt-5.4` text after iter 0005 was reverted, matching the iter-0004 ship state). It does invalidate any benchmark run started against iter 0006 HEAD before the manual `cp` we did at 2026-04-26 ~00:35Z.

## Codex round 6 cross-check (2026-04-26, GPT-5.5, xhigh, read-only)

Four questions submitted before any benchmark run — independent reasoning logged first, then codex critique, then synthesis.

**Q1 — F4/F9 0-kill regression as ship-blocker preflight signal.** Codex: not proven. F4/F9 evidence is confounded with iter-0005's reverted flag bundle (`--ignore-user-config --ignore-rules --ephemeral`); cheapest probe is F4 alone. → **Adopted into the falsification gate (step 3).**

**Q2 — Add a one-line harness grep guard for `codex exec.*&` as defense-in-depth?** Codex: rejected. Grep is brittle (debug log doesn't always carry the parseable command string; `Monitor` also fires in non-collapse runs like F9). Outcome-signature gates already catch the failure. → **Diff stays at 2 files.**

**Q3 — Expand falsification gate to F4 + F9?** Codex: yes — drops were large and orthogonal. → **Gate now F2 → F5 → F4 → F9 → full-suite.**

**Q4 — Absorb the watchdog `timed_out:false / invoke_exit:124` classification bug?** Codex: stay scoped. Land it as the next micro-iteration (iter 0007 candidate) so attribution stays clean. → **Deferred.**

Codex verdict: **EXPAND-SCOPE** — but on the falsification gate, not on the diff. Effect: stronger ship gate at zero diff cost.

## Actual change

### F2 alone (Run-id `20260426T003212Z-1ac7594-iter-0006-f2`, 2026-04-26 00:32–00:52Z)

| Signal | Pass criterion | Observed | Status |
|---|---|---|---|
| `LocalShellTask kill requested` | 0 | **0** | ✅ |
| `diff_bytes` | > 0 | **11340** | ✅ |
| `files_changed` | > 0 | **3** (`bin/cli.js`, `bin/doctor.js`, `tests/doctor.test.js`) | ✅ |
| `timed_out` / `invoke_exit` / `invoke_failure` | false / 0 / false | **false / 0 / false** | ✅ |
| variant verify | passing | **6/6 (1.0)** | ✅ |
| variant elapsed | 600–1200s | **1031s** | ✅ |
| variant disqualifier | false | **false** | ✅ |
| margin | ≥ +5 | **+16** (variant 94 / bare 78) | ✅ |
| Suite ship-gate (single-fixture) | PASS | **PASS** | ✅ |

Compared to iter-0005-full F2 (variant 1201s timeout, 2 kills, 58B "Codex is running…" transcript, verify 16%, score collapse, margin −82): a +98 swing.

**Important nuance — contract not directly exercised on F2.** The variant arm's claude-debug.log shows zero `codex exec` invocations and zero LocalShellTask kills; the orchestrator routed F2's BUILD/EVAL/CRITIC entirely through the Claude path on this run. Iter-0005 F2's collapse, by contrast, had two LocalShellTask kills on a transcript that explicitly said "Codex is running. I'll wait for completion notifications." So routing through codex on F2 is non-deterministic across runs. Three plausible explanations for the recovery:

1. **Sampling variance** — iter-0005 happened to pick codex; iter-0006 happened to pick claude.
2. **Contract-induced routing shift** — the orchestrator read the foreground-only contract and interpreted it as a reason to prefer claude when uncertain.
3. **Contract worked AND codex ran cleanly in foreground** — possible but no direct evidence in this run since codex wasn't invoked at all.

Either (1) or (2) explains the F2 recovery without the contract necessarily being load-bearing. F2 passes the falsification gate as written, but the contract's effectiveness on the codex-actually-invoked path will be more cleanly demonstrated by F5/F4/F9, which historically route through codex more reliably.

### F5 alone (Run-id `20260426T005514Z-1ac7594-iter-0006-f5`, 2026-04-26 00:55–01:15Z)

| Signal | Pass criterion | Observed | Status |
|---|---|---|---|
| `LocalShellTask kill requested` | 0 | **0** | ✅ |
| `diff_bytes` | > 0 | **2454** | ✅ |
| `files_changed` | > 0 | **1** (`bin/cli.js`) | ✅ |
| `timed_out` / `invoke_exit` / `invoke_failure` | false / 0 / false | **false / 0 / false** | ✅ |
| variant verify | 4/5 expected | **4/5 (0.8)** | ✅ |
| variant elapsed | 600–1200s | **1133s** | ✅ |
| variant disqualifier | false | **false** | ✅ |
| margin | ≥ +5 | **+5** (variant 96 / bare 91) | ✅ borderline (at floor) |
| Suite ship-gate (single-fixture) | PASS | **PASS** | ✅ |

vs iter-0005-full F5 (variant 1501s timeout, 1 kill, 0B transcript, verify 40%, score collapse, margin −35): a +40 swing. Same Claude-only routing pattern as F2 — `grep codex exec` against the variant claude-debug.log returns 0. Routing telemetry criterion still unmet after two passes.

**Note**: F5 margin +5 is exactly at the floor — small judge noise (±3 per axis) could push it to +2 in another run. If full-suite reproduces this, F5 is borderline for ship and will need a re-run for confidence.

### F4 alone (Run-id `20260426T011548Z-1ac7594-iter-0006-f4`, 2026-04-26 01:15–01:30Z)

| Signal | Pass criterion | Observed | Status |
|---|---|---|---|
| `LocalShellTask kill requested` | 0 | **0** | ✅ |
| `diff_bytes` | > 0 | **2271** | ✅ |
| `files_changed` | > 0 | **3** | ✅ |
| `timed_out` / `invoke_exit` / `invoke_failure` | false / 0 / false | **false / 0 / false** | ✅ |
| variant verify | passing | **4/4 (1.0)** | ✅ |
| variant elapsed | 600–1200s budget | **688s** | ✅ |
| variant disqualifier | false | **false** | ✅ |
| margin | ≥ +5 | **+12** (variant 94 / bare 82) | ✅ |
| **variant score ≥ 95 vs F4 baseline 100** | ≥ 95 (round 6) | **94** | ⚠️ FAIL by 1 (within ±3 judge noise band) |
| Suite ship-gate (single-fixture) | PASS | **PASS** | ✅ |

**F4 trajectory**: v3.7-final variant ~100 / margin +14 → iter-0005-full variant 86 / margin +1 (−13 collapse) → **iter-0006 variant 94 / margin +12**. Recovery direction is correct (−13 → −6 vs baseline) and the 0-kill / natural-exit signature is preserved.

Codex round 9 ruling: **BORDERLINE PASS, proceed to F9**. The score-94-vs-95 miss sits inside the declared judge ±3 noise band; orthogonal health signals are strong (+12 margin, 4/4 commands, 0 kills, recovery from iter-0005 collapse). The defensive criterion was meant to catch real mode-shift regressions; this result does not look like one. Don't burn an iter-0007 cycle on a 1-point miss inside the noise band.

Routing telemetry: STILL UNMET. F4 is the third Claude-only route in a row (`grep codex exec` returns 0). F9 is the last natural opportunity; if F9 also routes Claude-only, codex round 8's "codex-forced canary fixture" requirement kicks in before any ship attempt.

### F9 alone — first attempt INVALIDATED (Run-id `20260426T013212Z-1ac7594-iter-0006-f9`, 2026-04-26 01:32–02:09Z)

| Signal | Pass criterion | Observed | Status |
|---|---|---|---|
| `LocalShellTask kill requested` | 0 | **0** | ✅ |
| `diff_bytes` | > 0 | **20542** | ✅ |
| `files_changed` | > 0 | **6** (VISION.md, ROADMAP.md, phase-1 spec, cli.js, etc.) | ✅ |
| `timed_out` | false | **false** | ✅ |
| `invoke_exit` | 0 | **1** | ✗ |
| `invoke_failure` | false | **true** | ✗ |
| variant verify | ≥ 40% (per v3.7-final) | **20%** | ✗ |
| margin | ≥ +5 | **−2** (variant 77 / bare 79) | ✗ |
| Suite ship-gate | PASS | **FAIL** | ✗ |

**Root cause: environmental, not iter-0006 contract.** The variant arm did 28 minutes of substantive work (6 files, 20.5 KB diff including VISION/ROADMAP/phase-spec generation) before issuing an API request that began streaming bytes (6327 received), then went silent for 5 minutes. Claude's byte-level watchdog correctly fired (`[byte-watchdog] firing: idle=300000ms`) and aborted the stream with `Streaming idle timeout (byte-level): stream idle: no bytes for 300000ms, aborting stream`. Variant transcript: `API Error: Stream idle timeout - partial response received` (59 bytes total).

The bare arm completed normally on F9 (90s wall, invoke_exit 0, no API errors), so the stream timeout was variant-specific and not network-wide at that moment. iter-0005-full F9 also completed normally (margin +7, no API issue), confirming F9 is not chronically API-sensitive.

Codex round 10 ruling: **RERUN-F9.** Treating an upstream stream-idle timeout as contract failure would misclassify environmental noise as model behavior.

### F9 alone — re-run (Run-id `20260426T021155Z-1ac7594-iter-0006-f9-rerun`, 2026-04-26 02:11–03:13Z)

| Signal | Pass criterion | Observed | Status |
|---|---|---|---|
| `LocalShellTask kill requested` | 0 | **0** | ✅ |
| `diff_bytes` | > 0 | **24285** | ✅ |
| `files_changed` | > 0 | **7** | ✅ |
| `timed_out` | false | **true** (3601s, hit metadata.timeout=3600s wall-clock cap) | ✗ |
| `invoke_exit` | 0 | **124** (watchdog kill) | ✗ |
| variant verify | ≥ 40% | **20%** | ✗ |
| variant score | ≥ baseline−5 ≈ 91 | **56** | ✗ |
| margin (Suite ship-gate) | ≥ +5 | **+8** (variant 56 / bare 48) | ✅ |

Two F9 runs in a row failed in different ways but the variant arm consistently ran >30 min in iter-0006:

| F9 run | wall (V/B) | timed_out | invoke_exit | margin | variant score | failure mode |
|---|---|---|---|---|---|---|
| #1 (`iter-0006-f9`) | 2029s/90s | false | 1 | −2 | 77 | API stream idle timeout |
| #2 (`iter-0006-f9-rerun`) | 3601s/79s | true | 124 | +8 | 56 | wall-clock metadata.timeout |

vs iter-0005-full F9: 1805s natural exit, margin +7, score 86. So F9 in iter-0006 is consistently slower than iter-0005-revert. No codex involvement either run. **F9 wall-time regression is a separate parallel concern** from iter-0006 contract — opened as a tracked investigation.

Codex round 11 ruling: F9 #2 is a strict-criteria FAIL (timeout, verify 20%, score 56). The +8 margin alone is not ship evidence. Sequencing: **BUILD-CANARY first** (close routing-telemetry gap on actual codex surface area), then full-suite including canary, with F9 slowdown investigated in parallel. Do not use aggregate margin alone as ship evidence until F9 is fixed or acceptance criteria are explicitly re-baselined.

### Full suite (Run-id `20260426T034926Z-1ac7594-iter-0006-full`, 2026-04-26 03:49–10:53Z, ~7h05m wall)

Suite ran end-to-end without harness aborts. Skill sync verified clean before launch (`diff -rq config/skills/ .claude/skills/` empty for differing files). All 9 fixtures × 2 arms × 1 iter completed; all 9 judge passes succeeded. The pre-launch codex round (round 14 critic) flagged dropping `--accept-missing` so the 7-of-9 gate remained live; full-suite ran without it.

| Fixture | Cat | Variant | Bare | Margin | Winner | Variant verify | Walls (V/B) |
|---|---|---|---|---|---|---|---|
| F1-cli-trivial-flag | trivial | 96 | 89 | **+7** | variant | 4/5 | 480s / 37s |
| F2-cli-medium-subcommand | medium | 94 ⚠DQ | 75 | +19 | tie | 5/5 | 1200s / 80s |
| F3-backend-contract-risk | high-risk | 98 | 97 | +1 | variant | 3/4 | 991s / 56s |
| F4-web-browser-design | stress | 55 | 55 | 0 | tie | 0/8 | 1038s / 6351s |
| F5-fix-loop-red-green | stress | 59 | 59 | 0 | tie | 2/5 | 5630s / 4611s |
| F6-dep-audit-native-module | stress | 31 | 96 | **−65** | bare | 2/6 | 1762s / 59s |
| F7-out-of-scope-trap | stress | 96 | 94 | +2 | variant | 5/6 | 562s / 33s |
| F8-known-limit-ambiguous | edge | 81 | 81 | 0 | tie | 4/5 | 901s / 44s |
| F9-e2e-ideate-to-preflight | e2e | 64 | 53 | **+11** | variant | 1/5 | 1180s / 77s |

**Suite avg**: variant **74.9** / bare **77.7** / **margin −2.8**.
**Hard floors**: ✗ 1 variant disqualifier (F2). ✗ 3 of 8 gated fixtures with margin ≥ +5 (need ≥ 7).
**SHIP-GATE VERDICT: FAIL.**

#### Mechanism evidence

Variant arms invoked codex on multiple fixtures per `~/.codex/sessions/2026/04/26/` rollouts and per pipeline.state.json `phases.build.agent: "codex"`. Iter-0006's foreground-only contract was exercised on its stated surface area in this run — no Round-12-class harness-truth gap.

#### vs reference points

| Fixture | iter-0005-full margin | iter-0006-full margin | Δ |
|---|---|---|---|
| F2 | −82 | +19 | **+101** |
| F5 | −35 | 0 | +35 |
| F4 | +1 | 0 | −1 |
| F6 | (varied) | **−65** | NEW REGRESSION |
| F7 | +3 | +2 | −1 (preserved) |
| F9 | +7 | +11 | **+4** |
| Suite avg | **−7.1** | **−2.8** | +4.3 |

The contract recovered F2 by a real +101 swing and improved F9 / preserved F7. F5 partially recovered. **F6 is a new regression** that did not exist in iter-0005-full at the same magnitude — variant produced 0 files in 1762s, missed the `checksum` subcommand entirely, while bare scored 96 in 59s. The suite margin improved (−7.1 → −2.8) but remains negative and below ship-gate.

#### Wall-time pathology (separate concern)

Several fixtures show **unproductive long-running variant arms**: F1 480s (hit cap), F2 1200s (hit cap), F5 5630s (94 min), F6 1762s with 0 files, F4 1038s with 0 files. F5 and F4 both missed core requirements despite very long walls. F4 bare also 6351s (105 min). Reads as harness/timeout instability or metadata.timeout misconfig more than genuine task complexity. Independent of the iter-0006 contract.

## Codex round 14 — post-results critic (2026-04-26, GPT-5.5, xhigh, read-only)

Five-question post-suite review:

1. **Verdict — DEFER, not REVERT.** Ship-gate is hard FAIL so do not ship. But the contract diff is not the load-bearing failure: F2 +101 swing and F9 improvement are real evidence the contract did something useful. Isolate F6 and wall-time pathologies in iter-0007 before deciding whether the contract itself comes off.
2. **F6 hypothesis** — most likely contract-induced routing/budget starvation: 1762s with 0 files = arm spent time somewhere other than implementation. Fixture complexity weak as primary cause (bare scored 96 in 59s). Targeted iter-0006-vs-iter-0005-revert F6 single-fixture re-run is the clean isolation.
3. **F2 DQ root cause** — existing variant silent-fallback behavior exposed inside a recovered implementation path, not a direct foreground-contract side effect. Contract helps the score surface; silent fallback is a separate correctness violation. Likely needs the No-Workaround Bar from CLAUDE.md to surface earlier in the pipeline.
4. **Wall-times** — harness/timeout instability or metadata.timeout misconfig more than genuine complexity. F5/F4 missing core reqs despite huge walls reads as unproductive stuck execution.
5. **Contract diff** — keep it on the branch for iter-0007. Not shippable as-is, but does not need to come off unless F6 reproduces as contract-caused after targeted reruns.

## Lessons

1. **Single-fixture falsification gate is necessary but not sufficient.** F2/F5/F4/F9 single-fixture passes (with F9 borderline) didn't predict the F6 regression that only appeared in the integrated suite. Codex round 5's "correct sub-fix inside a failing integrated run is not a ship decision" applies here too — the inverse: passing single-fixture gates is no guarantee the integrated suite passes.
2. **F6 was not in the falsification gate.** The gate covered F2/F5/F4/F9. F6 was not gated independently because iter-0005-full's F6 was bounded-but-not-collapsed. iter-0006's full-suite F6 regression is a new failure mode the gate could not catch by design.
3. **Self-judgment bias risk surfaced.** All variant arms run BUILD/FIX on GPT-5.5; judge is also GPT-5.5. Cross-judge data via Opus 4.7 sidecar (`judge-opus-pass.sh`) — see "Cross-judge sidecar" section below — adds visibility on this. Permanent dual-judge queued as iter-0007/iter-0008 candidate (separate concern from this iter's hypothesis).
4. **Wall-time anomalies are a parallel investigation.** F1 cap-hit, F2 cap-hit, F4 6351s bare, F5 5630s variant — neither correlated with margin sign nor with ship-gate result, but suggest harness/timeout instability that should be characterized.

## Decision (iter-0006 final verdict — 2026-04-26 post-full-suite)

**DEFER iter-0006 verdict (FINAL).** Supersedes the round-12 harness-truth halt above (which was retracted in round 13 via ~/.codex/sessions/ evidence). This DEFER is on different grounds: the contract DID land on the codex path AND DID help F2/F9, but the integrated suite reveals F6 regression and wall-time pathology that block ship.

**Keep contract diff on branch.** Per codex round 14, the diff is not the proven cause of failure; reverting now would also revert the F2/F9 gains.

**Iter-0007 — F6 isolation single-fixture run.** Pre-iter-0007: re-run F6 on iter-0006 HEAD, then on iter-0005-revert HEAD (commit ab15f60 or earlier — pre-foreground-only-contract), with the same fixture timeout. Compare variant scores. If iter-0006 regresses F6 ≥ −20 vs iter-0005-revert, contract is implicated → REVERT diff before pursuing other iters. If F6 is similar across both, F6 is independent and the contract stays.

**Iter-0008 candidate — wall-time pathology investigation.** F4/F5 stuck-execution, F1/F2 cap-hits. Diagnostic first; no contract changes until characterized.

**Iter-0009/0010 candidates** (carried over): watchdog classification bug (round 6 deferral), sync-gap auto-mirror (round 7 Option A), DOCS Job 2 wider verification.

**No baseline freeze.** No SHIP, no `autoresearch/baselines/v3.8-iter0006.json` produced.

## Cross-judge sidecar (Opus 4.7, post-run, 2026-04-26)

Sidecar `benchmark/auto-resolve/scripts/judge-opus-pass.sh` ran Opus 4.7 over the same sanitized blind prompts (no contract change). Self-judgment bias mitigation — variant arms also run BUILD/FIX on GPT-5.5, so the GPT-5.5-only judge is rating its own family's output. Output: `cross-judge-summary.json` at run root, plus per-fixture `judge-opus.json`.

| Fixture | GPT margin | Opus margin | Winner agree | Sign agree |
|---|---|---|---|---|
| F1 | +7 | +2 | ✓ variant | ✓ |
| F2 | +19 (DQ→tie) | +10 | ✗ (DQ override flips winner) | ✓ |
| F3 | +1 | −4 | ✗ | ✗ (close call flip) |
| F4 | 0 | 0 | ✓ tie | ✓ |
| F5 | 0 | 0 | ✓ tie | ✓ |
| F6 | **−65** | **−84** | ✓ bare | ✓ |
| F7 | +2 | −2 | ✗ | ✗ (close call flip) |
| F8 | 0 | 0 | ✓ tie | ✓ |
| F9 | +11 | +3 | ✓ variant | ✓ |

**Aggregate**: winner_agree=6/9 (67%), sign_agree=7/9 (78%), mean_abs_margin_diff=5.56, Pearson(margins)=**0.988**.

**Opus suite avg**: variant 59.2 / bare 67.6 / **margin −8.4** (vs GPT-5.5 suite margin −2.8).

### Implications

1. **iter-0006 DEFER verdict is judge-robust.** Suite avg margin is negative under both judges; Opus's −8.4 is even more pessimistic than GPT's −2.8. F6 regression is amplified under Opus (−84 vs −65). No realistic dual-judge arbitration produces a SHIP outcome.
2. **F2 recovery is real under both judges.** The contract did help on F2 — not a single-judge artifact.
3. **F6 regression is real under both judges.** Iter-0007's F6 isolation single-fixture run is the right next step regardless of judge choice.
4. **Mild self-judgment bias detected.** Opus rates variant ~5.6 pts harsher than bare relative to GPT — i.e., GPT-5.5 inflates variant scores ~5.6 pts on average compared to a cross-model reference. Not catastrophic but real, and it accumulates across iterations. This is direct evidence for the iter-0012 permanent-dual-judge spec at `memory/project_dual_judge_2026_04_26.md`.
5. **Close-call flips (F3, F7) are exactly what dual-judge arbitration is for.** Both fixtures have margins inside ±5 — the kind of result single-judge ship-gates treat as deterministic but actually flip with judge choice. Iter-0012's `judge_disagreement: true` flag would mark these as inconclusive (margin=0) — preserving honesty about measurement uncertainty.

### Note on measurement contract

For iter-0006's ship verdict, the canonical judge per the run-time measurement contract is GPT-5.5. Cross-judge data is sidecar context, not contract. Permanent dual-judge becomes the contract starting iter-0012 (after isolation/wall-time iters land).

## Lessons

(filled after run)

## Codex round 12 — harness-truth finding (2026-04-26, GPT-5.5, xhigh, read-only)

After F9's two failures and the persistent routing-telemetry miss across all 5 fixtures, I dug into the variant arm's `claude-debug.log` files for prior runs. **Across iter-0001 through iter-0006, the variant arm has been issuing zero `codex exec` shell commands.** Spot checks:

| Run | `codex exec` invocations |
|---|---|
| iter-0005 F7 (the "successful inner-codex isolation" success, margin +3) | **0** |
| iter-0005-full F2 (the "−82 collapse" whose transcript said "Codex is running. I'll wait for completion notifications.") | **0** |
| iter-0006 F2/F5/F4/F9 #1/F9 #2 | **0 (all five)** |

`codex` is on PATH (`/Users/aipalm/.superset/bin/codex`, version 0.124.0). The variant arm's `claude -p` subprocess uses `--strict-mcp-config --mcp-config '{"mcpServers":{}}'` (iter 0004) which blocks `mcp__codex-cli__codex`, but `--dangerously-skip-permissions` allows arbitrary Bash, including `codex exec`. The orchestrator simply has not been shelling out.

`auto-resolve/SKILL.md` explicitly says "Phases routed to **Codex**: shell out to `codex exec` per the canonical flag set..." and `engine-routing.md` puts BUILD/FIX on Codex under `--engine auto`. Yet across all measured runs, BUILD/FIX have run on Claude.

Implications (per codex round 12):
1. **iter 0001–0006 all measured Claude-only variants vs Claude bare arms.** The "Codex builds, Claude critiques" GAN dynamic claimed by CLAUDE.md and README is not actually exercised by the benchmark.
2. **iter 0005's inner-codex-isolation hypothesis was logically unfalsifiable** — flags applied to codex calls that were never made cannot have caused the F7 −42 → +3 swing. The recovery's actual cause is something else (variance, the iter-0004 outer-MCP isolation alone, or sampling).
3. **iter 0006's foreground-only contract is theoretically meaningful but practically not testable** on the existing fixtures, because the BUILD path the contract regulates is not being entered.
4. **iter-0005 F2 transcript "Codex is running. I'll wait for completion notifications."** was likely a hallucinated state — the orchestrator wrote it but never ran `codex exec`. The 2 LocalShellTask kills were some other Bash hang (likely `tail -f` of a non-existent file the orchestrator imagined codex was writing).

Codex round 12 ruling (verbatim):

> You're right to halt. This is a harness-truth failure, not a tuning issue. If logs show zero `codex exec` across the runs used to support routing claims, then Codex/Claude split conclusions are invalid. Continuing iter-0006 now would only add bad evidence. Freeze benchmarking, then add a hard invariant: under `--engine auto`, BUILD/FIX must produce at least one observable `codex exec` or the run fails. Also log effective `PATH`, `which codex`, and command traces inside the `claude -p` subprocess to isolate downgrade vs routing noncompliance. After root-cause + fix, run one forced canary to prove the path, then resume normal iterations.

## Decision

**DEFER iter 0006 verdict.** The contract diff (foreground-only) stays on this branch as proposed work; it costs nothing to keep. Do NOT run the full suite, do NOT claim ship eligibility. The falsification gates (F2/F5/F4/F9 — three pass-by-margin, one borderline-fail-by-strict-criteria) are mechanism-indeterminate because the contract's claimed surface area (codex invocation) was never entered.

**Pivot to iter-0007 — Harness-truth investigation: reproduce the missing codex invocation and root-cause it.** Sequence per codex round 12:

1. Add diagnostic logging at the top of `run-fixture.sh` variant arm: write `PATH`, `which codex`, `codex --version` into the result dir before invoking `claude -p`. (Eliminates "codex not on PATH" hypothesis or confirms it.)
2. Reproduce a single fixture and inspect the SDK's tool-call trace in `claude-debug.log` for any sign of codex shell-out attempt or downgrade. Look for `engine downgraded: codex-unavailable` in the orchestrator's final report.
3. If silent-downgrade is the cause: trace it to the engine-preflight check, harden the check, log the downgrade explicitly in transcript.
4. If routing-noncompliance is the cause (orchestrator chose Claude despite routing table): tighten skill prompt or harness invariant.
5. Add a hard run-fixture invariant: under `--engine auto`, BUILD/FIX must produce ≥1 observable `codex exec` invocation in the per-arm debug log, OR the run is marked `invoke_failure: true` with reason `engine_routing_violated`. This is an observable check, not a behavior change.
6. After fix, build the codex-forced canary fixture (the round 8 ruling) to validate the iter-0006 foreground-only contract on its actual surface area.
7. Then resume normal iteration cadence — re-measure prior iterations against the corrected harness to determine whether their conclusions still hold.

The iter-0007 sync-gap-mirror work (codex round 7 Option A) and the watchdog classification bug (codex round 6 deferral) become iter-0008 and iter-0009 candidates respectively, behind the harness-truth iteration in priority.
