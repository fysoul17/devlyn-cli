# 0007 — F6 isolation single-fixture experiment (iter-0006 contract attribution)

**Status**: COMPLETE. Verdict: REVERT iter-0006.
**Started**: 2026-04-26
**Decided**: 2026-04-26

## Hypothesis

iter-0006's full-suite F6 collapse (variant 31 / margin −65 / 0 files / verify 0.33 / timed_out=true) was attributed by codex Round 14 to "contract-induced routing/budget starvation," but causality was not established. Possible mechanisms:

- **A**: iter-0006 foreground-only contract directly caused F6 to fail (contract-caused collapse).
- **B**: F6 has been chronically broken across iterations; iter-0006-full just got an unlucky run (chronic-but-noisy).
- **C**: Suite-cumulative load (7hr full-suite) hit F6 with API failures or resource exhaustion (suite-environmental).

Wall-time history (`autoresearch/walltime-history.md`) ruled out **B** for the 0-file/empty-transcript pattern: F6's variant arm produced 2-4 files / 4-6KB diff / verify 0.83 across **every prior iteration**. iter-0006-full's 0/0/0.33 was a clean break.

To discriminate **A vs C**: run F6 alone (no suite cumulative load) on iter-0006 HEAD, then compare against d895ffa (iter-0005-revert HEAD = state immediately before iter-0006 contract).

## Mechanism

Why-chain (extending from iter-0006):

