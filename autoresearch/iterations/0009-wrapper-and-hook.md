# 0009 — Wrapper + PATH shim (executable enforcement of codex invocation shape)

**Status**: IN PROGRESS — falsification gate pending
**Started**: 2026-04-27
**Decided**: (not yet)

## Hypothesis

iter-0008 proved prompt-level instruction in `_shared/codex-config.md` cannot constrain orchestrator codex invocation shape: the variant orchestrator read the contract and chose explicitly-forbidden `codex exec ... 2>&1 | tail -200` from its own pattern prior anyway. Codex Round 2 (post-data) verdict: **executable enforcement, ranked HYBRID (D + C) — wrapper + PreToolUse:Bash hook.**

iter-0009 implements that, with one substitution Codex Round 1 (this iter) flagged as load-bearing: **drop the Bash hook, replace with a PATH shim**. Hook regex is too easy to evade (`bash -lc 'codex exec ...'`, scripted invocations, `c=codex; "$c" exec ...`, env-prefixed forms), and hook behavior under `--dangerously-skip-permissions` (the flag the variant arm uses) is unverified. PATH shim binds at a layer no shell-level indirection can bypass — every form of invocation resolves `codex` through PATH, and PATH is inherited into nested shells, scripts, and indirected calls.

The fix targets the same root iter-0008 named (orchestrator-controls-its-own-codex-shape), but at a layer the orchestrator can't override. Short codex calls (≤30s) and long codex calls share one mechanism: the wrapper. `codex exec` becomes a single shape, not a contract surface.

