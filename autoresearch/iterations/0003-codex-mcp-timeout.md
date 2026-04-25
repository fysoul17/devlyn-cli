# 0003 — Codex MCP race: wall-clock timeout in benchmark harness

**Status**: PROPOSED
**Started**: (not yet)
**Decided**: (not yet)

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

`benchmark/auto-resolve/scripts/run-fixture.sh`: replace the existing `if [ -n "$TIMEOUT_CMD" ] ...` block with a portable shell-only watchdog that uses `sleep N; kill $child` in a backgrounded subshell. The watchdog kills the child on timeout, sets `INVOKE_EXIT=124` (the conventional "timed out" exit code), and run-fixture.sh's existing `invoke_failure` flag will route this into BLOCKED.

Optional: also call `devlyn:reap` (or its conservative-whitelist subset) before each fixture starts, to clear stale codex-mcp-server processes left from prior runs. Worth measuring whether the timeout alone is enough.

Cross-check the timeout pattern with codex before commit. codex 5.5 supplied a draft in the F7 hang diagnostic round; review it for race conditions (e.g., does the watchdog's own kill race against a normally-completing child?).

## Principles check (provisional, finalized after run)

| # | Principle | Status | Evidence |
|---|---|---|---|
| 1 | No overengineering | (provisional ✅) | ~15 lines added to run-fixture.sh. No new files. |
| 2 | No guesswork | ✅ | F7 prediction is direct: timeout caps wall time, clean re-run gets ≥+5 margin. |
| 3 | No workaround | ✅ | Timeout is the real fix for an unbounded wait. Reaping stale MCP servers (if added) is also root-cause. |
| 4 | Worldclass production-ready | (filled after run) | |
| 5 | Best practice | (filled after run) | |

## Actual change

(filled after run)

## Lessons

(filled after run)

## Decision

(filled after run)
