# 0003 — Codex MCP race: wall-clock timeout in benchmark harness

**Status**: SHIPPED (infra) / REFUTED (F7-recovery hypothesis)
**Started**: 2026-04-25
**Decided**: 2026-04-25

## Hypothesis

The benchmark harness intermittently hangs when codex CLI fails to initialize its MCP layer (root cause: race against lingering `codex-mcp-server` processes from older Claude Code MCP plugins or prior codex invocations). Wrapping each `codex exec` call in a wall-clock timeout (default 1500s) with explicit BLOCKED verdict on timeout will (a) cap worst-case fixture wall time, (b) surface the failure as a benchmark-data signal rather than silent stall, and (c) let the run-suite move on so the rest of the suite still produces data.

Predicted: F7 re-run (after this lands) completes within 30 min. F7 margin recovers to the F6 pattern (≥+5) once the variant arm gets a clean run with the iteration 0002 spec annotation already in place.

## Mechanism

Why-chain:
1. Why does F7 stall? → codex CLI sleeps with no rollout file and no network connection.
2. Why doesn't it write a rollout file? → It's stuck before session init.
3. Why is it stuck? → codex 5.5's hypothesis B: MCP-server-init race against lingering codex-mcp-server processes (1+ hour old, from a different parent). codex blocks on a stdio/socket handshake to a server that's not actually listening.
4. Why don't we kill the lingering processes? → They're owned by other Claude Code MCP plugins; we can't blanket-kill without breaking those plugins. Per `devlyn:reap` skill design, only conservative whitelist gets reaped.
5. Why does the benchmark just sit there? → No wall-clock timeout. macOS doesn't have GNU `timeout` by default; the run-fixture.sh script logs "no timeout utility on PATH — arm ran without wall clock limit" and proceeds.
6. Root: missing wall-clock guard. Fix at level 6 with a portable shell-only watchdog.

## Predicted change