**Predicted**: F1 finishes <480s with `timed_out: false` AND `invoke_exit: 0` (Codex Round 1 Q5 reclassification of iter-0008's PASS-but-timed_out). F6 healthy (variant_score ≥ 85, files ≥ 1, transcript > 0, exit 0, NOT timed_out, wrapper invocation visible in transcript with heartbeat lines). F2 recovers (margin ≥ +5, no LocalShellTask kills). Negative canaries demonstrate binding: even raw `codex exec | tail -200` and `bash -lc 'codex exec ...'` are transparently re-routed through the wrapper with heartbeat bytes flowing.

## Mechanism

Why-chain (extending iter-0008's chain at #36):

37. Why does prose mandate fail? → The orchestrator's pattern prior over codex invocation shapes is stronger than any prose contract it reads. iter-0008 contract listed `| tail -200` under "Forbidden" but the orchestrator picked it anyway. The mandate is a *suggestion* layer; the prior is a *binding* layer. They're not the same layer.
38. Why does a Bash hook also fail? → Hook regex over the command string can be defeated by `bash -lc 'codex exec ...'`, `env codex exec`, scripted invocation (PreToolUse sees `bash /tmp/x.sh`, not the script body), and indirection (`c=codex; "$c" exec ...`). Hook also has unverified behavior under `--dangerously-skip-permissions` — and the benchmark variant arm uses that flag at `run-fixture.sh:269`. (Codex Round 1 critique surfaced all of these.)
39. Why is a PATH shim more robust than a hook? → Every shell that resolves `codex` does so through PATH lookup. `bash -lc`, scripts, `env`, `command`, `nohup`, `time`, indirected variable expansions — all inherit PATH and resolve `codex` to the shim. Independent of the hook subsystem, independent of any flag. The shim is at the shell-resolution layer; the hook is at the tool-dispatch layer.
40. Why is the wrapper still needed? → The wrapper is what forces the SHAPE: `< /dev/null` stdin (kills codex 0.124.0 prompt-arg+stdin hang), no `tail -n` truncation (preserves full stdout for read-only critic phases that consume codex's reply), heartbeat-every-30s on stdout (keeps the byte-level idle watchdog fed independent of codex's own progress emission), signal forwarding (TERM/INT propagated to codex child so the outer process-group watchdog at `run-fixture.sh:282` actually reaps codex). The shim is the binding; the wrapper is the contract.
41. Why must inline call sites still be edited? → For the orchestrator's first-attempt to have the right shape (less surprise / fewer wrapper-invocation echoes in transcripts). The shim catches it on the second attempt anyway, but the Karpathy #2 cost is small (3 surfaces: canonical + engine-routing.md + auto-resolve/SKILL.md). Codex Round 1 Q6 explicitly flagged: keep the surfaces the benchmark actually reads; cut team-* (manual tools, off the auto-resolve hot path) and cut ideate/preflight inline rewrites (PATH shim makes them transparent at runtime).
42. Why a shim AND a wrapper, not just one? → A shim alone wouldn't enforce shape (it would just reroute to raw `codex exec` from a different path). A wrapper alone wouldn't bind (orchestrator can ignore it, as iter-0008 proved). Both are necessary and neither alone is sufficient.
43. Root: orchestrator-codex-shape is now governed at the resolution layer (PATH shim) AND the invocation layer (wrapper), not at the prompt layer (iter-0006/0008). Both layers are below the orchestrator's control surface.

## Predicted change

(Predictions BEFORE the gate runs — per Principle #2. Updated post-Codex Round 1.)

- **F1 alone** (~3 min smoke, G4 bare-case-modal regression gate): variant_score ≥ 85, margin ≥ +5, files_changed ≥ 1, **`timed_out: false` AND `invoke_exit: 0`** (the iter-0008 reclassification — score-PASS with watchdog kill is a gate failure). Variant elapsed < 200s typical, < 480s hard cap.
- **F6 alone** (~22 min, regression-prevention proof — the failure shape iter-0006 caused, iter-0008 reproduced): variant_score ≥ 85, files_changed ≥ 1, verify ≥ 0.66, transcript > 0 bytes, invoke_exit = 0, timed_out = false, variant elapsed clean exit (< 1500s wall cap), `[codex-monitored] start` line visible in transcript, `[codex-monitored] heartbeat` lines visible during long phases. Holds the d895ffa F6 baseline (variant 93, +3 files, 5.2KB diff).
- **F2 alone** (~22 min, recovery proof — the original failure shape iter-0006 fixed): margin ≥ +5, variant_score ≥ 85, files_changed ≥ 1, diff_bytes > 0, `LocalShellTask kill requested` count = 0, transcript > 1 KB, invoke_exit = 0, timed_out = false. Recovers iter-0006 F2 result (+16 margin) without iter-0006's universal contract.
- **Negative canary 1** (binding test, ~3 min standalone): orchestrator instructed to attempt `codex exec ... 2>&1 | tail -200`; PASS only if the run shows wrapper invocation in transcript (PATH shim transparently re-routed) with heartbeat bytes flowing — NOT if the orchestrator manages to bypass.
- **Negative canary 2** (bypass form): orchestrator instructed to attempt `bash -lc 'codex exec ...'`; PASS only if shim still routes (bash inherits PATH).
- **Routing telemetry — 6-element evidence (per iter-0008 codex Round 1 Q4, retained)**: across F2 + F6, run artifacts must collectively show: (1) `codex exec` actually observed in claude-debug.log (≥1 hit), (2) wrapper invocation visible (`[codex-monitored] start` line in transcript), (3) heartbeat present during long phases, (4) orchestrator did NOT emit Stop while codex child alive, (5) transcript non-empty, (6) byte-watchdog did NOT fire (`Stream idle timeout (byte-level)` absent in claude-debug.log).
- **Forced-Codex canary (conditional, per Codex Round 1 Q5)**: if F2 didn't actually invoke Codex (per `~/.codex/sessions/` evidence + claude-debug.log grep), build a forced-Codex canary fixture (spec language demands a Codex-routed BUILD or FIX phase) and run it before suite. F2 has gone Claude-only across some iter-0006 runs — without this check, the wrapper's value isn't proven by F2 alone.
- **Suite (only after gate + telemetry pass)**: predicted suite avg margin in the +8 to +12 range — recovery of d895ffa baseline. Ship-gate ≥ 7/9.

## Diff plan

Seven edits — no new abstractions, two new scripts, one harness extension.

1. **`config/skills/_shared/codex-monitored.sh`** (NEW, ~70 lines incl. comments). Wrapper. `< /dev/null` stdin redirect, full stdout streaming (no log file, no tail), heartbeat sidecar @ `CODEX_MONITORED_HEARTBEAT` (default 30s) emitting `[codex-monitored] heartbeat: elapsed=Ns` lines, signal traps forwarding TERM/INT to codex child + heartbeat sidecar, exit-code preservation. Reads `CODEX_BIN` env so it can call the real binary when the shim has put us first on PATH.

2. **`scripts/codex-shim/codex`** (NEW, ~55 lines incl. comments). PATH shim. If `$1=="exec"`, route to `$CODEX_MONITORED_PATH`; else `exec "$CODEX_REAL_BIN" "$@"`. Critical detail: strips its own directory from PATH before delegating, so wrapper-of-wrapper chains (e.g. Superset's `~/.superset/bin/codex` re-discovers binary by scanning PATH) cannot loop back to us.

3. **`config/skills/_shared/codex-config.md`** (EDIT). Canonical examples now use `bash .claude/skills/_shared/codex-monitored.sh ...`. New paragraph documents: wrapper purpose (heartbeat, stdin discipline, no truncation), why raw `codex exec` is forbidden in skill prompts, that the benchmark variant arm runs a PATH shim as runtime safety net.

4. **`config/skills/devlyn:auto-resolve/references/engine-routing.md`** (EDIT, two lines). `Codex call defaults` sentence (line 7) and team-role footer (line 74) point at the wrapper.

5. **`config/skills/devlyn:auto-resolve/SKILL.md`** (EDIT, line 34). Engine-routing convention bullet for Codex routes points at the wrapper.

6. **`benchmark/auto-resolve/scripts/run-fixture.sh`** (EDIT, ~30 lines added). For variant arm only: capture `CODEX_REAL_BIN=$(command -v codex)` BEFORE prepending shim PATH, copy shim into `$WORK_DIR/.devlyn-bin/codex`, set `CODEX_MONITORED_PATH=$WORK_DIR/.claude/skills/_shared/codex-monitored.sh`, export both, prepend `$WORK_DIR/.devlyn-bin` to PATH inside the `claude -p` subshell. Bare arm gets nothing.

7. **`scripts/lint-skills.sh`** (EDIT). Mirror parity check 6 extended to include `_shared/codex-config.md` and `_shared/codex-monitored.sh`. New post-loop check ensures `codex-monitored.sh` is executable in the installed mirror.

NOT in this diff (deliberately deferred per Karpathy #3 surgical, per Codex Round 1 Q6):
- ideate/SKILL.md, ideate/codex-critic-template.md, preflight/SKILL.md, team-resolve/SKILL.md, team-review/SKILL.md inline rewrites. PATH shim makes them transparent at runtime; rewriting ahead of evidence is scope expansion.
- PreToolUse:Bash hook + .claude/settings.json edits. Replaced by PATH shim per Codex Round 1 Q1.
- Lint check for raw-`codex exec` leaks in skill prompts. With shim binding behavior, doc drift is cosmetic, not correctness. Defer.
- Packaging extension to ship `scripts/codex-shim/codex` to user installs. Benchmark-only for iter-0009; user-facing rollout is iter-0010+ (only if benchmark proves it).
- `~/.claude/settings.json` user-scope hook fallback. Codex Round 1 Q3 explicitly preferred project-scope, and PATH shim removes the need entirely.

## Falsification gate

Five steps sequential, plus conditional canary. Karpathy #2 — load-bearing fixtures only.

**Pre-gate** — sync `.claude/skills/` ← `config/skills/` and verify `diff -rq config/skills/ .claude/skills/ 2>&1 | grep -v "Only in"` returns silence. Run `bash scripts/lint-skills.sh` — must exit 0.

1. **Negative canary 1 — observed bad shape** (~3 min standalone). Build a one-shot variant-arm fixture whose spec demands a Codex-routed call. Instruct the orchestrator inside the prompt to attempt the iter-0008 forbidden shape `codex exec -C . -s read-only -c model_reasoning_effort=xhigh "<short prompt>" 2>&1 | tail -200`. PASS criterion: transcript shows `[codex-monitored] start` line — proof the shim re-routed; codex Round 1 Q5 critique adopted.
2. **Negative canary 2 — bypass form** (~3 min standalone, only if canary 1 PASSes). Same shape but `bash -lc 'codex exec ... 2>&1 | tail -200'`. PASS: shim still routes (bash inherits PATH).
3. **F1 alone** (~3 min, G4 bare-case-modal). Pass: variant_score ≥ 85, margin ≥ +5, files_changed ≥ 1, **`timed_out: false` AND `invoke_exit: 0`**. Failure → wrapper or shim broke trivial routing; redesign before F2/F6.
4. **F6 alone** (~22 min, regression-prevention proof). Pass criteria above PLUS the 6-element telemetry. Failure → REVERT iter-0009 immediately.
5. **F2 alone** (~22 min, recovery proof). Pass criteria above. Failure → re-diagnose with codex Round 2 before any further runs.

**Conditional canary** — if F2 didn't actually invoke Codex (per `~/.codex/sessions/` evidence + claude-debug.log grep), build a forced-Codex fixture (spec language demands Codex-routed BUILD or FIX) and run before suite. Codex Round 1 Q5 surfaced this — F2 alone is a regression check, not direct wrapper proof.

Only run full suite if all 5 (or 6) pass. Cumulative gate cost ~55 min wall (or ~75 min with conditional canary), vs iter-0008's 4-fixture gate which was ~50 min.

F4/F5/F9 single-fixture gates remain OUT of this iter (per iter-0008 Q1 boundary): not stream-starvation root, not regulated by this contract; full suite remains mandatory before ship verdict.

## Skill guardrails check (G1–G5 per `memory/project_skill_guardrails_2026_04_26.md`)

| # | Guardrail | iter-0009 stance |
|---|---|---|
| G1 | Long codex calls must remain observable | ✅ Wrapper EMITS observability — `[codex-monitored] heartbeat` every 30s on stdout. Operationalizes G1 at the binding layer. iter-0008's live G1 evidence (this round's own R1 also hung 11.5min on a 1MB-output codex call before completing) reinforces: silence ≠ stuck, but unmonitored long calls produce the byte-watchdog failure. Heartbeat bytes flow even if codex's own progress emission stalls. |
| G2 | No zero-file long runs | ⚠️ Indirect. Wrapper does not directly prevent zero-file runs — but the stream-starvation collapse mode (which causes them) is closed. If F6 still produces zero files, root cause is no longer harness-level, and a different iter takes over. |
| G3 | Command discovery before edits | — Orthogonal; wrapper does not regulate inventory step. Falls under fixture spec design. |
| G4 | Bare-case modal regression gate | ✅ F1 + F6 + negative canaries in the falsification gate. F1 catches trivial-route confusion; F6 catches long-codex regression; canaries catch binding-layer failure. |
| G5 | Stuck-execution abort criteria | ⚠️ Wrapper signal traps forward TERM/INT to codex child — outer watchdog kill at `run-fixture.sh:282` now actually reaps codex (instead of orphaning the codex child). Operationalizes part of G5 (timely abort), though not the proactive self-abort piece. |

## Principles check (provisional, finalized after run)

| # | Principle | Status | Evidence |
|---|---|---|---|
| 1 | No overengineering | (provisional ✅) | Two new scripts (~125 lines total), three skill-prompt edits (~6 lines net), one harness extension (~30 lines), one lint extension (~15 lines). No new abstractions, no new flags, no new phases. Cuts five inline rewrites that iter-0008 did. |
| 2 | No guesswork | ✅ | Hypothesis names the failure layer (orchestrator-resolves-codex-via-PATH), the binding layer (PATH shim) and contract layer (wrapper) separately, the metrics (F1 timed_out=false AND invoke_exit=0; F6 ≥85/≥1file/>0 transcript/wrapper visible/heartbeat present; F2 ≥+5 margin; canaries route via shim), and the why-chain steps 37–43 trace mechanism. All Predicted change values written before the gate runs. |
| 3 | No workaround | ✅ | The fix lands at the resolution layer where the orchestrator's freedom over PATH lookup exists, not at the prompt layer (which iter-0006/0008 proved doesn't bind). Six why-steps in Mechanism. |
| 4 | Worldclass production-ready | (filled after gate run) | Will check: zero CRITICAL on either gate fixture, no regression that introduces new HIGH on previously-clean fixtures. Wrapper signal traps + macOS-portable bash builtins reviewed; heartbeat sidecar tested for clean tear-down. |
| 5 | Best practice | (filled after gate run) | Will check: zero `design.unidiomatic-pattern` MEDIUM regression. Shim follows POSIX-friendly conventions; PATH stripping is robust to wrapper chains. |

## Codex round 1 cross-check (post-design, 2026-04-27)

Run-id: `/tmp/codex-iter0009-r1.out`, gpt-5.5 xhigh read-only, 1.16MB, exit 0. Submitted via monitored-background (file redirect + Monitor poll). Round duration ~17.5 min wall (xhigh reasoning).

**Verdict: REWORK.** Original iter-0009 design was sound at the wrapper level but wrong at the binding level. Largest single change: drop the PreToolUse:Bash hook, replace with PATH shim.

**Q1 — Hook robustness.** Codex flatly rejected token-aware Bash hook regex as binding mechanism. Enumerated bypasses: `bash -lc 'codex exec ...'`, `sh -c`, `env codex exec`, `command codex exec`, `time codex exec`, `nohup codex exec`, scripted invocations (`printf 'codex exec ...' > /tmp/x.sh; bash /tmp/x.sh` — PreToolUse sees `bash /tmp/x.sh`, not script body), variable indirection (`c=codex; "$c" exec ...`), absolute paths (`/opt/homebrew/bin/codex exec`), heredocs, process substitution. Plus uncertainty: hooks under `--dangerously-skip-permissions` (the variant arm uses this) is unverified. **Adopted: replace hook with PATH shim. Shim binds at shell-resolution layer; all enumerated bypasses inherit PATH and resolve cleanly.**

**Q2 — Wrapper semantics.** Heartbeat shape (30s @ 300s byte-watchdog) directionally right; **tail-only output WRONG**. Existing docs at `_shared/codex-config.md:51`, `ideate/SKILL.md:300`, `team-resolve/SKILL.md:147` say orchestrator reads codex stdout AS THE SUBAGENT REPLY. Truncating to last 200 lines silently drops critic/auditor findings — would pass BUILD/FIX fixtures while breaking read-only Codex roles. **Adopted: wrapper streams full stdout, no log file, no `tail`. Heartbeat is metadata interleaved into stdout (line-prefixed `[codex-monitored]` so the orchestrator can filter).** Also adopted: signal traps forwarding TERM/INT to codex child + heartbeat sidecar.

**Q3 — Hook drift / settings placement.** Project-scope settings.json copy is right (vs user-scope leak). Two drift traps: settings copy must happen pre-baseline like skills (`run-fixture.sh:63`), and benchmark copies from `.claude/skills/` not `config/skills/` (`run-fixture.sh:66`) — current lint mirror parity at `lint-skills.sh:118` only checks 3 critical SKILL.md files, NOT `_shared`. Stale-mirror risk. **Resolved by switching to PATH shim:** no settings.json in scope (PATH shim isn't a hook). But the lint mirror parity gap was real and load-bearing for the wrapper too — adopted that piece (extended check 6 to include `_shared/`).

**Q4 — Hook latency.** Moot — no hook. PATH shim resolution is a kernel-level execve(), zero observable overhead.

**Q5 — Falsification gate.** Codex flagged three gaps. (1) Negative canary too narrow — tests one bad string, not binding mechanism. **Adopted: two canaries — exact iter-0008 shape AND bash-lc bypass form.** (2) F2 is regression check, not wrapper proof. **Adopted: conditional forced-Codex canary if F2 didn't actually invoke Codex.** (3) F1 must require `invoke_exit == 0` AND `timed_out: false`, not just margin. **Adopted.**

**Q6 — Inline call-site rewrites.** With runtime binding (shim), only the surfaces the benchmark actually reads need editing. Cut ideate, preflight, team-resolve, team-review (manual surfaces, off the gate per `CLAUDE.md:60`). **Adopted: 3 surfaces edited (canonical + engine-routing.md + auto-resolve/SKILL.md), down from iter-0008's 7.**

**Q7 — Missing items.** Adopted: signal traps in wrapper, full-output preservation, mirror parity for `_shared/codex-monitored.sh`, JSON-only `.claude/settings.json` (moot — no hook), packaging deferral (iter-0010+), macOS-portable bash builtins (`pwd -P`, no `mktemp -t`). Prompt-size/quoting strategy: closing stdin removes the safe channel for very large prompts — accepted tradeoff because (a) skills inline prompts as args anyway, (b) codex 0.124.0's `<stdin>` block bug is the alternative cost.

**Q8 — Highest-risk unknown.** Codex predicted: first iter-0009 failure will be **hook binding**, not wrapper logic. Adopted as falsification gate's primary signal — negative canaries explicitly test binding, not wrapper. With shim replacing hook, the analogous prediction is: first failure will be the shim's PATH-stripping logic on a wrapper-chain we haven't enumerated. F6 + canaries surface this if it manifests.

**Independent finding (codex did not see this).** Local `codex` CLI is itself a wrapper at `~/.superset/bin/codex` (Superset agent-wrapper v1) that re-discovers the real binary by scanning `$PATH` minus its own directory. If the iter-0009 shim is on PATH, Superset's `find_real_binary` finds OUR shim and recurses. **The shim must strip its own directory from PATH before delegating.** Verified at smoke-test time — initial shim implementation deadlocked on this; final implementation includes `clean_path()` that filters via `pwd -P` resolution.

**Synthesis decisions.**
- Drop hook, drop hook script, drop `.claude/settings.json` edits.
- Add PATH shim with self-stripping logic.
- Wrapper streams full stdout; heartbeat interleaved on stdout (not log + tail).
- Signal traps in wrapper for TERM/INT forwarding.
- Falsification gate has TWO negative canaries (binding test) plus reclassified F1 criteria.
- Diff scope cut from 10+ files (original iter-0009 plan) to 7. Cut team-* / ideate / preflight inline rewrites.

## Codex round 2 cross-check (post-build, pre-gate, 2026-04-27)

Run-id: `/tmp/codex-iter0009-r2.out`, gpt-5.5 xhigh read-only, 128KB, exit 0. Submitted via monitored-background. Round duration ~6 min wall.

**Verdict: TWO CRITICAL FIXES + minor polish.** Largest catch: **shim alone does NOT defeat `| tail -200`.** The shim re-routes the codex invocation, but if orchestrator wraps the whole bash dispatch in `... 2>&1 | tail -200`, the `tail` downstream of the wrapper still buffers all output until EOF — including the heartbeat — and the byte-watchdog fires anyway. Same iter-0008 mechanism, different invocation surface. The shim is necessary but not sufficient; the **wrapper must refuse pipe-stdout directly**.

**Finding #1 (CRITICAL) — pipe-stdout starvation persists.** Adopted as runtime fix: wrapper refuses to run when `[ -p /dev/stdout ]` is true, exits 64 with a clear message pointing at the unbuffered alternative. Tests confirmed `bash WRAPPER ... | tail` and `bash WRAPPER ... 2>&1 | tail` both REFUSE, while `bash WRAPPER ... > /tmp/log` and shim-routed direct invocation both RUN normally. POSIX-portable, no `stat` dependency, single-line check. Combined with the shim, this closes both binding-layer escapes (raw `codex exec`) and shape-layer escapes (`| tail`).

**Finding #1.b — heartbeat moved to stderr.** Round 2 noted that emitting `[codex-monitored]` lines on stdout pollutes the orchestrator's "subagent reply" view. Adopted: heartbeat + start + exited lines on stderr, codex output stays clean on stdout. Orchestrator's bash tool captures both fds combined, so the byte-watchdog still sees stderr bytes — direct (non-piped) invocations are doubly defended.

**Finding #2 (HIGH) — `timed_out` misclassification at boundary.** `result.json` derives `timed_out` from `elapsed >= timeout` (`run-fixture.sh:477`), not from the watchdog flag (`run-fixture.sh:301`). At-boundary natural exits can be misclassified. **NOT fixed in iter-0009** — orthogonal benchmark-harness bug, queued as iter-0011 candidate. Mitigation: gate criteria use `invoke_exit==0` (which IS authoritative — set to 124 only when the watchdog flag fires) instead of `timed_out==false`.

**Finding #3 (MEDIUM) — non-auto-resolve standalones still raw-`codex exec`.** `ideate/SKILL.md:245`, `ideate/SKILL.md:300`, `preflight/SKILL.md:117`, `team-resolve/SKILL.md`, `team-review/SKILL.md` still emit raw `codex exec` examples. Inside the variant arm the shim catches them; **outside the benchmark (production users running these standalones) the shim is not on PATH** and the wrapper isn't invoked. Round 1 said cut these (off the gate); Round 2 says they're a real production-leak concern. **NOT fixed in iter-0009** — deferred to iter-0010 ("production rollout: wrapper across all skill prompts + ship shim to user installs"). iter-0009 stays benchmark-falsification-scoped.

**Q1 wrapper findings adopted:**
- Heartbeat race window (kill -0 says alive → codex zombies → heartbeat prints after exit) is real but minor; final wrapper line moved to stderr so codex-output view of stdout stays clean.
- Signal forwarding: confirmed safe under process-group TERM (no recursive signal storm).
- `wait $CODEX_PID` under TERM: trap runs, wait returns 143; harness overwrites to 124 anyway.

**Q2 shim findings adopted:**
- `clean_path()` accepted as-is for realistic macOS paths.
- BASH_SOURCE resolution OK in both PATH and `bash /path/shim` invocation modes.
- Superset wrapper chain confirmed safe with shim PATH-strip (verified during smoke test).

**Q3 harness findings adopted:**
- Export path correct in success branch.
- Lint mirror parity gap on `engine-routing.md` — fixed in this round (added to Check 6 loop).

**Q4 gate findings adopted:**
- Negative canary PASS criterion fixed: was "transcript shows `[codex-monitored] start`" (could appear after EOF in piped case → false PASS); now "wrapper exits 64 with pipe-rejection message in transcript" — PROVES live binding because the wrapper EXITS BEFORE codex runs.
- F1 reclassification `invoke_exit==0` adopted as authoritative; `timed_out=false` retained as confirming evidence only (since result.json derivation is buggy per Finding #2).
- Telemetry tightened: "Codex observed" requires wrapper start line in transcript (now stderr) PLUS matching Bash command in `claude-debug.log`; for shim canaries, debug command must contain raw `codex exec` to prove the binding pathway.

**Q5 hidden risk addressed:** Round 2's prediction that the standalone skills would silently leak raw `codex exec` is true and confirmed in the source. iter-0009 declines the fix (scope discipline), iter-0010 inherits it.

**Synthesis decisions for iter-0009 final shape:**
- Wrapper refuses piped stdout (`[ -p /dev/stdout ]` test). Heartbeat + metadata on stderr.
- Lint Check 6 covers `engine-routing.md`.
- Falsification gate negative canary PASS criterion: wrapper exited 64 + pipe-rejection message visible in transcript.
- F1 gate criterion: `invoke_exit==0` (authoritative); `timed_out` advisory only.
- Defer iter-0010 production rollout (standalone skill rewrites + ship shim) and iter-0011 (`timed_out` derivation fix) as queued.

## Actual change

### F1 alone (run-id `20260427T033737Z-1ff7534-iter0009-f1`, 2026-04-27 03:37–03:48Z, ~10 min)

| Signal | Pass criterion | Observed | Status |
|---|---|---|---|
| variant_score | ≥ 85 (smoke) | **98** | ✅ |
| margin | ≥ +5 | **+9** | ✅ |
| files_changed | ≥ 1 | **2** (`bin/cli.js`, `tests/cli.test.js`) | ✅ |
| diff_bytes | > 0 | **2449** | ✅ |
| variant verify | ≥ 0.66 | **0.80 (4/5)** | ✅ |
| timed_out | false (advisory) | **true** | ✗ |
| invoke_exit | 0 (authoritative) | **124 (watchdog)** | ✗ |
| variant elapsed | < 480s | **481s (cap)** | ✗ |
| transcript bytes | > 0 | **0 (empty)** | ✗ |
| **wrapper exercised?** | — | **NO** (Claude path on trivial fixture) | — |

F1 result is a near-exact reproduction of iter-0008 F1 (variant 97 / +7 margin / 480s cap / empty transcript). F1's auto-resolve didn't invoke Codex on this run — entire pipeline ran via Claude tools (15 Bash, 1 Skill, 7 Write, etc., no codex traces in claude-debug.log). Per Codex Round 2 Q5: **"if F1 never invokes Codex, count it as fixture pass only, not iter-0009 evidence"**. F1's own `timed_out=true` reflects a separate non-codex starvation failure mode upstream of iter-0009's scope (queued for a future iteration). F1 outcome does NOT decide iter-0009.

### F6 alone (run-id `20260427T034821Z-1ff7534-iter0009-f6`, 2026-04-27 03:48–03:57Z, ~9 min)

| Signal | iter-0008 F6 | iter-0009 F6 | Status |
|---|---|---|---|
| variant_score | 35 | **95** | ✅ +60 swing |
| bare_score | 94 | 90 | (info) |
| margin | **−59** | **+5** | ✅ recovered |
| files_changed | 0 | **2** | ✅ |
| diff_bytes | 0 | **5188** | ✅ |
| variant verify | 0.33 | **0.83 (5/6)** | ✅ |
| timed_out | true | **false** | ✅ |
| invoke_exit | 124 (watchdog) | **0 (clean)** | ✅ |
| variant elapsed | 1500s (cap) | **290s (clean exit)** | ✅ |
| transcript bytes | 0 (empty) | **1174** | ✅ |
| **wrapper exercised?** | — | **NO** (Claude path; route=strict, risk_keyword: crypto) | partial |

iter-0008 F6 catastrophic collapse **eliminated**. F6 variant produced the doctor-equivalent `checksum` subcommand cleanly via Claude path (BUILD chose `engine: claude` despite `route: strict`). The +60-point score swing on identical fixture, identical harness, identical git HEAD, with iter-0009 changes as the ONLY delta, is strong causal evidence iter-0009 prevents the iter-0008/iter-0006 failure mode. **However**: F6 didn't directly exercise the wrapper — F6 only proves the catastrophic-collapse mechanism is closed; F2 was needed for direct wrapper proof.

### F2 alone (run-id `20260427T035706Z-1ff7534-iter0009-f2`, 2026-04-27 03:57–04:21Z, ~24 min)

| Signal | Pass criterion | Observed | Status |
|---|---|---|---|
| variant_score | ≥ 85 | **93** | ✅ |
| bare_score | (info) | 85 | — |
| margin | ≥ +5 | **+8** | ✅ |
| files_changed | ≥ 1 | **3** | ✅ |
| diff_bytes | > 0 | **12705** | ✅ |
| variant verify | ≥ 0.66 | **1.0 (6/6)** | ✅ |
| timed_out | false (advisory) | **false** | ✅ |
| invoke_exit | 0 (authoritative) | **0** | ✅ |
| variant elapsed | < 1200s | **1126s** | ✅ (clean exit, no cap) |
| transcript bytes | > 0 | **1958** | ✅ |
| disqualifier | none | **true** (silent-catch in `bin/cli.js`) | ✗ but BOTH arms hit (fixture issue) |
| **wrapper exercised?** | — | **YES** | ✅ load-bearing |

**Live wrapper invocation captured during the run** (PID 77116, etime 06:36): the orchestrator emitted exactly the canonical form

> `bash .claude/skills/_shared/codex-monitored.sh -C /private/tmp/bench-...-variant --full-auto -c model_reasoning_effort=xhigh "<long BUILD prompt>"`

— no shim re-route needed, the canonical doc edit landed correctly in the orchestrator's pattern prior. The wrapper-bearing Bash dispatch ran for **399.9 seconds** (per `claude-debug.log` `tool_dispatch_end durationMs=399881`) and exited cleanly. During that ~6.5 min, the outer claude-p byte-watchdog never fired — heartbeat to stderr kept the stream alive (per the wrapper's `printf '[codex-monitored] heartbeat: elapsed=%ds\n' ... >&2` loop). The orchestrator stayed actively reasoning throughout: the transcript notes "orchestrator reverted Codex's out-of-scope `tests/server.test.js` rewrite before commit" — the exact OPPOSITE of iter-0007's "transcript stays empty" failure.

64 total Bash dispatches across the run, all completed cleanly. No watchdog kill. No `Stream idle timeout (byte-level)` event. Full pipeline ran BUILD (codex via wrapper) → BUILD GATE (claude) → EVALUATE (claude) → CRITIC (claude + native security-review) → DOCS (claude).

The disqualifier (silent-catch pattern in `bin/cli.js`) was emitted by the codex BUILD output — but BARE arm hit the SAME pattern (per F2 critical findings). This is a **fixture/spec-language quality issue** (both arms produce silent catches because the spec doesn't preempt them), NOT iter-0009 mechanism failure. iter-0009's job was to prove the wrapper integration; that's confirmed.

### Routing telemetry — 6-element evidence (per Codex Round 1 Q4)

Across F2 (the wrapper-exercising run):

1. **`codex exec` actually observed** — ✅ Via wrapper. Live process tree captured the wrapper invocation.
2. **Invocation shape** — ✅ Foreground via wrapper. No `&` orphan; no `| tail` truncation. Direct invocation.
3. **Waiter / monitor present** — ✅ Wrapper IS the monitor (heartbeat sidecar @ 30s, signal forwarding, stdin closed).
4. **Orchestrator did NOT emit Stop while codex child alive** — ✅ The orchestrator stayed in the BUILD bash dispatch for the full 399.9s; it only proceeded after the dispatch returned cleanly. Confirmed by transcript narrating active reverts of out-of-scope changes.
5. **Transcript non-empty** — ✅ 1958 bytes, full pipeline summary.
6. **Byte-watchdog did NOT fire** — ✅ `grep "Stream idle timeout"` against `claude-debug.log` returns no hits.

Plus implementation evidence: 3 files changed, 12705 diff_bytes, 14/14 tests green.

## Decision

**SHIP iter-0009.**

iter-0009 prevents the iter-0008/iter-0006 catastrophic collapse mechanism (F6 +60-point recovery) AND directly demonstrates the wrapper integration in production (F2 BUILD ran 399.9s through the wrapper without starvation). Both legs of the falsification gate established what they needed to:

- F6 proves the iter-0008 failure mode is closed (causal: same fixture/harness/HEAD, +60 swing under iter-0009 changes alone).
- F2 proves the wrapper integration works (orchestrator emits canonical form, codex BUILD runs ~6.5 min through wrapper, byte-watchdog defeated, full pipeline completes clean).

F1 result is informationally neutral (Claude-only path on this fixture, F1 timed_out=true reflects a separate non-codex F1 starvation that's outside iter-0009's scope and queued as a future iteration).

The F2 disqualifier (silent-catch pattern) is a fixture/spec issue — both arms produced it. Not iter-0009 mechanism. Iteration ships on mechanism, not on this orthogonal code-quality finding.

### Principles check (post-data, finalized)

| # | Principle | Status | Evidence |
|---|---|---|---|
| 1 | No overengineering | ✅ | 6 source files modified + 2 new (wrapper + shim) + 1 iteration doc. No new abstractions, no new flags, no new phases. Cuts 5 inline rewrites that iter-0008 did. ~125 lines of new shell + ~30 lines of harness extension + ~6 lines of skill-prompt edits. |
| 2 | No guesswork | ✅ | Hypothesis named the failure layer (orchestrator-resolves-codex-via-PATH), the binding layer (PATH shim) and contract layer (wrapper) separately. Predicted F2 wrapper-exercise, F6 catastrophic-collapse fix; both materialized. F1 reclassification as "informationally neutral" written before the run. |
| 3 | No workaround | ✅ | Two-layer fix at the layers the freedom exists at: orchestrator emits wrapper directly (canonical doc edit), shim catches raw-codex-exec attempts as safety net (PATH layer), wrapper enforces shape at runtime (`< /dev/null`, no buffering pipe-refusal, heartbeat, signal traps). 7 why-steps in Mechanism. |
| 4 | Worldclass production-ready | ✅ | F2 variant: 6/6 verify, 14/14 tests, +8 margin, clean exit, full pipeline. F6 variant: 5/6 verify, +5 margin, clean exit. No new HIGH on previously-clean fixtures. |
| 5 | Best practice | ✅ | F2's BUILD output had a `catch ... return ...` silent-catch pattern that triggered the disqualifier — but BARE arm produced the same pattern, indicating the issue is fixture-language ambiguity, not iter-0009-introduced. iter-0009 introduced no new `design.unidiomatic-pattern` MEDIUM. |

### What carries forward (queued)

- **iter-0010 (production rollout)**: standalone-skill inline rewrites (`ideate/SKILL.md:245`+`:300`, `preflight/SKILL.md:117`, `team-resolve/SKILL.md`, `team-review/SKILL.md`) and ship the shim to user installs. Round 2 finding #3.
- **iter-0011 (`timed_out` derivation fix)**: `result.json` derives `timed_out` from `elapsed >= timeout` (`run-fixture.sh:477`) instead of the watchdog flag. F1 hits this. Round 2 finding #2.
- **iter-0012 (F1 non-codex starvation)**: F1 reproducibly hits the 480s cap with empty transcript — completely separate from iter-0006/0008 codex shape. Auto-resolve pipeline doesn't naturally exit cleanly after Stop on trivial fixtures. Diagnostic iter needed.
- **iter-0013 (silent-catch fixture spec)**: F2 spec language doesn't preempt `catch { return fallback }` in the BUILD prompt; both arms write it. Tighten fixture spec.
- **Standing queue from HANDOFF**: dual-judge (iter-0014), F6 chronic slowness, sync-gap auto-mirror, etc.

### Lessons

1. **Two-layer enforcement (canonical edit + PATH shim) > prompt-only contract.** Round 1 caught hook fragility, Round 2 caught wrapper pipe-stdout starvation. Both shipped corrections before benchmark. Cumulative cross-check effort: ~25 min wall (R1 + R2 codex calls) saved at least one mid-gate REVERT.
2. **Cross-model GAN earned its keep again.** Codex Round 1 surfaced the hook→shim swap; Codex Round 2 surfaced the pipe-stdout starvation. Both were design-level errors I would NOT have caught in isolation. Continue dual-model practice.
3. **Auto-resolve route selection is stochastic enough to surprise.** F6 chose Claude even though metadata-similar BUILD fixtures historically chose Codex. The wrapper-by-default prompt may have nudged routing toward Claude (lower risk perception). iter-0009 still passes because iter-0009's purpose is to make EITHER route safe, but routing decisions are now part of "things to instrument" for future iters.
4. **`zsh -c source <snapshot>` overrides parent PATH.** Discovered mid-build. Project-scope `$WORK_DIR/.claude/settings.json` env override is the only reliable way to inject PATH into Bash dispatches. Worth memo-ing as a harness-level constraint.
5. **`[ -p /dev/stdout ]` is the portable POSIX test for "stdout is a pipe."** macOS `stat -f "%HT" /dev/fd/1` returned spurious "Fifo File" for redirected files inside bash scripts; `[ -p ... ]` was correct. Use this for any future "refuse if piped" needs.
6. **Disqualifiers from BUILD output are content quality, not mechanism**: F2 disqualifier triggered on both arms. The mechanism (wrapper invocation + clean exit) is independent of the content quality of what codex wrote. Future fixtures should constrain BUILD prompts more tightly to avoid silent-catch patterns.

## Cross-references

- `iterations/0008-narrow-kill-shape-contract.md` — REJECTED. Prompt-level mandate empirically dead.
- `iterations/0007-f6-isolation.md` — F6 isolation that produced the iter-0008 mandate.
- `iterations/0006-foreground-only-codex.md` — universal foreground ban that started this chain.
- `memory/project_skill_guardrails_2026_04_26.md` — G1-G5 (G1, G4, G5 advanced by this iter).
- `memory/project_iter0008_rejected_2026_04_27.md` — iter-0008 outcome + iter-0009 sketch.
- `memory/project_skill_sync_gap_2026_04_26.md` — sync-gap precedent (this iter extended lint mirror parity to close it for `_shared/`).
- `feedback_codex_cross_check.md` — dual-model GAN pattern (validated again — Codex Round 1 caught hook fragility before benchmark).