26. Why was F6 single-fixture not in the original iter-0006 falsification gate? → Gate covered F2/F5/F4/F9 because iter-0005-full's F6 was bounded-but-not-collapsed (variant 1496s, 2 files, verify 0.83). F6 wasn't expected to regress.
27. Why does the contract regulate F6 differently than F2? → Contract bans `&` / `tail -f` / `Monitor` / `run_in_background` — eliminates background patterns. F2's failure mode in iter-0005 was "background codex + Stop response while codex still running" — exactly what contract bans. F6 may rely on background-with-tail to keep orchestrator stream alive during long codex thinking — which contract also bans.
28. Why would foreground codex break F6 but not F2/F4/F7? → If F6's BUILD codex call exceeds the orchestrator's API stream heartbeat tolerance (e.g., 10 min single Bash dispatch with no streaming), the orchestrator's connection state may degrade. Other fixtures have shorter codex calls.
29. Why didn't iter-0006 single-fixture F2/F5/F4 catch this? → Those fixtures' codex calls completed within shorter durations and didn't trigger the long-block failure mode. F6 is the canary fixture for long codex calls.
30. Root: foreground-only is too universal a rule. The actual failure-mode-of-concern (iter-0005's F2) is "orphaned/unmonitored background codex," not "all background codex." iter-0006 contract is over-specified.

## Diff plan

Two stages:

**Stage A — Diagnostic (this iteration)**: no diff. Just two F6-alone benchmark runs (iter-0006 HEAD vs d895ffa worktree) to establish causality. Both runs use existing run-suite.sh / run-fixture.sh / judge.sh; no harness changes.

**Stage B — Action (per verdict)**: if causality established → REVERT 1ac7594. Frame iter-0008 hypothesis: narrower kill-shape contract banning only orphaned/unmonitored background codex.

## Codex round 15 cross-check (pre-data)

Confirmed iter-0007 design: F6 single-fixture × 2 HEADs is minimal-information experiment. Folded iter-0008 (wall-time investigation) as read-only diagnostic in `walltime-history.md` rather than separate iteration. Cut iter-0012 (permanent dual-judge in judge.sh) — sidecar covers immediate need.

## Codex round 16 cross-check (mid-data)

Caught two errors in my first-draft `walltime-history.md`:
1. F6 prior-iter 0-files claim was a CSV-column misread (actual values: 4, 3, 3 — not 0). Corrected: F6 chronic 0-file pattern does NOT exist; iter-0006-full's 0 files IS unique.
2. F4/F5 "environmental noise" framing was too vague. Sharpened to "shared runtime/API failure" backed by direct artifact evidence (`Stream idle timeout`, `FailedToOpenSocket`, `ConnectionRefused` strings in claude-debug.log).

Decision rule sharpened from ≥20-score-regression to: "if d895ffa enters BUILD and produces files while iter-0006 does not → contract directly implicated."

## Actual change

### Run 1 (iter-0006 HEAD F6 alone, run-id `20260426T122836Z-1ac7594-iter-0007-f6-iso-on-0006`, 2026-04-26 12:28–12:53Z)

| Signal | Pass criterion | Observed | Status |
|---|---|---|---|
| variant_score | ≥ baseline (~92) | **35** | ✗ |
| diff_bytes | > 0 | **0** | ✗ |
| files_changed | > 0 | **0** | ✗ |
| transcript.txt size | > 0 bytes | **0 bytes (empty)** | ✗ |
| variant verify | ≥ 0.66 | **0.33** | ✗ |
| timed_out | False | **True** | ✗ |
| invoke_exit | 0 | **124** (watchdog) | ✗ |
| variant elapsed | clean exit < 1500s | **1500s (cap hit)** | ✗ |

**Reproduces** the iter-0006-full F6 collapse at single-fixture isolation. Suite-cumulative load is NOT the cause.

claude-debug.log diagnostic: a single `tool=Bash durationMs=600695` (10 min) dispatch in the middle of the run — the foreground codex exec call. Returned `outcome=ok`. After that, orchestrator did not resume meaningful work; transcript stayed at 0 bytes; watchdog killed at 1500s. API error count: 1 (low — not the dominant signal).

### Run 2 (d895ffa F6 alone, run-id `20260426T125555Z-d895ffa-iter-0007-f6-iso-on-d895ffa`, 2026-04-26 12:55–13:14Z)

| Signal | Pass criterion | Observed | Status |
|---|---|---|---|
| variant_score | ≥ baseline (~92) | **93** | ✅ |
| diff_bytes | > 0 | **5248** | ✅ |
| files_changed | > 0 | **3** (`bin/cli.js`, `tests/checksum.test.js`, docs/roadmap/phase-1/F6-...) | ✅ |
| transcript.txt size | > 0 bytes | **2213 bytes** | ✅ |
| variant verify | ≥ 0.66 | **0.83** | ✅ |
| timed_out | False | **False** | ✅ |
| invoke_exit | 0 | **0** | ✅ |
| variant elapsed | clean exit | **1098s** | ✅ |
| margin | informational | −3 (vs bare 96) | normal range |

Variant produced healthy output matching the chronic baseline (2-4 files, ~5KB diff, verify 0.83). Critical findings: minor scope leak (touched docs/roadmap metadata).

### Discriminator

| Signal | Run 1 (iter-0006) | Run 2 (d895ffa) | Δ |
|---|---|---|---|
| variant_score | 35 | 93 | **+58** |
| files | 0 | 3 | +3 |
| diff_bytes | 0 | 5248 | +5248 |
| transcript bytes | 0 | 2213 | +2213 |
| verify | 0.33 | 0.83 | +0.50 |
| invoke_exit | 124 | 0 | (clean) |
| timed_out | True | False | (clean) |

Same fixture, same harness, same skill chain except for iter-0006's 19-line foreground-only execution contract addition + 2-line engine-routing edit. **Variant score improves by 58 points when the contract is removed.** Causality established.

## Codex round 17 cross-check (post-data)

Verdict: **REVERT.** Mechanism read confirmed: foreground codex monopolizes the orchestrator for ~10 min Bash dispatch; after return, orchestrator does not recover stream control, watchdog kills. Universal foreground-only rule is too broad; long-running codex needs background + active observation (tail / poll / progress emission) to keep orchestrator alive.

Round 17 next-iter framing: **iter-0008 = narrow kill-shape ban.** Target the exact F2 failure class — orphaned/unmonitored background codex while orchestrator ends response. Allow background execution paired with active observation. "Ban orphaned background codex, not background codex itself."

## Lessons

1. **Universal contract rules can over-fit single failure modes.** iter-0006 banned a category (all backgrounding) to prevent a specific failure shape (unobserved background + Stop). The category is broader than the failure shape. F6 needed something the category enabled.
2. **Single-fixture isolation is the cheap discriminator.** 1hr (2 × ~30 min) gave us proof-of-causality that 7hr full-suite couldn't disentangle. Future "is contract X load-bearing?" questions should use this pattern by default.
3. **Bare-Case Guardrail violations are qualitative, not score-noise.** F6's 0-file / empty-transcript / watchdog-kill is a categorical product defect, not a "harder fixture got harder" signal. Treat that level of regression as immediate REVERT trigger.
4. **Read your own data carefully.** Round 16 caught me misreading my own CSV column order on F6's prior-iter file counts. The "harness false-negative" insight (verify capped at 0.83 by the `# fail 0` TAP rule) was also gained in that round — important context for interpreting future verify scores.

## Decision

**REVERT iter-0006 commit 1ac7594.**

- Restore `config/skills/_shared/codex-config.md` and `config/skills/devlyn:auto-resolve/references/engine-routing.md` to d895ffa state.
- Sync `.claude/skills/` to match the reverted `config/skills/` (cp the two files).
- Lose F2's iter-0006 +19 recovery; lose F9's +11; lose F7's +2 — but regain F6's −65 → ~0.
- Suite returns to iter-0005-revert (≈ iter-0004) effective state on the skill axis. F2's iter-0005-full collapse mechanism is back on the table — but iter-0008 will address it surgically.

**Next: iter-0008 — narrow kill-shape contract.** Replace the universal "foreground-only" rule with a targeted "no orphaned/unmonitored background codex" rule. Keep monitored background allowed. Re-run F2 single-fixture as the falsification gate; F6 single-fixture as the regression-prevention gate. Two-fixture gate before any full-suite.

**Skill guardrails memo grounded in this experiment**: separate doc to capture the auto-resolve product-quality lessons (no zero-file long runs, stuck-execution abort criteria, command discovery before edits, bare-case modal regression gate). See `memory/project_skill_guardrails_2026_04_26.md`.

**No baseline freeze.** Branch HEAD becomes the revert commit.