- F7 variant wall time: timeout-bounded ≤ 1500s (25 min). Currently unbounded.
- F7 margin: variant ≥ +5 once it gets a clean run. (Same prediction as iteration 0002 hypothesis would have made if the run hadn't been contaminated.)
- Other fixtures: no change in normal cases. Cases that would have stalled now show explicit BLOCKED verdict instead of silent hang.
- Suite reliability: full 9-fixture runs complete within their advertised 4-6 hr envelope, every time.

## Diff plan

`benchmark/auto-resolve/scripts/run-fixture.sh`:

1. Delete the now-dead `TIMEOUT_CMD` autodetect block (formerly lines 38–45) — gtimeout/timeout fallback is replaced by a single code path. (Karpathy #2: simplicity first.)
2. Replace the dual-path invocation block with a portable shell-only watchdog:
   - `set -m` + `exec claude ...` so the backgrounded job is its own process group leader (PGID = `claude` PID).
   - Watchdog subshell sleeps `$TIMEOUT`, then if the child is still alive: writes a flag file, sends `kill -TERM -- "-$CHILD_PID"` to the whole group, sleeps 5s, follows with `kill -KILL -- "-$CHILD_PID"`.
   - `wait "$CHILD_PID"` collects the natural exit code under `set +e`.
   - On timeout flag present, normalize `INVOKE_EXIT=124` (GNU `timeout` convention) so the existing `invoke_failure` logic routes the run into BLOCKED.
   - Negative PID kill is what reaps codex CLI + codex-mcp-server descendants — direct `kill $CHILD_PID` would leave grandchildren behind.

**Codex round outcome (cross-check):** codex 5.5 confirmed flag-file logic, `set +e` scoping, and 124-on-timeout normalization were correct, but flagged that killing only the immediate child PID leaks grandchildren (the actual root cause of F7). Accepted: switched to process-group kill via `set -m` + `exec` + negative-PID. Acknowledged minor race at the timeout boundary (natural-exit-during-watchdog-fire reported as timeout) — within acceptable harness semantics.

**Sanity test (pre-suite, on /tmp stub):** four cases — natural exit 0, natural exit 7, hang with grandchild + 2s timeout, transcript on timeout. All four pass; the grandchild marker confirms PG reaping works.

Optional follow-up (NOT in this iteration's diff): wrap each fixture run with a `devlyn:reap` pre-pass to clear stale codex-mcp-server processes from prior sessions. Defer until we measure whether the timeout alone is enough.

## Principles check (finalized)

| # | Principle | Status | Evidence |
|---|---|---|---|
| 1 | No overengineering | ✅ | run-fixture.sh: +25 lines net (deleted TIMEOUT_CMD detect, added watchdog). No new files. |
| 2 | No guesswork | ⚠️ | Hypothesis bundled two outcomes: (a) wall-time cap, (b) F7 recovery to ≥+5. (a) confirmed; (b) refuted. Should have been split. |
| 3 | No workaround | ✅ | Watchdog is root-cause for "unbounded wait" — fixes it. Does NOT pretend to fix the codex MCP race itself; that's queued as iter 0004. |
| 4 | Worldclass production-ready | ✅ | No CRITICAL/HIGH design or security findings introduced. F7's CRITICAL findings stem from variant arm producing zero output (same root cause as before this iteration). |
| 5 | Best practice | ✅ | Idiomatic shell job control: `set -m`, `exec`, negative-PID kill is the standard portable PG-reap pattern. |

## Actual change

**Run**: F7 subset only, run-id `20260425T074946Z-09c8646-iter-0003-f7`. Bare arm + judge + ship-gate downstream all healthy.

| Fixture | Variant | Bare | Margin | Winner | Wall (V/B) | timed_out (V) | invoke_exit (V) |
|---|---|---|---|---|---|---|---|
| F7-out-of-scope-trap | 56 | 98 | **−42** | bare | 1201s / 52s | true | 124 |

**Variant axis breakdown (judge.json)**: variant produced 0 bytes of transcript and 0 files changed — no implementation. CRITICAL findings: "version --format json does not produce JSON", "Required JSON-path test was not added". All trace to the variant arm being hung the entire 1200s budget.

**Watchdog infrastructure**: works as designed. `invoke_exit=124` set correctly, `timed_out=true`, downstream pipeline (judge, compile-report, ship-gate) ran without modification. No grandchildren leaked (verified pre-suite on stub harness).

**Wall time delta**: variant arm bounded at 1201s vs prior unbounded (multi-hour) hang. The full suite would now have a hard worst-case envelope of ≈ 9 × max(metadata.timeout_seconds) instead of unbounded.

## Lessons

1. **The watchdog is good harness infra independent of F7's fate.** Without it, any future fixture that triggers the codex MCP race (or any other source of stall) hangs the suite indefinitely. Cap-and-move-on is correct harness behavior. This part of the change has earned its place.

2. **The F7 recovery prediction was wrong because it conflated two failures.** I assumed "F7 hung" and "F7 failed to implement the spec" had the same fix. Empty variant transcript at T+1200s shows the MCP race is genuinely the dominant blocker — claude never got past pre-session-init to even *start* the spec work. The iteration 0002 spec annotation can't help if the variant arm never runs.

3. **`set -m` + `exec` + `kill -- -PGID` works on macOS Bash 3.2 and reaps grandchildren reliably.** The stub sanity test (transparent grandchild marker) confirmed this before the real run. Codex round flagged the original draft's grandchild leak; without that pushback, the watchdog would have killed only the `claude` parent and left codex-mcp-server processes orphaned — exactly the symptom we were trying to avoid.

4. **Bundling violation:** the iteration template asks for ONE hypothesis. Mine had two implicit outcomes (wall-time cap + F7 score recovery) and the playbook's "no bundling" anti-pattern caught me. Future iterations: if the predicted change has two metrics, split them into two iterations — even when the diff is shared.

5. **Refined hypothesis for iteration 0004:** F7's variant hangs because the codex CLI (invoked by auto-resolve's BUILD/EVAL/CRITIC phases) races against lingering codex-mcp-server processes from prior Claude Code sessions. Pre-arm reaping of stale `codex-mcp-server` processes (via the conservative whitelist pattern from `devlyn:reap`) should give the variant arm a clean MCP startup and unblock the actual implementation work. Predicted outcome: F7 variant transcript becomes non-empty, completion within ≈10–15 min, margin recovers per iteration 0002's prediction (≥+5).

## Decision

**SHIPPED (harness infra) / REFUTED (F7-recovery hypothesis).** Two-faced verdict reflecting the split:

- The run-fixture.sh watchdog change retains. It's strict harness improvement: caps any future stall, makes the full suite have a bounded worst-case wall time, doesn't change any margin upward but stops one source of unbounded loss.
- The "F7 recovers to ≥+5" half of the prediction is rejected. That hypothesis is replaced by iteration 0004 (codex-mcp-server pre-arm reap), which addresses the actual race condition.
- **Full-suite run is DEFERRED.** Running it now would re-confirm F7 timeout under the watchdog at +22 min cost and not change ship-gate (still FAIL). The next full suite happens after iteration 0004 lands.
